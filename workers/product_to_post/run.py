from __future__ import annotations

import argparse
import json
import os
import socket
import traceback
from datetime import datetime, timezone
from typing import Any

from .calendar import build_calendar
from .common import SupabaseREST, first_row
from .enrich import enrich_public_landing
from .marketing import MarketingBrain
from .render import SIZES, render_creative


PRODUCT_FIELDS = "id,product_name,description,category_raw,brand_name,merchant_name,program_name,tracking_url,thumb_url,image_url,availability,currency,price,full_price,discount_pct,purchase_friction,valid_to,is_active,hard_gate_pass,market_eligible,is_preferred_offer,merchant_trust_score,validity_days_remaining"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def opportunity_for(db: SupabaseREST, product_id: str) -> dict[str, Any] | None:
    rows = db.get("opportunity_scores", f"product_id=eq.{product_id}&select=*&order=calculated_at.desc&limit=1")
    return first_row(rows)


def product_by_id(db: SupabaseREST, product_id: str) -> dict[str, Any] | None:
    rows = db.get("products", f"id=eq.{product_id}&select={PRODUCT_FIELDS}&limit=1")
    return first_row(rows)


def eligible(product: dict[str, Any] | None) -> bool:
    if not product:
        return False
    if product.get("is_active") is False or product.get("hard_gate_pass") is False:
        return False
    if product.get("market_eligible") is False or product.get("is_preferred_offer") is False:
        return False
    return bool(product.get("tracking_url") and (product.get("image_url") or product.get("thumb_url")))


def select_products(db: SupabaseREST, run: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]]:
    if run.get("mode") == "manual":
        pid = run.get("product_id")
        if not pid:
            raise RuntimeError("manual_run_product_id_missing")
        product = product_by_id(db, pid)
        if not eligible(product):
            raise RuntimeError("manual_product_failed_hard_gate_or_missing_tracking_media")
        opp = opportunity_for(db, pid)
        reason = {"mode":"manual","higo":(opp or {}).get("higo_adjusted"),"confidence":(opp or {}).get("confidence")}
        return [(product, opp, reason)]

    limit = max(1, min(int(run.get("requested_count") or 1) * 6, 300))
    rows = db.get(
        "opportunity_scores",
        f"select=*,products({PRODUCT_FIELDS})&decision=neq.DROP&order=higo_adjusted.desc,confidence.desc&limit={limit}",
    ) or []
    selected = []
    seen = set()
    for opp in rows:
        product = opp.get("products")
        if isinstance(product, list):
            product = product[0] if product else None
        if not eligible(product):
            continue
        pid = product["id"]
        if pid in seen:
            continue
        if opp.get("competition_kill") is True:
            continue
        confidence = float(opp.get("confidence") or 0)
        higo = float(opp.get("higo_adjusted") or 0)
        if confidence < 0.55 or higo < 70:
            continue
        seen.add(pid)
        selected.append((product, opp, {
            "mode":"auto","higo":higo,"confidence":confidence,
            "demand":opp.get("demand_score"),"forecast":opp.get("forecast_momentum_score"),
            "offer":opp.get("offer_score"),"merchant_trust":product.get("merchant_trust_score"),
        }))
        if len(selected) >= int(run.get("requested_count") or 1):
            break
    if not selected:
        raise RuntimeError("auto_selection_returned_no_eligible_products")
    return selected


def upsert_item(db: SupabaseREST, run_id: str, product: dict[str, Any], rank: int, reason: dict[str, Any]) -> dict[str, Any]:
    rows = db.post("product_to_post_items?on_conflict=run_id,product_id", {
        "run_id":run_id,"product_id":product["id"],"selection_rank":rank,"selection_reason":reason,"status":"selected","updated_at":now_iso()
    }, upsert=True)
    return first_row(rows) or first_row(db.get("product_to_post_items",f"run_id=eq.{run_id}&product_id=eq.{product['id']}&select=*&limit=1"))


