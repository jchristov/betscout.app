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
    "volleyball": "NCAA VOLLEYBALL",
    "hockey": "ICE HOCKEY / NHL",
    "football": "AMERICAN FOOTBALL / NFL",
    "baseball": "BASEBALL / MLB",
}


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


def _draw_vektorpulse_shield(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int = 24) -> None:
    """Draw the VektorPulse hexagonal shield & emerald pulse wave."""
    import math

    pts: list[tuple[float, float]] = []
    for i in range(6):
        ang = math.radians(-90 + i * 60)
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    draw.polygon(pts, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    wave = [
        (cx - radius * 0.62, cy + 1),
        (cx - radius * 0.30, cy + 1),
        (cx - radius * 0.12, cy + radius * 0.42),
        (cx + radius * 0.12, cy - radius * 0.48),
        (cx + radius * 0.32, cy + radius * 0.10),
        (cx + radius * 0.62, cy - radius * 0.32),
    ]
    draw.line(wave, fill=(34, 197, 94), width=3)


def _strip_non_ascii_symbols(text: str) -> str:
    """Strip emoji codepoints that standard system TTFs don't render while preserving accented European letters."""
    out: list[str] = []
    for ch in str(text or ""):
        cp = ord(ch)
        if cp > 0x2000 and cp not in (0x2013, 0x2014, 0x20AC, 0x2192, 0x2265, 0x00B7):
            continue
        out.append(ch)
    return " ".join("".join(out).split())


def render_pick_card_png(
    pick_data: dict[str, Any],
    output_path: Path | None = None,
) -> bytes:
    """Render a 1080x580 dark-mode VektorPulse Pick Card PNG for a single pick or settlement alert."""
    w, h = 1080, 580
    img = Image.new("RGB", (w, h), (11, 15, 23))
    draw = ImageDraw.Draw(img)

    # Subtle background gradient & glow accents
    for y in range(h):
        r = int(11 + (y / h) * 6)
        g = int(15 + (y / h) * 10)
        b = int(23 + (y / h) * 16)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Outer card frame
    draw.rounded_rectangle([(20, 20), (w - 20, h - 20)], radius=20, fill=(19, 27, 41), outline=(34, 48, 73), width=2)
    # Top accent bar
    draw.rounded_rectangle([(22, 22), (w - 22, 28)], radius=4, fill=(56, 189, 248))

    f_brand = _load_font(26, bold=True)
    f_sub = _load_font(15, bold=False)
    f_pill = _load_font(14, bold=True)
    f_match = _load_font(34, bold=True)
    f_pick_lbl = _load_font(15, bold=True)
    f_pick_val = _load_font(30, bold=True)
    f_kpi_lbl = _load_font(13, bold=True)
    f_kpi_val = _load_font(26, bold=True)
    f_footer = _load_font(14, bold=False)

    # Header: Logo + VektorPulse brand
    _draw_vektorpulse_shield(draw, 66, 68, radius=24)
    draw.text((104, 46), "VEKTORPULSE", font=f_brand, fill=(230, 237, 247))
    draw.text((104, 76), "SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE", font=f_sub, fill=(139, 155, 180))

    sport_cat = str(pick_data.get("sport_cat") or pick_data.get("sport") or "soccer").lower()
    comp_raw = _strip_non_ascii_symbols(
        str(pick_data.get("competition") or pick_data.get("sport_league") or SPORT_LABELS.get(sport_cat, "QUANT PICK"))
    )
    tier_raw = _strip_non_ascii_symbols(str(pick_data.get("tier") or "HIGH-CONVICTION EDGE")).upper()
    badge_status = _strip_non_ascii_symbols(str(pick_data.get("status_badge") or "LIVE AI SIGNAL")).upper()

    # Right header pill
    badge_col = (34, 197, 94) if "LOSS" not in badge_status else (239, 68, 68)
    draw.rounded_rectangle([(w - 270, 48), (w - 48, 86)], radius=18, fill=(15, 23, 42), outline=badge_col, width=2)
    draw.text((w - 252, 59), badge_status[:22], font=f_pill, fill=badge_col)

    # Divider
    draw.line([(48, 112), (w - 48, 112)], fill=(34, 48, 73), width=1)

    # Competition & Kickoff meta row
    kickoff_str = _strip_non_ascii_symbols(str(pick_data.get("date_local") or pick_data.get("date") or "Upcoming Slate"))
    sport_tag = SPORT_LABELS.get(sport_cat, sport_cat.upper())
    draw.rounded_rectangle([(48, 128), (48 + min(420, len(comp_raw) * 9 + 36), 160)], radius=8, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
    draw.text((62, 136), f"{sport_tag}  ·  {comp_raw}"[:44], font=f_pill, fill=(56, 189, 248))
    draw.text((w - 48 - len(kickoff_str) * 8 - 60, 136), f"KICKOFF: {kickoff_str}", font=f_pill, fill=(148, 163, 184))

    # Matchup Title
    match_str = _strip_non_ascii_symbols(str(pick_data.get("match") or f"{pick_data.get('home', '')} vs {pick_data.get('away', '')}"))
    if len(match_str) > 46:
        match_str = match_str[:44] + "..."
    draw.text((48, 180), match_str, font=f_match, fill=(255, 255, 255))

    # Main Pick Highlight Box
    draw.rounded_rectangle([(48, 240), (w - 48, 348)], radius=14, fill=(13, 31, 28), outline=(34, 197, 94), width=2)
    draw.text((72, 256), "RECOMMENDED MODEL PICK", font=f_pick_lbl, fill=(134, 239, 172))
    pick_str = _strip_non_ascii_symbols(str(pick_data.get("pick_name") or pick_data.get("pick") or ""))
    if len(pick_str) > 48:
        pick_str = pick_str[:46] + "..."
    draw.text((72, 284), pick_str, font=f_pick_val, fill=(34, 197, 94))

    # Tier pill inside pick box
    draw.rounded_rectangle([(w - 290, 266), (w - 72, 312)], radius=10, fill=(28, 25, 23), outline=(245, 158, 11), width=2)
    draw.text((w - 272, 281), f"TIER: {tier_raw[:16]}", font=f_pill, fill=(245, 158, 11))

    # 4 KPI Boxes Row (Odds, Win Prob, Min Fair Odds, Score / Dutch Projection)
    win_prob = pick_data.get("win_prob")
    wp_str = f"{float(win_prob) * 100:.1f}%" if win_prob is not None and float(win_prob) > 0 else "High Conf"
    odds_val = pick_data.get("odds")
    odds_disp = _strip_non_ascii_symbols(str(pick_data.get("odds_display") or (f"{float(odds_val):.2f}" if odds_val else "—")))
    fair_val = pick_data.get("min_fair_odds")
    if not fair_val and win_prob and float(win_prob) > 0.05:
        fair_val = 1.0 / float(win_prob)
    fair_str = f"@ {float(fair_val):.2f}" if fair_val else "Calibrated"
    esc_str = _strip_non_ascii_symbols(str(pick_data.get("exact_score_pick") or pick_data.get("score_proj") or "Moneyline Edge"))
    if len(esc_str) > 22:
        esc_str = esc_str[:20] + ".."

    kpis = [
        ("BOOKMAKER ODDS", odds_disp[:16], (34, 197, 94)),
        ("MODEL WIN PROB", wp_str, (56, 189, 248)),
        ("MIN FAIR ODDS", fair_str, (230, 237, 247)),
        ("SCORE PROJECTION", esc_str, (245, 158, 11)),
    ]
    box_w = (w - 96 - 36) // 4
    for idx, (k_lbl, k_val, k_col) in enumerate(kpis):
        bx0 = 48 + idx * (box_w + 12)
        bx1 = bx0 + box_w
        draw.rounded_rectangle([(bx0, 372), (bx1, 478)], radius=12, fill=(15, 22, 35), outline=(34, 48, 73), width=1)
        draw.text((bx0 + 18, 390), k_lbl, font=f_kpi_lbl, fill=(139, 155, 180))
        draw.text((bx0 + 18, 420), k_val, font=f_kpi_val, fill=k_col)

    # Footer bar
    draw.line([(48, 504), (w - 48, 504)], fill=(34, 48, 73), width=1)
    draw.text(
        (48, 520),
        "Out-of-Sample Walk-Forward Validated  ·  Dixon-Coles Score Matrix  ·  ¼-Kelly Risk Sizing",
        font=f_footer,
        fill=(139, 155, 180),
    )
    draw.text((w - 285, 520), "vektorpulse.ai · Quant Desk", font=f_footer, fill=(56, 189, 248))

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
    """Render a multi-row PNG summary board for a daily digest or multi-pick slate."""
    rows = picks[:10]
    if len(rows) == 1:
        return render_pick_card_png(rows[0], output_path=output_path)

    row_h = 66
    w = 1120
    h = 195 + max(1, len(rows)) * row_h + 65
    img = Image.new("RGB", (w, h), (11, 15, 23))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(18, 18), (w - 18, h - 18)], radius=18, fill=(19, 27, 41), outline=(34, 48, 73), width=2)
    draw.rounded_rectangle([(20, 20), (w - 20, 26)], radius=4, fill=(56, 189, 248))

    f_brand = _load_font(24, bold=True)
    f_sub = _load_font(14, bold=False)
    f_th = _load_font(13, bold=True)
    f_td = _load_font(16, bold=False)
    f_td_b = _load_font(16, bold=True)

    _draw_vektorpulse_shield(draw, 62, 64, radius=22)
    draw.text((98, 43), f"VEKTORPULSE — {_strip_non_ascii_symbols(title)}", font=f_brand, fill=(230, 237, 247))
    draw.text((98, 73), _strip_non_ascii_symbols(subtitle), font=f_sub, fill=(139, 155, 180))

    # Table Header
    y_head = 118
    draw.rounded_rectangle([(38, y_head), (w - 38, y_head + 38)], radius=8, fill=(15, 22, 35))
    draw.text((52, y_head + 11), "KICKOFF", font=f_th, fill=(148, 163, 184))
    draw.text((225, y_head + 11), "MATCHUP", font=f_th, fill=(148, 163, 184))
    draw.text((595, y_head + 11), "RECOMMENDED PICK", font=f_th, fill=(148, 163, 184))
    draw.text((865, y_head + 11), "WIN PROB", font=f_th, fill=(148, 163, 184))
    draw.text((975, y_head + 11), "ODDS", font=f_th, fill=(148, 163, 184))

    y_cur = y_head + 46
    for idx, p in enumerate(rows):
        bg_col = (15, 22, 35) if idx % 2 == 1 else (19, 27, 41)
        draw.rounded_rectangle([(38, y_cur), (w - 38, y_cur + row_h - 6)], radius=8, fill=bg_col, outline=(30, 41, 59), width=1)
        tm = _strip_non_ascii_symbols(str(p.get("date_local") or p.get("date") or ""))[:18]
        mt = _strip_non_ascii_symbols(str(p.get("match") or f"{p.get('home','')} vs {p.get('away','')}"))[:32]
        pk = _strip_non_ascii_symbols(str(p.get("pick_name") or p.get("pick") or ""))[:24]
        wp = p.get("win_prob")
        wp_s = f"{float(wp)*100:.1f}%" if wp else "—"
        od_s = _strip_non_ascii_symbols(str(p.get("odds_display") or f"{float(p.get('odds') or 0):.2f}"))[:10]

        draw.text((52, y_cur + 20), tm, font=f_td, fill=(148, 163, 184))
        draw.text((225, y_cur + 20), mt, font=f_td_b, fill=(230, 237, 247))
        draw.text((595, y_cur + 20), pk, font=f_td_b, fill=(34, 197, 94))
        draw.text((865, y_cur + 20), wp_s, font=f_td_b, fill=(56, 189, 248))
        draw.text((975, y_cur + 20), od_s, font=f_td_b, fill=(245, 158, 11))
        y_cur += row_h

    draw.text(
        (42, h - 46),
        "VektorPulse Quantitative Desk  ·  59,062 Verified Matches Across 7 Sports & 27 Championships",
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
