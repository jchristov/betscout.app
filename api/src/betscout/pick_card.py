"""High-resolution PNG Pick Card & Daily Slate Image Generator for Discord & Telegram notifications."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

SPORT_LABELS: dict[str, str] = {
    "soccer": "FOOTBALL / SOCCER",
    "tennis": "ATP / WTA TENNIS",
    "basketball": "BASKETBALL / FIBA / NBA",
    "volleyball": "VOLLEYBALL",
    "hockey": "ICE HOCKEY / NHL",
    "football": "AMERICAN FOOTBALL / NFL",
    "baseball": "BASEBALL / MLB",
    "handball": "HANDBALL",
    "darts": "DARTS",
    "table_tennis": "TABLE TENNIS",
    "curling": "CURLING",
}

SPORT_EMOJIS: dict[str, str] = {
    "soccer": "⚽",
    "tennis": "🎾",
    "basketball": "🏀",
    "volleyball": "🏐",
    "hockey": "🏒",
    "football": "🏈",
    "baseball": "⚾",
    "handball": "🤾",
    "darts": "🎯",
    "table_tennis": "🏓",
    "curling": "🥌",
}


def _infer_sport_cat(raw_val: str | None) -> str:
    low = str(raw_val or "").lower().strip()
    if not low:
        return "soccer"
    if any(k in low for k in ("curling",)):
        return "curling"
    if any(k in low for k in ("table_tennis", "table tennis", "tt star", "tt-star", "tt elite", "ittf", "wtt")):
        return "table_tennis"
    if any(k in low for k in ("handball", "ehf", "ihf", "starligue", "hbl")):
        return "handball"
    if any(k in low for k in ("darts", "pdc", "bdo", "wdf", "modus")):
        return "darts"
    if any(k in low for k in ("tennis", "atp", "wta", "itf", "challenger", "utr")):
        return "tennis"
    if any(k in low for k in ("volleyball", "fivb", "cev", "superlega", "plusliga")):
        return "volleyball"
    if any(k in low for k in ("basketball", "nba", "wnba", "ncaam", "ncaaw", "fiba", "nbl", "euroleague", "acb")):
        return "basketball"
    if any(k in low for k in ("hockey", "nhl", "khl", "shl", "ahl", "liiga", "del")):
        return "hockey"
    if any(k in low for k in ("american football", "nfl", "ncaaf", "cfl")):
        return "football"
    if low == "football":
        return "football"
    if any(k in low for k in ("baseball", "mlb", "npb", "kbo")):
        return "baseball"
    return "soccer"


def _render_sport_icon_rgba(sport_cat: str, size: int = 30) -> Image.Image:
    """Render a 4x supersampled anti-aliased RGBA Sport Icon badge for `sport_cat`."""
    import math

    sp = _infer_sport_cat(sport_cat)
    scale = 4
    S = size * scale
    cx = cy = int(S // 2)
    r = int(S * 0.43)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    bbox = [(cx - r, cy - r), (cx + r, cy + r)]

    # Subtle outer glow ring
    draw.ellipse([(cx - r - 4, cy - r - 4), (cx + r + 4, cy + r + 4)], fill=(56, 189, 248, 32))

    if sp == "tennis":
        draw.ellipse(bbox, fill=(163, 230, 53, 255), outline=(34, 197, 94, 255), width=6)
        draw.arc([(cx - int(r * 1.32), cy - int(r * 0.85)), (cx - int(r * 0.16), cy + int(r * 0.85))], start=-55, end=55, fill=(255, 255, 255, 245), width=7)
        draw.arc([(cx + int(r * 0.16), cy - int(r * 0.85)), (cx + int(r * 1.32), cy + int(r * 0.85))], start=125, end=235, fill=(255, 255, 255, 245), width=7)
    elif sp == "basketball":
        draw.ellipse(bbox, fill=(249, 115, 22, 255), outline=(251, 146, 60, 255), width=6)
        draw.line([(cx - r + 6, cy), (cx + r - 6, cy)], fill=(15, 23, 42, 240), width=6)
        draw.line([(cx, cy - r + 6), (cx, cy + r - 6)], fill=(15, 23, 42, 240), width=6)
        draw.arc([(cx - int(r * 1.2), cy - int(r * 0.8)), (cx - int(r * 0.12), cy + int(r * 0.8))], start=-55, end=55, fill=(15, 23, 42, 240), width=6)
        draw.arc([(cx + int(r * 0.12), cy - int(r * 0.8)), (cx + int(r * 1.2), cy + int(r * 0.8))], start=125, end=235, fill=(15, 23, 42, 240), width=6)
    elif sp == "hockey":
        draw.ellipse(bbox, fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=6)
        draw.line([(cx - int(r * 0.55), cy - int(r * 0.55)), (cx + int(r * 0.42), cy + int(r * 0.42))], fill=(56, 189, 248, 255), width=10)
        draw.line([(cx + int(r * 0.42), cy + int(r * 0.42)), (cx + int(r * 0.78), cy + int(r * 0.26))], fill=(56, 189, 248, 255), width=10)
        draw.ellipse([(cx - int(r * 0.58), cy + int(r * 0.16)), (cx + int(r * 0.18), cy + int(r * 0.58))], fill=(226, 232, 240, 255))
    elif sp == "football":
        draw.ellipse([(cx - r, cy - int(r * 0.68)), (cx + r, cy + int(r * 0.68))], fill=(180, 83, 9, 255), outline=(245, 158, 11, 255), width=6)
        draw.line([(cx - int(r * 0.45), cy), (cx + int(r * 0.45), cy)], fill=(255, 255, 255, 255), width=6)
        for lx in (-int(r * 0.3), 0, int(r * 0.3)):
            draw.line([(cx + lx, cy - 10), (cx + lx, cy + 10)], fill=(255, 255, 255, 255), width=6)
    elif sp == "baseball":
        draw.ellipse(bbox, fill=(248, 250, 252, 255), outline=(148, 163, 184, 255), width=6)
        draw.arc([(cx - int(r * 1.25), cy - int(r * 0.8)), (cx - int(r * 0.15), cy + int(r * 0.8))], start=-55, end=55, fill=(239, 68, 68, 255), width=7)
        draw.arc([(cx + int(r * 0.15), cy - int(r * 0.8)), (cx + int(r * 1.25), cy + int(r * 0.8))], start=125, end=235, fill=(239, 68, 68, 255), width=7)
    elif sp == "table_tennis":
        draw.ellipse(bbox, fill=(15, 23, 42, 255), outline=(239, 68, 68, 255), width=6)
        draw.ellipse([(cx - int(r * 0.65), cy - int(r * 0.65)), (cx + int(r * 0.35), cy + int(r * 0.35))], fill=(239, 68, 68, 255), outline=(252, 165, 165, 255), width=5)
        draw.line([(cx + int(r * 0.15), cy + int(r * 0.15)), (cx + int(r * 0.62), cy + int(r * 0.62))], fill=(217, 119, 6, 255), width=12)
        draw.ellipse([(cx + int(r * 0.18), cy - int(r * 0.65)), (cx + int(r * 0.68), cy - int(r * 0.15))], fill=(255, 255, 255, 255))
    elif sp == "darts":
        draw.ellipse(bbox, fill=(15, 23, 42, 255), outline=(239, 68, 68, 255), width=7)
        r_mid = int(r * 0.62)
        r_in = int(r * 0.28)
        draw.ellipse([(cx - r_mid, cy - r_mid), (cx + r_mid, cy + r_mid)], outline=(34, 197, 94, 255), width=7)
        draw.ellipse([(cx - r_in, cy - r_in), (cx + r_in, cy + r_in)], fill=(239, 68, 68, 255))
    elif sp == "curling":
        draw.ellipse(bbox, fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=7)
        r_mid = int(r * 0.62)
        r_in = int(r * 0.28)
        draw.ellipse([(cx - r_mid, cy - r_mid), (cx + r_mid, cy + r_mid)], outline=(248, 250, 252, 255), width=6)
        draw.ellipse([(cx - r_in, cy - r_in), (cx + r_in, cy + r_in)], fill=(239, 68, 68, 255))
    elif sp in ("volleyball", "handball"):
        col_fill = (56, 189, 248, 255) if sp == "volleyball" else (245, 158, 11, 255)
        draw.ellipse(bbox, fill=(15, 23, 42, 255), outline=col_fill, width=6)
        draw.arc([(cx - r + 8, cy - r + 8), (cx + r - 8, cy + r - 8)], start=20, end=160, fill=col_fill, width=6)
        draw.arc([(cx - r + 8, cy - r + 8), (cx + r - 8, cy + r - 8)], start=200, end=340, fill=(241, 245, 249, 255), width=6)
        draw.line([(cx - r + 10, cy), (cx + r - 10, cy)], fill=col_fill, width=6)
    else:
        draw.ellipse(bbox, fill=(241, 245, 249, 255), outline=(56, 189, 248, 255), width=6)
        r_pent = r * 0.44
        pent_pts = [
            (cx + r_pent * math.cos(math.radians(-90 + i * 72)), cy + r_pent * math.sin(math.radians(-90 + i * 72)))
            for i in range(5)
        ]
        draw.polygon(pent_pts, fill=(15, 23, 42, 255))
        for px, py in pent_pts:
            ang = math.atan2(py - cy, px - cx)
            draw.line([(px, py), (cx + (r - 6) * math.cos(ang), cy + (r - 6) * math.sin(ang))], fill=(15, 23, 42, 255), width=6)

    return img.resize((size, size), resample=Image.Resampling.LANCZOS)


def _render_sport_emoji_rgba(sport_cat: str, size: int = 34) -> Image.Image:
    """Render the exact notification card Sport Icon (`⚽`, `🎾`, `🏀`, `🏐`, `🏒`, `🏈`, `⚾`, `🤾`, `🎯`, `🏓`)
    using the bundled 64x64 RGBA PNG assets (`assets/sport_icons/{sp}.png`) first so Cloud Run Linux and macOS
    produce the exact same icons, with font/vector fallback."""
    sp = _infer_sport_cat(sport_cat)
    bundled_png = Path(__file__).resolve().parent / "assets" / "sport_icons" / f"{sp}.png"
    if bundled_png.exists():
        try:
            with Image.open(bundled_png) as im_b:
                return im_b.convert("RGBA").resize((size, size), resample=Image.Resampling.LANCZOS)
        except Exception:
            pass
    emoji_ch = SPORT_EMOJIS.get(sp, "⚽")
    emoji_font_paths = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/NotoColorEmoji.ttf",
    ]
    for fp in emoji_font_paths:
        if not Path(fp).exists():
            continue
        for strike_sz in (64, 96, 109, 48, 40, 32):
            try:
                f_em = ImageFont.truetype(fp, strike_sz)
                canvas = Image.new("RGBA", (strike_sz * 2, strike_sz * 2), (0, 0, 0, 0))
                d_em = ImageDraw.Draw(canvas, "RGBA")
                d_em.text((strike_sz // 4, strike_sz // 4), emoji_ch, font=f_em, embedded_color=True)
                bbox = canvas.getbbox()
                if bbox:
                    crop = canvas.crop(bbox)
                    cw, ch = crop.size
                    side = max(cw, ch, 1)
                    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                    sq.paste(crop, ((side - cw) // 2, (side - ch) // 2), crop)
                    return sq.resize((size, size), resample=Image.Resampling.LANCZOS)
            except Exception:
                continue
    return _render_sport_icon_rgba(sp, size=size)


def _paste_sport_icon(img: Image.Image, sport_cat: str, cx: int, cy: int, size: int = 26) -> None:
    icon_rgba = _render_sport_emoji_rgba(sport_cat, size=size)
    img.paste(icon_rgba, (int(cx - size // 2), int(cy - size // 2)), icon_rgba)


def _compact_timestamp(ts_str: str) -> str:
    """Convert '2026-10-26 20:30 CET' -> 'Oct 26 · 20:30 CET' so multiple timestamps fit cleanly without clipping."""
    s = _strip_non_ascii_symbols(ts_str)
    if not s:
        return ""
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
        "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        m_abbr = months.get(s[5:7], s[5:7])
        day_s = s[8:10]
        rest = s[10:].lstrip(" T").strip()
        return f"{m_abbr} {day_s}, {rest}" if rest else f"{m_abbr} {day_s}"
    return s


def _draw_sport_icon(draw: ImageDraw.ImageDraw, sport_cat: str, cx: int, cy: int, radius: int = 12) -> None:
    """Draw a crisp vector sport icon at `(cx, cy)` so every generated PNG card has a clear visual sport emblem."""
    import math

    sp = _infer_sport_cat(sport_cat)
    r = radius
    bbox = [(cx - r, cy - r), (cx + r, cy + r)]

    if sp == "tennis":
        # Optic yellow-green tennis ball with white curved seams
        draw.ellipse(bbox, fill=(163, 230, 53), outline=(34, 197, 94), width=2)
        draw.arc([(cx - int(r * 1.3), cy - int(r * 0.85)), (cx - int(r * 0.15), cy + int(r * 0.85))], start=-55, end=55, fill=(255, 255, 255), width=2)
        draw.arc([(cx + int(r * 0.15), cy - int(r * 0.85)), (cx + int(r * 1.3), cy + int(r * 0.85))], start=125, end=235, fill=(255, 255, 255), width=2)
    elif sp == "basketball":
        # Orange basketball with dark ribs
        draw.ellipse(bbox, fill=(249, 115, 22), outline=(251, 146, 60), width=2)
        draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(15, 23, 42), width=2)
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(15, 23, 42), width=2)
        draw.arc([(cx - int(r * 1.2), cy - int(r * 0.8)), (cx - int(r * 0.1), cy + int(r * 0.8))], start=-55, end=55, fill=(15, 23, 42), width=2)
        draw.arc([(cx + int(r * 0.1), cy - int(r * 0.8)), (cx + int(r * 1.2), cy + int(r * 0.8))], start=125, end=235, fill=(15, 23, 42), width=2)
    elif sp == "hockey":
        # Crossed cyan hockey stick + dark puck
        draw.ellipse(bbox, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
        draw.line([(cx - int(r * 0.55), cy - int(r * 0.55)), (cx + int(r * 0.45), cy + int(r * 0.45))], fill=(56, 189, 248), width=3)
        draw.line([(cx + int(r * 0.45), cy + int(r * 0.45)), (cx + int(r * 0.75), cy + int(r * 0.30))], fill=(56, 189, 248), width=3)
        draw.ellipse([(cx - int(r * 0.55), cy + int(r * 0.15)), (cx + int(r * 0.15), cy + int(r * 0.55))], fill=(226, 232, 240))
    elif sp == "football":
        # NFL prolate football with white laces
        draw.ellipse([(cx - r, cy - int(r * 0.68)), (cx + r, cy + int(r * 0.68))], fill=(180, 83, 9), outline=(245, 158, 11), width=2)
        draw.line([(cx - int(r * 0.45), cy), (cx + int(r * 0.45), cy)], fill=(255, 255, 255), width=2)
        for lx in (-int(r * 0.3), 0, int(r * 0.3)):
            draw.line([(cx + lx, cy - 3), (cx + lx, cy + 3)], fill=(255, 255, 255), width=2)
    elif sp == "baseball":
        # White baseball with red seams
        draw.ellipse(bbox, fill=(241, 245, 249), outline=(148, 163, 184), width=2)
        draw.arc([(cx - int(r * 1.25), cy - int(r * 0.8)), (cx - int(r * 0.15), cy + int(r * 0.8))], start=-55, end=55, fill=(239, 68, 68), width=2)
        draw.arc([(cx + int(r * 0.15), cy - int(r * 0.8)), (cx + int(r * 1.25), cy + int(r * 0.8))], start=125, end=235, fill=(239, 68, 68), width=2)
    elif sp == "table_tennis":
        # Red table tennis paddle + white ball
        draw.ellipse([(cx - int(r * 0.85), cy - int(r * 0.85)), (cx + int(r * 0.45), cy + int(r * 0.45))], fill=(239, 68, 68), outline=(252, 165, 165), width=2)
        draw.line([(cx + int(r * 0.2), cy + int(r * 0.2)), (cx + int(r * 0.75), cy + int(r * 0.75))], fill=(217, 119, 6), width=4)
        draw.ellipse([(cx + int(r * 0.25), cy - int(r * 0.75)), (cx + int(r * 0.85), cy - int(r * 0.15))], fill=(255, 255, 255))
    elif sp == "darts":
        # Bullseye target rings
        draw.ellipse(bbox, fill=(15, 23, 42), outline=(239, 68, 68), width=2)
        r_mid = int(r * 0.62)
        r_in = int(r * 0.28)
        draw.ellipse([(cx - r_mid, cy - r_mid), (cx + r_mid, cy + r_mid)], outline=(34, 197, 94), width=2)
        draw.ellipse([(cx - r_in, cy - r_in), (cx + r_in, cy + r_in)], fill=(239, 68, 68))
    elif sp in ("volleyball", "handball"):
        col_fill = (56, 189, 248) if sp == "volleyball" else (245, 158, 11)
        draw.ellipse(bbox, fill=(15, 23, 42), outline=col_fill, width=2)
        draw.arc([(cx - r + 2, cy - r + 2), (cx + r - 2, cy + r - 2)], start=20, end=160, fill=col_fill, width=2)
        draw.arc([(cx - r + 2, cy - r + 2), (cx + r - 2, cy + r - 2)], start=200, end=340, fill=(241, 245, 249), width=2)
        draw.line([(cx - r + 3, cy), (cx + r - 3, cy)], fill=col_fill, width=2)
    else:
        # Football / Soccer ball: outer ring + center pentagon + 5 spoke seams
        draw.ellipse(bbox, fill=(241, 245, 249), outline=(56, 189, 248), width=2)
        r_pent = r * 0.44
        pent_pts = [
            (cx + r_pent * math.cos(math.radians(-90 + i * 72)), cy + r_pent * math.sin(math.radians(-90 + i * 72)))
            for i in range(5)
        ]
        draw.polygon(pent_pts, fill=(15, 23, 42))
        for px, py in pent_pts:
            ang = math.atan2(py - cy, px - cx)
            draw.line([(px, py), (cx + (r - 2) * math.cos(ang), cy + (r - 2) * math.sin(ang))], fill=(15, 23, 42), width=2)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _draw_betscout_shield(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int = 24) -> None:
    """Draw the BetScout hexagonal radar shield, crosshair ticks, rising scout vector, and target lock."""
    import math

    pts: list[tuple[float, float]] = []
    for i in range(6):
        ang = math.radians(-90 + i * 60)
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    draw.polygon(pts, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    # Inner radar circle & crosshair ticks
    r_in = int(radius * 0.58)
    draw.ellipse([(cx - r_in, cy - r_in), (cx + r_in, cy + r_in)], outline=(30, 64, 110), width=1)
    draw.line([(cx, cy - radius + 5), (cx, cy - r_in - 2)], fill=(56, 189, 248), width=1)
    draw.line([(cx, cy + r_in + 2), (cx, cy + radius - 5)], fill=(56, 189, 248), width=1)
    draw.line([(cx - radius + 5, cy), (cx - r_in - 2, cy)], fill=(56, 189, 248), width=1)
    draw.line([(cx + r_in + 2, cy), (cx + radius - 5, cy)], fill=(56, 189, 248), width=1)
    # Scout rising vector & target lock node
    tx, ty = cx + radius * 0.44, cy - radius * 0.42
    vec = [
        (cx - radius * 0.50, cy + radius * 0.38),
        (cx - radius * 0.12, cy + radius * 0.04),
        (cx + radius * 0.06, cy + radius * 0.18),
        (tx, ty),
    ]
    draw.line(vec, fill=(34, 197, 94), width=3)
    draw.ellipse([(tx - 3, ty - 3), (tx + 3, ty + 3)], fill=(34, 197, 94), outline=(56, 189, 248), width=1)


_draw_vektorpulse_shield = _draw_betscout_shield


def render_logo_png(
    size: int = 512,
    output_path: Path | None = None,
) -> bytes:
    """Render a high-resolution supersampled (4x AA) RGBA PNG of the BetScout rounded-squircle quant logo."""
    scale = 4
    S = size * scale
    cx = cy = S / 2.0
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    pad = int(S * (3.0 / 64.0))
    corner_r = int(S * (16.0 / 64.0))
    rim_w = max(4, int(S * (2.4 / 64.0)))

    # Rounded squircle mask
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([(pad, pad), (S - pad, S - pad)], radius=corner_r, fill=255)

    # Deep obsidian-navy vertical gradient inside squircle
    bg = Image.new("RGBA", (S, S), (19, 32, 56, 255))
    bg_draw = ImageDraw.Draw(bg, "RGBA")
    for y in range(S):
        t = y / max(1, S - 1)
        r = int(19 * (1 - t) + 6 * t)
        g = int(32 * (1 - t) + 11 * t)
        b = int(56 * (1 - t) + 22 * t)
        bg_draw.line([(0, y), (S, y)], fill=(r, g, b, 255))
    img.paste(bg, (0, 0), mask)

    # Outer squircle rim
    draw.rounded_rectangle(
        [(pad, pad), (S - pad, S - pad)],
        radius=corner_r,
        outline=(45, 212, 191, 255),
        width=rim_w,
    )

    def _pt(ux: float, uy: float) -> tuple[float, float]:
        return (S * (ux / 64.0), S * (uy / 64.0))

    # Option 7.3: Subtle Azimuth Ring (r = 18.5 / 64) + 8-Facet 3D Chiseled Bevel Compass (No Center Dot)
    r_ring = S * (18.5 / 64.0)
    draw.ellipse(
        [(cx - r_ring, cy - r_ring), (cx + r_ring, cy + r_ring)],
        outline=(56, 189, 248, 72),
        width=max(2, int(S * (1.4 / 64.0))),
    )

    # North split bevel
    draw.polygon([_pt(32.0, 8.0), _pt(32.0, 32.0), _pt(27.0, 27.0)], fill=(253, 224, 71, 255))
    draw.polygon([_pt(32.0, 8.0), _pt(37.0, 27.0), _pt(32.0, 32.0)], fill=(16, 185, 129, 255))
    # South split bevel
    draw.polygon([_pt(32.0, 56.0), _pt(32.0, 32.0), _pt(37.0, 37.0)], fill=(52, 211, 153, 255))
    draw.polygon([_pt(32.0, 56.0), _pt(27.0, 37.0), _pt(32.0, 32.0)], fill=(4, 120, 87, 255))
    # East split bevel
    draw.polygon([_pt(56.0, 32.0), _pt(32.0, 32.0), _pt(37.0, 27.0)], fill=(125, 211, 252, 255))
    draw.polygon([_pt(56.0, 32.0), _pt(37.0, 37.0), _pt(32.0, 32.0)], fill=(2, 132, 199, 255))
    # West split bevel
    draw.polygon([_pt(8.0, 32.0), _pt(32.0, 32.0), _pt(27.0, 37.0)], fill=(56, 189, 248, 255))
    draw.polygon([_pt(8.0, 32.0), _pt(27.0, 27.0), _pt(32.0, 32.0)], fill=(3, 105, 161, 255))

    # Downsample 4x -> 1x with LANCZOS anti-aliasing
    final_img = img.resize((size, size), resample=Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    final_img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)
    return png_bytes


def _strip_non_ascii_symbols(text: str) -> str:
    """Strip emoji codepoints that standard system TTFs don't render while preserving accented European letters."""
    out: list[str] = []
    for ch in str(text or ""):
        cp = ord(ch)
        if cp > 0x2000 and cp not in (0x2013, 0x2014, 0x20AC, 0x2192, 0x2265, 0x00B7):
            continue
        out.append(ch)
    return " ".join("".join(out).split())


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> float:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return float(bbox[2] - bbox[0])
    except Exception:
        return float(len(text) * 10)


