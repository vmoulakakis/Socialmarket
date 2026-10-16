"""Pure, side-effect-free Linkwise weekly discovery and expiry classifier.

Not wired into any production job. This is a proposal with no network/database writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json


def canonical_product_key(program_id: str, product_id: str) -> str:
    """Use stable IDs; changes in product price must not alter identity."""
    if not str(program_id).strip() or str(program_id).strip().lower() == "unknown":
        raise ValueError("Unverified program identity")
    if not str(product_id).strip():
        raise ValueError("Missing product ID")
    return f"{str(program_id).strip()}:{str(product_id).strip()}"


def content_fingerprint(product: dict) -> str:
    """Hash meaningful normalized offer fields, not transient scan timestamps."""
    fields = (
        "product_name", "price_eur", "currency", "in_stock",
        "valid_from", "valid_to", "tracking_url", "image_url", "commission_eur",
    )
    normalized = {key: product.get(key) for key in fields}
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def classify_offer(
    incoming: dict,
    existing_fingerprint: str | None,
    *,
    now: datetime | None = None,
) -> str:
    """Return EXPIRED, NEW, CHANGED, or UNCHANGED; do not mutate input."""
    now = now or datetime.now(timezone.utc)
    end = incoming.get("valid_to")
    if end:
        try:
            expires = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except ValueError:
            return "NEEDS_REVIEW"
        if expires <= now:
            return "EXPIRED"
    fingerprint = content_fingerprint(incoming)
    if existing_fingerprint is None:
        return "NEW"
    return "UNCHANGED" if existing_fingerprint == fingerprint else "CHANGED"
