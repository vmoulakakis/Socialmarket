from __future__ import annotations

import argparse
import os
import socket
from typing import Any

from .common import SupabaseREST, decrypt_state, download_media
from .providers import PublishError, provider_for


class AssistedSocialWorker:
    """Verifies saved sessions and prepares a human-finalized publish package.

    This worker deliberately does not click the final Publish/Post/Share control.
    Unattended publishing remains on the existing official OAuth/API routes.
    """

    def __init__(self) -> None:
        self.db = SupabaseREST()
        self.worker_id = os.getenv("SOCIAL_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
        self.headless = os.getenv("SOCIAL_BROWSER_HEADLESS", "true").lower() not in {"0", "false", "no"}

    def claim(self, limit: int) -> list[dict[str, Any]]:
        rows = self.db.rpc(
            "claim_social_publish_jobs",
            {"p_worker_id": self.worker_id, "p_limit": max(1, min(limit, 20)), "p_lease_seconds": 600},
        )
        return rows if isinstance(rows, list) else []

    def account_for(self, job: dict[str, Any]) -> dict[str, Any] | None:
        if job.get("account_id"):
            rows = self.db.select(
                "social_session_accounts",
                filters={"id": f"eq.{job['account_id']}"},
                limit=1,
            )
            return rows[0] if rows else None
        rows = self.db.select(
            "social_session_accounts",
            filters={
                "platform": f"eq.{job['platform']}",
                "status": "in.(paired,connected)",
            },
            order="updated_at.desc",
            limit=1,
        )
        return rows[0] if rows else None

    def session_state(self, account_id: str) -> dict[str, Any]:
        rows = self.db.select(
            "social_session_vault",
            filters={"account_id": f"eq.{account_id}"},
            select="encrypted_state",
            limit=1,
        )
        if not rows:
            raise PublishError("session_vault_missing")
        return decrypt_state(rows[0]["encrypted_state"])

    def heartbeat(self, account_id: str, status: str, error: str | None = None) -> None:
        self.db.rpc(
            "social_session_worker_heartbeat",
            {"p_account_id": account_id, "p_status": status, "p_error": error},
        )

    def process(self, job: dict[str, Any]) -> dict[str, Any]:
        platform = str(job.get("platform") or "").lower()
        payload = job.get("payload") or {}
        if job.get("publish_mode") == "existing_api":
            result = {"status": "blocked", "reason": "use existing official API route for unattended publishing"}
            self.db.patch(
                "social_publish_jobs",
                {"id": f"eq.{job['id']}"},
                {"status": "blocked", "last_error": result["reason"], "result": result},
            )
            return result

        account = self.account_for(job)
        if not account:
            result = {"status": "blocked", "reason": f"no paired {platform} session account"}
            self.db.patch(
                "social_publish_jobs",
                {"id": f"eq.{job['id']}"},
                {"status": "blocked", "last_error": result["reason"], "result": result},
            )
            return result

        account_id = account["id"]
        try:
            state = self.session_state(account_id)
            media_url = payload.get("media_url") or payload.get("source_image_url")
            if not media_url and isinstance(payload.get("media_urls"), list) and payload["media_urls"]:
                media_url = payload["media_urls"][0]
            media_path = download_media(media_url) if media_url else None
            provider = provider_for(platform, state, headless=self.headless)
            result = provider.prepare(payload, media_path)
            self.db.patch(
                "social_publish_jobs",
                {"id": f"eq.{job['id']}"},
                {
                    "status": "assisted",
                    "account_id": account_id,
                    "last_error": None,
                    "result": result,
                },
            )
            self.heartbeat(account_id, "connected", None)
            return result
        except Exception as exc:
            error = str(exc)[:1200]
            self.db.patch(
                "social_publish_jobs",
                {"id": f"eq.{job['id']}"},
                {"status": "failed", "last_error": error, "result": {"status": "failed", "error": error}},
            )
            try:
                self.heartbeat(account_id, "error", error)
            except Exception:
                pass
            raise

    def run_once(self, limit: int) -> int:
        failures = 0
        jobs = self.claim(limit)
        if not jobs:
            print("no due assisted social jobs")
            return 0
        for job in jobs:
            try:
                result = self.process(job)
                print(f"{job['id']} {job['platform']}: {result.get('status')}")
            except Exception as exc:
                failures += 1
                print(f"{job['id']} {job.get('platform')}: failed: {exc}")
        return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare no-app social publishing jobs")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    return 1 if AssistedSocialWorker().run_once(args.limit) else 0


if __name__ == "__main__":
    raise SystemExit(main())