def _fit_font_and_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    start_size: int,
    min_size: int = 13,
    bold: bool = True,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, str]:
    """Dynamically shrink font size down to `min_size` so `text` fits inside `max_width` without clipping;
    only ellipsis-truncate if still wider at `min_size`."""
    clean = _strip_non_ascii_symbols(text)
    for sz in range(start_size, min_size - 1, -2):
        f = _load_font(sz, bold=bold)
        if _text_width(draw, clean, f) <= max_width:
            return f, clean
    f_min = _load_font(min_size, bold=bold)
    ell = clean
    while len(ell) > 4 and _text_width(draw, ell + "...", f_min) > max_width:
        ell = ell[:-1].rstrip()
    return f_min, (ell + "..." if ell != clean else clean)


def _draw_text_with_muted_vs(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font_bold: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    primary_rgb: tuple[int, int, int] = (255, 255, 255),
    muted_rgb: tuple[int, int, int] = (148, 163, 184),
) -> None:
    """Draw a matchup string (`Home vs Away`) with team names in bold `primary_rgb` and `vs` in regular `muted_rgb`."""
    if " vs " not in text:
        draw.text(xy, text, font=font_bold, fill=primary_rgb)
        return
    font_reg = _load_font(font_size, bold=False)
    x_cur, y_cur = xy
    parts = text.split(" vs ")
    for idx, part in enumerate(parts):
        if part:
            draw.text((x_cur, y_cur), part, font=font_bold, fill=primary_rgb)
            x_cur += int(_text_width(draw, part, font_bold))
        if idx < len(parts) - 1:
            vs_str = " vs "
            draw.text((x_cur, y_cur), vs_str, font=font_reg, fill=muted_rgb)
            x_cur += int(_text_width(draw, vs_str, font_reg))



