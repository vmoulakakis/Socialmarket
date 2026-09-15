from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import heapq
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import ijson
import requests

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import stream_feed as sf  # noqa: E402

AUDIENCE = "socialmarket-supabase-worker"
GATEWAY = os.getenv(
    "VMDB_WORKER_GATEWAY",
    "https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/github-worker-gateway",
)
CLIENT = "CD104"
DEFAULT_CATEGORIES = "3,67,25,27,29,33,63,147,87,89,99,103,109,117,119"
SOURCE_KEY = "linkwise_cd104"
POLICY_KEY = "linkwise_bootstrap_v1"
COLUMNS = (
    "product_id",
    "product_name",
    "description",
    "category",
    "brand_name",
    "model_name",
    "tracking_url",
    "thumb_url",
    "image_url",
    "in_stock",
    "availability",
    "valid_from",
    "valid_to",
    "on_sale",
    "currency",
    "price",
    "full_price",
    "discount",
    "times_bought",
    "sku",
)
BASE = (
    "https://affiliate.linkwi.se/feeds/1.2/{client}/programs-joined/"
    "columns-{columns}/catinc-{category}/catex-0/proginc-0/progex-0/feed.json"
)

_TOKEN: str | None = None
_TOKEN_AT = 0.0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _oidc_token(force: bool = False) -> str:
    global _TOKEN, _TOKEN_AT
    if _TOKEN and not force and time.time() - _TOKEN_AT < 180:
        return _TOKEN
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not request_token:
        raise RuntimeError("GitHub OIDC environment unavailable; workflow needs id-token: write")
    sep = "&" if "?" in url else "?"
    r = requests.get(
        f"{url}{sep}audience={quote(AUDIENCE)}",
        headers={"Authorization": f"Bearer {request_token}"},
        timeout=30,
    )
    r.raise_for_status()
    _TOKEN = r.json()["value"]
    _TOKEN_AT = time.time()
    return _TOKEN


def db_call(method: str, resource: str, params=None, data=None, prefer: str | None = None):
    payload = {"method": method, "resource": resource}
    if params:
        payload["params"] = params
    if data is not None:
        payload["data"] = data
    if prefer:
        payload["prefer"] = prefer
    for attempt in range(2):
        token = _oidc_token(force=attempt > 0)
        r = requests.post(
            GATEWAY,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=180,
        )
        if r.status_code == 401 and attempt == 0:
            continue
        r.raise_for_status()
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(body)
        return body.get("result")
    raise RuntimeError("OIDC gateway authentication failed")


def feed_url(category: str) -> str:
    return BASE.format(client=CLIENT, columns=",".join(COLUMNS), category=category)


def num(v, default=None):
    if v in (None, ""):
        return default
    try:
        return float(str(v).replace("€", "").replace("%", "").replace(",", ".").strip())
    except Exception:
        return default


def normalize_domain(v: str | None) -> str | None:
    return sf.normalize_domain(v)


def merchant_match(domain: str | None, domain_map: dict[str, dict]) -> dict | None:
    d = normalize_domain(domain)
    if not d:
        return None
    exact = domain_map.get(d)
    if exact:
        return exact
    for canonical, merchant in domain_map.items():
        if d.endswith("." + canonical):
            return merchant
    return None


def commission_for_product(price: float, merchant: dict) -> tuple[float | None, str]:
    # Hard-gate with conservative minimum terms where explicit rates exist.
    choices: list[tuple[float, str]] = []
    flat = num(merchant.get("flat_commission_min_eur"))
    pct = num(merchant.get("percent_commission_min"))
    if flat is not None and flat > 0:
        choices.append((flat, "flat_min"))
    if pct is not None and pct > 0:
        choices.append((price * pct / 100.0, f"percent_min:{pct:g}"))
    if choices:
        return min(choices, key=lambda x: x[0])
    estimate = num(merchant.get("expected_commission_eur"))
    if estimate is not None and estimate > 0:
        return estimate, "merchant_expected_estimate"
    return None, "unknown"


