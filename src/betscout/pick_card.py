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
}


def _infer_sport_cat(raw_val: str | None) -> str:
    low = str(raw_val or "").lower().strip()
    if not low:
        return "soccer"
    if "table_tennis" in low or "table tennis" in low:
        return "table_tennis"
    if "handball" in low:
        return "handball"
    if "darts" in low:
        return "darts"
    if "tennis" in low or low in ("atp", "wta"):
        return "tennis"
    if "volleyball" in low:
        return "volleyball"
    if "basketball" in low or low in ("nba", "wnba", "ncaam", "ncaaw", "fiba", "nbl"):
        return "basketball"
    if "hockey" in low or low == "nhl":
        return "hockey"
    if "american football" in low or low in ("nfl", "football"):
        return "football"
    if "baseball" in low or low == "mlb":
        return "baseball"
    return "soccer"


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
    """Render a high-resolution supersampled (4x AA) RGBA PNG of the BetScout hexagonal radar-shield logo."""
    import math

    scale = 4
    S = size * scale
    cx = cy = S / 2.0
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Hexagon vertices (matching SVG viewBox 0..64 -> radius ~ 29/64 of width)
    R_outer = S * (29.0 / 64.0)
    hex_pts = [
        (cx + R_outer * math.cos(math.radians(-90 + i * 60)), cy + R_outer * math.sin(math.radians(-90 + i * 60)))
        for i in range(6)
    ]

    # Create mask for interior of hexagon
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(hex_pts, fill=255)

    # Diagonal gradient background inside hexagon (#0f172a -> #131b29 -> #0b2436)
    bg = Image.new("RGBA", (S, S), (15, 23, 42, 255))
    bg_draw = ImageDraw.Draw(bg, "RGBA")
    for y in range(S):
        t = y / max(1, S - 1)
        r = int(15 * (1 - t) + 11 * t)
        g = int(23 * (1 - t) + 36 * t)
        b = int(42 * (1 - t) + 54 * t)
        bg_draw.line([(0, y), (S, y)], fill=(r, g, b, 255))
    img.paste(bg, (0, 0), mask)

    # Radar sweep sector (-90 deg to -25 deg)
    r_outer_ring = S * (19.0 / 64.0)
    r_inner_ring = S * (11.0 / 64.0)
    draw.pieslice(
        [(cx - r_outer_ring, cy - r_outer_ring), (cx + r_outer_ring, cy + r_outer_ring)],
        start=-90,
        end=-25,
        fill=(34, 197, 94, 48),
    )

    # Outer hex border (cyan-emerald gradient rim)
    rim_w = max(4, int(S * (2.4 / 64.0)))
    for i in range(6):
        p1 = hex_pts[i]
        p2 = hex_pts[(i + 1) % 6]
        col = (56, 189, 248, 255) if i in (0, 4, 5) else ((16, 185, 129, 255) if i in (1, 3) else (34, 197, 94, 255))
        draw.line([p1, p2], fill=col, width=rim_w)
        draw.ellipse([(p1[0] - rim_w / 2, p1[1] - rim_w / 2), (p1[0] + rim_w / 2, p1[1] + rim_w / 2)], fill=col)

    # Dashed outer radar ring (r = 19/64)
    dash_w = max(2, int(S * (1.2 / 64.0)))
    for deg in range(0, 360, 15):
        draw.arc(
            [(cx - r_outer_ring, cy - r_outer_ring), (cx + r_outer_ring, cy + r_outer_ring)],
            start=deg,
            end=deg + 9,
            fill=(56, 189, 248, 72),
            width=dash_w,
        )

    # Solid inner reticle ring (r = 11/64)
    draw.ellipse(
        [(cx - r_inner_ring, cy - r_inner_ring), (cx + r_inner_ring, cy + r_inner_ring)],
        outline=(56, 189, 248, 90),
        width=max(2, int(S * (1.1 / 64.0))),
    )

    # Cardinal crosshair ticks (N, S, W, E)
    tick_w = max(3, int(S * (1.8 / 64.0)))
    t_out = S * (23.5 / 64.0)
    t_in = S * (18.5 / 64.0)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        draw.line(
            [(cx + dx * t_in, cy + dy * t_in), (cx + dx * t_out, cy + dy * t_out)],
            fill=(56, 189, 248, 195),
            width=tick_w,
        )

    # Rising Scout Edge Vector (M16 44 L27 33 L33 38 L46 18 in 64x64 space)
    def _pt(ux: float, uy: float) -> tuple[float, float]:
        return (S * (ux / 64.0), S * (uy / 64.0))

    v_pts = [_pt(16, 44), _pt(27, 33), _pt(33, 38), _pt(46, 18)]
    vec_w = max(6, int(S * (3.8 / 64.0)))
    # Soft glow pass
    glow_w = int(vec_w * 2.1)
    draw.line(v_pts, fill=(34, 197, 94, 55), width=glow_w, joint="curve")
    # Main vector segments (cyan -> mint -> emerald)
    draw.line([v_pts[0], v_pts[1]], fill=(56, 189, 248, 255), width=vec_w)
    draw.line([v_pts[1], v_pts[2]], fill=(52, 211, 153, 255), width=vec_w)
    draw.line([v_pts[2], v_pts[3]], fill=(34, 197, 94, 255), width=vec_w)
    for vx, vy in v_pts:
        draw.ellipse([(vx - vec_w / 2, vy - vec_w / 2), (vx + vec_w / 2, vy + vec_w / 2)], fill=(52, 211, 153, 255))

    # Arrowhead at (46, 18)
    ah_pts = [_pt(39.5, 17.5), _pt(46.5, 17.5), _pt(46.5, 24.5)]
    ah_w = max(5, int(S * (3.0 / 64.0)))
    draw.line(ah_pts, fill=(34, 197, 94, 255), width=ah_w, joint="curve")

    # Mid-node at (27, 33)
    m_pt = _pt(27, 33)
    mr = S * (2.5 / 64.0)
    draw.ellipse([(m_pt[0] - mr, m_pt[1] - mr), (m_pt[0] + mr, m_pt[1] + mr)], fill=(56, 189, 248, 255))

    # Target lock ring & center dot at (46, 18)
    t_pt = _pt(46, 18)
    tr_outer = S * (5.6 / 64.0)
    tr_inner = S * (2.8 / 64.0)
    draw.ellipse(
        [(t_pt[0] - tr_outer, t_pt[1] - tr_outer), (t_pt[0] + tr_outer, t_pt[1] + tr_outer)],
        outline=(34, 197, 94, 140),
        width=max(2, int(S * (1.3 / 64.0))),
    )
    draw.ellipse([(t_pt[0] - tr_inner, t_pt[1] - tr_inner), (t_pt[0] + tr_inner, t_pt[1] + tr_inner)], fill=(34, 197, 94, 255))

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