def _humanize_raw_market_codes(text: str, home: str = "", away: str = "") -> str:
    """Convert any raw internal market codes (`PLUS15_H`, `SETS20_A`, `DC_1X`, `DNB_H`, `UNDER_GAMES_21.5`, `OVER_2_5`)
    into human-readable labels so internal enum codes never leak onto notification cards."""
    import re

    s = str(text or "").strip()
    if not s:
        return s
    replacements = {
        "(PLUS15_H)": "+1.5 Sets",
        "(PLUS15_A)": "+1.5 Sets",
        "PLUS15_H": f"{home} +1.5 Sets".strip() if home else "+1.5 Sets",
        "PLUS15_A": f"{away} +1.5 Sets".strip() if away else "+1.5 Sets",
        "(SETS20_H)": "2:0 Straight Sets",
        "(SETS20_A)": "0:2 Straight Sets",
        "SETS20_H": f"{home} 2:0 Sets".strip() if home else "2:0 Straight Sets",
        "SETS20_A": f"{away} 0:2 Sets".strip() if away else "0:2 Straight Sets",
        "(DC_1X)": "or Draw (1X)",
        "(DC_X2)": "or Draw (X2)",
        "DC_1X": f"{home} or Draw (1X)".strip() if home else "Double Chance 1X",
        "DC_X2": f"{away} or Draw (X2)".strip() if away else "Double Chance X2",
        "(DNB_H)": "Draw No Bet (DNB)",
        "(DNB_A)": "Draw No Bet (DNB)",
        "DNB_H": f"{home} DNB".strip() if home else "Draw No Bet (DNB)",
        "DNB_A": f"{away} DNB".strip() if away else "Draw No Bet (DNB)",
        "(OVER_2_5)": "Over 2.5 Goals",
        "OVER_2_5": "Over 2.5 Goals",
        "(OVER_1_5)": "Over 1.5 Goals",
        "OVER_1_5": "Over 1.5 Goals",
        "SET_SHIELD": "+1.5 Sets Shield",
        "STRAIGHT_SETS": "2:0 Straight Sets",
        "DC_SHIELD": "Double Chance Shield",
        "DNB_SHIELD": "Draw No Bet Shield",
        "TOTALS_OVER": "Over Total Goals",
        "TOTALS_UNDER": "Under Total Games",
    }
    for k, v in replacements.items():
        if k in s:
            s = s.replace(k, v)
    s = re.sub(r"\(?UNDER_GAMES_([0-9.]+)\)?", r"Under \1 Games", s)
    s = re.sub(r"\(?OVER_GOALS_([0-9.]+)\)?", r"Over \1 Goals", s)
    return " ".join(s.split())


