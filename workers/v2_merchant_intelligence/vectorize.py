from __future__ import annotations

import argparse
import json
import os

from gateway import call


def vector_literal(values) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in values) + "]"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-jobs", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--worker", default=os.getenv("GITHUB_RUN_ID", "local") + "-embed")
    args = parser.parse_args()

    from sentence_transformers import SentenceTransformer

    model_name = os.getenv("MERCHANT_EMBEDDING_MODEL", "BAAI/bge-m3")
    model = SentenceTransformer(model_name, trust_remote_code=False)
    if model.get_sentence_embedding_dimension() != 1024:
        raise RuntimeError(f"expected 1024 embedding dimensions, got {model.get_sentence_embedding_dimension()}")

    completed = failed = 0
    run_ids = set()
    while completed + failed < args.max_jobs:
        jobs = call(
            "claim_embedding",
            p_worker=args.worker,
            p_limit=min(args.batch_size, args.max_jobs - completed - failed),
            p_lease_minutes=120,
        ) or []
        if not jobs:
            break
        texts = [str(job.get("semantic_text") or "").strip() for job in jobs]
        vectors = model.encode(
            texts,
            batch_size=min(16, len(texts)),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        for job, embedding in zip(jobs, vectors):
            run_id = (job.get("payload") or {}).get("run_id")
            if run_id:
                run_ids.add(run_id)
            try:
                call(
                    "complete_embedding",
                    p_job_id=job["job_id"],
                    p_embedding=vector_literal(embedding),
                    p_model=model_name,
                )
                completed += 1
                print(json.dumps({"merchant": job.get("merchant_name"), "embedding": "ready"}), flush=True)
            except Exception as exc:
                failed += 1
                try:
                    call("fail_job", p_job_id=job["job_id"], p_error=str(exc), p_retry_minutes=60)
                except Exception:
                    pass
                print(json.dumps({"merchant": job.get("merchant_name"), "embedding": "failed", "error": str(exc)[:400]}), flush=True)

    for run_id in sorted(run_ids):
        try:
            state = call("refresh_run_status", p_run_id=run_id)
            print(json.dumps({"run_id": run_id, "run_status": state}), flush=True)
        except Exception as exc:
            print(json.dumps({"run_id": run_id, "run_status": "status_update_failed", "error": str(exc)[:300]}), flush=True)

    print(json.dumps({"completed_embeddings": completed, "failed_embeddings": failed, "model": model_name}))
    return 0 if completed or not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
