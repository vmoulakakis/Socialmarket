#!/usr/bin/env python3
"""Linkwise CD104 streamed delta: scan JSON, INSERT ONLY products absent from VMDB.

The whole upstream feed must be scanned to know which products are unseen unless
the HTTP source explicitly confirms no change (ETag/304). The worker never
rewrites an existing product, price, raw JSON, stock, or tracking URL.

Production is explicit: --commit --vault-source. No automatic import or cron.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

import ijson
import requests
try:
    from .full_feed_vmdb_v1 import (
        parse_price, parse_expiry, program_from_tracking, stock_value,
    )
except ImportError:
    from full_feed_vmdb_v1 import (
        parse_price, parse_expiry, program_from_tracking, stock_value,
    )

FEED_SECRET_NAME = "socialmarket_linkwise_cd104_full_feed_url_v1"
MAX_BATCH_ITEMS = 150
MAX_BATCH_BYTES = 4 * 1024 * 1024
MAX_ROW_BYTES = 4 * 1024 * 1024

def valid_source_url(source: str) -> bool:
    try:
        parsed = urlparse(source)
        return (
            parsed.scheme == "https" and
            parsed.hostname == "affiliate.linkwi.se" and
            parsed.username is None and parsed.password is None and
            parsed.port is None and parsed.query == "" and parsed.fragment == "" and
            parsed.path.startswith("/feeds/1.2/CD104/programs-all/") and
            parsed.path.endswith("/feed.json")
        )
    except ValueError:
        return False

def canonical_key(program_id: str | None, product_id: str) -> str:
    # Same convention as the already imported 3,921 rows: <program>|<product_id>.
    # No title, price, URL, or mutable property in identity. Unknowns are quarantined.
    if not product_id or not product_id.strip() or "|" in product_id:
        raise ValueError("unusable_product_id")
    program = program_id or "unknown"
    return program + "|" + product_id

def transform_delta(p: dict) -> dict:
    if not isinstance(p, dict):
        raise ValueError("feed_item_not_an_object")
    product_id = str(p.get("product_id") or "").strip()
    if not product_id:
        raise ValueError("missing_source_product_id")
    tracking_url = str(p.get("tracking_url") or "").strip()
    program = program_from_tracking(tracking_url)
    key = canonical_key(program, product_id)
    currency = str(p.get("currency") or "").upper().strip()
    price = parse_price(p.get("price"))
    reasons = []
    if not program:
        reasons.append("unknown_linkwise_program")
    if not tracking_url.startswith("https://"):
        reasons.append("missing_tracked_https_link")
    if currency != "EUR":
        reasons.append("currency_unverified")
    if price is None:
        reasons.append("price_invalid")
    if (expiry := parse_expiry(p.get("valid_to"))) is not None:
        if datetime.fromisoformat(expiry) <= datetime.now(timezone.utc):
            reasons.append("offer_expired")
    # URL/price/status remain exactly source-owned. Full raw JSON is kept only
    # when genuinely new; known records are never rewritten.
    raw_json = json.dumps(p, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if len(raw_json.encode("utf-8")) > MAX_ROW_BYTES:
        raise ValueError("oversized_source_product")
    return {
        "record_key": key,
        "source_product_id": product_id,
        "program_id": program or "unknown",
        "product_title": str(p.get("product_name") or p.get("model_name") or "").strip() or None,
        "category_raw": str(p.get("category") or "").strip() or None,
        "currency": currency or None,
        "price": price,
        "tracking_url": tracking_url or None,
        "stock_available": stock_value(p.get("in_stock")),
        "valid_to": expiry,
        "raw_json": p,
        "content_sha256": hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
        "quarantine_reason": ",".join(reasons) or None,
    }

@contextmanager
def connect_database():
    import psycopg
    url = os.getenv("SOCIALMARKET_DB_URL")
    if not url:
        raise RuntimeError("database_secret_not_configured")
    conn = psycopg.connect(url, sslmode="require", connect_timeout=15)
    try:
        yield conn
    finally:
        conn.close()

def get_vault_url(conn) -> str:
    with conn.cursor() as cursor:
        cursor.execute(
            "select decrypted_secret from vault.decrypted_secrets where name=%s limit 1",
            (FEED_SECRET_NAME,),
        )
        row = cursor.fetchone()
    if not row or not row[0] or not valid_source_url(row[0]):
        raise RuntimeError("feed_source_vault_missing_or_invalid")
    return row[0]

def last_source_etag(conn) -> str | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """select checkpoint->>'etag' from sm_intel.feed_runs
               where state='completed' and checkpoint->>'mode'='new_only'
                 and checkpoint->>'etag' is not null
               order by finished_at desc limit 1"""
        )
        row = cursor.fetchone()
    return row[0] if row else None

def run(args) -> dict:
    conn_ctx = connect_database() if args.vault_source or args.commit else None
    conn = conn_ctx.__enter__() if conn_ctx else None
    response = None
    stream = None
    run_id = None
    seen = 0
    invalid = 0
    candidates = 0
    new_count = 0
    skipped = 0
    conflicts = 0
    admitted = 0
    batch: list[dict] = []
    bytes_batch = 0
    prev_etag = None
    try:
        if args.vault_source:
            source = get_vault_url(conn)
            if conn and args.skip_unchanged:
                prev_etag = last_source_etag(conn)
        elif args.feed_url:
            source = args.feed_url
        else:
            source = None
        if source and not valid_source_url(source):
            raise RuntimeError("feed_source_not_allowlisted")

        if args.file:
            stream = args.file.open("rb")
            response_meta: dict[str, str | None] = {"etag": None, "last_modified": None}
        else:
            headers = {
                "Accept-Encoding": "gzip",
                "User-Agent": "SocialMarket-Delta-Scanner/1.0",
            }
            if prev_etag:
                headers["If-None-Match"] = prev_etag
            response = requests.get(
                source, stream=True, headers=headers,
                timeout=(30, 180), allow_redirects=False,
            )
            if response.status_code == 304:
                if not prev_etag:
                    raise RuntimeError("unexpected_not_modified")
                return {"mode": "unchanged_source", "scanned": 0, "new_products": 0}
            if response.status_code != 200:
                raise RuntimeError("feed_source_http_error")
            response_meta = {
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            response.raw.decode_content = True
            stream = response.raw

        if args.commit:
            # No writes unless explicitly selected, with full scan required.
            if args.max_records:
                raise RuntimeError("partial_commit_forbidden")
            with conn.cursor() as cur:
                cur.execute(
                    """insert into sm_intel.feed_runs(source_key,state,checkpoint)
                       values ('linkwise_cd104','running',%s::jsonb) returning id""",
                    (json.dumps({"mode":"new_only","etag":response_meta["etag"],
                                 "last_modified":response_meta["last_modified"]}),),
                )
                run_id = cur.fetchone()[0]
            conn.commit()

        def flush():
            nonlocal bytes_batch,new_count,skipped,conflicts,admitted,candidates
            if not batch:
                return
            candidates += len(batch)
            if conn and args.commit:
                from psycopg.types.json import Jsonb
                with conn.cursor() as cur:
                    cur.execute(
                        "select sm_intel.ingest_new_only_batch(%s,%s::jsonb)",
                        (run_id, Jsonb(batch)),
                    )
                    result = cur.fetchone()[0]
                conn.commit()
                new_count += int(result["new_products"])
                skipped += int(result["existing_or_duplicate"])
                conflicts += int(result["identity_conflicts"])
                admitted += int(result["commercially_admitted"])
            batch.clear()
            bytes_batch = 0

        for record in ijson.items(stream, "item", use_float=True):
            seen += 1
            try:
                item = transform_delta(record)
            except (ValueError, TypeError, OverflowError):
                invalid += 1
                continue
            item_size = len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if item_size > MAX_BATCH_BYTES:
                raise RuntimeError("source_row_too_large_for_safe_batch")
            if batch and (len(batch) >= MAX_BATCH_ITEMS or bytes_batch + item_size > MAX_BATCH_BYTES):
                flush()
            batch.append(item)
            bytes_batch += item_size
            if args.max_records and seen >= args.max_records:
                break

        flush()
        if seen == 0:
            raise RuntimeError("empty_or_invalid_json_feed")
        if args.commit:
            with conn.cursor() as cur:
                cur.execute(
                    """update sm_intel.feed_runs set state='completed',finished_at=now(),
                       checkpoint=checkpoint||%s::jsonb
                       where id=%s and state='running'""",
                    (json.dumps({"read_rows":seen,"invalid_rows":invalid}),run_id),
                )
            conn.commit()
        return {
            "mode":"committed_new_only" if args.commit else "read_only_stream_preview",
            "scanned":seen,"source_rows_with_identity":candidates,
            "invalid_identity_rows":invalid,"new_products":new_count if args.commit else None,
            "already_existing_or_duplicate":skipped if args.commit else None,
            "ambiguous_legacy_merchant_identity":conflicts if args.commit else None,
            "commercially_admitted":admitted if args.commit else None,
            "run_id":str(run_id) if run_id else None,
            "source_etag_present":bool(response_meta["etag"]),
        }
    except Exception as err:
        if conn and run_id:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute(
                    """update sm_intel.feed_runs set state='failed',finished_at=now(),
                      error_code=%s,checkpoint=checkpoint||%s::jsonb
                      where id=%s and state='running'""",
                    (type(err).__name__,json.dumps({"scanned":seen,"invalid":invalid}),run_id),
                )
            conn.commit()
        raise
    finally:
        if response:
            response.close()
        elif stream:
            stream.close()
        if conn_ctx:
            conn_ctx.__exit__(None,None,None)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src=ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file",type=Path)
    src.add_argument("--feed-url",type=str)
    src.add_argument("--vault-source",action="store_true")
    ap.add_argument("--commit",action="store_true",
        help="Only insert new source products. NEVER update existing products.")
    ap.add_argument("--max-records",type=int,default=0)
    ap.add_argument("--skip-unchanged",action="store_true",
        help="Send If-None-Match when last complete delta scan has ETag")
    args=ap.parse_args()
    if args.commit and (args.max_records or not args.vault_source):
        ap.error("commits_require_complete_scan_using_vault_source")
    if args.max_records<0:
        ap.error("max_records_must_be_nonnegative")
    try:
        print(json.dumps({"ok":True,**run(args)},ensure_ascii=False))
    except Exception as ex:
        # Never disclose connection strings, source URLs, or raw source payloads.
        print(json.dumps({"ok":False,"error_type":type(ex).__name__}),file=sys.stderr)
        return 2
    return 0
if __name__=="__main__":
    sys.exit(main())
