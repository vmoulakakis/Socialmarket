#!/usr/bin/env python3
"""VMDB SocialMarket full Linkwise JSON scan -> private sm_intel catalog (v1).

The source feed is streamed, never loaded into RAM. Every record enters the
raw catalog; ONLY verified commission terms with calculated >= EUR10 are
admitted by the database trigger and batch function.

Safe by default: --commit and SOCIALMARKET_DB_URL are required for writes.
No legacy tables, jobs, cron, other VMDB tenants or marketing links are changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import ijson
import requests

BATCH_LIMIT = 250
SOURCE_KEY = "linkwise_cd104"
PROGRAM_PATH = re.compile(r"^/z/([0-9]+)-[0-9]+/CD104(?:/|$)", re.I)
TRUE_VALUES = {"true", "1", "yes", "y", "available", "in stock"}
FALSE_VALUES = {"false", "0", "no", "n", "unavailable", "out of stock"}


def program_from_tracking(url: str | None) -> str | None:
    if not url:
        return None
    try:
        u = urlparse(url)
        if u.scheme != "https" or not (u.hostname or "").lower().endswith(".linkwi.se"):
            return None
        m = PROGRAM_PATH.match(u.path)
        return m.group(1) if m else None
    except ValueError:
        return None


def stock_value(v: object) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().casefold()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return None


def parse_price(v: object) -> str | None:
    try:
        if v is None or str(v).strip() == "":
            return None
        raw = str(v).replace("€", "").replace(" ", "")
        if "." in raw and "," in raw:
            raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(",", ".")
        n = Decimal(raw)
        if not n.is_finite() or n <= 0 or n > Decimal("9999999999"):
            return None
        return format(n.quantize(Decimal("0.0001")), "f")
    except (ValueError, InvalidOperation):
        return None


def parse_expiry(v: object) -> str | None:
    if not v:
        return None
    try:
        s = str(v).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except ValueError:
        return None


def transform(p: dict) -> dict:
    # ijson parses decimal numbers exactly. JSONB retains their values.
    raw_string = json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    sha = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
    product_id = str(p.get("product_id") or p.get("id") or "").strip()
    tracking = str(p.get("tracking_url") or "").strip()
    program = program_from_tracking(tracking)
    sku = str(p.get("sku") or "").strip()
    # Names and prices are deliberately excluded from canonical identity.
    identity = "|".join([program or hashlib.sha256(tracking.encode()).hexdigest()[:16], product_id or sha, sku])
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    currency = str(p.get("currency") or "").strip().upper()
    price = parse_price(p.get("price"))
    reasons = []
    if not product_id:
        reasons.append("product_id_missing")
    if not program:
        reasons.append("program_unresolved_from_linkwise_tracking")
    if not tracking.startswith("https://"):
        reasons.append("tracking_https_missing")
    if currency != "EUR":
        reasons.append("non_eur_or_unknown_currency")
    if price is None:
        reasons.append("invalid_price")
    return {
        "record_key": key,
        "source_product_id": product_id or None,
        "program_id": program,
        "product_title": str(p.get("product_name") or p.get("model_name") or "").strip() or None,
        "category_raw": str(p.get("category") or "").strip() or None,
        "currency": currency or None,
        "price": price,
        "tracking_url": tracking or None,
        "stock_available": stock_value(p.get("in_stock")),
        "valid_to": parse_expiry(p.get("valid_to")),
        "raw_json": p,
        "content_sha256": sha,
        "quarantine_reason": ",".join(reasons) if reasons else None,
    }


def rows_from_stream(stream):
    for row in ijson.items(stream, "item"):
        if not isinstance(row, dict):
            raise ValueError("feed_items_must_be_json_objects")
        yield row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="Offline local JSON array, safe for fixtures")
    source.add_argument("--feed-url", help="HTTPS affiliate.linkwi.se /feed.json endpoint")
    parser.add_argument("--commit", action="store_true", help="Explicitly enable writes into private VMDB")
    parser.add_argument("--max-records", type=int, default=0, help="Bounded diagnostic; never marks complete")
    args = parser.parse_args()

    if args.commit and args.max_records:
        raise SystemExit("refusing_partial_commit: use dry-run for --max-records")
    if args.commit and not os.environ.get("SOCIALMARKET_DB_URL"):
        raise SystemExit("missing_SOCIALMARKET_DB_URL")
    if args.feed_url:
        url = urlparse(args.feed_url)
        if url.scheme != "https" or url.hostname != "affiliate.linkwi.se" or not url.path.endswith("/feed.json"):
            raise SystemExit("feed_url_not_allowlisted")

    conn = None
    run_id = None
    if args.commit:
        import psycopg
        from psycopg.types.json import Jsonb
        # PostgreSQL role must have access to sm_intel. No credentials printed.
        conn = psycopg.connect(os.environ["SOCIALMARKET_DB_URL"], sslmode="require")
        with conn.cursor() as cur:
            cur.execute("""insert into sm_intel.feed_runs(source_key,state,checkpoint)
                           values (%s,'running','{}'::jsonb) returning id""", (SOURCE_KEY,))
            run_id = cur.fetchone()[0]
        conn.commit()

    seen = 0
    quarantine = 0
    batch: dict[str, dict] = {}
    response = None
    try:
        if args.file:
            stream = args.file.open("rb")
        else:
            response = requests.get(args.feed_url, stream=True, timeout=(30, 180),
                                    headers={"User-Agent": "SocialMarketAI-FullCatalog/1.0"})
            response.raise_for_status()
            if urlparse(response.url).hostname != "affiliate.linkwi.se":
                raise RuntimeError("feed_redirect_host_untrusted")
            response.raw.decode_content = True
            stream = response.raw
        try:
            for record in rows_from_stream(stream):
                seen += 1
                item = transform(record)
                if item["quarantine_reason"]:
                    quarantine += 1
                batch[item["record_key"]] = item
                if len(batch) >= BATCH_LIMIT:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("select sm_intel.ingest_full_feed_batch(%s,%s::jsonb)",
                                        (run_id, Jsonb(list(batch.values()))))
                        conn.commit()
                    batch.clear()
                if args.max_records and seen >= args.max_records:
                    break
            if batch and conn:
                with conn.cursor() as cur:
                    cur.execute("select sm_intel.ingest_full_feed_batch(%s,%s::jsonb)",
                                (run_id, Jsonb(list(batch.values()))))
                conn.commit()
            if seen == 0:
                raise RuntimeError("empty_feed_refusing_completion")
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""update sm_intel.feed_runs set state='completed',
                                     finished_at=now(),checkpoint=jsonb_build_object('records',%s,'mode','full')
                                     where id=%s and state='running'""", (seen, run_id))
                conn.commit()
        finally:
            if args.file:
                stream.close()
        print(json.dumps({"ok": True, "mode": "committed" if args.commit else "dry_run",
                          "run_id": str(run_id) if run_id else None,
                          "scanned": seen, "quarantined": quarantine,
                          "commercial_gate": "verified_source_terms_calculated_commission_gte_10_eur"},
                         ensure_ascii=False))
        return 0
    except Exception as ex:
        if conn and run_id:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute("""update sm_intel.feed_runs set state='failed',finished_at=now(),
                                  error_code=%s,checkpoint=jsonb_build_object('records',%s)
                               where id=%s and state='running'""",
                            (type(ex).__name__,seen,run_id))
            conn.commit()
        print(json.dumps({"ok": False, "error_type": type(ex).__name__, "scanned": seen}), file=sys.stderr)
        return 1
    finally:
        if response is not None:
            response.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