def valid_to_state(value: str | None) -> tuple[bool, float, int | None]:
    if not value:
        return True, 65.0, None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        days = (parsed.date() - dt.datetime.now(dt.timezone.utc).date()).days
        if days < 1:
            return False, 0.0, days
        if days >= 60:
            return True, 100.0, days
        if days >= 30:
            return True, 85.0, days
        if days >= 14:
            return True, 70.0, days
        return True, 50.0, days
    except Exception:
        return False, 0.0, None


def bootstrap_score(n: dict, commission: float, validity_score: float) -> tuple[float, dict]:
    times_bought = max(0.0, num(n.get("times_bought"), 0.0) or 0.0)
    discount = max(0.0, num(n.get("discount_pct"), 0.0) or 0.0)
    commission_score = min(100.0, 20.0 + max(0.0, commission - 10.0) * 3.2)
    demand_score = min(100.0, math.log10(1.0 + times_bought) * 32.0)
    discount_score = min(100.0, discount * 2.0)
    media_score = 100.0 if n.get("image_url") or n.get("thumb_url") else 0.0
    score = (
        commission_score * 0.38
        + demand_score * 0.30
        + discount_score * 0.12
        + validity_score * 0.12
        + media_score * 0.08
    )
    components = {
        "commission": round(commission_score, 3),
        "demand_proxy": round(demand_score, 3),
        "discount": round(discount_score, 3),
        "validity": round(validity_score, 3),
        "media": round(media_score, 3),
    }
    return round(max(0.0, min(100.0, score)), 3), components


def content_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def shortlist_record(raw: dict, merchant: dict, min_commission: float):
    n = sf.normalize(raw)
    product_id = str(n.get("external_product_id") or "").strip()
    if not product_id:
        return None, "missing_product_id"
    if not n.get("product_name"):
        return None, "missing_product_name"
    tracking = n.get("tracking_url")
    if not tracking or "linkwi.se" not in tracking.lower():
        return None, "invalid_tracking"
    if n.get("in_stock") is not True:
        return None, "not_confirmed_in_stock"
    price = num(n.get("price"))
    if price is None or price <= 0:
        return None, "invalid_price"
    target_domain = normalize_domain(n.get("target_domain"))
    if not target_domain:
        return None, "missing_target_domain"
    valid, validity_score, validity_days = valid_to_state(n.get("valid_to"))
    if not valid:
        return None, "expired_or_invalid_validity"
    commission, basis = commission_for_product(price, merchant)
    if commission is None:
        return None, "commission_unknown"
    if commission + 1e-9 < min_commission:
        return None, "commission_under_floor"
    score, components = bootstrap_score(n, commission, validity_score)
    route = sf.linkwise_route(tracking)
    target_url = n.get("target_url")
    compact = {
        "product_id": product_id,
        "product_name": str(n.get("product_name")),
        "model_name": n.get("model_name"),
        "category": n.get("category_raw"),
        "price": round(price, 6),
        "full_price": num(n.get("full_price")),
        "discount_pct": num(n.get("discount_pct")),
        "times_bought": n.get("times_bought"),
        "tracking_url": tracking,
        "target_url": target_url,
        "target_domain": target_domain,
        "linkwise_route": route,
        "image_url": n.get("image_url") or n.get("thumb_url"),
        "valid_from": n.get("valid_from"),
        "valid_to": n.get("valid_to"),
        "validity_days": validity_days,
        "expected_commission_eur": round(commission, 6),
        "commission_basis": basis,
        "bootstrap_score": score,
        "score_components": components,
        "merchant_id": merchant["id"],
        "merchant_name": merchant["merchant_name"],
        "merchant_domain": merchant["canonical_domain"],
        "legacy_merchant_id": merchant["legacy_merchant_id"],
    }
    compact["content_hash"] = content_hash(compact)
    return compact, None


