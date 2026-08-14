from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from cryptography.fernet import Fernet


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"missing environment variable: {name}")
    return value


def fernet_from_secret(secret: str | None = None) -> Fernet:
    raw = (secret or required_env("SOCIAL_SESSION_KEY")).encode("utf-8")
    if len(raw) < 16:
        raise RuntimeError("SOCIAL_SESSION_KEY must be at least 16 characters")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_state(state: dict[str, Any]) -> tuple[str, str]:
    payload = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    token = fernet_from_secret().encrypt(payload).decode("ascii")
    fingerprint = hashlib.sha256(payload).hexdigest()
    return token, fingerprint


def decrypt_state(token: str) -> dict[str, Any]:
    payload = fernet_from_secret().decrypt(token.encode("ascii"))
    return json.loads(payload.decode("utf-8"))


class SupabaseREST:
    def __init__(self) -> None:
        self.base = required_env("SUPABASE_URL").rstrip("/")
        self.key = required_env("SUPABASE_SERVICE_ROLE_KEY")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "apikey": self.key,
                "authorization": f"Bearer {self.key}",
                "content-type": "application/json",
            }
        )

    def _request(self, method: str, path: str, *, body: Any = None, params: dict[str, Any] | None = None, prefer: str | None = None) -> Any:
        headers = dict(self.session.headers)
        if prefer:
            headers["prefer"] = prefer
        response = self.session.request(
            method,
            f"{self.base}/rest/v1/{path.lstrip('/')}",
            params=params,
            data=None if body is None else json.dumps(body),
            headers=headers,
            timeout=45,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"supabase {method} {path}: {response.status_code} {response.text[:700]}")
        if not response.text:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def rpc(self, name: str, args: dict[str, Any] | None = None) -> Any:
        return self._request("POST", f"rpc/{name}", body=args or {})

    def select(self, table: str, *, filters: dict[str, str] | None = None, select: str = "*", order: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"select": select}
        for key, value in (filters or {}).items():
            params[key] = value
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        return self._request("GET", table, params=params) or []

    def insert(self, table: str, row: dict[str, Any], *, return_representation: bool = True) -> Any:
        prefer = "return=representation" if return_representation else "return=minimal"
        return self._request("POST", table, body=row, prefer=prefer)

    def upsert(self, table: str, row: dict[str, Any], *, on_conflict: str) -> Any:
        return self._request(
            "POST",
            table,
            body=row,
            params={"on_conflict": on_conflict},
            prefer="resolution=merge-duplicates,return=representation",
        )

    def patch(self, table: str, filters: dict[str, str], values: dict[str, Any]) -> Any:
        return self._request("PATCH", table, body=values, params=filters, prefer="return=representation")


def download_media(url: str | None) -> Path | None:
    if not url:
        return None
    if url.startswith("file://"):
        p = Path(url[7:]).expanduser().resolve()
        if not p.exists():
            raise RuntimeError(f"media file does not exist: {p}")
        return p
    p = Path(url).expanduser()
    if p.exists():
        return p.resolve()
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("media_url must be http(s), file://, or an existing local path")
    response = requests.get(url, timeout=90, stream=True)
    response.raise_for_status()
    suffix = Path(quote(url, safe="")).suffix[:8] or ".bin"
    content_type = response.headers.get("content-type", "").lower()
    if "jpeg" in content_type:
        suffix = ".jpg"
    elif "png" in content_type:
        suffix = ".png"
    elif "webp" in content_type:
        suffix = ".webp"
    elif "mp4" in content_type:
        suffix = ".mp4"
    fd, temp_path = tempfile.mkstemp(prefix="socialmarket-media-", suffix=suffix)
    os.close(fd)
    with open(temp_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    return Path(temp_path)