def _split_primary_and_sub_kpi(raw_val: str) -> tuple[str, str]:
    """Split a composite KPI string like '1.33 (Fair 1.34, EV +2.1%)' or '2:0 (9.8%) · Cluster 2:0/2:1/3:0 (28.5%)'
    into `(primary_headline, secondary_subline)` so neither line is ever cut off inside a KPI box."""
    import re

    s = _humanize_raw_market_codes(_strip_non_ascii_symbols(raw_val))
    if not s:
        return "—", ""
    # Strip trailing ' (H)' or ' (A)' side tags so 'H' or 'A' is never split onto a second row
    s = re.sub(r"\s+\([HA]\)$", "", s).strip()
    if " · " in s:
        p1, p2 = s.split(" · ", 1)
        p1 = re.sub(r"\s+\([HA]\)$", "", p1.strip())
        p2 = re.sub(r"^\([HA]\)\s*", "", p2.strip())
        if p2 in ("H", "A", "(H)", "(A)"):
            p2 = ""
        return p1, p2
    if " | " in s:
        p1, p2 = s.split(" | ", 1)
        p1 = re.sub(r"\s+\([HA]\)$", "", p1.strip())
        p2 = re.sub(r"^\([HA]\)\s*", "", p2.strip())
        if p2 in ("H", "A", "(H)", "(A)"):
            p2 = ""
        return p1, p2
    if "(" in s and s.endswith(")") and not s.startswith("("):
        idx = s.find("(")
        head = s[:idx].strip()
        sub = s[idx + 1 : -1].strip()
        if sub in ("H", "A"):
            return head, ""
        if head and len(s) > 14:
            return head, sub
    return s, ""


def _draw_rounded_card_with_top_accent(
    img: Image.Image,
    bbox: tuple[int, int, int, int],
    radius: int,
    fill_rgb: tuple[int, int, int],
    outline_rgb: tuple[int, int, int],
    outline_width: int,
    accent_rgb: tuple[int, int, int],
    accent_height: int = 3,
) -> None:
    """Draw a rounded card with a smooth CSS `border-top` style accent along the top arc."""
    x0, y0, x1, y1 = bbox
    w, h = img.size

    # Render the entire card + border + top colored border at 4x supersampling for pixel-perfect anti-aliased corners
    ss = 4
    layer_hi = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(layer_hi)
    r_hi = radius * ss
    ow_hi = max(1, outline_width * ss)
    aw_hi = max(ow_hi, accent_height * ss)

    # 1. Card interior fill + standard slate border
    draw_hi.rounded_rectangle(
        [x0 * ss, y0 * ss, x1 * ss, y1 * ss],
        radius=r_hi,
        fill=(*fill_rgb, 255),
        outline=(*outline_rgb, 255),
        width=ow_hi,
    )

    # 2. Colored top border stroke along the exact same rounded perimeter, masked to the top edge/arc
    top_stroke_hi = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ts_draw = ImageDraw.Draw(top_stroke_hi)
    ts_draw.rounded_rectangle(
        [x0 * ss, y0 * ss, x1 * ss, y1 * ss],
        radius=r_hi,
        outline=(*accent_rgb, 255),
        width=aw_hi,
    )

    # Vertical alpha gradient mask so the colored top border follows the top curve and feathers smoothly into the side borders
    mask_hi = Image.new("L", (w * ss, h * ss), 0)
    m_draw = ImageDraw.Draw(mask_hi)
    solid_end = y0 * ss + int(r_hi * 0.45)
    fade_end = y0 * ss + int(r_hi * 0.95)
    m_draw.rectangle([x0 * ss, y0 * ss, x1 * ss, solid_end], fill=255)
    for py in range(solid_end, fade_end):
        alpha = int(255 * (1.0 - (py - solid_end) / max(1, fade_end - solid_end)))
        m_draw.line([(x0 * ss, py), (x1 * ss, py)], fill=alpha)

    layer_hi.paste(top_stroke_hi, (0, 0), mask_hi)
    layer_sm = layer_hi.resize((w, h), resample=Image.Resampling.LANCZOS)
    img.paste(layer_sm, (0, 0), layer_sm)