def render_pick_card_png(
    pick_data: dict[str, Any],
    output_path: Path | None = None,
) -> bytes:
    """Render a 1080x580 dark-mode BetScout Pick Card PNG with dynamic text measurement so zero text is ever cut off."""
    w, h = 1080, 580
    img = Image.new("RGB", (w, h), (11, 15, 23))
    draw = ImageDraw.Draw(img)

    # Subtle background gradient
    for y in range(h):
        r = int(11 + (y / h) * 6)
        g = int(15 + (y / h) * 10)
        b = int(23 + (y / h) * 16)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Outer card frame & top accent bar
    draw.rounded_rectangle([(20, 20), (w - 20, h - 20)], radius=20, fill=(19, 27, 41), outline=(34, 48, 73), width=2)
    draw.rounded_rectangle([(22, 22), (w - 22, 28)], radius=4, fill=(56, 189, 248))

    f_brand = _load_font(26, bold=True)
    f_sub = _load_font(14, bold=False)
    f_pill = _load_font(13, bold=True)
    f_pick_lbl = _load_font(14, bold=True)
    f_kpi_lbl = _load_font(12, bold=True)
    f_footer = _load_font(13, bold=False)

    # Header: Logo + BetScout brand
    _draw_betscout_shield(draw, 66, 68, radius=24)
    draw.text((104, 45), "BETSCOUT", font=f_brand, fill=(230, 237, 247))
    draw.text((104, 76), "SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE", font=f_sub, fill=(139, 155, 180))

    sport_cat = _infer_sport_cat(pick_data.get("sport_cat") or pick_data.get("sport") or pick_data.get("competition") or "soccer")
    comp_raw = _strip_non_ascii_symbols(
        str(pick_data.get("competition") or pick_data.get("sport_league") or SPORT_LABELS.get(sport_cat, "QUANT PICK"))
    )
    tier_raw = _strip_non_ascii_symbols(str(pick_data.get("tier") or "HIGH-CONVICTION")).upper()
    badge_status = _strip_non_ascii_symbols(str(pick_data.get("status_badge") or tier_raw or "LIVE AI SIGNAL")).upper()

    # Right header pill (auto-sized width)
    badge_col = (34, 197, 94) if "LOSS" not in badge_status else (239, 68, 68)
    f_badge, badge_fit = _fit_font_and_text(draw, badge_status, max_width=240, start_size=14, min_size=11, bold=True)
    bw_px = int(_text_width(draw, badge_fit, f_badge)) + 36
    draw.rounded_rectangle([(w - 48 - bw_px, 48), (w - 48, 86)], radius=18, fill=(15, 23, 42), outline=badge_col, width=2)
    draw.text((w - 48 - bw_px + 18, 59), badge_fit, font=f_badge, fill=badge_col)

    # Divider
    draw.line([(48, 110), (w - 48, 110)], fill=(34, 48, 73), width=1)

    # Competition (with Vector Sport Icon!) & Timestamps (Announced · Start · Ended) row
    kickoff_str = _strip_non_ascii_symbols(str(pick_data.get("date_local") or pick_data.get("date") or "Upcoming Slate"))
    announced_str = _strip_non_ascii_symbols(str(pick_data.get("announced_at_local") or pick_data.get("announced_at") or pick_data.get("logged_at") or ""))
    ended_str = _strip_non_ascii_symbols(str(pick_data.get("ended_at_local") or pick_data.get("ended_at") or ""))

    sport_tag = SPORT_LABELS.get(sport_cat, sport_cat.upper())
    comp_label = f"{sport_tag}  ·  {comp_raw}" if comp_raw.upper() not in sport_tag else sport_tag
    f_comp, comp_fit = _fit_font_and_text(draw, comp_label, max_width=430, start_size=13, min_size=10, bold=True)
    comp_box_w = int(_text_width(draw, comp_fit, f_comp)) + 54
    draw.rounded_rectangle([(48, 122), (48 + comp_box_w, 156)], radius=8, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
    _draw_sport_icon(draw, sport_cat, 68, 139, radius=11)
    draw.text((88, 131), comp_fit, font=f_comp, fill=(56, 189, 248))

    # Build right-aligned timeline string: Announced | Start | Ended (if ended)
    time_parts: list[str] = []
    if announced_str:
        time_parts.append(f"ANNOUNCED: {announced_str}")
    time_parts.append(f"START: {kickoff_str}")
    if ended_str:
        time_parts.append(f"ENDED: {ended_str}")
    ko_label = "   ·   ".join(time_parts)
    max_ko_w = w - 96 - comp_box_w - 16
    f_ko, ko_fit = _fit_font_and_text(draw, ko_label, max_width=max(260, max_ko_w), start_size=12, min_size=10, bold=True)
    ko_w = int(_text_width(draw, ko_fit, f_ko))
    draw.text((w - 48 - ko_w, 132), ko_fit, font=f_ko, fill=(148, 163, 184))

    # Matchup Title (auto-scaled so long team/player names never get cut off)
    match_raw = _strip_non_ascii_symbols(str(pick_data.get("match") or f"{pick_data.get('home', '')} vs {pick_data.get('away', '')}"))
    f_match, match_fit = _fit_font_and_text(draw, match_raw, max_width=w - 96, start_size=34, min_size=20, bold=True)
    draw.text((48, 174), match_fit, font=f_match, fill=(255, 255, 255))

    # Main Pick Highlight Box (Clean 2-line layout without overlapping right-hand tier box!)
    draw.rounded_rectangle([(48, 232), (w - 48, 352)], radius=14, fill=(13, 31, 28), outline=(34, 197, 94), width=2)
    draw.text((70, 246), "RECOMMENDED MODEL PICK", font=f_pick_lbl, fill=(134, 239, 172))

    # Clean pick string: separate main team/player pick from any secondary score suffix
    raw_pick_full = _strip_non_ascii_symbols(str(pick_data.get("pick_name") or pick_data.get("pick") or "Top Model Pick"))
    main_pick_line = raw_pick_full
    sub_pick_line = ""
    if " · " in raw_pick_full:
        parts_p = raw_pick_full.split(" · ", 1)
        main_pick_line, sub_pick_line = parts_p[0].strip(), parts_p[1].strip()
    elif " | " in raw_pick_full:
        parts_p = raw_pick_full.split(" | ", 1)
        main_pick_line, sub_pick_line = parts_p[0].strip(), parts_p[1].strip()

    f_pick_main, main_pick_fit = _fit_font_and_text(draw, main_pick_line, max_width=w - 140, start_size=28, min_size=17, bold=True)
    draw.text((70, 272), main_pick_fit, font=f_pick_main, fill=(34, 197, 94))

    if not sub_pick_line:
        esc_candidate = _strip_non_ascii_symbols(str(pick_data.get("exact_score_pick") or ""))
        if esc_candidate and esc_candidate != "—":
            sub_pick_line = f"Score / Set Target: {esc_candidate}"
        else:
            sub_pick_line = f"Conviction Tier: {tier_raw}  ·  Verified Out-of-Sample Quantitative Signal"
    f_pick_sub, sub_pick_fit = _fit_font_and_text(draw, sub_pick_line, max_width=w - 140, start_size=15, min_size=12, bold=False)
    draw.text((70, 316), sub_pick_fit, font=f_pick_sub, fill=(203, 213, 225))

    # 4 KPI Boxes Row (Odds, Win Prob, Min Fair Odds, Score / Dutch Projection)
    win_prob = pick_data.get("win_prob")
    wp_str = f"{float(win_prob) * 100:.1f}%" if win_prob is not None and float(win_prob) > 0 else "High Conf"
    odds_val = pick_data.get("odds")
    odds_disp = _strip_non_ascii_symbols(str(pick_data.get("odds_display") or (f"{float(odds_val):.2f}" if odds_val else "—")))
    fair_val = pick_data.get("min_fair_odds")
    if not fair_val and win_prob and float(win_prob) > 0.05:
        fair_val = 1.0 / float(win_prob)
    fair_str = f"@ {float(fair_val):.2f}" if fair_val else "Calibrated"
    esc_raw = _strip_non_ascii_symbols(str(pick_data.get("exact_score_pick") or pick_data.get("score_proj") or "Moneyline Edge"))
    # Clean compact score projection for KPI box #4
    esc_short = esc_raw.split("|")[0].strip() if "|" in esc_raw else esc_raw

    kpis = [
        ("BOOKMAKER ODDS", odds_disp, (34, 197, 94)),
        ("MODEL WIN PROB", wp_str, (56, 189, 248)),
        ("MIN FAIR ODDS", fair_str, (230, 237, 247)),
        ("SCORE PROJECTION", esc_short, (245, 158, 11)),
    ]
    box_w = (w - 96 - 36) // 4
    for idx, (k_lbl, k_val, k_col) in enumerate(kpis):
        bx0 = 48 + idx * (box_w + 12)
        bx1 = bx0 + box_w
        draw.rounded_rectangle([(bx0, 374), (bx1, 482)], radius=12, fill=(15, 22, 35), outline=(34, 48, 73), width=1)
        draw.text((bx0 + 16, 390), k_lbl, font=f_kpi_lbl, fill=(139, 155, 180))
        f_kv, kv_fit = _fit_font_and_text(draw, k_val, max_width=box_w - 30, start_size=24, min_size=13, bold=True)
        draw.text((bx0 + 16, 422), kv_fit, font=f_kv, fill=k_col)

    # Footer bar
    draw.line([(48, 506), (w - 48, 506)], fill=(34, 48, 73), width=1)
    draw.text(
        (48, 522),
        "Out-of-Sample Walk-Forward Validated  ·  Dixon-Coles Score Matrix  ·  ¼-Kelly Risk Sizing",
        font=f_footer,
        fill=(139, 155, 180),
    )
    footer_r = "betscout.app · Quant Desk"
    fr_w = int(_text_width(draw, footer_r, f_footer))
    draw.text((w - 48 - fr_w, 522), footer_r, font=f_footer, fill=(56, 189, 248))

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
    """Render a multi-row PNG summary board for a daily digest or multi-pick slate with dynamic text fitting."""
    rows = picks[:10]
    if len(rows) == 1:
        return render_pick_card_png(rows[0], output_path=output_path)

    row_h = 66
    w = 1160
    h = 195 + max(1, len(rows)) * row_h + 65
    img = Image.new("RGB", (w, h), (11, 15, 23))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(18, 18), (w - 18, h - 18)], radius=18, fill=(19, 27, 41), outline=(34, 48, 73), width=2)
    draw.rounded_rectangle([(20, 20), (w - 20, 26)], radius=4, fill=(56, 189, 248))

    f_sub = _load_font(14, bold=False)
    f_th = _load_font(13, bold=True)

    _draw_betscout_shield(draw, 62, 64, radius=22)
    f_hdr, hdr_fit = _fit_font_and_text(draw, f"BETSCOUT — {title}", max_width=w - 130, start_size=24, min_size=16, bold=True)
    draw.text((98, 43), hdr_fit, font=f_hdr, fill=(230, 237, 247))
    f_sub_fit, sub_fit = _fit_font_and_text(draw, subtitle, max_width=w - 130, start_size=14, min_size=11, bold=False)
    draw.text((98, 74), sub_fit, font=f_sub_fit, fill=(139, 155, 180))

    # Table Header
    y_head = 118
    draw.rounded_rectangle([(38, y_head), (w - 38, y_head + 38)], radius=8, fill=(15, 22, 35))
    draw.text((50, y_head + 11), "START / END TIME", font=f_th, fill=(148, 163, 184))
    draw.text((255, y_head + 11), "SPORT & MATCHUP", font=f_th, fill=(148, 163, 184))
    draw.text((610, y_head + 11), "RECOMMENDED PICK", font=f_th, fill=(148, 163, 184))
    draw.text((915, y_head + 11), "WIN PROB", font=f_th, fill=(148, 163, 184))
    draw.text((1020, y_head + 11), "ODDS", font=f_th, fill=(148, 163, 184))

    y_cur = y_head + 46
    for idx, p in enumerate(rows):
        bg_col = (15, 22, 35) if idx % 2 == 1 else (19, 27, 41)
        draw.rounded_rectangle([(38, y_cur), (w - 38, y_cur + row_h - 6)], radius=8, fill=bg_col, outline=(30, 41, 59), width=1)
        row_sp = _infer_sport_cat(p.get("sport_cat") or p.get("sport_league") or p.get("competition") or "soccer")
        tm_start = _strip_non_ascii_symbols(str(p.get("date_local") or p.get("date") or ""))
        tm_end = _strip_non_ascii_symbols(str(p.get("ended_at_local") or p.get("ended_at") or ""))
        tm_ann = _strip_non_ascii_symbols(str(p.get("announced_at_local") or p.get("announced_at") or ""))
        mt = _strip_non_ascii_symbols(str(p.get("match") or f"{p.get('home','')} vs {p.get('away','')}"))
        pk_raw = _strip_non_ascii_symbols(str(p.get("pick_name") or p.get("pick") or ""))
        pk_clean = pk_raw.split("[")[0].split("(Win")[0].strip() or pk_raw
        wp = p.get("win_prob")
        wp_s = f"{float(wp)*100:.1f}%" if wp else "—"
        od_s = _strip_non_ascii_symbols(str(p.get("odds_display") or f"{float(p.get('odds') or 0):.2f}"))

        f_mt, mt_fit = _fit_font_and_text(draw, mt, max_width=320, start_size=15, min_size=12, bold=True)
        f_pk, pk_fit = _fit_font_and_text(draw, pk_clean, max_width=290, start_size=15, min_size=12, bold=True)
        f_wp, wp_fit = _fit_font_and_text(draw, wp_s, max_width=95, start_size=15, min_size=12, bold=True)
        f_od, od_fit = _fit_font_and_text(draw, od_s, max_width=95, start_size=15, min_size=12, bold=True)

        if tm_end:
            f_t1, t1_fit = _fit_font_and_text(draw, f"Start: {tm_start}", max_width=195, start_size=12, min_size=10, bold=False)
            f_t2, t2_fit = _fit_font_and_text(draw, f"Ended: {tm_end}", max_width=195, start_size=11, min_size=10, bold=False)
            draw.text((50, y_cur + 11), t1_fit, font=f_t1, fill=(148, 163, 184))
            draw.text((50, y_cur + 31), t2_fit, font=f_t2, fill=(56, 189, 248))
        elif tm_ann:
            f_t1, t1_fit = _fit_font_and_text(draw, f"Start: {tm_start}", max_width=195, start_size=12, min_size=10, bold=True)
            f_t2, t2_fit = _fit_font_and_text(draw, f"Ann: {tm_ann}", max_width=195, start_size=11, min_size=10, bold=False)
            draw.text((50, y_cur + 11), t1_fit, font=f_t1, fill=(203, 213, 225))
            draw.text((50, y_cur + 31), t2_fit, font=f_t2, fill=(139, 155, 180))
        else:
            f_tm, tm_fit = _fit_font_and_text(draw, tm_start, max_width=195, start_size=13, min_size=11, bold=False)
            draw.text((50, y_cur + 21), tm_fit, font=f_tm, fill=(148, 163, 184))

        _draw_sport_icon(draw, row_sp, 268, y_cur + 30, radius=11)
        draw.text((288, y_cur + 20), mt_fit, font=f_mt, fill=(230, 237, 247))
        draw.text((610, y_cur + 20), pk_fit, font=f_pk, fill=(34, 197, 94) if "LOSS" not in pk_clean and "(L " not in pk_clean else (239, 68, 68))
        draw.text((915, y_cur + 20), wp_fit, font=f_wp, fill=(56, 189, 248))
        draw.text((1020, y_cur + 20), od_fit, font=f_od, fill=(245, 158, 11))
        y_cur += row_h

    draw.text(
        (42, h - 46),
        "BetScout Quantitative Desk (betscout.app)  ·  59,062 Verified Matches Across 7 Sports & 27 Championships",
        font=f_sub,
        fill=(139, 155, 180),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)
    return png_bytes
