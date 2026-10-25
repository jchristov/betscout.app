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
    """Render a 1080x580 dark-mode VektorPulse Pick Card PNG with dynamic text measurement so zero text is ever cut off."""
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

    # Header: Logo + VektorPulse brand
    _draw_vektorpulse_shield(draw, 66, 68, radius=24)
    draw.text((104, 45), "VEKTORPULSE", font=f_brand, fill=(230, 237, 247))
    draw.text((104, 76), "SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE", font=f_sub, fill=(139, 155, 180))

    sport_cat = str(pick_data.get("sport_cat") or pick_data.get("sport") or "soccer").lower()
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

    # Competition & Kickoff meta row
    kickoff_str = _strip_non_ascii_symbols(str(pick_data.get("date_local") or pick_data.get("date") or "Upcoming Slate"))
    sport_tag = SPORT_LABELS.get(sport_cat, sport_cat.upper())
    comp_label = f"{sport_tag}  ·  {comp_raw}" if comp_raw.upper() not in sport_tag else sport_tag
    f_comp, comp_fit = _fit_font_and_text(draw, comp_label, max_width=560, start_size=14, min_size=11, bold=True)
    comp_box_w = int(_text_width(draw, comp_fit, f_comp)) + 28
    draw.rounded_rectangle([(48, 124), (48 + comp_box_w, 156)], radius=8, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
    draw.text((62, 132), comp_fit, font=f_comp, fill=(56, 189, 248))

    ko_label = f"KICKOFF: {kickoff_str}"
    f_ko, ko_fit = _fit_font_and_text(draw, ko_label, max_width=360, start_size=14, min_size=11, bold=True)
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
    footer_r = "VektorPulse Quant Desk"
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

    _draw_vektorpulse_shield(draw, 62, 64, radius=22)
    f_hdr, hdr_fit = _fit_font_and_text(draw, f"VEKTORPULSE — {title}", max_width=w - 130, start_size=24, min_size=16, bold=True)
    draw.text((98, 43), hdr_fit, font=f_hdr, fill=(230, 237, 247))
    f_sub_fit, sub_fit = _fit_font_and_text(draw, subtitle, max_width=w - 130, start_size=14, min_size=11, bold=False)
    draw.text((98, 74), sub_fit, font=f_sub_fit, fill=(139, 155, 180))

    # Table Header
    y_head = 118
    draw.rounded_rectangle([(38, y_head), (w - 38, y_head + 38)], radius=8, fill=(15, 22, 35))
    draw.text((50, y_head + 11), "KICKOFF", font=f_th, fill=(148, 163, 184))
    draw.text((220, y_head + 11), "MATCHUP", font=f_th, fill=(148, 163, 184))
    draw.text((590, y_head + 11), "RECOMMENDED PICK", font=f_th, fill=(148, 163, 184))
    draw.text((910, y_head + 11), "WIN PROB", font=f_th, fill=(148, 163, 184))
    draw.text((1020, y_head + 11), "ODDS", font=f_th, fill=(148, 163, 184))

    y_cur = y_head + 46
    for idx, p in enumerate(rows):
        bg_col = (15, 22, 35) if idx % 2 == 1 else (19, 27, 41)
        draw.rounded_rectangle([(38, y_cur), (w - 38, y_cur + row_h - 6)], radius=8, fill=bg_col, outline=(30, 41, 59), width=1)
        tm = _strip_non_ascii_symbols(str(p.get("date_local") or p.get("date") or ""))
        mt = _strip_non_ascii_symbols(str(p.get("match") or f"{p.get('home','')} vs {p.get('away','')}"))
        pk_raw = _strip_non_ascii_symbols(str(p.get("pick_name") or p.get("pick") or ""))
        pk_clean = pk_raw.split("[")[0].split("(Win")[0].strip() or pk_raw
        wp = p.get("win_prob")
        wp_s = f"{float(wp)*100:.1f}%" if wp else "—"
        od_s = _strip_non_ascii_symbols(str(p.get("odds_display") or f"{float(p.get('odds') or 0):.2f}"))

        f_tm, tm_fit = _fit_font_and_text(draw, tm, max_width=160, start_size=14, min_size=11, bold=False)
        f_mt, mt_fit = _fit_font_and_text(draw, mt, max_width=355, start_size=16, min_size=12, bold=True)
        f_pk, pk_fit = _fit_font_and_text(draw, pk_clean, max_width=305, start_size=16, min_size=12, bold=True)
        f_wp, wp_fit = _fit_font_and_text(draw, wp_s, max_width=95, start_size=16, min_size=12, bold=True)
        f_od, od_fit = _fit_font_and_text(draw, od_s, max_width=95, start_size=16, min_size=12, bold=True)

        draw.text((50, y_cur + 21), tm_fit, font=f_tm, fill=(148, 163, 184))
        draw.text((220, y_cur + 20), mt_fit, font=f_mt, fill=(230, 237, 247))
        draw.text((590, y_cur + 20), pk_fit, font=f_pk, fill=(34, 197, 94))
        draw.text((910, y_cur + 20), wp_fit, font=f_wp, fill=(56, 189, 248))
        draw.text((1020, y_cur + 20), od_fit, font=f_od, fill=(245, 158, 11))
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