def scan_category(category: str, domain_map: dict[str, dict], min_commission: float, keep_per_merchant: int):
    last_error = None
    for attempt in range(1, 4):
        scanned = 0
        matched = Counter()
        rejected = Counter()
        heaps: dict[str, list] = defaultdict(list)
        serial = 0
        try:
            with requests.get(
                feed_url(category),
                stream=True,
                timeout=(30, 900),
                headers={"User-Agent": "SocialMarketAI/4 product-bootstrap", "Accept-Encoding": "gzip, deflate"},
            ) as r:
                r.raise_for_status()
                r.raw.decode_content = True
                for raw in ijson.items(r.raw, "item"):
                    if not isinstance(raw, dict):
                        continue
                    scanned += 1
                    tracking = raw.get("tracking_url")
                    domain = sf.target_domain(tracking)
                    merchant = merchant_match(domain, domain_map)
                    if not merchant:
                        continue
                    mid = merchant["id"]
                    matched[mid] += 1
                    rec, reason = shortlist_record(raw, merchant, min_commission)
                    if not rec:
                        rejected[(mid, reason)] += 1
                        continue
                    serial += 1
                    item = (float(rec["bootstrap_score"]), serial, rec)
                    h = heaps[mid]
                    if len(h) < keep_per_merchant:
                        heapq.heappush(h, item)
                    elif item[0] > h[0][0]:
                        heapq.heapreplace(h, item)
            return {
                "category": category,
                "scanned": scanned,
                "matched": dict(matched),
                "rejected": {f"{k[0]}::{k[1]}": v for k, v in rejected.items()},
                "rows": {mid: [x[2] for x in h] for mid, h in heaps.items()},
                "attempt": attempt,
            }
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 4)
    raise RuntimeError(f"Linkwise category {category} failed after retries: {last_error}")


def merge_scans(results: list[dict], merchants: list[dict], max_per_merchant: int):
    merged: dict[str, dict[str, dict]] = {m["id"]: {} for m in merchants}
    stats = {m["id"]: {"matched": 0, "rejected": Counter()} for m in merchants}
    total_scanned = 0
    for result in results:
        total_scanned += int(result["scanned"])
        for mid, count in result["matched"].items():
            stats[mid]["matched"] += int(count)
        for key, count in result["rejected"].items():
            mid, reason = key.split("::", 1)
            stats[mid]["rejected"][reason] += int(count)
        for mid, rows in result["rows"].items():
            bucket = merged[mid]
            for row in rows:
                pid = row["product_id"]
                old = bucket.get(pid)
                if old is None or float(row["bootstrap_score"]) > float(old["bootstrap_score"]):
                    bucket[pid] = row
    shortlisted = {}
    for merchant in merchants:
        mid = merchant["id"]
        rows = sorted(
            merged[mid].values(),
            key=lambda x: (float(x["bootstrap_score"]), float(x["expected_commission_eur"])),
            reverse=True,
        )[:max_per_merchant]
        shortlisted[mid] = rows
    return total_scanned, shortlisted, stats


def create_run(merchant: dict, categories: list[str], matched_count: int):
    payload = {
        "merchant_id": merchant["id"],
        "policy_key": POLICY_KEY,
        "status": "running",
        "checkpoint": {
            "source": SOURCE_KEY,
            "feed": "programs-joined",
            "categories": categories,
            "matched_rows": matched_count,
            "publication_gate": "not_evaluated",
        },
        "started_at": now_iso(),
    }
    rows = db_call("POST", "product_discovery_runs", data=payload, prefer="return=representation") or []
    if not rows:
        raise RuntimeError(f"Could not create discovery run for {merchant['merchant_name']}")
    return rows[0]["id"]


