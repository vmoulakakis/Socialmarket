from __future__ import annotations

import io
import textwrap
from pathlib import Path
from typing import Any

import qrcode
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont


SIZES = {"instagram":(1080,1350),"facebook":(1080,1350),"tiktok":(1080,1920),"linkedin":(1200,1200)}


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _download_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=30, headers={"user-agent":"Mozilla/5.0 SocialMarketCreative/1.0"})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _fit(img: Image.Image, box: tuple[int,int]) -> Image.Image:
    copy = img.copy()
    copy.thumbnail(box, Image.Resampling.LANCZOS)
    return copy


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 4) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
            if len(lines) >= max_lines:
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    return lines[:max_lines]


def render_creative(product: dict[str,Any], variant: dict[str,Any], tracking_url: str) -> bytes:
    platform = variant["platform"]
    w,h = SIZES.get(platform,(1080,1350))
    image_url = product.get("image_url") or product.get("thumb_url")
    if not image_url:
        raise RuntimeError("product_image_missing")
    product_img = _download_image(image_url)
    bg = product_img.resize((w,h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=38))
    overlay = Image.new("RGBA",(w,h),(0,0,0,120))
    canvas = Image.alpha_composite(bg.convert("RGBA"),overlay)
    draw = ImageDraw.Draw(canvas)

    margin = int(w*0.065)
    top = int(h*0.06)
    headline_font = _font(max(42,int(w*0.055)),bold=True)
    body_font = _font(max(25,int(w*0.029)))
    price_font = _font(max(34,int(w*0.04)),bold=True)
    small_font = _font(max(20,int(w*0.022)))

    headline = variant.get("headline") or variant.get("hook") or product.get("product_name") or "Product find"
    y = top
    for line in _wrap(draw,headline,headline_font,w-margin*2,4):
        draw.text((margin,y),line,font=headline_font,fill="white")
        y += int(headline_font.size*1.2) if hasattr(headline_font,"size") else 55

    card_y = int(h*0.28)
    card_h = int(h*0.47)
    draw.rounded_rectangle((margin,card_y,w-margin,card_y+card_h),radius=34,fill=(255,255,255,238))
    fitted = _fit(product_img,(int(w*0.72),int(card_h*0.7)))
    px = (w-fitted.width)//2
    py = card_y + int(card_h*0.06)
    canvas.alpha_composite(fitted.convert("RGBA"),(px,py))

    price = product.get("price")
    full = product.get("full_price")
    discount = product.get("discount_pct")
    offer_y = card_y + card_h - int(card_h*0.16)
    if price is not None:
        price_text = f"€{float(price):.2f}"
        draw.text((margin+32,offer_y),price_text,font=price_font,fill=(15,23,42,255))
        if full is not None and float(full) > float(price):
            draw.text((margin+32+draw.textbbox((0,0),price_text,font=price_font)[2]+24,offer_y+8),f"από €{float(full):.2f}",font=small_font,fill=(90,100,115,255))
    if discount is not None and float(discount) > 0:
        badge=f"-{float(discount):.0f}%"
        bw=draw.textbbox((0,0),badge,font=price_font)[2]+44
        draw.rounded_rectangle((w-margin-bw,offer_y-8,w-margin-16,offer_y+price_font.size+18),radius=18,fill=(15,23,42,255))
        draw.text((w-margin-bw+20,offer_y),badge,font=price_font,fill="white")

    cta = variant.get("cta") or "Δες την προσφορά"
    bottom_y = int(h*0.82)
    draw.text((margin,bottom_y),cta,font=body_font,fill="white")
    disclosure = variant.get("disclosure") or "Affiliate / διαφημιστικό περιεχόμενο"
    draw.text((margin,bottom_y+body_font.size+16),disclosure,font=small_font,fill=(235,235,235,255))

    qr_allowed = platform != "tiktok" and (variant.get("creative_direction") or {}).get("qr_allowed",True)
    if qr_allowed:
        qr = qrcode.make(tracking_url).convert("RGB")
        qsize = int(min(w,h)*0.15)
        qr = qr.resize((qsize,qsize),Image.Resampling.NEAREST)
        qx,qy=w-margin-qsize,h-margin-qsize
        draw.rounded_rectangle((qx-14,qy-14,qx+qsize+14,qy+qsize+14),radius=18,fill="white")
        canvas.alpha_composite(qr.convert("RGBA"),(qx,qy))

    out=io.BytesIO()
    canvas.convert("RGB").save(out,"PNG",optimize=True)
    return out.getvalue()
