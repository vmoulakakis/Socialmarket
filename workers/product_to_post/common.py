from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[2]


class SupabaseREST:
    def __init__(self) -> None:
        self.url = os.environ["SUPABASE_URL"].rstrip("/")
        self.key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": self.key,
            "authorization": f"Bearer {self.key}",
            "content-type": "application/json",
        })

    def _request(self, method: str, path: str, *, json_body: Any = None, prefer: str | None = None, timeout: int = 60):
        headers = {}
        if prefer:
            headers["Prefer"] = prefer
        r = self.session.request(method, f"{self.url}/rest/v1/{path}", json=json_body, headers=headers, timeout=timeout)
        if not r.ok:
            raise RuntimeError(f"supabase {method} {path} -> {r.status_code}: {r.text[:900]}")
        if not r.text:
            return None
        try:
            return r.json()
        except Exception:
            return r.text

    def get(self, table: str, query: str = ""):
        suffix = f"?{query}" if query else ""
        return self._request("GET", f"{table}{suffix}")

    def post(self, table: str, rows: Any, *, upsert: bool = False, return_representation: bool = True):
        prefer = []
        if upsert:
            prefer.append("resolution=merge-duplicates")
        prefer.append("return=representation" if return_representation else "return=minimal")
        return self._request("POST", table, json_body=rows, prefer=",".join(prefer))

    def patch(self, table: str, query: str, values: dict[str, Any]):
        return self._request("PATCH", f"{table}?{query}", json_body=values, prefer="return=representation")

    def rpc(self, name: str, payload: dict[str, Any]):
        return self._request("POST", f"rpc/{name}", json_body=payload)

    def upload(self, bucket: str, path: str, content: bytes, content_type: str = "image/png") -> str:
        url = f"{self.url}/storage/v1/object/{bucket}/{quote(path, safe='/')}"
        headers = {
            "apikey": self.key,
            "authorization": f"Bearer {self.key}",
            "content-type": content_type,
            "x-upsert": "true",
        }
        r = requests.post(url, data=content, headers=headers, timeout=90)
        if not r.ok:
            raise RuntimeError(f"storage upload {r.status_code}: {r.text[:700]}")
        return path


def load_skill(name: str) -> str:
    path = ROOT / "agents" / "skills" / name / "SKILL.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clean_text(value: Any, limit: int = 1000) -> str:
    return " ".join(str(value or "").split())[:limit]


def first_row(value: Any) -> dict[str, Any] | None:
    return value[0] if isinstance(value, list) and value else None