def _get_sport_pill_colors(sport_cat: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """Return `(fill_rgb, border_rgb, text_rgb)` matching `getSportBadgeTheme` in the Vue 3 app."""
    sp = _infer_sport_cat(sport_cat)
    palettes: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = {
        "soccer": ((10, 36, 28), (52, 211, 153), (110, 231, 183)),
        "tennis": ((24, 38, 14), (163, 230, 53), (217, 249, 157)),
        "basketball": ((44, 22, 12), (251, 146, 60), (253, 186, 116)),
        "hockey": ((10, 34, 46), (34, 211, 238), (165, 243, 252)),
        "football": ((44, 30, 12), (251, 191, 36), (253, 230, 138)),
        "table_tennis": ((42, 16, 46), (232, 121, 249), (245, 208, 254)),
        "volleyball": ((42, 36, 12), (250, 204, 21), (254, 240, 138)),
        "baseball": ((44, 16, 26), (251, 113, 133), (254, 205, 211)),
        "handball": ((20, 24, 52), (129, 140, 248), (199, 210, 254)),
        "darts": ((44, 16, 18), (248, 113, 113), (254, 202, 202)),
        "curling": ((12, 34, 46), (56, 189, 248), (186, 230, 253)),
    }
    return palettes.get(sp, palettes["soccer"])


def _get_badge_pill_colors(
    badge_status: str,
    tier_raw: str,
    is_win_card: bool = False,
    is_loss_card: bool = False,
) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """Return `(fill_rgb, border_rgb, text_rgb)` matching the color-coded tier/signal badges in the Vue 3 app."""
    combined = f"{badge_status} {tier_raw}".upper()
    if is_loss_card or "LOSS" in combined:
        return ((46, 16, 28), (244, 63, 94), (253, 164, 175))
    if is_win_card or "SETTLED WIN" in combined:
        return ((10, 38, 28), (52, 211, 153), (110, 231, 183))
    if "STEAM" in combined:
        return ((46, 22, 12), (251, 146, 60), (254, 215, 170))
    if "MISPRICED" in combined or "EDGE +" in combined or "PROFIT BOOST" in combined or "BOOSTER" in combined:
        return ((10, 38, 28), (52, 211, 153), (110, 231, 183))
    if "LIVE" in combined or "REBOUND" in combined:
        return ((46, 16, 28), (244, 63, 94), (253, 164, 175))
    if "TOP_8PCT" in combined or "TOP 8%" in combined or "TIER_0" in combined:
        return ((32, 20, 56), (167, 139, 250), (221, 214, 254))
    if "BANKER" in combined or "TIER_1" in combined or "TOP_10PCT" in combined or "TOP 10%" in combined or "70%" in combined or "72%" in combined:
        return ((44, 30, 12), (251, 191, 36), (253, 230, 138))
    if "HIGH_CONF" in combined or "HIGH-CONF" in combined or "TOP_15PCT" in combined or "UEFA" in combined or "QUANT EDGE" in combined:
        return ((10, 34, 48), (34, 211, 238), (165, 243, 252))
    return ((22, 26, 54), (129, 140, 248), (199, 210, 254))


def render_pick_card_png(
    pick_data: dict[str, Any],
    output_path: Path | None = None,
) -> bytes:
    """Render a 1080x580 dark-mode BetScout Pick Card PNG with 4x supersampled sport & brand icons,
    2-line KPI breakdown cards, and dynamic text fitting so zero content is ever cut off."""
    w, h = 1080, 580
    img = Image.new("RGB", (w, h), (9, 13, 21))
    draw = ImageDraw.Draw(img)

    # Rich vertical gradient background with subtle navy depth
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(9 + t * 7)
        g = int(13 + t * 11)
        b = int(21 + t * 18)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    tier_raw = _humanize_raw_market_codes(_strip_non_ascii_symbols(str(pick_data.get("tier") or "HIGH-CONVICTION"))).upper()
    badge_status = _humanize_raw_market_codes(
        _strip_non_ascii_symbols(
            str(pick_data.get("status_badge") or pick_data.get("badge") or tier_raw or "LIVE AI PICK")
        )
    ).upper()
    raw_pick_probe = _strip_non_ascii_symbols(str(pick_data.get("pick_name") or pick_data.get("pick") or "")).upper()
    pnl_val = pick_data.get("pnl_best")
    has_ended = bool(pick_data.get("ended_at_local") or pick_data.get("ended_at"))

    is_loss_card = (
        "LOSS" in badge_status
        or " (L " in f" {raw_pick_probe} "
        or (pnl_val is not None and float(pnl_val) < 0)
    )
    is_win_card = (
        not is_loss_card
        and (
            "WIN" in badge_status
            or "SETTLED" in badge_status
            or " (W " in f" {raw_pick_probe} "
            or (pnl_val is not None and float(pnl_val) > 0)
            or has_ended
        )
    )

    # Top border color-coding: Cyan for Picks, Green for Resolved Wins, Red/Pink for Resolved Losses
    if is_loss_card:
        top_border_col = (244, 63, 94)
    elif is_win_card:
        top_border_col = (34, 197, 94)
    else:
        top_border_col = (56, 189, 248)

    # Outer card frame (app-consistent frosted dark slate palette) + smoothly curved color-coded top border
    _draw_rounded_card_with_top_accent(
        img,
        bbox=(18, 18, w - 18, h - 18),
        radius=20,
        fill_rgb=(13, 20, 35),
        outline_rgb=(42, 59, 92),
        outline_width=2,
        accent_rgb=top_border_col,
        accent_height=3,
    )

    f_brand = _load_font(27, bold=True)
    f_sub = _load_font(13, bold=False)
    f_pick_lbl = _load_font(13, bold=True)
    f_kpi_lbl = _load_font(11, bold=True)
    f_footer = _load_font(13, bold=False)
    f_footer_b = _load_font(13, bold=True)

    # Header: 4x supersampled BetScout logo + two-tone "Bet" (white) + "Scout" (emerald) brand title matching App Header
    logo_bytes = render_logo_png(size=52)
    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    img.paste(logo_img, (44, 40), logo_img)
    bet_w = int(_text_width(draw, "Bet", f_brand))
    draw.text((108, 43), "Bet", font=f_brand, fill=(255, 255, 255))
    draw.text((108 + bet_w, 43), "Scout", font=f_brand, fill=(52, 211, 153))
    draw.text((108, 75), "SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE", font=f_sub, fill=(148, 163, 184))

    sport_cat = _infer_sport_cat(
        " ".join(
            str(x or "")
            for x in (
                pick_data.get("sport_cat"),
                pick_data.get("sport"),
                pick_data.get("sport_league"),
                pick_data.get("competition"),
            )
        )
    )
    comp_raw = _strip_non_ascii_symbols(
        str(pick_data.get("competition") or pick_data.get("sport_league") or SPORT_LABELS.get(sport_cat, "QUANT PICK"))
    )

    # Right header pill (color-coded to match app tier/signal badges!)
    b_fill, b_border, b_text = _get_badge_pill_colors(badge_status, tier_raw, is_win_card=is_win_card, is_loss_card=is_loss_card)
    f_badge, badge_fit = _fit_font_and_text(draw, badge_status, max_width=245, start_size=13, min_size=10, bold=True)
    bw_px = int(_text_width(draw, badge_fit, f_badge)) + 36
    bx_right = w - 44
    bx_left = bx_right - bw_px
    draw.rounded_rectangle([(bx_left, 46), (bx_right, 86)], radius=20, fill=b_fill, outline=b_border, width=2)
    draw.text((bx_left + 18, 58), badge_fit, font=f_badge, fill=b_text)

    # Divider
    draw.line([(44, 106), (w - 44, 106)], fill=(34, 48, 73), width=1)

    # Row 2: Sport-Color-Coded Competition Pill on Left + Muted Timestamp Pill on Right
    kickoff_str = _compact_timestamp(str(pick_data.get("date_local") or pick_data.get("date") or "Upcoming"))
    announced_str = _compact_timestamp(str(pick_data.get("announced_at_local") or pick_data.get("announced_at") or pick_data.get("logged_at") or ""))
    ended_str = _compact_timestamp(str(pick_data.get("ended_at_local") or pick_data.get("ended_at") or ""))

    sport_tag = SPORT_LABELS.get(sport_cat, sport_cat.upper())
    comp_label = f"{sport_tag}  ·  {comp_raw}" if comp_raw.upper() not in sport_tag else sport_tag
    c_fill, c_border, c_text = _get_sport_pill_colors(sport_cat)
    f_comp, comp_fit = _fit_font_and_text(draw, comp_label, max_width=400, start_size=12, min_size=10, bold=True)
    comp_box_w = int(_text_width(draw, comp_fit, f_comp)) + 28
    draw.rounded_rectangle([(44, 118), (44 + comp_box_w, 152)], radius=9, fill=c_fill, outline=c_border, width=1)
    draw.text((58, 128), comp_fit, font=f_comp, fill=c_text)

    # Build right-aligned timestamp pill(s) in muted slate matching app table Kickoff styling
    max_ko_w = max(260, w - 88 - comp_box_w - 14)
    if ended_str:
        # Upon resolution: show Pick date above Start and Ended dates
        pick_line = f"Pick: {announced_str or kickoff_str}"
        span_line = f"Start: {kickoff_str}   |   Ended: {ended_str}"
        f_ko1, ko1_fit = _fit_font_and_text(draw, pick_line, max_width=max_ko_w, start_size=11, min_size=9, bold=False)
        f_ko2, ko2_fit = _fit_font_and_text(draw, span_line, max_width=max_ko_w, start_size=11, min_size=9, bold=True)
        ko_w = max(int(_text_width(draw, ko1_fit, f_ko1)), int(_text_width(draw, ko2_fit, f_ko2))) + 28
        box_left = w - 44 - ko_w
        draw.rounded_rectangle([(box_left, 114), (w - 44, 158)], radius=9, fill=(11, 17, 30), outline=(42, 58, 86), width=1)
        draw.text((box_left + 14, 120), ko1_fit, font=f_ko1, fill=(148, 163, 184))
        draw.text((box_left + 14, 137), ko2_fit, font=f_ko2, fill=(203, 213, 225))
    else:
        time_parts: list[str] = []
        if announced_str:
            time_parts.append(f"Pick: {announced_str}")
        time_parts.append(f"Start: {kickoff_str}")
        ko_label = "   |   ".join(time_parts)
        f_ko, ko_fit = _fit_font_and_text(draw, ko_label, max_width=max_ko_w, start_size=12, min_size=9, bold=False)
        ko_w = int(_text_width(draw, ko_fit, f_ko)) + 24
        draw.rounded_rectangle([(w - 44 - ko_w, 118), (w - 44, 152)], radius=9, fill=(11, 17, 30), outline=(42, 58, 86), width=1)
        draw.text((w - 44 - ko_w + 12, 128), ko_fit, font=f_ko, fill=(148, 163, 184))

    # Matchup Title with Sport Emoji on the left (auto-scaled so long names never clip, with muted 'vs')
    match_raw = _strip_non_ascii_symbols(str(pick_data.get("match") or f"{pick_data.get('home', '')} vs {pick_data.get('away', '')}"))
    _paste_sport_icon(img, sport_cat, 62, 190, size=34)
    f_match, match_fit = _fit_font_and_text(draw, match_raw, max_width=w - 140, start_size=32, min_size=18, bold=True)
    _draw_text_with_muted_vs(
        draw,
        (88, 173),
        match_fit,
        f_match,
        int(getattr(f_match, "size", 28)),
        primary_rgb=(255, 255, 255),
        muted_rgb=(148, 163, 184),
    )

    # Main Pick Highlight Card (emerald for picks/wins, red/pink for resolved losses) with clipped left accent bar
    box_fill = (13, 33, 29) if not is_loss_card else (38, 16, 26)
    box_border = (34, 197, 94) if not is_loss_card else (244, 63, 94)
    draw.rounded_rectangle([(44, 224), (w - 44, 352)], radius=14, fill=box_fill)
    ss_p = 4
    pm_hi = Image.new("L", (w * ss_p, h * ss_p), 0)
    ImageDraw.Draw(pm_hi).rounded_rectangle([45 * ss_p, 225 * ss_p, (w - 45) * ss_p, 351 * ss_p], radius=13 * ss_p, fill=255)
    pa_hi = Image.new("RGBA", (w * ss_p, h * ss_p), (0, 0, 0, 0))
    ImageDraw.Draw(pa_hi).rectangle([44 * ss_p, 224 * ss_p, 53 * ss_p, 352 * ss_p], fill=(*box_border, 255))
    pc_hi = Image.new("RGBA", (w * ss_p, h * ss_p), (0, 0, 0, 0))
    pc_hi.paste(pa_hi, (0, 0), pm_hi)
    pc_sm = pc_hi.resize((w, h), resample=Image.Resampling.LANCZOS)
    img.paste(pc_sm, (0, 0), pc_sm)
    draw.rounded_rectangle([(44, 224), (w - 44, 352)], radius=14, outline=box_border, width=2)
    pick_box_hdr = (
        "RESOLVED PAPER-BET RESULT (LOSS)"
        if is_loss_card
        else ("RESOLVED PAPER-BET RESULT (WIN)" if is_win_card else "RECOMMENDED MODEL PICK")
    )
    draw.text((72, 238), pick_box_hdr, font=f_pick_lbl, fill=(134, 239, 172) if not is_loss_card else (253, 164, 175))

    raw_pick_full = _humanize_raw_market_codes(
        _strip_non_ascii_symbols(str(pick_data.get("pick_name") or pick_data.get("pick") or "Top Model Pick")),
        home=str(pick_data.get("home") or ""),
        away=str(pick_data.get("away") or ""),
    )
    main_pick_line = raw_pick_full
    sub_pick_line = ""
    if " · " in raw_pick_full:
        parts_p = raw_pick_full.split(" · ", 1)
        main_pick_line, sub_pick_line = parts_p[0].strip(), parts_p[1].strip()
    elif " | " in raw_pick_full:
        parts_p = raw_pick_full.split(" | ", 1)
        main_pick_line, sub_pick_line = parts_p[0].strip(), parts_p[1].strip()
    elif "(" in raw_pick_full and raw_pick_full.endswith(")") and not raw_pick_full.startswith("("):
        idx_p = raw_pick_full.rfind("(")
        inner_p = raw_pick_full[idx_p + 1 : -1].strip()
        if inner_p in ("H", "A", "1X", "X2"):
            pass
        elif len(raw_pick_full) > 22:
            main_pick_line = raw_pick_full[:idx_p].strip()
            sub_pick_line = _humanize_raw_market_codes(inner_p)

    f_pick_main, main_pick_fit = _fit_font_and_text(draw, main_pick_line, max_width=w - 144, start_size=28, min_size=16, bold=True)
    draw.text((72, 266), main_pick_fit, font=f_pick_main, fill=box_border)

    if not sub_pick_line:
        esc_candidate = _strip_non_ascii_symbols(str(pick_data.get("exact_score_pick") or ""))
        if esc_candidate and esc_candidate != "—":
            sub_pick_line = f"Score / Set Target: {esc_candidate}"
        else:
            sub_pick_line = f"Conviction Tier: {tier_raw}  ·  Verified Out-of-Sample Quantitative Signal"
    f_pick_sub, sub_pick_fit = _fit_font_and_text(draw, sub_pick_line, max_width=w - 144, start_size=15, min_size=11, bold=False)
    draw.text((72, 314), sub_pick_fit, font=f_pick_sub, fill=(203, 213, 225))

    # 4 KPI Cards Row (app-consistent color-coded top accent bars + Win-Prob progress bar)
    win_prob = pick_data.get("win_prob")
    wp_str_override = _strip_non_ascii_symbols(str(pick_data.get("win_prob_str") or ""))
    if wp_str_override:
        wp_str = wp_str_override
    elif win_prob is not None and float(win_prob) > 0:
        wp_str = f"{float(win_prob) * 100:.1f}%"
    else:
        wp_str = "High Conf"

    odds_val = pick_data.get("odds")
    odds_disp_raw = _strip_non_ascii_symbols(str(pick_data.get("odds_display") or (f"{float(odds_val):.2f}" if odds_val else "—")))
    odds_main, odds_sub = _split_primary_and_sub_kpi(odds_disp_raw)
    if not odds_sub and odds_val:
        odds_sub = "Live Market Price"

    fair_str_override = _strip_non_ascii_symbols(str(pick_data.get("fair_str") or ""))
    fair_val = pick_data.get("min_fair_odds")
    if not fair_val and win_prob and float(win_prob) > 0.05:
        fair_val = 1.0 / float(win_prob)
    fair_str = fair_str_override if fair_str_override else (f"@ {float(fair_val):.2f}" if fair_val else "Calibrated")

    esc_raw = _strip_non_ascii_symbols(str(pick_data.get("exact_score_pick") or pick_data.get("score_proj") or "Moneyline Edge"))
    esc_main, esc_sub = _split_primary_and_sub_kpi(esc_raw)
    if not esc_sub:
        esc_sub = "Dixon-Coles / Set Matrix"

    kpis = [
        ("BOOKMAKER ODDS", odds_main, odds_sub, (251, 191, 36)),
        ("MODEL WIN PROB", wp_str, f"Tier: {tier_raw}", (52, 211, 153)),
        ("MIN FAIR ODDS", fair_str, "Zero-Vig Model Floor", (56, 189, 248)),
        ("SCORE PROJECTION", esc_main, esc_sub, (232, 121, 249)),
    ]
    box_w = (w - 88 - 36) // 4
    for idx, (k_lbl, k_main, k_sub, k_col) in enumerate(kpis):
        bx0 = 44 + idx * (box_w + 12)
        bx1 = bx0 + box_w
        _draw_rounded_card_with_top_accent(
            img,
            bbox=(bx0, 370, bx1, 488),
            radius=12,
            fill_rgb=(10, 16, 29),
            outline_rgb=(38, 54, 84),
            outline_width=1,
            accent_rgb=k_col,
            accent_height=2,
        )
        draw.text((bx0 + 16, 386), k_lbl, font=f_kpi_lbl, fill=(148, 163, 184))
        f_km, km_fit = _fit_font_and_text(draw, k_main, max_width=box_w - 28, start_size=24, min_size=14, bold=True)
        draw.text((bx0 + 16, 412), km_fit, font=f_km, fill=k_col)
        if k_sub:
            f_ks, ks_fit = _fit_font_and_text(draw, k_sub, max_width=box_w - 28, start_size=12, min_size=9, bold=False)
            draw.text((bx0 + 16, 454), ks_fit, font=f_ks, fill=(148, 163, 184))

    # Footer bar (two-tone "Bet" white + "Scout" emerald matching App Header)
    draw.line([(44, 508), (w - 44, 508)], fill=(34, 48, 73), width=1)
    draw.text(
        (44, 524),
        "Out-of-Sample Walk-Forward Validated  ·  Dixon-Coles Score Matrix  ·  ¼-Kelly Risk Sizing",
        font=f_footer,
        fill=(148, 163, 184),
    )
    bet_fw = int(_text_width(draw, "Bet", f_footer_b))
    scout_fw = int(_text_width(draw, "Scout", f_footer_b))
    fx_start = w - 44 - (bet_fw + scout_fw)
    draw.text((fx_start, 524), "Bet", font=f_footer_b, fill=(255, 255, 255))
    draw.text((fx_start + bet_fw, 524), "Scout", font=f_footer_b, fill=(52, 211, 153))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)
    return png_bytes