def write_merchant(merchant: dict, rows: list[dict], stats: dict, categories: list[str]):
    run_id = create_run(merchant, categories, stats["matched"])
    try:
        db_call(
            "PATCH",
            "commerce_feed_eligible_offers",
            params={"merchant_profile_id": f"eq.{merchant['id']}", "source_key": f"eq.{SOURCE_KEY}"},
            data={"is_active": False},
        )
        db_call(
            "PATCH",
            "merchant_product_candidates",
            params={"merchant_id": f"eq.{merchant['id']}", "admission_status": "eq.pending"},
            data={"admission_status": "hold"},
        )

        offers = []
        candidates = []
        observed = now_iso()
        for row in rows:
            program_key = merchant["legacy_merchant_id"]
            offers.append(
                {
                    "source_key": SOURCE_KEY,
                    "source_product_id": row["product_id"],
                    "program_id": program_key,
                    "program_name": merchant["merchant_name"],
                    "merchant_profile_id": merchant["id"],
                    "merchant_domain": merchant["canonical_domain"],
                    "linkwise_route": row.get("linkwise_route"),
                    "model_name": row.get("model_name"),
                    "product_name": row["product_name"],
                    "category_raw": row.get("category"),
                    "price_eur": row["price"],
                    "expected_commission_eur": row["expected_commission_eur"],
                    "commission_basis": row["commission_basis"],
                    "tracking_url": row["tracking_url"],
                    "image_url": row.get("image_url"),
                    "in_stock": True,
                    "valid_from": row.get("valid_from"),
                    "valid_to": row.get("valid_to"),
                    "discount": row.get("discount_pct"),
                    "times_bought": row.get("times_bought"),
                    "content_hash": row["content_hash"],
                    "raw_snapshot": {
                        "target_url": row.get("target_url"),
                        "target_domain": row.get("target_domain"),
                        "linkwise_route": row.get("linkwise_route"),
                        "score_components": row.get("score_components"),
                        "validity_days": row.get("validity_days"),
                        "program_key_kind": "vmdb_legacy_merchant_id",
                    },
                    "last_seen_at": observed,
                    "is_active": True,
                    "intelligence_status": "pending",
                    "bootstrap_score": row["bootstrap_score"],
                }
            )
            candidates.append(
                {
                    "discovery_run_id": run_id,
                    "merchant_id": merchant["id"],
                    "source_product_id": row["product_id"],
                    "canonical_key": f"{SOURCE_KEY}:{row['product_id']}",
                    "product_name": row["product_name"],
                    "product_url": row.get("target_url"),
                    "tracking_url": row["tracking_url"],
                    "category": row.get("category"),
                    "price_eur": row["price"],
                    "expected_commission_eur": row["expected_commission_eur"],
                    "admission_status": "pending",
                    "evidence": {
                        "stage": "bootstrap",
                        "source": SOURCE_KEY,
                        "joined_feed": True,
                        "tracking_shape_verified": True,
                        "merchant_domain": merchant["canonical_domain"],
                        "linkwise_route": row.get("linkwise_route"),
                        "commission_basis": row["commission_basis"],
                        "bootstrap_score": row["bootstrap_score"],
                        "score_components": row.get("score_components"),
                        "image_url": row.get("image_url"),
                        "discount_pct": row.get("discount_pct"),
                        "times_bought": row.get("times_bought"),
                        "valid_to": row.get("valid_to"),
                        "observed_at": observed,
                        "publish_ready": False,
                    },
                }
            )

        if offers:
            db_call(
                "POST",
                "commerce_feed_eligible_offers",
                params={"on_conflict": "source_key,program_id,source_product_id"},
                data=offers,
                prefer="resolution=merge-duplicates,return=minimal",
            )
            db_call(
                "POST",
                "merchant_product_candidates",
                params={"on_conflict": "merchant_id,canonical_key"},
                data=candidates,
                prefer="resolution=merge-duplicates,return=minimal",
            )

        rejected = max(0, int(stats["matched"]) - len(rows))
        db_call(
            "PATCH",
            "product_discovery_runs",
            params={"id": f"eq.{run_id}"},
            data={
                "status": "succeeded",
                "scanned_count": int(stats["matched"]),
                "candidate_count": len(rows),
                "admitted_count": 0,
                "rejected_count": rejected,
                "checkpoint": {
                    "source": SOURCE_KEY,
                    "feed": "programs-joined",
                    "categories": categories,
                    "matched_rows": int(stats["matched"]),
                    "shortlisted": len(rows),
                    "rejections": dict(stats["rejected"]),
                    "publish_ready": False,
                },
                "completed_at": now_iso(),
            },
        )
        return run_id
    except Exception as exc:
        db_call(
            "PATCH",
            "product_discovery_runs",
            params={"id": f"eq.{run_id}"},
            data={"status": "failed", "error": str(exc)[:1500], "completed_at": now_iso()},
        )
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    ap.add_argument("--categories", default=os.getenv("LINKWISE_CATEGORY_IDS", DEFAULT_CATEGORIES))
    ap.add_argument("--max-per-merchant", type=int, default=int(os.getenv("PRODUCT_MAX_PER_MERCHANT", "30")))
    ap.add_argument("--min-commission", type=float, default=float(os.getenv("PRODUCT_MIN_COMMISSION_EUR", "10")))
    ap.add_argument("--workers", type=int, default=int(os.getenv("LINKWISE_SCAN_WORKERS", "4")))
    args = ap.parse_args()

    if not 1 <= args.max_per_merchant <= 30:
        raise SystemExit("PRODUCT_MAX_PER_MERCHANT must be between 1 and 30")
    if args.min_commission < 10:
        raise SystemExit("PRODUCT_MIN_COMMISSION_EUR cannot be below 10")

    merchants = db_call(
        "GET",
        "merchant_product_bootstrap_eligible",
        params={
            "select": "id,legacy_merchant_id,merchant_name,canonical_domain,flat_commission_min_eur,flat_commission_max_eur,percent_commission_min,percent_commission_max,expected_commission_eur,metadata,program_approved,tracking_verified",
            "order": "merchant_name.asc",
        },
    ) or []
    if not merchants:
        raise SystemExit("No bootstrap-eligible merchants in VMDB")

    domain_map = {normalize_domain(m["canonical_domain"]): m for m in merchants if normalize_domain(m.get("canonical_domain"))}
    categories = [x.strip() for x in args.categories.split(",") if x.strip()]
    workers = max(1, min(6, args.workers))
    keep_per_category = max(args.max_per_merchant * 2, 40)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(scan_category, category, domain_map, args.min_commission, keep_per_category): category
            for category in categories
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({"category_complete": result["category"], "scanned": result["scanned"], "attempt": result["attempt"]}), flush=True)

    if len(results) != len(categories):
        raise RuntimeError("Incomplete Linkwise category scan; refusing partial write")

    total_scanned, shortlisted, stats = merge_scans(results, merchants, args.max_per_merchant)
    summary_merchants = []
    total_shortlisted = 0
    for merchant in merchants:
        mid = merchant["id"]
        rows = shortlisted[mid]
        total_shortlisted += len(rows)
        item = {
            "merchant": merchant["merchant_name"],
            "domain": merchant["canonical_domain"],
            "matched": stats[mid]["matched"],
            "shortlisted": len(rows),
            "top_score": rows[0]["bootstrap_score"] if rows else None,
            "top_expected_commission_eur": rows[0]["expected_commission_eur"] if rows else None,
            "rejections": dict(stats[mid]["rejected"]),
        }
        summary_merchants.append(item)

    result = {
        "ok": True,
        "mode": args.mode,
        "source": "linkwise_programs_joined",
        "policy": POLICY_KEY,
        "paid_ai_used": False,
        "categories": categories,
        "total_feed_rows_scanned": total_scanned,
        "bootstrap_merchants": len(merchants),
        "total_shortlisted": total_shortlisted,
        "max_per_merchant": args.max_per_merchant,
        "min_commission_eur": args.min_commission,
        "publish_ready": False,
        "merchants": summary_merchants,
    }

    if args.mode == "live":
        run_ids = {}
        for merchant in merchants:
            mid = merchant["id"]
            run_ids[mid] = write_merchant(merchant, shortlisted[mid], stats[mid], categories)
        health = db_call("POST", "rpc/vmdb_product_bootstrap_health", data={})
        result["run_ids"] = run_ids
        result["health"] = health
        if isinstance(health, dict) and not health.get("ok", False):
            raise RuntimeError(f"Product bootstrap health failed: {health}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
