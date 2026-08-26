from __future__ import annotations

import io
import os
import textwrap
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


def _fit_product(image: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), (246, 247, 249))
    padded = ImageOps.contain(image, (int(width * 0.88), int(height * 0.88)), method=Image.Resampling.LANCZOS)
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
    qr = qrcode.QRCode(version=None, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return image.resize((size, size), Image.Resampling.NEAREST)


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
    image_zone = int(height * (0.66 if variant_id != "reel_9x16" else 0.69))
    canvas = _fit_product(source_image, width, image_zone)
    full = Image.new("RGB", (width, height), (15, 23, 42))
    full.paste(canvas, (0, 0))
    draw = ImageDraw.Draw(full)

    margin = 62
    panel_y = image_zone
    draw.rectangle((0, panel_y, width, height), fill=(15, 23, 42))
    eyebrow_font = _font(26, True)
    headline_font = _font(58 if variant_id != "reel_9x16" else 64, True)
    sub_font = _font(30, False)
    cta_font = _font(29, True)
    fine_font = _font(20, False)

    eyebrow = (merchant_name or "Λύσεις που Αξίζουν").upper()[:70]
    draw.text((margin, panel_y + 38), eyebrow, font=eyebrow_font, fill=(165, 180, 252))

    headline = str(variant.get("headline") or product_name or "Πρόταση που αξίζει")
    lines = _wrap(draw, headline, headline_font, width - margin * 2 - 190, 3)
    y = panel_y + 88
    for line in lines:
        draw.text((margin, y), line, font=headline_font, fill=(255, 255, 255))
        y += headline_font.size + 8

    subheadline = str(variant.get("subheadline") or "").strip()
    if subheadline:
        sub_lines = _wrap(draw, subheadline, sub_font, width - margin * 2 - 190, 2)
        y += 4
        for line in sub_lines:
            draw.text((margin, y), line, font=sub_font, fill=(203, 213, 225))
            y += sub_font.size + 7

    cta = str(variant.get("cta") or "Δες το προϊόν")[:48]
    cta_y = min(height - 112, y + 22)
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_w = cta_bbox[2] - cta_bbox[0] + 42
    cta_h = cta_bbox[3] - cta_bbox[1] + 26
    draw.rounded_rectangle((margin, cta_y, margin + cta_w, cta_y + cta_h), radius=16, fill=(255, 255, 255))
    draw.text((margin + 21, cta_y + 11), cta, font=cta_font, fill=(15, 23, 42))

    price_text = ""
    try:
        if effective_price not in (None, ""):
            price_text = f"€{float(effective_price):.2f}"
    except Exception:
        price_text = ""
    if price_text:
        price_font = _font(28, True)
        bbox = draw.textbbox((0, 0), price_text, font=price_font)
        draw.text((width - margin - (bbox[2] - bbox[0]), panel_y + 42), price_text, font=price_font, fill=(255, 255, 255))

    qr_size = 132 if variant_id != "reel_9x16" else 148
    qr_img = _qr(tracking_url, qr_size)
    qr_x = width - margin - qr_size
    qr_y = height - margin - qr_size
    full.paste(qr_img, (qr_x, qr_y))
    draw.text((qr_x, qr_y - 28), "SCAN / LINK", font=fine_font, fill=(203, 213, 225))
    draw.text((margin, height - 38), "Διαφημιστικός / affiliate σύνδεσμος", font=fine_font, fill=(100, 116, 139))

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
    source = _download_image(str(row.get("image_url") or ""))
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