def persist_evidence(db: SupabaseREST, item_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    rows = db.post("product_enrichment_evidence", {
        "item_id":item_id,"source_url":evidence["source_url"],"resolved_url":evidence.get("resolved_url"),
        "http_status":evidence.get("http_status"),"facts":evidence.get("facts") or {},"source_meta":evidence.get("source_meta") or {},
        "content_hash":evidence.get("content_hash"),
    })
    return first_row(rows) or {}


def persist_angles(db: SupabaseREST, item_id: str, angles: list[dict[str, Any]], telemetry: dict[str, Any]) -> list[dict[str, Any]]:
    persisted = []
    ordered = sorted(angles, key=lambda x: float(x.get("score") or 0), reverse=True)
    for idx, a in enumerate(ordered):
        key = str(a.get("angle_key") or f"angle-{idx+1}")[:80]
        rows = db.post("marketing_angles?on_conflict=item_id,angle_key", {
            "item_id":item_id,"angle_key":key,"framework":str(a.get("framework") or "evidence")[:80],
            "persona":a.get("persona"),"hook":str(a.get("hook") or "")[:1000],"promise":a.get("promise"),
            "proof_points":a.get("proof_points") or [],"objections":a.get("objections") or [],"cta":a.get("cta"),
            "score":max(0,min(100,float(a.get("score") or 0))),"rationale":a.get("rationale"),"selected":idx < 2,
            "model_route":telemetry,"prompt_version":"p2p-v1",
        }, upsert=True)
        row = first_row(rows)
        if row:
            persisted.append(row)
    return persisted


def persist_variants(db: SupabaseREST, item_id: str, angle_id: str, variants: list[dict[str, Any]], telemetry: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    counters: dict[str,int] = {}
    for idx, v in enumerate(variants):
        platform = str(v.get("platform") or "").lower()
        if platform not in {"facebook","instagram","tiktok","linkedin"}:
            continue
        counters[platform] = counters.get(platform,0)+1
        key = str(v.get("variant_key") or f"{platform}-{counters[platform]}")[:100]
        tags = v.get("hashtags") or []
        if isinstance(tags,str):
            tags = [x for x in tags.split() if x.startswith("#")]
        rows = db.post("social_post_variants?on_conflict=item_id,platform,variant_key", {
            "item_id":item_id,"angle_id":angle_id,"platform":platform,"variant_key":key,
            "headline":str(v.get("headline") or "")[:500],"hook":str(v.get("hook") or "")[:700],
            "caption":str(v.get("caption") or "")[:5000],"hashtags":tags[:20],"cta":v.get("cta"),
            "disclosure":v.get("disclosure") or "Affiliate / διαφημιστικό περιεχόμενο",
            "media_format":v.get("media_format"),"creative_direction":v.get("creative_direction") or {},
            "selected":counters[platform] <= 4,"status":"needs_creative","model_route":telemetry,
        }, upsert=True)
        row = first_row(rows)
        if row:
            out.append(row)
    return out


def render_platform_assets(db: SupabaseREST, run: dict[str,Any], item: dict[str,Any], product: dict[str,Any], opp: dict[str,Any] | None, variants: list[dict[str,Any]]) -> dict[str,str]:
    assets: dict[str,str] = {}
    for platform in run.get("platforms") or []:
        candidate = next((v for v in variants if v["platform"] == platform), None)
        if not candidate:
            continue
        job = first_row(db.post("creative_jobs", {
            "product_id":product["id"],"opportunity_score_id":(opp or {}).get("id"),"status":"rendering",
            "concept_type":"product-to-post-v1","platform_target":platform,"tracking_url":product["tracking_url"],
            "brief":{"variant_id":candidate["id"],"headline":candidate.get("headline"),"creative_direction":candidate.get("creative_direction") or {},"run_id":run["id"]},
            "started_at":now_iso(),
        }))
        if not job:
            continue
        try:
            image = render_creative(product,candidate,product["tracking_url"])
            storage_path = f"product-to-post/{run['id']}/{item['id']}/{platform}-{candidate['id']}.png"
            db.upload("creatives",storage_path,image,"image/png")
            w,h = SIZES.get(platform,(1080,1350))
            asset = first_row(db.post("creative_assets", {
                "creative_job_id":job["id"],"asset_type":"social_post","storage_path":storage_path,"width":w,"height":h,
                "copy":{"variant_id":candidate["id"],"headline":candidate.get("headline"),"caption":candidate.get("caption")},
                "qr_payload":None if platform=="tiktok" else product["tracking_url"],"quality_score":82,
                "visual_audit":{"status":"needs_review","renderer":"product-to-post-v1","product_fidelity":"source-image-preserved","qr_checked":platform!="tiktok"},
            }))
            if asset:
                assets[platform] = asset["id"]
            db.patch("creative_jobs",f"id=eq.{job['id']}",{"status":"completed","finished_at":now_iso()})
        except Exception as exc:
            db.patch("creative_jobs",f"id=eq.{job['id']}",{"status":"failed","finished_at":now_iso(),"brief":{**(job.get("brief") or {}),"render_error":str(exc)[:500]}})
    return assets


def process_item(db: SupabaseREST, brain: MarketingBrain, run: dict[str,Any], product: dict[str,Any], opp: dict[str,Any] | None, reason: dict[str,Any], rank: int) -> dict[str,Any]:
    item = upsert_item(db,run["id"],product,rank,reason)
    if not item:
        raise RuntimeError("failed_to_create_run_item")
    evidence = enrich_public_landing(product["tracking_url"],product)
    persist_evidence(db,item["id"],evidence)
    db.patch("product_to_post_items",f"id=eq.{item['id']}",{"status":"enriched","updated_at":now_iso()})

    angles_raw, angle_route = brain.angles(product,evidence,opp)
    angles = persist_angles(db,item["id"],angles_raw,angle_route)
    if not angles:
        raise RuntimeError("no_marketing_angles_generated")
    db.patch("product_to_post_items",f"id=eq.{item['id']}",{"status":"strategized","updated_at":now_iso()})

    variants: list[dict[str,Any]] = []
    selected_angles = [a for a in angles if a.get("selected")][:2] or angles[:1]
    route_log = []
    for angle in selected_angles:
        raw, route = brain.variants(product,evidence,angle,run.get("platforms") or [])
        route_log.append(route)
        variants.extend(persist_variants(db,item["id"],angle["id"],raw,route))
    if not variants:
        raise RuntimeError("no_social_variants_generated")

    assets = render_platform_assets(db,run,item,product,opp,variants)
    for v in variants:
        db.patch("social_post_variants",f"id=eq.{v['id']}",{"status":"needs_approval"})
    db.patch("product_to_post_items",f"id=eq.{item['id']}",{"status":"rendered","updated_at":now_iso()})

    slots = build_calendar(variants,int(run.get("horizon_days") or 30))
    for slot in slots:
        asset_id = assets.get(slot["platform"])
        db.post("social_content_calendar?on_conflict=run_id,variant_id,scheduled_at", {
            "run_id":run["id"],"item_id":item["id"],"variant_id":slot["variant_id"],"platform":slot["platform"],
            "scheduled_at":slot["scheduled_at"],"objective":slot["objective"],"status":"needs_approval",
            "tracking_url":product["tracking_url"],"creative_asset_id":asset_id,"metadata":slot["metadata"],
        }, upsert=True)
    db.patch("product_to_post_items",f"id=eq.{item['id']}",{"status":"planned","updated_at":now_iso()})
    return {"product_id":product["id"],"product_name":product.get("product_name"),"angles":len(angles),"variants":len(variants),"assets":len(assets),"calendar_slots":len(slots),"model_routes":[angle_route,*route_log]}


def process_run(db: SupabaseREST, run: dict[str,Any]) -> dict[str,Any]:
    brain = MarketingBrain()
    selected = select_products(db,run)
    results = []
    for idx,(product,opp,reason) in enumerate(selected,1):
        try:
            results.append(process_item(db,brain,run,product,opp,reason,idx))
        except Exception as exc:
            rows = db.get("product_to_post_items",f"run_id=eq.{run['id']}&product_id=eq.{product['id']}&select=id&limit=1")
            item = first_row(rows)
            if item:
                db.patch("product_to_post_items",f"id=eq.{item['id']}",{"status":"failed","error":str(exc)[:900],"updated_at":now_iso()})
            results.append({"product_id":product["id"],"product_name":product.get("product_name"),"error":str(exc)[:900]})
    successes = [x for x in results if not x.get("error")]
    if not successes:
        raise RuntimeError("all_selected_products_failed")
    summary = {"selected":len(selected),"successful":len(successes),"failed":len(selected)-len(successes),"items":results}
    db.patch("product_to_post_runs",f"id=eq.{run['id']}",{
        "status":"needs_approval","summary":summary,"model_route":"github_models_free_or_deterministic","finished_at":now_iso(),"updated_at":now_iso(),"error":None,
    })
    return summary


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id",default="")
    parser.add_argument("--limit",type=int,default=int(os.getenv("P2P_MAX_RUNS","2")))
    args=parser.parse_args()
    db=SupabaseREST()
    worker_id=os.getenv("P2P_WORKER_ID") or f"github-{socket.gethostname()}"
    if args.run_id:
        run=first_row(db.get("product_to_post_runs",f"id=eq.{args.run_id}&select=*&limit=1"))
        if not run:
            raise RuntimeError("run_not_found")
        if run.get("status") not in {"queued","failed"}:
            print(json.dumps({"ok":True,"skipped":True,"status":run.get("status")}));return 0
        patched=db.patch("product_to_post_runs",f"id=eq.{args.run_id}",{"status":"processing","worker_id":worker_id,"started_at":run.get("started_at") or now_iso(),"updated_at":now_iso(),"error":None})
        runs=patched or []
    else:
        runs=db.rpc("claim_product_to_post_runs",{"p_worker_id":worker_id,"p_limit":max(1,min(args.limit,10))}) or []
    output=[]
    for run in runs:
        try:
            output.append({"run_id":run["id"],"summary":process_run(db,run)})
        except Exception as exc:
            trace=traceback.format_exc(limit=8)
            try:
                db.patch("product_to_post_runs",f"id=eq.{run['id']}",{"status":"failed","error":f"{exc}\n{trace}"[:3500],"finished_at":now_iso(),"updated_at":now_iso()})
            except Exception:
                pass
            output.append({"run_id":run.get("id"),"error":str(exc)})
    print(json.dumps({"ok":True,"worker_id":worker_id,"processed":len(output),"runs":output},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
