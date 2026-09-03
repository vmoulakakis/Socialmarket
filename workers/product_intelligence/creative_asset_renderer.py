from __future__ import annotations

import io
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode

SIZES = {
    "feed_4x5": (1080, 1350),
    "reel_9x16": (1080, 1920),
    "square_1x1": (1080, 1080),
}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

ACTIVE_STATUSES = {"approved", "queued", "scheduled", "publishing", "published"}


def _font(size: int, bold: bool = False):
    candidates = FONT_CANDIDATES if bold else REGULAR_CANDIDATES
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _download_image(url: str) -> Image.Image:
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("valid product image URL required")
    req = urllib.request.Request(url, headers={"User-Agent": "SocialMarketCreative/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        content_type = str(response.headers.get("content-type") or "")
        if "image" not in content_type.lower():
            raise ValueError(f"source is not an image: {content_type}")
        raw = response.read(12 * 1024 * 1024 + 1)
    if len(raw) > 12 * 1024 * 1024:
        raise ValueError("source image too large")
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if image.width < 180 or image.height < 180:
        raise ValueError("source image too small")
    return image


def _fit_product(image: Image.Image, width: int, height: int, bg=(246, 247, 249)) -> Image.Image:
    canvas = Image.new("RGB", (width, height), bg)
    padded = ImageOps.contain(image, (int(width * 0.90), int(height * 0.88)), method=Image.Resampling.LANCZOS)
    x = (width - padded.width) // 2
    y = (height - padded.height) // 2
    canvas.paste(padded, (x, y))
    return canvas


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = str(text or "").strip().split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines)) < len(" ".join(words)):
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=font)[2] > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def _qr(tracking_url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(version=None, box_size=10, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return image.resize((size, size), Image.Resampling.NEAREST)


def _clip(text: Any, max_chars: int) -> str:
    value = str(text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


def _as_list(value: Any, limit: int = 3) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif value:
        items = [value]
    else:
        items = []
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _contract(variant: dict[str, Any], product_name: str) -> dict[str, Any]:
    """Return a normalized JSON-driven visual contract.

    The creative gateway may send either direct legacy fields or a nested JSON
    contract. New SocialMarket creatives should prefer `visual_contract` because
    it makes image generation deterministic and fully automatic.
    """

    raw = (
        variant.get("visual_contract")
        or variant.get("post_visual_contract")
        or variant.get("visual")
        or {}
    )
    if not isinstance(raw, dict):
        raw = {}

    benefits = _as_list(
        raw.get("benefits")
        or raw.get("benefit_bullets")
        or variant.get("benefits")
        or variant.get("benefit_bullets"),
        3,
    )
    if not benefits:
        benefits = [
            "Λύνει συγκεκριμένο καθημερινό πρόβλημα",
            "Καθαρή επιλογή χωρίς περίπλοκη αναζήτηση",
            "Δες λεπτομέρειες πριν αγοράσεις",
        ]

    headline = (
        raw.get("pain_headline")
        or raw.get("headline")
        or variant.get("pain_headline")
        or variant.get("headline")
        or product_name
        or "Λύση για πραγματικό πρόβλημα"
    )
    subheadline = (
        raw.get("solution_line")
        or raw.get("subheadline")
        or variant.get("solution_line")
        or variant.get("subheadline")
        or "Δες αν ταιριάζει σε αυτό που χρειάζεσαι."
    )

    return {
        "layout": raw.get("layout") or "problem_solver_large_qr_v1",
        "eyebrow": raw.get("eyebrow") or variant.get("eyebrow") or "DEALORA AI · ΕΞΥΠΝΗ ΠΡΟΤΑΣΗ",
        "pain_headline": _clip(headline, 92),
        "solution_line": _clip(subheadline, 130),
        "benefits": [_clip(x, 58) for x in benefits],
        "cta": _clip(raw.get("cta") or variant.get("cta") or "Σκάναρε & δες λεπτομέρειες", 52),
        "qr_label": _clip(raw.get("qr_label") or "ΣΚΑΝΑΡΕ ΕΔΩ", 28),
        "trust_line": _clip(raw.get("trust_line") or "Ελεγμένο affiliate προϊόν · δες λεπτομέρειες πριν αγοράσεις", 92),
        "footer": _clip(raw.get("footer") or "Διαφημιστικός / affiliate σύνδεσμος", 90),
        "show_price": bool(raw.get("show_price", True)),
        "qr_size_ratio": float(raw.get("qr_size_ratio") or 0.24),
    }


def _rounded(draw: ImageDraw.ImageDraw, box, radius=24, fill=(255, 255, 255), outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render_variant(
    *,
    source_image: Image.Image,
    variant: dict[str, Any],
    product_name: str,
    merchant_name: str,
    tracking_url: str,
    effective_price: Any = None,
) -> bytes:
    variant_id = str(variant.get("id") or "feed_4x5")
    width, height = SIZES.get(variant_id, SIZES["feed_4x5"])
    contract = _contract(variant, product_name)

    # Problem-solver ad layout. The product image stays real and deterministic;
    # no synthetic product depiction is created by this renderer.
    margin = 58 if variant_id != "reel_9x16" else 62
    product_h = int(height * (0.50 if variant_id != "reel_9x16" else 0.54))
    panel_y = product_h - 18

    full = Image.new("RGB", (width, height), (10, 15, 28))
    hero = _fit_product(source_image, width, product_h, bg=(241, 245, 249))
    full.paste(hero, (0, 0))
    draw = ImageDraw.Draw(full)

    # Top dark overlay for brand and price readability.
    draw.rectangle((0, 0, width, 118), fill=(11, 18, 32))
    eyebrow_font = _font(25 if variant_id != "reel_9x16" else 28, True)
    draw.text((margin, 38), contract["eyebrow"], font=eyebrow_font, fill=(191, 219, 254))

    price_text = ""
    if contract["show_price"]:
        try:
            if effective_price not in (None, ""):
                price_text = f"€{float(effective_price):.2f}"
        except Exception:
            price_text = ""
    if price_text:
        price_font = _font(30 if variant_id != "reel_9x16" else 34, True)
        bbox = draw.textbbox((0, 0), price_text, font=price_font)
        badge_w = bbox[2] - bbox[0] + 42
        _rounded(draw, (width - margin - badge_w, 30, width - margin, 82), radius=18, fill=(15, 23, 42))
        draw.text((width - margin - badge_w + 21, 42), price_text, font=price_font, fill=(255, 255, 255))

    draw.rectangle((0, panel_y, width, height), fill=(15, 23, 42))
    card_x0, card_y0 = margin, panel_y + 42
    card_x1, card_y1 = width - margin, height - margin
    _rounded(draw, (card_x0, card_y0, card_x1, card_y1), radius=32, fill=(248, 250, 252))

    qr_ratio = min(0.28, max(0.20, contract["qr_size_ratio"]))
    qr_size = int(width * qr_ratio)
    qr_img = _qr(tracking_url, qr_size)
    qr_x = card_x1 - qr_size - 36
    qr_y = card_y1 - qr_size - 76
    qr_label_font = _font(23 if variant_id != "reel_9x16" else 26, True)
    qr_label_bbox = draw.textbbox((0, 0), contract["qr_label"], font=qr_label_font)
    qr_label_x = qr_x + max(0, (qr_size - (qr_label_bbox[2] - qr_label_bbox[0])) // 2)
    draw.text((qr_label_x, qr_y - 35), contract["qr_label"], font=qr_label_font, fill=(15, 23, 42))
    # White QR quiet-zone frame.
    _rounded(draw, (qr_x - 16, qr_y - 16, qr_x + qr_size + 16, qr_y + qr_size + 16), radius=16, fill=(255, 255, 255), outline=(226, 232, 240))
    full.paste(qr_img, (qr_x, qr_y))

    text_right_limit = qr_x - 42
    headline_font = _font(50 if variant_id != "reel_9x16" else 60, True)
    sub_font = _font(29 if variant_id != "reel_9x16" else 34, False)
    bullet_font = _font(27 if variant_id != "reel_9x16" else 32, True)
    trust_font = _font(20 if variant_id != "reel_9x16" else 24, False)
    cta_font = _font(28 if variant_id != "reel_9x16" else 33, True)
    footer_font = _font(18 if variant_id != "reel_9x16" else 21, False)

    x = card_x0 + 36
    y = card_y0 + 34
    for line in _wrap(draw, contract["pain_headline"], headline_font, text_right_limit - x, 3):
        draw.text((x, y), line, font=headline_font, fill=(15, 23, 42))
        y += headline_font.size + 7

    y += 8
    for line in _wrap(draw, contract["solution_line"], sub_font, text_right_limit - x, 2):
        draw.text((x, y), line, font=sub_font, fill=(51, 65, 85))
        y += sub_font.size + 8

    y += 18
    for benefit in contract["benefits"]:
        draw.ellipse((x, y + 4, x + 32, y + 36), fill=(22, 163, 74))
        draw.text((x + 8, y + 2), "✓", font=_font(24, True), fill=(255, 255, 255))
        for idx, line in enumerate(_wrap(draw, benefit, bullet_font, text_right_limit - x - 52, 2)):
            draw.text((x + 48, y + idx * (bullet_font.size + 3)), line, font=bullet_font, fill=(15, 23, 42))
        y += max(44, bullet_font.size + 18)

    cta = contract["cta"]
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_w = min(text_right_limit - x, cta_bbox[2] - cta_bbox[0] + 52)
    cta_y = min(card_y1 - 112, y + 14)
    _rounded(draw, (x, cta_y, x + cta_w, cta_y + 62), radius=18, fill=(15, 23, 42))
    draw.text((x + 26, cta_y + 15), cta, font=cta_font, fill=(255, 255, 255))

    trust_y = min(card_y1 - 52, cta_y + 74)
    for line in _wrap(draw, contract["trust_line"], trust_font, text_right_limit - x, 2):
        draw.text((x, trust_y), line, font=trust_font, fill=(71, 85, 105))
        trust_y += trust_font.size + 5

    footer = contract["footer"]
    draw.text((card_x0 + 34, card_y1 - 30), footer, font=footer_font, fill=(100, 116, 139))
    if merchant_name:
        merchant = _clip(str(merchant_name), 40)
        bbox = draw.textbbox((0, 0), merchant, font=footer_font)
        draw.text((card_x1 - 34 - (bbox[2] - bbox[0]), card_y1 - 30), merchant, font=footer_font, fill=(100, 116, 139))

    out = io.BytesIO()
    full.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_pack(row: dict[str, Any]) -> list[dict[str, Any]]:
    short_url = str(row.get("affiliate_short_url") or "")
    if not short_url.startswith("https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/socialscheduler-go/r-"):
        raise ValueError("validated affiliate short URL required")
    pack = row.get("creative_pack") or {}
    variants = list(pack.get("variants") or [])
    if len(variants) != 3:
        raise ValueError("creative pack must have exactly 3 variants")
    # Feed image URLs can expire or return an HTML anti-bot page by the time the
    # nightly creative job runs. Try the other feed-provided images first, then
    # recover an authoritative image from the already validated merchant landing.
    attrs = row.get("product_attributes") or {}
    candidates = [row.get("image_url"), *(attrs.get("extra_images") or [])]
    source = None
    failures: list[str] = []
    attempted: set[str] = set()
    for candidate in candidates:
        url = str(candidate or "").strip()
        if not url or url in attempted:
            continue
        attempted.add(url)
        try:
            source = _download_image(url)
            row["image_url"] = url
            break
        except Exception as exc:
            failures.append(f"{url[:180]}: {str(exc)[:180]}")

    if source is None:
        # Lazy import avoids coupling the deterministic renderer to the ranking
        # pipeline at module import time.
        from night_brain_gate_tools import recover_image

        recovered_url, recovery = recover_image({
            "extra_images": [],
            "target_url": attrs.get("target_url"),
            "tracking_validation": {
                "status": "validated_structural"
                if attrs.get("target_url") and attrs.get("target_domain")
                else "invalid"
            },
        })
        if recovered_url and recovered_url not in attempted:
            try:
                source = _download_image(recovered_url)
                row["image_url"] = recovered_url
                row["creative_image_recovery"] = recovery
            except Exception as exc:
                failures.append(f"{recovered_url[:180]}: {str(exc)[:180]}")

    if source is None:
        detail = "; ".join(failures[-4:]) or "no candidate image URLs"
        raise ValueError(f"no downloadable product image after feed/landing fallbacks: {detail}")
    results = []
    for variant in variants:
        variant_id = str(variant.get("id") or "").strip()
        if variant_id not in SIZES:
            raise ValueError(f"unsupported creative variant: {variant_id}")
        png = render_variant(
            source_image=source,
            variant=variant,
            product_name=str(row.get("product_name") or ""),
            merchant_name=str(row.get("merchant_name") or ""),
            tracking_url=short_url,
            effective_price=row.get("effective_price"),
        )
        results.append({"variant_id": variant_id, "png": png})
    return results