def render_digest_slate_png(
    picks: list[dict[str, Any]],
    title: str = "DAILY HIGH-CONVICTION PICKS SLATE",
    subtitle: str = "Out-of-Sample Calibrated Multi-Sport Edge & Score Projections",
    output_path: Path | None = None,
) -> bytes:
    """Render a multi-row PNG summary board for a daily digest or multi-pick slate with 4x supersampled sport icons and dynamic text fitting."""
    rows = picks[:10]
    if len(rows) == 1:
        return render_pick_card_png(rows[0], output_path=output_path)

    row_h = 74
    w = 1180
    h = 195 + max(1, len(rows)) * row_h + 65
    img = Image.new("RGB", (w, h), (9, 13, 21))
    draw = ImageDraw.Draw(img)

    # Determine slate state for top border color-coding:
    # Cyan for active Picks slates, Green for Resolved Win recaps, Red/Pink for Resolved Loss recaps
    win_rows = sum(
        1
        for r in rows
        if " (W " in str(r.get("pick_name") or r.get("pick") or "")
        or "WIN" in str(r.get("status_badge") or r.get("badge") or "").upper()
        or (r.get("pnl_best") is not None and float(r.get("pnl_best")) > 0)
    )
    loss_rows = sum(
        1
        for r in rows
        if " (L " in str(r.get("pick_name") or r.get("pick") or "")
        or "LOSS" in str(r.get("status_badge") or r.get("badge") or "").upper()
        or (r.get("pnl_best") is not None and float(r.get("pnl_best")) < 0)
    )
    is_settled_slate = (
        win_rows > 0
        or loss_rows > 0
        or "SETTLED" in title.upper()
        or "RECAP" in title.upper()
    )
    is_loss_slate = is_settled_slate and (loss_rows > win_rows or "LOSS" in title.upper())
    if is_settled_slate:
        slate_top_col = (244, 63, 94) if is_loss_slate else (34, 197, 94)
        slate_badge_lbl = f"SETTLED · {win_rows}W–{loss_rows}L" if (win_rows or loss_rows) else "SETTLED RECAP"
        sb_fill = (46, 16, 28) if is_loss_slate else (10, 38, 28)
        sb_border = (244, 63, 94) if is_loss_slate else (52, 211, 153)
        sb_text = (253, 164, 175) if is_loss_slate else (110, 231, 183)
    else:
        slate_top_col = (56, 189, 248)
        slate_badge_lbl = f"ACTIVE SLATE · {len(rows)} PICKS"
        sb_fill = (10, 34, 48)
        sb_border = (34, 211, 238)
        sb_text = (165, 243, 252)

    _draw_rounded_card_with_top_accent(
        img,
        bbox=(18, 18, w - 18, h - 18),
        radius=18,
        fill_rgb=(13, 20, 35),
        outline_rgb=(42, 59, 92),
        outline_width=2,
        accent_rgb=slate_top_col,
        accent_height=3,
    )

    f_sub = _load_font(13, bold=False)
    f_sub_b = _load_font(13, bold=True)
    f_th = _load_font(12, bold=True)

    # Top-right color-coded badge pill on Slate Board
    f_sbadge, sbadge_fit = _fit_font_and_text(draw, slate_badge_lbl, max_width=220, start_size=12, min_size=10, bold=True)
    sb_w = int(_text_width(draw, sbadge_fit, f_sbadge)) + 32
    sb_right = w - 38
    sb_left = sb_right - sb_w
    draw.rounded_rectangle([(sb_left, 42), (sb_right, 78)], radius=18, fill=sb_fill, outline=sb_border, width=2)
    draw.text((sb_left + 16, 53), sbadge_fit, font=f_sbadge, fill=sb_text)

    logo_bytes = render_logo_png(size=48)
    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    img.paste(logo_img, (42, 40), logo_img)
    f_hdr, hdr_fit = _fit_font_and_text(draw, f"BetScout — {title}", max_width=w - 165 - sb_w, start_size=24, min_size=15, bold=True)
    bet_hw = int(_text_width(draw, "Bet", f_hdr))
    scout_hw = int(_text_width(draw, "Scout", f_hdr))
    draw.text((102, 42), "Bet", font=f_hdr, fill=(255, 255, 255))
    draw.text((102 + bet_hw, 42), "Scout", font=f_hdr, fill=(52, 211, 153))
    rest_title = hdr_fit[len("BetScout") :] if hdr_fit.startswith("BetScout") else f" — {title}"
    draw.text((102 + bet_hw + scout_hw, 42), rest_title, font=f_hdr, fill=(241, 245, 249))
    f_sub_fit, sub_fit = _fit_font_and_text(draw, subtitle, max_width=w - 165 - sb_w, start_size=14, min_size=11, bold=False)
    draw.text((102, 73), sub_fit, font=f_sub_fit, fill=(148, 163, 184))

    # Table Header
    y_head = 116
    draw.rounded_rectangle([(38, y_head), (w - 38, y_head + 38)], radius=8, fill=(13, 20, 33))
    draw.text((50, y_head + 12), "TIMELINE (PICK / START / END)", font=f_th, fill=(148, 163, 184))
    draw.text((262, y_head + 12), "SPORT", font=f_th, fill=(148, 163, 184))
    draw.text((322, y_head + 12), "MATCHUP & SCORE", font=f_th, fill=(148, 163, 184))
    draw.text((645, y_head + 12), "RECOMMENDED PICK", font=f_th, fill=(148, 163, 184))
    draw.text((935, y_head + 12), "WIN PROB", font=f_th, fill=(148, 163, 184))
    draw.text((1035, y_head + 12), "ODDS", font=f_th, fill=(148, 163, 184))

    y_cur = y_head + 46
    for idx, p in enumerate(rows):
        bg_col = (13, 20, 33) if idx % 2 == 1 else (19, 27, 43)
        draw.rounded_rectangle([(38, y_cur), (w - 38, y_cur + row_h - 6)], radius=8, fill=bg_col, outline=(30, 41, 59), width=1)
        row_sp = _infer_sport_cat(
            " ".join(
                str(x or "")
                for x in (
                    p.get("sport_cat"),
                    p.get("sport"),
                    p.get("sport_league"),
                    p.get("competition"),
                )
            )
        )
        tm_start = _compact_timestamp(str(p.get("date_local") or p.get("date") or ""))
        tm_end = _compact_timestamp(str(p.get("ended_at_local") or p.get("ended_at") or ""))
        tm_ann = _compact_timestamp(str(p.get("announced_at_local") or p.get("announced_at") or p.get("logged_at") or ""))

        mt_raw = _strip_non_ascii_symbols(str(p.get("match") or f"{p.get('home','')} vs {p.get('away','')}"))
        mt_score_sub = _strip_non_ascii_symbols(str(p.get("settled_score") or p.get("score_str") or ""))
        if "[" in mt_raw and mt_raw.endswith("]"):
            b_idx = mt_raw.rfind("[")
            extracted_sc = mt_raw[b_idx + 1 : -1].strip()
            mt_raw = mt_raw[:b_idx].strip()
            if not mt_score_sub and extracted_sc:
                mt_score_sub = extracted_sc

        pk_raw = _strip_non_ascii_symbols(str(p.get("pick_name") or p.get("pick") or ""))
        pk_clean = pk_raw.split("[")[0].split("(Win")[0].strip() or pk_raw
        # Extract settled result suffix like '(W +0.32u)' or '(L -1.00u)' before splitting
        settled_res_sub = ""
        if " (W " in pk_clean or " (L " in pk_clean:
            tag_idx = pk_clean.rfind(" (W ") if " (W " in pk_clean else pk_clean.rfind(" (L ")
            settled_res_sub = pk_clean[tag_idx + 2 : -1].strip()
            pk_clean = pk_clean[:tag_idx].strip()
        pk_main, pk_sub = _split_primary_and_sub_kpi(pk_clean)
        if settled_res_sub and not pk_sub:
            pk_sub = settled_res_sub
        elif not pk_sub:
            esc_row = _strip_non_ascii_symbols(str(p.get("exact_score_pick") or ""))
            if esc_row and esc_row != "—":
                pk_sub = esc_row.split("|")[0].split("·")[0].strip()

        wp = p.get("win_prob")
        wp_s = f"{float(wp)*100:.1f}%" if wp else "—"
        od_raw = _strip_non_ascii_symbols(str(p.get("odds_display") or f"{float(p.get('odds') or 0):.2f}"))
        od_main, _ = _split_primary_and_sub_kpi(od_raw)

        f_mt, mt_fit = _fit_font_and_text(draw, mt_raw, max_width=310, start_size=15, min_size=11, bold=True)
        f_pk, pk_fit = _fit_font_and_text(draw, pk_main, max_width=275, start_size=15, min_size=11, bold=True)
        f_wp, wp_fit = _fit_font_and_text(draw, wp_s, max_width=88, start_size=15, min_size=11, bold=True)
        f_od, od_fit = _fit_font_and_text(draw, od_main, max_width=95, start_size=15, min_size=11, bold=True)

        if tm_end:
            pick_dt_str = tm_ann or tm_start
            f_t0, t0_fit = _fit_font_and_text(draw, f"Pick: {pick_dt_str}", max_width=202, start_size=10, min_size=9, bold=False)
            f_t1, t1_fit = _fit_font_and_text(draw, f"Start: {tm_start}", max_width=202, start_size=10, min_size=9, bold=True)
            f_t2, t2_fit = _fit_font_and_text(draw, f"Ended: {tm_end}", max_width=202, start_size=10, min_size=9, bold=False)
            draw.text((50, y_cur + 8), t0_fit, font=f_t0, fill=(148, 163, 184))
            draw.text((50, y_cur + 26), t1_fit, font=f_t1, fill=(203, 213, 225))
            draw.text((50, y_cur + 44), t2_fit, font=f_t2, fill=(56, 189, 248))
        elif tm_ann:
            f_t0, t0_fit = _fit_font_and_text(draw, f"Pick: {tm_ann}", max_width=202, start_size=11, min_size=9, bold=False)
            f_t1, t1_fit = _fit_font_and_text(draw, f"Start: {tm_start}", max_width=202, start_size=11, min_size=9, bold=True)
            draw.text((50, y_cur + 14), t0_fit, font=f_t0, fill=(148, 163, 184))
            draw.text((50, y_cur + 36), t1_fit, font=f_t1, fill=(203, 213, 225))
        else:
            f_tm, tm_fit = _fit_font_and_text(draw, tm_start, max_width=202, start_size=12, min_size=10, bold=True)
            draw.text((50, y_cur + 25), tm_fit, font=f_tm, fill=(203, 213, 225))

        # Dedicated Sport Emoji column spanning the height of both the Matchup row and the Score row (38x38px)
        _paste_sport_icon(img, row_sp, 286, y_cur + 34, size=38)

        if mt_score_sub:
            _draw_text_with_muted_vs(
                draw,
                (322, y_cur + 13),
                mt_fit,
                f_mt,
                int(getattr(f_mt, "size", 15)),
                primary_rgb=(241, 245, 249),
                muted_rgb=(148, 163, 184),
            )
            score_line = f"Score: {mt_score_sub}" if not mt_score_sub.lower().startswith("score") else mt_score_sub
            f_ms, ms_fit = _fit_font_and_text(draw, score_line, max_width=310, start_size=12, min_size=9, bold=False)
            draw.text((322, y_cur + 37), ms_fit, font=f_ms, fill=(148, 163, 184))
        else:
            _draw_text_with_muted_vs(
                draw,
                (322, y_cur + 24),
                mt_fit,
                f_mt,
                int(getattr(f_mt, "size", 15)),
                primary_rgb=(241, 245, 249),
                muted_rgb=(148, 163, 184),
            )

        pk_col = (34, 197, 94) if "LOSS" not in pk_clean and "(L " not in pk_raw else (244, 63, 94)
        if pk_sub:
            draw.text((645, y_cur + 13), pk_fit, font=f_pk, fill=pk_col)
            sub_col = (
                (244, 63, 94)
                if pk_sub.startswith("L ")
                else ((52, 211, 153) if pk_sub.startswith("W ") else (148, 163, 184))
            )
            f_pks, pks_fit = _fit_font_and_text(draw, pk_sub, max_width=275, start_size=12, min_size=9, bold=False)
            draw.text((645, y_cur + 37), pks_fit, font=f_pks, fill=sub_col)
        else:
            draw.text((645, y_cur + 24), pk_fit, font=f_pk, fill=pk_col)
        draw.text((935, y_cur + 24), wp_fit, font=f_wp, fill=(56, 189, 248))
        draw.text((1035, y_cur + 24), od_fit, font=f_od, fill=(245, 158, 11))
        y_cur += row_h

    draw.text(
        (42, h - 46),
        "Out-of-Sample Walk-Forward Validated  ·  Dixon-Coles Score Matrix  ·  ¼-Kelly Risk Sizing",
        font=f_sub,
        fill=(148, 163, 184),
    )
    bet_sfw = int(_text_width(draw, "Bet", f_sub_b))
    scout_sfw = int(_text_width(draw, "Scout", f_sub_b))
    sfx = w - 42 - (bet_sfw + scout_sfw)
    draw.text((sfx, h - 46), "Bet", font=f_sub_b, fill=(255, 255, 255))
    draw.text((sfx + bet_sfw, h - 46), "Scout", font=f_sub_b, fill=(52, 211, 153))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)
    return png_bytes
