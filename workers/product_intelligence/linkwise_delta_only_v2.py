#!/usr/bin/env python3
"""Full Linkwise CD104 streaming scan; import ONLY new, verified >=EUR10 offers.

SAFE DEFAULT: dry-run; never fetches feed unless explicitly executed.
- O(1) memory w.r.t total rows: ijson stream + bounded 100-record batches.
- Exactly-once DB effects through source identity + insert-only SQL + replayed batch offsets.
- No changes to existing products, prices, JSON, stock, original timestamps or URLs.
- Resume an interrupted run ONLY with the same strong source ETag; otherwise restart
  as a new full scan, safely skipping previously inserted identities.
- Program IDs resolved only from genuine go.linkwi.se tracking URLs in the feed.
  Do not trust the uploaded 315-site deeplink spreadsheet: most rows use the wrong
  shared program ID 12858.
- Any unknown/expired/unverified commission terms: no product admission.
- No embeddings, agents, model tokens or scraping required in this worker.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import ijson
import requests

try:
    from .full_feed_vmdb_v1 import parse_price, parse_expiry, stock_value, program_from_tracking
except ImportError:
    from full_feed_vmdb_v1 import parse_price, parse_expiry, stock_value, program_from_tracking

SOURCE = "linkwise_cd104"
FEED_SECRET_NAME = "socialmarket_linkwise_cd104_full_feed_url_v1"
ROOTS = {"item", "products.item", "data.item"}
DEFAULT_BATCH = 100
MAX_RECORD_BYTES = 128 * 1024


def check_feed_url(raw: str) -> str:
    p = urlparse(raw)
    if (p.scheme != "https" or p.hostname != "affiliate.linkwi.se" or
        p.username or p.password or p.port or p.query or p.fragment or
        not p.path.startswith("/feeds/1.2/CD104/programs-all/columns-") or
        "/catinc-" not in p.path or "/catex-" not in p.path or
        "/proginc-0/progex-0/" not in p.path or
        not p.path.endswith("/feed.json")):
        raise ValueError("wrong_or_unapproved_linkwise_feed_url")
    return raw


def fingerprint(headers: dict, url: str) -> tuple[str | None, bool]:
    # A strong ETag is sufficient for exact offset replay of the same source snapshot.
    tag = (headers.get("ETag") or "").strip()
    lm = (headers.get("Last-Modified") or "").strip()
    length = (headers.get("Content-Length") or "").strip()
    strong = bool(tag and not tag.startswith("W/"))
    if not (tag or lm or length):
        return None, False
    key = json.dumps([urlparse(url).path, tag, lm, length],separators=(",",":"))
    return hashlib.sha256(key.encode()).hexdigest(), strong


def product_to_row(record: dict, max_bytes: int = MAX_RECORD_BYTES) -> tuple[dict, bool]:
    raw = json.dumps(record, ensure_ascii=False, separators=(",",":"), sort_keys=True,
                     default=str, allow_nan=False)
    too_large = len(raw.encode("utf-8")) > max_bytes
    if too_large:
        # Hard memory/DB size bound: never store truncated source claims as a product.
        # Identity metadata-only placeholder is rejected at the DB hard gate.
        slim = {"oversize_omitted":True}
    else:
        slim = record
    source_product_id = str(record.get("product_id") or "").strip()
    tracking = str(record.get("tracking_url") or "").strip()
    program = program_from_tracking(tracking)
    key = (program or "unknown") + "|" + (source_product_id or hashlib.sha256(raw.encode()).hexdigest()[:20])
    currency = str(record.get("currency") or "").strip().upper()
    price = parse_price(record.get("price"))
    errors = []
    if not source_product_id:
        errors.append("product_id_missing")
    if not program:
        errors.append("official_linkwise_program_id_missing")
    if currency != "EUR":
        errors.append("non_eur_currency")
    if price is None:
        errors.append("invalid_price")
    if too_large:
        errors.append("oversize_omitted")
    return {
        "record_key":key,"source_product_id":source_product_id or None,
        "program_id":program,"product_title":str(record.get("product_name") or record.get("model_name") or "")[:500],
        "category_raw":str(record.get("category") or "")[:350],
        "currency":currency or None,"price":price,
        "tracking_url":tracking or None,"stock_available":stock_value(record.get("in_stock")),
        "valid_to":parse_expiry(record.get("valid_to")),"raw_json":slim,
        "content_sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "quarantine_reason":",".join(errors) if errors else None,
    },too_large


def stream_records(stream, root: str):
    if root not in ROOTS:
        raise ValueError("unsupported_json_root")
    for item in ijson.items(stream,root,use_float=True):
        if not isinstance(item,dict):
            raise ValueError("product_item_not_json_object")
        yield item


def last_completed_etag(conn):
    with conn.cursor() as cur:
        cur.execute("""select checkpoint->>'etag' from sm_intel.feed_runs
           where state='completed' and checkpoint->>'mode'='delta_new_only'
           and checkpoint->>'etag' is not null order by finished_at desc limit 1""")
        found=cur.fetchone()
    return found[0] if found else None


def source_stream(args, previous_etag=None):
    if args.file:
        f = args.file.open("rb")
        return f,None,None,False,None
    url = check_feed_url(args.feed_url or os.environ.get("LINKWISE_FULL_FEED_URL",""))
    headers={"User-Agent":"SocialMarketAI-DeltaImport/2.0","Accept-Encoding":"gzip, deflate"}
    if previous_etag:
        headers["If-None-Match"]=previous_etag
    response = requests.get(url,stream=True,timeout=(35,180),headers=headers,allow_redirects=False)
    if response.status_code==304 and previous_etag:
        response.close()
        return None,None,None,False,None
    response.raise_for_status()
    # Redirect is refused; no code should accidentally expose feed identity.
    if response.url != url:
        response.close()
        raise ValueError("redirect_or_source_url_changed")
    response.raw.decode_content=True
    fp,strong = fingerprint(response.headers,url)
    return response.raw,response,fp,strong,response.headers.get("ETag")


def execute_delta_batch(conn,run_id,offset,rows,fp):
    from psycopg.types.json import Jsonb
    with conn.cursor() as cur:
        cur.execute("select sm_intel.ingest_new_only_batch(%s,%s,%s::jsonb,%s)",
                    (run_id,offset,Jsonb(rows),fp))
        result=cur.fetchone()[0]
    conn.commit()
    return result


def start_run(conn,fp,args,strong):
    if args.resume_run_id:
        if not strong or not fp:
            raise RuntimeError("resume_requires_strong_etag")
        with conn.cursor() as cur:
            cur.execute("""select scanned,state,source_fingerprint
                           from sm_intel.feed_runs
                           where id=%s and source_key=%s for update""",
                        (args.resume_run_id,SOURCE))
            row=cur.fetchone()
            if not row or row[1] not in ("failed","partial") or row[2]!=fp:
                raise RuntimeError("unsafe_resume_snapshot_or_state")
            cur.execute("""update sm_intel.feed_runs
                set state='running',error_code=null,finished_at=null where id=%s""",
                        (args.resume_run_id,))
        conn.commit()
        return uuid.UUID(args.resume_run_id),int(row[0])
    with conn.cursor() as cur:
        cur.execute("""insert into sm_intel.feed_runs
             (source_key,state,source_fingerprint,checkpoint)
             values (%s,'running',%s,'{"mode":"delta_new_only","offset":0}'::jsonb)
             returning id""",(SOURCE,fp))
        run_id=cur.fetchone()[0]
    conn.commit()
    return run_id,0


def verify_preflight(conn):
    with conn.cursor() as cur:
        cur.execute("""select count(*) from sm_intel.commission_terms
           where review_status='verified' and publisher_key='CD104'
             and currency='EUR' and effective_from<=now()
             and (effective_until>now() or
                  (effective_until is null and evidence->>'explicit_open_ended_verified'='true'))""")
        number=cur.fetchone()[0]
    if number<1:
        raise RuntimeError("zero_verified_current_commission_terms_no_safe_import")


def run(args):
    if args.batch_size<1 or args.batch_size>250:
        raise ValueError("batch_size_must_be_1_to_250")
    if args.max_records and args.commit:
        raise ValueError("bounded_preview_cannot_commit")
    if args.resume_run_id and not args.commit:
        raise ValueError("resume_needs_commit")
    if args.commit and not args.vault_source:
        raise RuntimeError("production_import_requires_vault_source")
    if args.commit and not os.environ.get("SOCIALMARKET_DB_URL"):
        raise RuntimeError("database_secret_not_configured")
    if args.file and args.commit and os.environ.get("SOCIALMARKET_ALLOW_LOCAL_FILE_COMMIT")!="true":
        raise RuntimeError("local_file_commit_disabled_by_default")
    conn=None
    run_id=None
    etag=None
    raw_stream=None
    response=None
    scanned=0
    inserted=0
    existing=0
    unqualified=0
    unresolved=0
    oversized=0
    try:
        if args.commit or args.vault_source:
            import psycopg
            conn=psycopg.connect(os.environ["SOCIALMARKET_DB_URL"],sslmode="require",
                                 connect_timeout=10)
            if args.commit: verify_preflight(conn)
        if args.vault_source:
            with conn.cursor() as cur:
                cur.execute("select decrypted_secret from vault.decrypted_secrets where name=%s limit 1",
                            (FEED_SECRET_NAME,))
                row=cur.fetchone()
            if not row or not row[0]:
                raise RuntimeError("approved_vault_feed_secret_missing")
            args.feed_url=check_feed_url(row[0])
        prev_etag=last_completed_etag(conn) if args.skip_unchanged and conn else None
        raw_stream,response,fp,strong,etag = source_stream(args,prev_etag)
        if raw_stream is None:
            print(json.dumps({"ok":True,"mode":"unchanged_etag","scanned":0,"new_inserted":0,
                              "existing_rows_updated":0}))
            return 0
        if conn:
            run_id,skip=start_run(conn,fp,args,strong)
        else:
            skip=0
        iterator=stream_records(raw_stream,args.root)
        # Offset resumes stream from beginning with O(1) memory; no HTTP range guesses.
        for _ in itertools.islice(iterator,skip):
            scanned+=1
        if scanned!=skip:
            raise RuntimeError("feed_shorter_than_verified_resume_offset")
        rows=[]
        batch_start=skip
        for product in iterator:
            scanned+=1
            row,is_oversize=product_to_row(product,args.max_record_bytes)
            oversized+=int(is_oversize)
            rows.append(row)
            if len(rows)>=args.batch_size:
                if conn:
                    d=execute_delta_batch(conn,run_id,batch_start,rows,fp)
                    inserted+=d["new"]
                    existing+=d["existing"]
                    unqualified+=d["unqualified"]
                    unresolved+=d["unresolved"]
                batch_start=scanned
                rows.clear()
            if args.max_records and scanned>=args.max_records:
                break
        if rows and conn:
            d=execute_delta_batch(conn,run_id,batch_start,rows,fp)
            inserted+=d["new"]
            existing+=d["existing"]
            unqualified+=d["unqualified"]
            unresolved+=d["unresolved"]
        if scanned==0:
            raise RuntimeError("empty_feed_no_commit")
        if conn:
            with conn.cursor() as cur:
                cur.execute("""update sm_intel.feed_runs
                    set state='completed',finished_at=now(),
                    checkpoint=jsonb_build_object('offset',%s,'mode','delta_new_only',
                                    'source_fingerprint',%s,'etag',%s,'source_complete',true)
                    where id=%s and state='running' and scanned=%s""",
                    (scanned,fp,etag,run_id,scanned))
                if cur.rowcount!=1:
                    raise RuntimeError("feed_completion_checkpoint_does_not_match")
            conn.commit()
        summary={"ok":True,"mode":"delta_commit" if conn else "preview_only",
            "scanned":scanned,"new_inserted":inserted if conn else None,
            "existing_skipped":existing if conn else None,
            "unqualified_skipped":unqualified if conn else None,
            "unresolved_program_skipped":unresolved if conn else None,
            "oversize_skipped":oversized,"run_id":str(run_id) if run_id else None,
            "verified_min_commission_eur":10,
            "existing_rows_updated":0,"source_fingerprint_available":bool(fp),
            "source_resume_safe":strong}
        print(json.dumps(summary,ensure_ascii=False))
        return 0
    except Exception as error:
        if conn and run_id:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute("""update sm_intel.feed_runs
                     set state='failed',finished_at=now(),error_code=%s
                     where id=%s and state='running'""",
                    (type(error).__name__,run_id))
            conn.commit()
        print(json.dumps({"ok":False,"error_type":type(error).__name__,
             "scanned":scanned,"details":"No existing product or offer was overwritten."}),
            file=sys.stderr)
        return 1
    finally:
        if response is not None:
            response.close()
        elif raw_stream is not None:
            raw_stream.close()
        if conn is not None:
            conn.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_mutually_exclusive_group()
    s.add_argument("--file",type=Path)
    s.add_argument("--feed-url")
    s.add_argument("--vault-source",action="store_true")
    p.add_argument("--commit",action="store_true")
    p.add_argument("--skip-unchanged",action="store_true")
    p.add_argument("--resume-run-id")
    p.add_argument("--batch-size",type=int,default=DEFAULT_BATCH)
    p.add_argument("--max-records",type=int,default=0)
    p.add_argument("--root",choices=sorted(ROOTS),default="item")
    p.add_argument("--max-record-bytes",type=int,default=MAX_RECORD_BYTES)
    args=p.parse_args()
    if not args.file and not args.vault_source and not (args.feed_url or os.getenv("LINKWISE_FULL_FEED_URL")):
        p.error("feed_source_required")
    if args.vault_source and not os.environ.get("SOCIALMARKET_DB_URL"):
        p.error("vault_source_requires_database_secret")
    if not 4096<=args.max_record_bytes<=1024*1024:
        p.error("max_record_bytes_out_of_range")
    return run(args)

if __name__=="__main__":
    raise SystemExit(main())
