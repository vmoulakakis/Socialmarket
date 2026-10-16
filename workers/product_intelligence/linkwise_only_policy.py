"""Pure Linkwise-only rules. Not connected to production ingestion or posting.

This module deliberately performs no HTTP requests, database writes, or scheduling.
It supplies safety contracts for a future, separately reviewed integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlparse
import re


@dataclass(frozen=True)
class Program:
    program_id: str
    name: str
    domain: str
    approval_verified: bool = False
    tracking_verified: bool = False


@dataclass(frozen=True)
class Match:
    status: str
    program: Program | None
    evidence: str


def _domain(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else "https://" + value)
    return (parsed.hostname or "").lower().removeprefix("www.").rstrip(".")


def _linkwise_host(url: str) -> bool:
    host = _domain(url)
    return host == "linkwi.se" or host.endswith(".linkwi.se")


def route_program_id(tracking_url: str) -> str | None:
    """Read numeric program ID from a /z/<program>-<variant>/CD... link."""
    if not _linkwise_host(tracking_url):
        return None
    segments = [unquote(s) for s in urlparse(tracking_url).path.split("/") if s]
    if len(segments) < 3 or segments[0].lower() != "z":
        return None
    match = re.fullmatch(r"(\d+)-\d+", segments[1])
    return match.group(1) if match and segments[2].upper().startswith("CD") else None


def destination_domain(tracking_url: str) -> str | None:
    """Parse the destination without following redirects or making network calls."""
    if not _linkwise_host(tracking_url):
        return None
    query = parse_qs(urlparse(tracking_url).query)
    target = next((v[0] for k in ("lnkurl", "url", "redirect") if (v := query.get(k))), None)
    if not target:
        return None
    for _ in range(3):
        decoded = unquote(target)
        if decoded == target:
            break
        target = decoded
    parsed = urlparse(target)
    return _domain(target) if parsed.scheme in ("https", "http") and parsed.hostname else None


def match_program(
    explicit_program_id: str | None,
    tracking_url: str,
    programs: Mapping[str, Program],
) -> Match:
    """Never invent program IDs or infer publisher approval from a merchant domain."""
    if not _linkwise_host(tracking_url):
        return Match("invalid_tracking", None, "tracking_url_not_linkwise")
    explicit = str(explicit_program_id or "").strip()
    if explicit.lower() == "unknown":
        explicit = ""
    routed = route_program_id(tracking_url)
    if explicit and routed and explicit != routed:
        return Match("conflict", None, "explicit_program_id_disagrees_with_tracking_route")
    pid = explicit or routed
    if pid:
        program = programs.get(pid)
        if not program:
            return Match("unmatched", None, "program_id_absent_from_verified_registry")
        if not program.approval_verified or not program.tracking_verified:
            return Match("verification_required", program, "approval_or_tracking_not_confirmed")
        return Match("matched", program, "verified_program_id_and_tracking")
    domain = destination_domain(tracking_url)
    suggestions = [p for p in programs.values() if _domain(p.domain) == domain] if domain else []
    if len(suggestions) == 1:
        return Match("review", suggestions[0], "domain_only_not_authoritative")
    return Match("unmatched", None, "no_authoritative_program_id")


def weekly_scan_due(last_success: datetime | None, now: datetime) -> bool:
    """Weekly discovery only; a cron heartbeat is not itself a discovery run."""
    if last_success is None:
        return True
    if last_success.tzinfo is None or now.tzinfo is None:
        raise ValueError("timezone-aware timestamps required")
    return now >= last_success + timedelta(days=7)


def discovery_decision(is_existing: bool, valid_to: datetime | None, now: datetime) -> str:
    """An existing product is not reprocessed simply because it was observed again.

    Explicit expiry wins. Missing from one feed is NOT sufficient expiry evidence.
    """
    if now.tzinfo is None:
        raise ValueError("timezone-aware timestamps required")
    if valid_to is not None:
        if valid_to.tzinfo is None:
            raise ValueError("timezone-aware expiry required")
        if valid_to <= now:
            return "EXPIRE"
    return "SKIP_EXISTING" if is_existing else "INSERT_NEW"


def approved_epc_per_click(
    commission_per_sale_eur: float,
    conversion_rate_percent: float,
    approval_rate_percent: float,
) -> float:
    """The Linkwise dashboard's EPC per 100 clicks is NOT EUR/click."""
    if commission_per_sale_eur < 0 or not 0 <= conversion_rate_percent <= 100 or not 0 <= approval_rate_percent <= 100:
        raise ValueError("invalid commission or rates")
    return commission_per_sale_eur * conversion_rate_percent / 100 * approval_rate_percent / 100


def epc100_to_per_click(epc100_eur: float) -> float:
    if epc100_eur < 0:
        raise ValueError("EPC100 cannot be negative")
    return epc100_eur / 100
