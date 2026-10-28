"""Generate `docs/png-notification-cards.html` showcasing all 12 BetScout PNG Notification Card designs."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = (
    Path(__file__).resolve().parents[2]
    if (Path(__file__).resolve().parents[2] / "docs").exists()
    else Path(__file__).resolve().parents[1]
)

from betscout.pick_card import render_digest_slate_png, render_pick_card_png  # noqa: E402


def _b64(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def main() -> None:
    single_cards = [
        {
            "category": "1 · Football Pre-Match High-Conviction Pick (Dixon-Coles 28-Score Matrix)",
            "description": "Sent for qualifying football picks passing the 7-factor composite + T-60m Starting XI safety gate.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "ITA.1 · SERIE A",
                "match": "AS Roma vs Cagliari",
                "pick_name": "AS Roma (H)",
                "tier": "top_8pct",
                "badge": "TOP 8% QUANT EDGE",
                "odds_display": "1.33 (Fair 1.26, EV +5.6%)",
                "win_prob_str": "79.4%",
                "fair_str": "@ 1.26",
                "exact_score_pick": "2:0 (16.4%) · Cluster 2:0 / 1:0 / 2:1",
                "announced_at_local": "2026-10-28 08:15 CET",
                "date_local": "2026-10-28 20:45 CET",
            },
        },
        {
            "category": "2 · ATP / WTA Tennis Banker Pick (Markov Set-Score Matrix)",
            "description": "Sent for high-probability tennis bankers passing Surface Elo, 6m Game-Win%, rest/turnaround, and drift gates.",
            "payload": {
                "sport_cat": "tennis",
                "competition": "ATP · VIENNA INDOOR HARD",
                "match": "Jannik Sinner vs Alex de Minaur",
                "pick_name": "Jannik Sinner",
                "tier": "banker_70pct",
                "badge": "TENNIS BANKER ≥70%",
                "odds_display": "1.25 (Fair 1.18, EV +5.9%)",
                "win_prob_str": "84.8%",
                "fair_str": "@ 1.18",
                "exact_score_pick": "Sets 2:0 (64.2%, Fair 1.56)",
                "announced_at_local": "2026-10-28 09:00 CET",
                "date_local": "2026-10-28 17:30 CET",
            },
        },
        {
            "category": "3 · NBA Basketball Quantitative Edge (Shooting & Possession Gate)",
            "description": "Sent when NBA composite score >= 0.16 and the 3PT Volume & Turnover-Security safety gate passes.",
            "payload": {
                "sport_cat": "basketball",
                "competition": "NBA · REGULAR SEASON",
                "match": "Boston Celtics vs New York Knicks",
                "pick_name": "Boston Celtics (H)",
                "tier": "high_conf",
                "badge": "NBA HIGH-CONF EDGE",
                "odds_display": "1.48 (Fair 1.38, EV +7.2%)",
                "win_prob_str": "72.5%",
                "fair_str": "@ 1.38",
                "exact_score_pick": "116:107 · Spread -5.5 (63.8%)",
                "announced_at_local": "2026-10-28 14:00 CET",
                "date_local": "2026-10-29 00:30 CET",
            },
        },
        {
            "category": "4 · NHL Ice Hockey Edge (Goalie Save% & Shot Volume Gate)",
            "description": "Sent for NHL matchups backed by rolling Goalie Save%, shot-on-goal differential, and rest advantage.",
            "payload": {
                "sport_cat": "hockey",
                "competition": "NHL · REGULAR SEASON",
                "match": "Colorado Avalanche vs Dallas Stars",
                "pick_name": "Colorado Avalanche (H)",
                "tier": "top_15pct",
                "badge": "NHL QUANT EDGE",
                "odds_display": "1.62 (Fair 1.52, EV +6.6%)",
                "win_prob_str": "65.8%",
                "fair_str": "@ 1.52",
                "exact_score_pick": "4:2 (13.8%) · Cluster 3:1 / 4:2 / 3:2",
                "announced_at_local": "2026-10-28 15:20 CET",
                "date_local": "2026-10-29 02:00 CET",
            },
        },
        {
            "category": "5 · NFL American Football Edge (Yards-Per-Play & Turnover Margin)",
            "description": "Sent for NFL selections where net Yards-Per-Play (YPP), third-down efficiency, and Elo align.",
            "payload": {
                "sport_cat": "football",
                "competition": "NFL · WEEK 9",
                "match": "Kansas City Chiefs vs Tampa Bay Buccaneers",
                "pick_name": "Kansas City Chiefs (H)",
                "tier": "high_conf",
                "badge": "NFL HIGH-CONF PICK",
                "odds_display": "1.36 (Fair 1.28, EV +6.2%)",
                "win_prob_str": "78.1%",
                "fair_str": "@ 1.28",
                "exact_score_pick": "27:17 · Margin -6.5 (61.4%)",
                "announced_at_local": "2026-10-28 12:00 CET",
                "date_local": "2026-10-29 01:15 CET",
            },
        },
        {
            "category": "6 · Table Tennis Session Banker (Cold-Session Rust Gate Verified)",
            "description": "Sent for Table Tennis favorites with verified active <48h session rhythm and chronological Last-3 form edge.",
            "payload": {
                "sport_cat": "table_tennis",
                "competition": "WTT · CHAMPIONS MONTPELLIER",
                "match": "Felix Lebrun vs Truls Moregard",
                "pick_name": "Felix Lebrun",
                "tier": "banker_70pct",
                "badge": "TT BANKER ≥72%",
                "odds_display": "1.34 (Fair 1.26, EV +6.3%)",
                "win_prob_str": "79.2%",
                "fair_str": "@ 1.26",
                "exact_score_pick": "Sets 3:1 (41.0%) · Cluster 3:0 / 3:1",
                "announced_at_local": "2026-10-28 11:10 CET",
                "date_local": "2026-10-28 19:00 CET",
            },
        },
        {
            "category": "7 · Bookmaker Odds Mispricing Dislocation Alert (EDGE ≥ +2.0pp)",
            "description": "Triggered when BetScout's calibrated model win probability exceeds the vig-free market line by >= +2.0pp.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "ENG.1 · PREMIER LEAGUE",
                "match": "Aston Villa vs Bournemouth",
                "pick_name": "Aston Villa (H)",
                "tier": "top_8pct",
                "badge": "MISPRICED EDGE +4.8pp",
                "odds_display": "1.68 (Fair 1.54, EV +9.1%)",
                "win_prob_str": "64.9%",
                "fair_str": "@ 1.54",
                "exact_score_pick": "2:1 (14.2%) · Cluster 2:0 / 2:1 / 3:1",
                "announced_at_local": "2026-10-28 10:05 CET",
                "date_local": "2026-10-28 16:00 CET",
            },
        },
        {
            "category": "8 · Sharp Closing-Line Steam Move Alert (CLV ≥ +3.0%)",
            "description": "Sent when bookmaker odds shorten sharply after BetScout logs a pick, confirming institutional steam.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "ESP.1 · LALIGA",
                "match": "Real Madrid vs Villarreal",
                "pick_name": "Real Madrid (H)",
                "tier": "top_8pct",
                "badge": "STEAM MOVE +6.4% CLV",
                "odds_display": "1.49 (Close 1.40, CLV +6.4%)",
                "win_prob_str": "74.6%",
                "fair_str": "@ 1.34",
                "exact_score_pick": "2:0 (15.8%) · Cluster 2:0 / 2:1 / 3:1",
                "announced_at_local": "2026-10-28 08:30 CET",
                "date_local": "2026-10-28 21:00 CET",
            },
        },
        {
            "category": "9 · High-Probability Banker Profitability Booster (2-Leg & 3-Leg Combo)",
            "description": "Combines 2 or 3 high-win-probability (>=72%), lower-odds bankers into a high-yielding multiplier ticket.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "BANKER PROFITABILITY BOOSTER",
                "match": "2-Leg Anchor Banker Double",
                "pick_name": "Jannik Sinner + AS Roma",
                "tier": "BANKER_BOOSTER",
                "badge": "+66% PROFIT BOOST",
                "odds_display": "1.66x (+66% Net Yield)",
                "win_prob_str": "67.3%",
                "fair_str": "@ 1.49",
                "exact_score_pick": "2-Leg Uncorrelated Banker Multiplier",
                "announced_at_local": "2026-10-28 09:15 CET",
                "date_local": "2026-10-28 17:30 CET",
            },
        },
        {
            "category": "10 · Live In-Play Dominance Rebound & Late-Goal Alert (Cyan Top Border)",
            "description": "Triggered in real time when a backed pre-match favorite is level/trailing despite dominating live Shots-on-Target.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "GER.1 · BUNDESLIGA (LIVE 74')",
                "match": "Bayern Munich vs Bayer Leverkusen [1-1]",
                "pick_name": "Bayern Munich (H) · Next Goal / Win",
                "tier": "top_8pct",
                "badge": "LIVE REBOUND · SoT 8-1",
                "odds_display": "1.78 (Live In-Play Line)",
                "win_prob_str": "68.4%",
                "fair_str": "@ 1.46",
                "exact_score_pick": "2:1 (38.5%) · 76-90m Goal Prob 64%",
                "announced_at_local": "2026-10-28 18:30 CET",
                "date_local": "2026-10-28 20:02 CET (LIVE)",
            },
        },
        {
            "category": "11 · Resolved Single Pick Recap — WIN (Green Top Border)",
            "description": "Published when a tracked pick settles as a WIN, featuring a Green top border and realized unit profit.",
            "payload": {
                "sport_cat": "tennis",
                "competition": "ATP · BASEL INDOOR HARD",
                "match": "Ben Shelton vs Aleksandar Kovacevic",
                "pick_name": "Ben Shelton (W +0.26u) · Final Score: 2-1 (6-7, 7-6, 6-3)",
                "tier": "banker_70pct",
                "status_badge": "SETTLED WIN (+0.26U)",
                "pnl_best": 0.26,
                "odds_display": "1.26 (Close 1.22, CLV +3.3%)",
                "win_prob_str": "79.5%",
                "fair_str": "@ 1.26",
                "exact_score_pick": "2-1 (6-7, 7-6, 6-3) · Set Cluster Hit",
                "announced_at_local": "2026-10-27 11:00 CET",
                "date_local": "2026-10-27 19:10 CET",
                "ended_at_local": "2026-10-27 21:42 CET",
            },
        },
        {
            "category": "12 · Resolved Single Pick Recap — LOSS (Red/Pink Top Border)",
            "description": "Published when a tracked pick settles as a LOSS, featuring a Red/Pink top border and crimson result box.",
            "payload": {
                "sport_cat": "soccer",
                "competition": "ENG.1 · PREMIER LEAGUE",
                "match": "Newcastle United vs Brighton",
                "pick_name": "Newcastle United (L -1.00u) · Final Score: 0-1 (0-1, 0-0)",
                "tier": "top_10pct",
                "status_badge": "SETTLED LOSS (-1.00U)",
                "pnl_best": -1.00,
                "odds_display": "1.62 (Close 1.58, CLV +2.5%)",
                "win_prob_str": "64.2%",
                "fair_str": "@ 1.56",
                "exact_score_pick": "Final Score: 0-1 (Missed 2:1 Target)",
                "announced_at_local": "2026-10-26 09:00 CET",
                "date_local": "2026-10-26 16:00 CET",
                "ended_at_local": "2026-10-26 17:55 CET",
            },
        },
    ]

    slate_active_rows = [
        {
            "sport_cat": "tennis",
            "match": "Jannik Sinner vs Alex de Minaur",
            "pick_name": "Jannik Sinner",
            "exact_score_pick": "Sets 2:0 (64.2%)",
            "win_prob": 0.848,
            "odds": 1.25,
            "odds_display": "1.25",
            "announced_at_local": "2026-10-28 09:00 CET",
            "date_local": "2026-10-28 17:30 CET",
        },
        {
            "sport_cat": "table_tennis",
            "match": "Felix Lebrun vs Truls Moregard",
            "pick_name": "Felix Lebrun",
            "exact_score_pick": "Sets 3:1 (41.0%)",
            "win_prob": 0.792,
            "odds": 1.34,
            "odds_display": "1.34",
            "announced_at_local": "2026-10-28 11:10 CET",
            "date_local": "2026-10-28 19:00 CET",
        },
        {
            "sport_cat": "soccer",
            "match": "AS Roma vs Cagliari",
            "pick_name": "AS Roma",
            "exact_score_pick": "2:0 (16.4%)",
            "win_prob": 0.794,
            "odds": 1.33,
            "odds_display": "1.33",
            "announced_at_local": "2026-10-28 08:15 CET",
            "date_local": "2026-10-28 20:45 CET",
        },
        {
            "sport_cat": "soccer",
            "match": "Real Madrid vs Villarreal",
            "pick_name": "Real Madrid",
            "exact_score_pick": "2:0 (15.8%)",
            "win_prob": 0.746,
            "odds": 1.49,
            "odds_display": "1.49",
            "announced_at_local": "2026-10-28 08:30 CET",
            "date_local": "2026-10-28 21:00 CET",
        },
        {
            "sport_cat": "basketball",
            "match": "Boston Celtics vs New York Knicks",
            "pick_name": "Boston Celtics",
            "exact_score_pick": "Spread -5.5 (63.8%)",
            "win_prob": 0.725,
            "odds": 1.48,
            "odds_display": "1.48",
            "announced_at_local": "2026-10-28 14:00 CET",
            "date_local": "2026-10-29 00:30 CET",
        },
        {
            "sport_cat": "hockey",
            "match": "Colorado Avalanche vs Dallas Stars",
            "pick_name": "Colorado Avalanche",
            "exact_score_pick": "4:2 (13.8%)",
            "win_prob": 0.658,
            "odds": 1.62,
            "odds_display": "1.62",
            "announced_at_local": "2026-10-28 15:20 CET",
            "date_local": "2026-10-29 02:00 CET",
        },
    ]

    slate_settled_rows = [
        {
            "sport_cat": "tennis",
            "match": "Ben Shelton vs Aleksandar Kovacevic [2-1 (6-7, 7-6, 6-3)]",
            "pick_name": "Ben Shelton (W +0.26u)",
            "win_prob": 0.795,
            "odds": 1.26,
            "odds_display": "1.26",
            "date_local": "2026-10-27 19:10 CET",
            "ended_at_local": "2026-10-27 21:42 CET",
        },
        {
            "sport_cat": "soccer",
            "match": "Galatasaray vs Fenerbahce [3-1 (2-0, 1-1)]",
            "pick_name": "Galatasaray (W +0.58u)",
            "win_prob": 0.684,
            "odds": 1.58,
            "odds_display": "1.58",
            "date_local": "2026-10-27 18:00 CET",
            "ended_at_local": "2026-10-27 19:54 CET",
        },
        {
            "sport_cat": "basketball",
            "match": "Oklahoma City Thunder vs Atlanta Hawks [128-104]",
            "pick_name": "Oklahoma City Thunder (W +0.29u)",
            "win_prob": 0.782,
            "odds": 1.29,
            "odds_display": "1.29",
            "date_local": "2026-10-27 01:00 CET",
            "ended_at_local": "2026-10-27 03:24 CET",
        },
        {
            "sport_cat": "football",
            "match": "Denver Broncos vs Carolina Panthers [28-14]",
            "pick_name": "Denver Broncos (W +0.42u)",
            "win_prob": 0.741,
            "odds": 1.42,
            "odds_display": "1.42",
            "date_local": "2026-10-26 21:25 CET",
            "ended_at_local": "2026-10-27 00:32 CET",
        },
        {
            "sport_cat": "soccer",
            "match": "Espanyol vs Sevilla [0-2 (0-2, 0-0)]",
            "pick_name": "Sevilla X2 / Win (W +0.83u)",
            "win_prob": 0.642,
            "odds": 1.83,
            "odds_display": "1.83",
            "date_local": "2026-10-25 21:00 CET",
            "ended_at_local": "2026-10-25 22:55 CET",
        },
    ]

    active_slate_b64 = _b64(
        render_digest_slate_png(
            slate_active_rows,
            title="DAILY HIGH-CONVICTION SLATE (6 ACTIVE PICKS)",
            subtitle="Ultra-Fast Fine-Tuned AI Decision Model · Multi-Sport Calibrated Picks",
        )
    )
    settled_slate_b64 = _b64(
        render_digest_slate_png(
            slate_settled_rows,
            title="SETTLED PAPER-BET RECAP (5 RESOLVED)",
            subtitle="Cumulative Ledger: 62 Settled (59W - 3L · 95.2%) · Profit: +20.68u (ROI +33.3%)",
        )
    )

    html_parts = [
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BetScout — PNG Notification Cards Design Catalog (12 Designs)</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; padding: 32px 24px 64px;
      background: #04070e; color: #f8fafc;
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }
    .wrap { max-width: 1360px; margin: 0 auto; }
    .badge {
      display: inline-block; padding: 4px 12px; border-radius: 999px;
      font-size: 11px; font-weight: 800; letter-spacing: 0.05em;
      background: rgba(16, 185, 129, 0.18); color: #6ee7b7;
      border: 1px solid rgba(52, 211, 153, 0.45);
    }
    h1 { font-size: 30px; margin: 10px 0 6px; letter-spacing: -0.02em; }
    p.lead { color: #cbd5e1; font-size: 14.5px; margin: 0 0 28px; max-width: 880px; line-height: 1.55; }
    h2.section-hdr {
      font-size: 20px; color: #38bdf8; margin: 36px 0 16px;
      padding-bottom: 8px; border-bottom: 1px solid #1e293b;
    }
    .slate-grid { display: grid; grid-template-columns: 1fr; gap: 24px; margin-bottom: 36px; }
    @media (min-width: 1100px) { .slate-grid { grid-template-columns: 1fr 1fr; } }
    .cards-grid { display: grid; grid-template-columns: 1fr; gap: 22px; }
    @media (min-width: 920px) { .cards-grid { grid-template-columns: 1fr 1fr; } }
    .card-box {
      background: linear-gradient(145deg, rgba(24, 35, 58, 0.72), rgba(12, 19, 34, 0.88));
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-radius: 16px; padding: 18px;
      box-shadow: 0 16px 38px rgba(0, 0, 0, 0.55);
    }
    .card-box h3 { margin: 0 0 6px; font-size: 15px; color: #ffffff; }
    .card-box p { margin: 0 0 12px; font-size: 12.5px; color: #94a3b8; line-height: 1.45; }
    .card-box img {
      width: 100%; height: auto; display: block;
      border-radius: 12px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <span class="badge">BETSCOUT NOTIFICATION ENGINE · 12 PNG CARD ARCHETYPES</span>
    <h1>BetScout — PNG Notification Cards Design Catalog</h1>
    <p class="lead">
      Complete catalog of all high-resolution PNG notification card designs generated by BetScout for Discord &amp;
      Telegram syndication (featuring the <strong>Option 7.3 3D Chiseled Bevel Compass</strong> logo, native color
      sport emojis, two-line KPI split boxes, and settled score recaps).
    </p>

    <h2 class="section-hdr">Part I · Multi-Row Slate Boards (1180px Wide — Morning Digest &amp; Settled Recaps)</h2>
    <div class="slate-grid">
      <div class="card-box">
        <h3>11 · Daily High-Conviction Multi-Sport Slate Board (Morning Digest)</h3>
        <p>Published automatically at 09:00 CET and via the Share Picks modal for multi-pick slates across all 10 sports.</p>
        <img src=\""""
        + active_slate_b64
        + """\" alt="Daily Active Slate PNG" />
      </div>
      <div class="card-box">
        <h3>12 · Automated Settled Paper-Bet Recap Board (Resolved Results &amp; Ledger ROI)</h3>
        <p>Published automatically when matches finish and settle, showing 2-line Matchup + Final Score, unit PnL, and cumulative W-L record.</p>
        <img src=\""""
        + settled_slate_b64
        + """\" alt="Settled Slate Recap PNG" />
      </div>
    </div>

    <h2 class="section-hdr">Part II · Single Match &amp; Alert Cards (1080×560px — All 10 Archetypes)</h2>
    <div class="cards-grid">
"""
    ]

    for item in single_cards:
        png_b = render_pick_card_png(item["payload"])
        b64_uri = _b64(png_b)
        html_parts.append(
            f"""      <div class="card-box">
        <h3>{item["category"]}</h3>
        <p>{item["description"]}</p>
        <img src="{b64_uri}" alt="{item["category"]}" />
      </div>
"""
        )

    html_parts.append(
        """    </div>
  </div>
</body>
</html>
"""
    )

    out_file = ROOT / "docs" / "png-notification-cards.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("".join(html_parts), encoding="utf-8")
    print(f"Wrote {out_file} ({out_file.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
