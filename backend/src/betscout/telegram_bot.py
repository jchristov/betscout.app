"""Discord & Telegram Social Publisher (`src/betscout/telegram_bot.py`).

Primary Social Integration: **Discord** (`https://discord.com/api/...`)
  - Supports **Discord Incoming Webhook** (`DISCORD_WEBHOOK_URL` — simplest 1-step setup in Discord Channel -> Integrations -> Webhooks)
  - Or **Discord Bot Token + Channel ID** (`DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` -> `POST /api/v10/channels/{id}/messages`)

Optional Secondary Integration: **Telegram** (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`)
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import load_dotenv
from .dashboard import DEFAULT_LOCAL_TZ, _format_local_time, _league_to_sport_cat, build_best_bets_summary
from .espn import LEAGUE_LABELS
from .paper_bet import (
    build_recommended_2leg_doubles,
    get_paper_ledger_summary,
    settle_pending_paper_bets,
)

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
    "snooker": "🎱",
    "mma": "🥊",
}


def html_to_discord_markdown(text: str) -> str:
    """Convert our HTML-formatted digest (`<b>`, `<i>`, `<code>`) into clean Discord Markdown."""
    s = text
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.DOTALL)
    s = re.sub(r"<i>(.*?)</i>", r"*\1*", s, flags=re.DOTALL)
    s = re.sub(r"<code>(.*?)</code>", r"`\1`", s, flags=re.DOTALL)
    return html.unescape(s)


def format_telegram_digest(
    rec: dict[str, Any],
    db_path: Path | None = None,
    min_odds: float = 1.15,
    sport_filter: str = "all",
    day_filter: str = "today",
    max_picks: int = 12,
    include_settled: bool = True,
    tz_name: str = DEFAULT_LOCAL_TZ,
) -> str:
    """Build a Telegram HTML-formatted digest of settled paper bets and daily upcoming/live picks.
    By default (`day_filter='today'`), includes only Today's local picks (or next 30h if late evening)
    and recent 24h settled bets + today's vetoes so channel posts stay focused on imminent action.
    Pass `day_filter='all'` to include the full multi-day horizon.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    if db_path and db_path.exists():
        try:
            settle_pending_paper_bets(db_path)
            rec = {**rec, "paper_ledger": get_paper_ledger_summary(db_path)}
        except Exception:
            pass

    now_loc = datetime.now(ZoneInfo(tz_name))
    today_ymd = now_loc.strftime("%Y-%m-%d")
    tom_ymd = (now_loc + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_ymd = (now_loc - timedelta(days=1)).strftime("%Y-%m-%d")

    ledger = rec.get("paper_ledger") or {}
    all_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=sport_filter)

    norm_day = (day_filter or "today").lower().strip()
    if norm_day == "today":
        best_bets = [b for b in all_bets if (b.get("date_local") or _format_local_time(b["date"], tz_name))[:10] == today_ymd]
        day_label = f"Today ({today_ymd})"
        if not best_bets:
            best_bets = [b for b in all_bets if (b.get("date_local") or _format_local_time(b["date"], tz_name))[:10] in (today_ymd, tom_ymd)]
            day_label = f"Today & Tomorrow ({today_ymd} / {tom_ymd})" if best_bets else "All Upcoming Days"
            if not best_bets:
                best_bets = all_bets
    elif norm_day == "tomorrow":
        best_bets = [b for b in all_bets if (b.get("date_local") or _format_local_time(b["date"], tz_name))[:10] == tom_ymd]
        day_label = f"Tomorrow ({tom_ymd})"
    elif norm_day in ("next48h", "2days"):
        best_bets = [b for b in all_bets if (b.get("date_local") or _format_local_time(b["date"], tz_name))[:10] in (today_ymd, tom_ymd)]
        day_label = f"Today + Tomorrow ({today_ymd}..{tom_ymd})"
    elif norm_day == "all":
        best_bets = all_bets
        day_label = "All Upcoming Days"
    else:
        best_bets = [b for b in all_bets if (b.get("date_local") or _format_local_time(b["date"], tz_name))[:10] == norm_day]
        day_label = norm_day

    gen_local = _format_local_time(rec.get("generated_at") or "", tz_name)

    lines: list[str] = [
        f"⚡ <b>BETSCOUT — DAILY UPDATES &amp; PICKS ({html.escape(day_label)})</b>",
        f"🕒 <i>Generated: {html.escape(gen_local)}</i>",
        "",
    ]

    if include_settled and ledger.get("settled_count", 0) > 0:
        s_cnt = ledger.get("settled_count", 0)
        s_wins = ledger.get("settled_wins", 0)
        s_loss = ledger.get("settled_losses", 0)
        s_prof = float(ledger.get("settled_profit_u") or 0.0)
        s_roi = float(ledger.get("settled_roi_best") or 0.0) * 100.0
        prof_icon = "🟢" if s_prof >= 0 else "🔴"
        lines.append(
            f"{prof_icon} <b>Settled Paper-Bets: {s_cnt} ({s_wins}W - {s_loss}L) | "
            f"PnL: {s_prof:+.2f}u (ROI {s_roi:+.1f}%)</b>"
        )
        settled_bets = [t for t in (ledger.get("bets") or []) if t.get("status") == "SETTLED"]
        if norm_day != "all":
            recent_settled = [
                t for t in settled_bets
                if _format_local_time(t.get("kickoff") or "", tz_name)[:10] in (today_ymd, yesterday_ymd)
            ]
            settled_to_show = recent_settled[-6:] if recent_settled else settled_bets[-4:]
        else:
            settled_to_show = settled_bets[-6:]
        for tr in settled_to_show:
            pnl_v = float(tr.get("pnl_best") or 0.0)
            badge = "✅ WIN" if pnl_v > 0 else "❌ LOSS"
            sp_emoji = SPORT_EMOJIS.get(_league_to_sport_cat(tr["league"]), "🎯")
            pick_name = tr["home"] if tr["side"] == "H" else tr["away"]
            sc_str = tr.get("score_str") or "—"
            lines.append(
                f"  {badge} ({pnl_v:+.2f}u) {sp_emoji} <b>{html.escape(pick_name)}</b> "
                f"@ {tr['logged_best_odds']:.2f} — <i>{html.escape(tr['home'])} vs {html.escape(tr['away'])} "
                f"[{html.escape(sc_str)}]</i>"
            )
        lines.append("")

    # Vetoed injury alerts (filtered to daily window when norm_day != 'all')
    vetoed = [
        p for p in (rec.get("qualifying_picks") or [])
        if str(p.get("action", "")).startswith("VETOED")
        and (
            norm_day == "all"
            or _format_local_time(p.get("kickoff") or "", tz_name)[:10] in (today_ymd, tom_ymd)
        )
    ]
    if vetoed and sport_filter in ("all", "soccer"):
        lines.append("🚨 <b>Daily System-1 Injury / Lineup Vetoes (DO NOT BET):</b>")
        for v in vetoed[:4]:
            lg_lbl = LEAGUE_LABELS.get(v["league"], v["league"].upper())
            sp_emoji = SPORT_EMOJIS.get(_league_to_sport_cat(v["league"]), "⚽")
            lines.append(
                f"  ⛔ {sp_emoji} <b>{html.escape(v['home'])} vs {html.escape(v['away'])}</b> ({html.escape(lg_lbl)}) — "
                f"<code>{html.escape(v['action'])}</code>"
            )
        lines.append("")

    lines.append(
        f"🔥 <b>Daily Picks ({html.escape(day_label)} · Odds &gt; {min_odds:.2f} · Showing {min(len(best_bets), max_picks)} of {len(best_bets)}):</b>"
    )
    if not best_bets:
        lines.append("  <i>No qualifying picks above threshold in current window.</i>")
    else:
        for idx, b in enumerate(best_bets[:max_picks], start=1):
            sp_emoji = SPORT_EMOJIS.get(b.get("sport_cat", "soccer"), "🎯")
            loc_time = b.get("date_local") or _format_local_time(b["date"], tz_name)
            esc_line = (
                f"\n   🎲 Exact Score: <b>{html.escape(b['exact_score_pick'])}</b>"
                if b.get("exact_score_pick") and b["exact_score_pick"] != "—"
                else ""
            )
            lines.append(
                f"{idx}. {sp_emoji} <b>{html.escape(b['match'])}</b>\n"
                f"   🕒 <code>{html.escape(loc_time)}</code> · {sp_emoji} {html.escape(b['sport_league'])}\n"
                f"   🎯 Pick: <b>{html.escape(b['pick'])}</b> · 💰 Odds: <b>{html.escape(b['odds_display'])}</b>"
                f"{esc_line}"
            )

    doubles = build_recommended_2leg_doubles(
        rec.get("qualifying_picks") or [],
        rec.get("tennis_picks") or [],
        rec.get("other_sport_picks") or [],
        max_doubles=6,
    ) or (rec.get("recommended_doubles") or [])
    if norm_day != "all":
        allowed_days = (
            {today_ymd, tom_ymd}
            if norm_day in ("today", "next48h", "2days")
            else ({tom_ymd} if norm_day == "tomorrow" else {norm_day})
        )
        doubles = [
            d for d in doubles
            if _format_local_time(d["leg_1"].get("kickoff") or "", tz_name)[:10] in allowed_days
            and _format_local_time(d["leg_2"].get("kickoff") or "", tz_name)[:10] in allowed_days
        ]
    # Propose Banker Profitability Booster Combos whenever >=2 high-win-probability (>=72%), low-odds (1.10..1.48) bankers exist in the slate
    banker_pool = sorted(
        [
            b for b in best_bets[:max_picks]
            if float(b.get("win_prob") or 0.0) >= 0.72 and 1.10 <= float(b.get("odds") or 0.0) <= 1.48
        ],
        key=lambda x: (-float(x.get("win_prob") or 0.0), float(x.get("odds") or 9.9)),
    )
    if len(banker_pool) >= 2:
        b1, b2 = banker_pool[0], banker_pool[1]
        o1, o2 = float(b1["odds"]), float(b2["odds"])
        p1, p2 = float(b1["win_prob"]), float(b2["win_prob"])
        comb_o2 = o1 * o2
        comb_p2 = p1 * p2 * 100.0
        n1 = html.escape(str(b1.get("pick_name") or b1["pick"]))
        n2 = html.escape(str(b2.get("pick_name") or b2["pick"]))
        lines.append("")
        lines.append("🚀 <b>Banker Profitability Booster Combos (Low-Odds Multipliers):</b>")
        lines.append(
            f"  • <b>2-Leg Banker Double (@ {comb_o2:.2f}x · +{int(round((comb_o2 - 1)*100))}% Profit · {comb_p2:.1f}% Win Prob):</b> "
            f"{n1} (@{o1:.2f}) + {n2} (@{o2:.2f})"
        )
        if len(banker_pool) >= 3:
            b3 = banker_pool[2]
            o3, p3 = float(b3["odds"]), float(b3["win_prob"])
            n3 = html.escape(str(b3.get("pick_name") or b3["pick"]))
            comb_o3 = comb_o2 * o3
            comb_p3 = (p1 * p2 * p3) * 100.0
            lines.append(
                f"  • <b>3-Leg Banker Treble (@ {comb_o3:.2f}x · +{int(round((comb_o3 - 1)*100))}% Profit · {comb_p3:.1f}% Win Prob):</b> "
                f"{n1} (@{o1:.2f}) + {n2} (@{o2:.2f}) + {n3} (@{o3:.2f})"
            )

    if doubles and sport_filter == "all":
        lines.append("")
        lines.append("🔗 <b>Recommended 2-Leg High-Probability Combos (Parlays):</b>")
        for idx_d, d in enumerate(doubles[:5], start=1):
            l1, l2 = d["leg_1"], d["leg_2"]
            c_lbl = d.get("combo_label") or "Cross-Sport Banker"
            e1 = SPORT_EMOJIS.get(_league_to_sport_cat(l1["league"]), "🎯")
            e2 = SPORT_EMOJIS.get(_league_to_sport_cat(l2["league"]), "🎯")
            m1_str = f" [{l1['market']}]" if l1.get("market") else ""
            m2_str = f" [{l2['market']}]" if l2.get("market") else ""
            lines.append(
                f"  <b>Combo #{idx_d} ({html.escape(c_lbl)})</b> — Odds: <b>{d['combined_odds']:.2f}</b> "
                f"(WinProb {d['combined_prob']*100:.1f}%, Fair {d['min_fair_odds']:.2f})\n"
                f"   1️⃣ {e1} {html.escape(l1['match'])}{html.escape(m1_str)} → <b>{html.escape(l1['pick'])}</b> @ {l1['odds']:.2f} ({l1['prob']*100:.0f}%)\n"
                f"   2️⃣ {e2} {html.escape(l2['match'])}{html.escape(m2_str)} → <b>{html.escape(l2['pick'])}</b> @ {l2['odds']:.2f} ({l2['prob']*100:.0f}%)"
            )

    has_unconfirmed_time = any(b.get("time_valid") is False or "*" in str(b.get("date_local") or "") for b in best_bets[:max_picks])
    if has_unconfirmed_time:
        lines.append("")
        lines.append("<i>* Provisional / unconfirmed start time (updates automatically once official Order of Play is released).</i>")
    lines.append("")
    lines.append("⚡ <i>BetScout · Sports Edge &amp; Score Intelligence</i>")
    return "\n".join(lines)


def format_discord_digest(
    rec: dict[str, Any],
    db_path: Path | None = None,
    min_odds: float = 1.15,
    sport_filter: str = "all",
    day_filter: str = "today",
    max_picks: int = 12,
    include_settled: bool = True,
    tz_name: str = DEFAULT_LOCAL_TZ,
) -> str:
    """Build a Discord Markdown digest of settled paper bets, System-1 vetoes, and daily upcoming/live picks."""
    html_msg = format_telegram_digest(
        rec=rec,
        db_path=db_path,
        min_odds=min_odds,
        sport_filter=sport_filter,
        day_filter=day_filter,
        max_picks=max_picks,
        include_settled=include_settled,
        tz_name=tz_name,
    )
    return html_to_discord_markdown(html_msg)


SPORT_DISCORD_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "soccer": ("DISCORD_WEBHOOK_URL_SOCCER", "DISCORD_WEBHOOK_URL_FOOTBALL"),
    "tennis": ("DISCORD_WEBHOOK_URL_TENNIS", "DISCORD_WEBHOOK_URL_ATP", "DISCORD_WEBHOOK_URL_WTA"),
    "basketball": ("DISCORD_WEBHOOK_URL_BASKETBALL", "DISCORD_WEBHOOK_URL_NBA", "DISCORD_WEBHOOK_URL_WNBA", "DISCORD_WEBHOOK_URL_US_SPORTS"),
    "volleyball": ("DISCORD_WEBHOOK_URL_VOLLEYBALL", "DISCORD_WEBHOOK_URL_US_SPORTS"),
    "hockey": ("DISCORD_WEBHOOK_URL_HOCKEY", "DISCORD_WEBHOOK_URL_NHL", "DISCORD_WEBHOOK_URL_US_SPORTS"),
    "football": ("DISCORD_WEBHOOK_URL_NFL", "DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL", "DISCORD_WEBHOOK_URL_US_SPORTS"),
    "baseball": ("DISCORD_WEBHOOK_URL_BASEBALL", "DISCORD_WEBHOOK_URL_MLB", "DISCORD_WEBHOOK_URL_US_SPORTS"),
    "handball": ("DISCORD_WEBHOOK_URL_HANDBALL",),
    "darts": ("DISCORD_WEBHOOK_URL_DARTS",),
    "table_tennis": ("DISCORD_WEBHOOK_URL_TABLE_TENNIS",),
}


def resolve_discord_webhook_for_sport(
    sport_or_league: str | None = None,
    explicit_webhook_url: str | None = None,
    env_path: Path | None = None,
    custom_sport_webhooks: dict[str, str] | None = None,
) -> str:
    """Resolve the target Discord Webhook URL for a given sport/league (`soccer`, `tennis`, `hockey`, etc.).
    Priority:
      1. `explicit_webhook_url` (if passed directly by caller)
      2. `custom_sport_webhooks[sport_cat]` (if configured in WebApp Settings UI)
      3. Per-sport environment variable (`DISCORD_WEBHOOK_URL_TENNIS`, `DISCORD_WEBHOOK_URL_SOCCER`, etc.)
      4. Global `DISCORD_WEBHOOK_URL` fallback.
    """
    load_dotenv(env_path=env_path, override=True)
    if explicit_webhook_url and explicit_webhook_url.strip():
        return explicit_webhook_url.strip()
    sp_cat = _league_to_sport_cat(sport_or_league or "") if (sport_or_league and sport_or_league != "all") else ""
    if sp_cat and custom_sport_webhooks and isinstance(custom_sport_webhooks, dict):
        ui_wh = str(custom_sport_webhooks.get(sp_cat) or "").strip()
        if ui_wh.startswith("https://discord"):
            return ui_wh
    if sp_cat and sp_cat in SPORT_DISCORD_ENV_KEYS:
        for env_k in SPORT_DISCORD_ENV_KEYS[sp_cat]:
            val = (os.environ.get(env_k) or "").strip()
            if val.startswith("https://discord"):
                return val
    if custom_sport_webhooks and isinstance(custom_sport_webhooks, dict):
        g_ui = str(custom_sport_webhooks.get("global") or "").strip()
        if g_ui.startswith("https://discord"):
            return g_ui
    return (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()


def get_discord_env_config(
    env_path: Path | None = None,
    custom_sport_webhooks: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Reload `.env` on the fly and return current Discord configuration status (global + per-sport webhooks)."""
    load_dotenv(env_path=env_path, override=True)
    webhook_url = resolve_discord_webhook_for_sport(None, env_path=env_path, custom_sport_webhooks=custom_sport_webhooks)
    bot_token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel_id = (os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    has_webhook = webhook_url.startswith("https://discord.com/api/webhooks/") or webhook_url.startswith(
        "https://discordapp.com/api/webhooks/"
    )
    has_bot = bool(bot_token and channel_id)
    masked_webhook = (webhook_url[:38] + "..." + webhook_url[-6:]) if len(webhook_url) > 48 else ""

    sport_webhooks_status: dict[str, dict[str, Any]] = {}
    for sp_cat, env_keys in SPORT_DISCORD_ENV_KEYS.items():
        sp_url = ""
        source = "global_fallback"
        if custom_sport_webhooks and isinstance(custom_sport_webhooks, dict):
            cand_ui = str(custom_sport_webhooks.get(sp_cat) or "").strip()
            if cand_ui.startswith("https://discord"):
                sp_url = cand_ui
                source = "settings_ui"
        if not sp_url:
            for ek in env_keys:
                cand_env = (os.environ.get(ek) or "").strip()
                if cand_env.startswith("https://discord"):
                    sp_url = cand_env
                    source = ek
                    break
        eff_url = sp_url or webhook_url
        sport_webhooks_status[sp_cat] = {
            "env_keys": list(env_keys),
            "has_dedicated": bool(sp_url),
            "source": source if sp_url else ("DISCORD_WEBHOOK_URL" if has_webhook else "unconfigured"),
            "masked_webhook": (eff_url[:38] + "..." + eff_url[-6:]) if len(eff_url) > 48 else "",
        }

    return {
        "configured": bool(has_webhook or has_bot or any(v["has_dedicated"] for v in sport_webhooks_status.values())),
        "mode": "webhook" if has_webhook else ("bot" if has_bot else "unconfigured"),
        "has_webhook": has_webhook,
        "masked_webhook": masked_webhook,
        "has_bot": has_bot,
        "channel_id": channel_id,
        "sport_webhooks": sport_webhooks_status,
    }


def _chunk_discord_text(md_text: str, max_len: int = 1900) -> list[str]:
    """Split a long Discord Markdown message on blank-line (block) boundaries first so a pick
    block (1. Match / Time / Pick) is never split in half across two messages."""
    if len(md_text) <= max_len:
        return [md_text]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    # Group consecutive lines belonging to a numbered pick (e.g. '1. ...', '   🕒 ...', '   🎯 ...') into one atomic block
    blocks: list[str] = []
    buf: list[str] = []
    for line in md_text.splitlines():
        if line.startswith("   ") and buf:
            buf.append(line)
        else:
            if buf:
                blocks.append("\n".join(buf))
            buf = [line]
    if buf:
        blocks.append("\n".join(buf))

    for blk in blocks:
        add_len = len(blk) + (1 if cur else 0)
        if cur and (cur_len + add_len > max_len):
            chunks.append("\n".join(cur))
            cur = [blk]
            cur_len = len(blk)
        else:
            cur.append(blk)
            cur_len += add_len
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def send_discord_message(
    text: str,
    webhook_url: str | None = None,
    bot_token: str | None = None,
    channel_id: str | None = None,
    dry_run: bool = False,
    env_path: Path | None = None,
    sport: str | None = None,
    custom_sport_webhooks: dict[str, str] | None = None,
    image_bytes: bytes | None = None,
    image_filename: str = "betscout_pick.png",
    also_send_to_global: bool = True,
) -> dict[str, Any]:
    """Post a Markdown-formatted message (and optional PNG card attachment) to a Discord channel via Webhook URL or Bot Token + Channel ID.
    When `sport` resolves to a dedicated per-sport webhook AND `also_send_to_global=True`, the message is sent to the global
    `DISCORD_WEBHOOK_URL` channel AS WELL AS the dedicated per-sport webhook channel ('on top of the global webhook for everything')."""
    load_dotenv(env_path=env_path, override=True)
    md_text = html_to_discord_markdown(text)
    chunks = _chunk_discord_text(md_text, max_len=1950)

    wh_url = resolve_discord_webhook_for_sport(
        sport_or_league=sport,
        explicit_webhook_url=webhook_url,
        env_path=env_path,
        custom_sport_webhooks=custom_sport_webhooks,
    )
    global_wh_url = resolve_discord_webhook_for_sport(
        sport_or_league=None,
        explicit_webhook_url=None,
        env_path=env_path,
        custom_sport_webhooks=custom_sport_webhooks,
    )
    target_webhooks: list[str] = []
    if webhook_url and webhook_url.strip():
        target_webhooks.append(webhook_url.strip())
    else:
        if also_send_to_global and global_wh_url:
            target_webhooks.append(global_wh_url)
        if wh_url and wh_url not in target_webhooks:
            target_webhooks.append(wh_url)

    b_tok = (bot_token or os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    ch_id = (channel_id or os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    configured = bool(target_webhooks or (b_tok and ch_id))

    if dry_run or not configured:
        return {
            "ok": True,
            "dry_run": True,
            "configured": configured,
            "channel": ch_id or ("webhook" if target_webhooks else "<DISCORD_WEBHOOK_URL not set>"),
            "webhooks_count": len(target_webhooks),
            "message_length": len(md_text),
            "chunks_count": len(chunks),
            "has_image": bool(image_bytes),
            "preview": md_text,
        }

    import tempfile

    message_ids: list[str] = []
    last_resp: dict[str, Any] = {}
    targets_to_post = target_webhooks if target_webhooks else [""]

    for active_wh in targets_to_post:
        if active_wh:
            sep = "&" if "?" in active_wh else "?"
            target_url = f"{active_wh}{sep}wait=true"
            headers = ["-H", "Content-Type: application/json"]
        else:
            target_url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
            headers = [
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bot {b_tok}",
            ]

        for idx_c, chunk in enumerate(chunks):
            payload: dict[str, Any] = {"content": chunk, "username": "BetScout Quant Desk"} if active_wh else {"content": chunk}
            attach_img = (idx_c == len(chunks) - 1) and bool(image_bytes)
            if attach_img and image_bytes:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                    tf.write(image_bytes)
                    tmp_png = Path(tf.name)
                try:
                    auth_headers = ["-H", f"Authorization: Bot {b_tok}"] if not active_wh else []
                    proc = subprocess.run(
                        [
                            "curl", "-s", "-m", "20", "-X", "POST", target_url,
                            *auth_headers,
                            "-F", f"payload_json={json.dumps(payload)}",
                            "-F", f"files[0]=@{tmp_png};filename={image_filename};type=image/png",
                        ],
                        capture_output=True,
                        text=True,
                    )
                finally:
                    tmp_png.unlink(missing_ok=True)
            else:
                proc = subprocess.run(
                    [
                        "curl", "-s", "-m", "15", "-X", "POST", target_url,
                        *headers,
                        "-d", json.dumps(payload),
                    ],
                    capture_output=True,
                    text=True,
                )
            if proc.returncode != 0 or not proc.stdout.strip():
                if not message_ids:
                    return {"ok": False, "error": proc.stderr or "Empty response from Discord API"}
                continue
            try:
                resp = json.loads(proc.stdout)
                if isinstance(resp, dict) and resp.get("id"):
                    message_ids.append(str(resp["id"]))
                    last_resp = resp
                elif not message_ids:
                    return {"ok": False, "error": resp.get("message") or str(resp), "raw": resp}
            except Exception as exc:
                if "<!DOCTYPE html>" in proc.stdout or "<html" in proc.stdout.lower():
                    return {"ok": False, "error": "Network proxy blocked request to Discord API"}
                if not message_ids:
                    return {"ok": False, "error": str(exc), "raw": proc.stdout[:300]}

    return {
        "ok": True,
        "dry_run": False,
        "message_id": message_ids[0] if message_ids else None,
        "message_ids": message_ids,
        "chunks_sent": len(message_ids),
        "webhooks_sent": len(target_webhooks),
        "has_image": bool(image_bytes),
        "channel_id": last_resp.get("channel_id"),
    }


_SETTLEMENT_NOTIFY_LOCK = threading.Lock()


def notify_new_settlements_to_discord(
    db_path: Path,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Atomically claim `SETTLED` rows where `notified_at IS NULL` (using `BEGIN IMMEDIATE` + thread lock),
    post a single compact settlement recap to Discord, and prevent duplicate notifications across concurrent
    SSE / background-poller / CLI threads."""
    if not db_path.exists():
        return {"ok": True, "notified_count": 0}

    with _SETTLEMENT_NOTIFY_LOCK:
        conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_bets)").fetchall()}
            if "notified_at" not in cols:
                conn.execute("ALTER TABLE paper_bets ADD COLUMN notified_at TEXT")
            combo_cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_combos)").fetchall()}
            if combo_cols and "notified_at" not in combo_cols:
                conn.execute("ALTER TABLE paper_combos ADD COLUMN notified_at TEXT")

            unnotified = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM paper_bets WHERE status = 'SETTLED' AND notified_at IS NULL ORDER BY kickoff ASC"
                ).fetchall()
            ]
            unnotified_combos = (
                [
                    dict(r)
                    for r in conn.execute(
                        "SELECT * FROM paper_combos WHERE status = 'SETTLED' AND notified_at IS NULL ORDER BY kickoff ASC"
                    ).fetchall()
                ]
                if combo_cols
                else []
            )
            if not unnotified and not unnotified_combos:
                conn.execute("COMMIT")
                conn.close()
                return {"ok": True, "notified_count": 0}

            claim_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not dry_run:
                for r in unnotified:
                    conn.execute(
                        "UPDATE paper_bets SET notified_at = ? WHERE league = ? AND event_id = ? AND notified_at IS NULL",
                        (claim_iso, r["league"], r["event_id"]),
                    )
                for c in unnotified_combos:
                    conn.execute(
                        "UPDATE paper_combos SET notified_at = ? WHERE combo_id = ? AND notified_at IS NULL",
                        (claim_iso, c["combo_id"]),
                    )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            conn.close()
            raise
        conn.close()

        summary = get_paper_ledger_summary(db_path)
        s_cnt = summary.get("settled_count", 0)
        s_wins = summary.get("settled_wins", 0)
        s_loss = summary.get("settled_losses", 0)
        s_prof = float(summary.get("settled_profit_u") or 0.0)
        s_roi = float(summary.get("settled_roi_best") or 0.0) * 100.0

        lines: list[str] = [
            f"🔔 **BETSCOUT — NEW SETTLED PAPER-BET ALERT ({len(unnotified) + len(unnotified_combos)} Resolved)**",
            f"📈 *Cumulative Ledger: {s_cnt} Settled ({s_wins}W - {s_loss}L) · Profit: {s_prof:+.2f}u (ROI {s_roi:+.1f}%)*",
            "",
        ]
        for r in unnotified:
            pnl_v = float(r.get("pnl_best") or 0.0)
            badge = "✅ **WIN**" if pnl_v > 0 else "❌ **LOSS**"
            sp_emoji = SPORT_EMOJIS.get(_league_to_sport_cat(r["league"]), "🎯")
            pick_name = r["home"] if r["side"] == "H" else r["away"]
            sc_str = r.get("settled_score") or f"Winner: {r.get('settled_outcome')}"
            esc_info = ""
            if r.get("exact_score_pred"):
                hit_icon = "🎯 Exact/Cluster HIT!" if r.get("exact_score_hit") == 1 else f"(Proj: {r['exact_score_pred']})"
                esc_info = f" · 🎲 {hit_icon}"
            lines.append(
                f"• {badge} (`{pnl_v:+.2f}u`) {sp_emoji} **{pick_name}** @ **{r['logged_best_odds']:.2f}** — "
                f"*{r['home']} vs {r['away']}* [`{sc_str}`]{esc_info}"
            )
        for c in unnotified_combos:
            c_pnl = float(c.get("pnl") or 0.0)
            c_badge = "✅ **2-LEG COMBO WIN**" if c_pnl > 0 else "❌ **2-LEG COMBO LOSS**"
            l1, l2 = json.loads(c["leg1_json"]), json.loads(c["leg2_json"])
            lines.append(
                f"• 🔗 {c_badge} (`{c_pnl:+.2f}u`) **{c['combo_label']}** @ **{float(c['combined_odds']):.2f}** — "
                f"*{l1.get('pick')}* [`{c.get('leg1_score') or '—'}`] + *{l2.get('pick')}* [`{c.get('leg2_score') or '—'}`]"
            )

        # Render a PNG settlement card / slate image to attach to the Discord settlement alert
        settle_img_bytes: bytes | None = None
        try:
            from .pick_card import render_digest_slate_png, render_pick_card_png

            if len(unnotified) == 1 and not unnotified_combos:
                r0 = unnotified[0]
                pnl0 = float(r0.get("pnl_best") or 0.0)
                settle_img_bytes = render_pick_card_png({
                    "sport_cat": _league_to_sport_cat(r0["league"]),
                    "competition": LEAGUE_LABELS.get(r0["league"], r0["league"].upper()),
                    "announced_at_local": _format_local_time(r0["logged_at"]) if r0.get("logged_at") else "",
                    "date_local": _format_local_time(r0["kickoff"]),
                    "ended_at_local": _format_local_time(r0.get("updated_at") or claim_iso),
                    "match": f"{r0['home']} vs {r0['away']} [{r0.get('settled_score') or ''}]",
                    "pick_name": f"{r0['home'] if r0['side'] == 'H' else r0['away']} ({'WIN' if pnl0 > 0 else 'LOSS'} {pnl0:+.2f}u)",
                    "tier": r0.get("tier") or "SETTLED",
                    "status_badge": f"{'WIN' if pnl0 > 0 else 'LOSS'} ({pnl0:+.2f}u)",
                    "win_prob": r0.get("p_mkt"),
                    "odds": r0.get("logged_best_odds"),
                    "odds_display": f"{float(r0.get('logged_best_odds') or 1.0):.2f}",
                    "exact_score_pick": r0.get("exact_score_pred") or r0.get("settled_score") or "Settled",
                })
            elif unnotified:
                slate_rows = [
                    {
                        "sport_cat": _league_to_sport_cat(r["league"]),
                        "announced_at_local": _format_local_time(r["logged_at"]) if r.get("logged_at") else "",
                        "date_local": _format_local_time(r["kickoff"]),
                        "ended_at_local": _format_local_time(r.get("updated_at") or claim_iso),
                        "match": f"{r['home']} vs {r['away']}",
                        "settled_score": r.get("settled_score") or "",
                        "pick_name": f"{r['home'] if r['side'] == 'H' else r['away']} ({'W' if float(r.get('pnl_best') or 0) > 0 else 'L'} {float(r.get('pnl_best') or 0):+.2f}u)",
                        "win_prob": r.get("p_mkt"),
                        "odds": r.get("logged_best_odds"),
                        "odds_display": f"{float(r.get('logged_best_odds') or 1.0):.2f}",
                    }
                    for r in unnotified
                ]
                settle_img_bytes = render_digest_slate_png(
                    slate_rows,
                    title=f"SETTLED PAPER-BET RECAP ({len(unnotified)} RESOLVED)",
                    subtitle=f"Cumulative Ledger: {s_cnt} Settled ({s_wins}W - {s_loss}L) · Profit: {s_prof:+.2f}u (ROI {s_roi:+.1f}%)",
                )
        except Exception:
            settle_img_bytes = None

        msg = "\n".join(lines)
        res = send_discord_message(
            msg,
            webhook_url=webhook_url,
            dry_run=dry_run,
            env_path=None,
            image_bytes=settle_img_bytes,
            image_filename="betscout_settlement.png",
        )
        # Also route sport-specific settlement alerts to any dedicated per-sport Discord webhooks configured in .env
        if not webhook_url:
            global_wh = resolve_discord_webhook_for_sport(None)
            by_sp_unnotified: dict[str, list[dict[str, Any]]] = {}
            for r in unnotified:
                sp_c = _league_to_sport_cat(r["league"])
                sp_wh = resolve_discord_webhook_for_sport(sp_c)
                if sp_wh and sp_wh != global_wh:
                    by_sp_unnotified.setdefault(sp_c, []).append(r)
            for sp_c, sp_rows in by_sp_unnotified.items():
                sp_wh = resolve_discord_webhook_for_sport(sp_c)
                sp_lines = [
                    f"🔔 **BETSCOUT ({sp_c.upper()}) — NEW SETTLED PAPER-BET ALERT ({len(sp_rows)} Resolved)**",
                    "",
                ]
                for r in sp_rows:
                    pnl_v = float(r.get("pnl_best") or 0.0)
                    badge = "✅ **WIN**" if pnl_v > 0 else "❌ **LOSS**"
                    sp_emoji = SPORT_EMOJIS.get(sp_c, "🎯")
                    pick_name = r["home"] if r["side"] == "H" else r["away"]
                    sc_str = r.get("settled_score") or f"Winner: {r.get('settled_outcome')}"
                    sp_lines.append(
                        f"• {badge} (`{pnl_v:+.2f}u`) {sp_emoji} **{pick_name}** @ **{r['logged_best_odds']:.2f}** — *{r['home']} vs {r['away']}* [`{sc_str}`]"
                    )
                send_discord_message("\n".join(sp_lines), webhook_url=sp_wh, dry_run=dry_run)

            # Also publish settled WIN/LOSS recaps to the Free Public Teaser Channel (`DISCORD_WEBHOOK_URL_FREE_TEASER`)
            # and any active B2B Syndicate customer webhooks (`subscriber_webhooks` in betscout.db)
            free_teaser_wh = (os.environ.get("DISCORD_WEBHOOK_URL_FREE_TEASER") or "").strip()
            if free_teaser_wh.startswith("https://discord") and free_teaser_wh != global_wh:
                send_discord_message(
                    msg + "\n\n🚀 *Unlock all daily VIP picks, exact-score matrices & 2-leg combos at **https://betscout.app***",
                    webhook_url=free_teaser_wh,
                    dry_run=dry_run,
                    image_bytes=settle_img_bytes,
                    image_filename="betscout_settlement.png",
                    also_send_to_global=False,
                )
            try:
                from .monetization import list_subscriber_webhooks

                for sub_wh in list_subscriber_webhooks(db_path, active_only=True):
                    if sub_wh.get("channel_type") == "discord" and str(sub_wh.get("target_url_or_chat") or "").startswith("https://discord"):
                        send_discord_message(
                            msg,
                            webhook_url=str(sub_wh["target_url_or_chat"]),
                            dry_run=dry_run,
                            image_bytes=settle_img_bytes,
                            image_filename="betscout_settlement.png",
                            also_send_to_global=False,
                        )
            except Exception:
                pass
        if not dry_run and not res.get("ok"):
            # Release claim so a future retry can send if network/webhook failed
            c_rel = sqlite3.connect(db_path, timeout=15.0)
            for r in unnotified:
                c_rel.execute(
                    "UPDATE paper_bets SET notified_at = NULL WHERE league = ? AND event_id = ? AND notified_at = ?",
                    (r["league"], r["event_id"], claim_iso),
                )
            for c in unnotified_combos:
                c_rel.execute(
                    "UPDATE paper_combos SET notified_at = NULL WHERE combo_id = ? AND notified_at = ?",
                    (c["combo_id"], claim_iso),
                )
            c_rel.commit()
            c_rel.close()

        # Also mirror settlement alerts + PNG card to Telegram when configured
        if not webhook_url:
            try:
                if get_telegram_env_config().get("configured"):
                    send_telegram_message(
                        discord_markdown_to_telegram_html(msg),
                        dry_run=dry_run,
                        image_bytes=settle_img_bytes,
                        image_filename="betscout_settlement.png",
                    )
            except Exception:
                pass
        return {**res, "notified_count": len(unnotified) + len(unnotified_combos)}


def notify_new_picks_to_discord(
    db_path: Path,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Atomically claim newly logged pre-match `PENDING` rows in `paper_bets` where `pick_notified_at IS NULL`,
    post their initial Pick Suggestion + high-res Cyan-bordered PNG Card/Slate to Discord (plus per-sport webhooks),
    and prevent duplicate announcements across concurrent scans."""
    if not db_path.exists():
        return {"ok": True, "notified_picks_count": 0}

    with _SETTLEMENT_NOTIFY_LOCK:
        conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_bets)").fetchall()}
            if "pick_notified_at" not in cols:
                conn.execute("ALTER TABLE paper_bets ADD COLUMN pick_notified_at TEXT")

            unnotified_picks = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM paper_bets WHERE status = 'PENDING' AND pick_notified_at IS NULL AND (is_live = 0 OR is_live IS NULL) ORDER BY kickoff ASC"
                ).fetchall()
            ]
            if not unnotified_picks:
                conn.execute("COMMIT")
                conn.close()
                return {"ok": True, "notified_picks_count": 0}

            claim_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not dry_run:
                for r in unnotified_picks:
                    conn.execute(
                        "UPDATE paper_bets SET pick_notified_at = ? WHERE league = ? AND event_id = ? AND pick_notified_at IS NULL",
                        (claim_iso, r["league"], r["event_id"]),
                    )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            conn.close()
            raise
        conn.close()

        summary = get_paper_ledger_summary(db_path)
        s_cnt = int(summary.get("settled_count") or 0)
        s_wins = int(summary.get("settled_wins") or 0)
        s_loss = int(summary.get("settled_losses") or 0)
        s_wr = (s_wins / max(1, s_cnt)) * 100.0 if s_cnt else 0.0
        s_prof = float(summary.get("settled_profit_u") or 0.0)
        s_roi = float(summary.get("settled_roi_best") or 0.0) * 100.0

        def _row_win_prob(r: dict[str, Any]) -> float:
            lg_l = str(r.get("league") or "").lower()
            comp_v = float(r.get("composite_score") or 0.0)
            if lg_l in ("atp", "wta", "nba", "wnba", "nhl", "nfl", "mlb", "table_tennis", "handball", "darts") and 0.45 <= comp_v <= 0.99:
                return comp_v
            return min(max(float(r.get("p_mkt") or 0.62) + 0.04, 0.52), 0.92)

        def _format_pick_bullet(r: dict[str, Any]) -> str:
            sp_c = _league_to_sport_cat(r["league"])
            sp_emoji = SPORT_EMOJIS.get(sp_c, "🎯")
            pick_name = r["home"] if r["side"] == "H" else r["away"]
            comp_lbl = LEAGUE_LABELS.get(r["league"], str(r["league"]).upper())
            ko_loc = _format_local_time(r["kickoff"])
            wp_v = _row_win_prob(r)
            fair_o = 1.0 / max(wp_v, 0.05)
            odds_v = float(r.get("logged_best_odds") or 1.25)
            esc_str = f" · 🎲 Score Target: **{r['exact_score_pred']}**" if r.get("exact_score_pred") else ""
            return (
                f"• {sp_emoji} **{r['home']} vs {r['away']}** (*{comp_lbl}* · 🕒 `{ko_loc}`)\n"
                f"  👉 Pick: **{pick_name} ({r['side']})** @ **{odds_v:.2f}** "
                f"(Win Prob `{wp_v*100:.1f}%`, Min Fair `{fair_o:.2f}`, Tier `{r.get('tier') or 'high_conf'}`){esc_str}"
            )

        def _build_card_payload(r: dict[str, Any]) -> dict[str, Any]:
            wp_v = _row_win_prob(r)
            fair_o = 1.0 / max(wp_v, 0.05)
            odds_v = float(r.get("logged_best_odds") or 1.25)
            pick_name = r["home"] if r["side"] == "H" else r["away"]
            return {
                "sport_cat": _league_to_sport_cat(r["league"]),
                "competition": LEAGUE_LABELS.get(r["league"], str(r["league"]).upper()),
                "announced_at_local": _format_local_time(r.get("logged_at") or claim_iso),
                "date_local": _format_local_time(r["kickoff"]),
                "match": f"{r['home']} vs {r['away']}",
                "pick_name": f"{pick_name} ({r['side']})",
                "tier": r.get("tier") or "HIGH-CONF",
                "badge": str(r.get("tier") or "LIVE AI PICK").upper(),
                "win_prob": wp_v,
                "win_prob_str": f"{wp_v * 100:.1f}%",
                "odds": odds_v,
                "odds_display": f"{odds_v:.2f} (Fair {fair_o:.2f})",
                "fair_str": f"@ {fair_o:.2f}",
                "exact_score_pick": r.get("exact_score_pred") or "Moneyline Edge",
            }

        lines: list[str] = [
            f"🎯 **BETSCOUT — NEW HIGH-CONVICTION PRE-MATCH PICK{'S' if len(unnotified_picks) != 1 else ''} ({len(unnotified_picks)} Active)**",
            f"📈 *Verified Ledger: {s_cnt} Settled ({s_wins}W - {s_loss}L · {s_wr:.1f}%) · Profit: {s_prof:+.2f}u (ROI {s_roi:+.1f}%)*",
            "",
        ]
        for r in unnotified_picks[:15]:
            lines.append(_format_pick_bullet(r))
        if len(unnotified_picks) > 15:
            lines.append(f"\n*…plus {len(unnotified_picks) - 15} more active pre-match picks on <https://betscout.app>*")
        else:
            lines.append("\n🌐 *Live Quant Desk, Exact-Score Splits & 2-Leg Combos: <https://betscout.app>*")

        pick_img_bytes: bytes | None = None
        try:
            from .pick_card import render_digest_slate_png, render_pick_card_png

            card_payloads = [_build_card_payload(r) for r in unnotified_picks[:10]]
            if len(card_payloads) == 1:
                pick_img_bytes = render_pick_card_png(card_payloads[0])
            elif card_payloads:
                pick_img_bytes = render_digest_slate_png(
                    card_payloads,
                    title=f"NEW HIGH-CONVICTION PICKS SLATE ({len(unnotified_picks)} ACTIVE)",
                    subtitle=f"Verified Track Record: {s_cnt} Settled ({s_wins}W - {s_loss}L · {s_wr:.1f}%) · Profit: {s_prof:+.2f}u",
                )
        except Exception:
            pick_img_bytes = None

        msg = "\n".join(lines)
        res = send_discord_message(
            msg,
            webhook_url=webhook_url,
            dry_run=dry_run,
            env_path=None,
            image_bytes=pick_img_bytes,
            image_filename="betscout_picks.png",
        )

        # Also route sport-specific pre-match pick cards to dedicated per-sport Discord webhooks
        if not webhook_url:
            global_wh = resolve_discord_webhook_for_sport(None)
            by_sp_picks: dict[str, list[dict[str, Any]]] = {}
            for r in unnotified_picks:
                sp_c = _league_to_sport_cat(r["league"])
                sp_wh = resolve_discord_webhook_for_sport(sp_c)
                if sp_wh and sp_wh != global_wh:
                    by_sp_picks.setdefault(sp_c, []).append(r)
            for sp_c, sp_rows in by_sp_picks.items():
                sp_wh = resolve_discord_webhook_for_sport(sp_c)
                sp_lines = [
                    f"🎯 **BETSCOUT ({sp_c.upper()}) — NEW HIGH-CONVICTION PICK{'S' if len(sp_rows) != 1 else ''} ({len(sp_rows)} Active)**",
                    "",
                ]
                for r in sp_rows[:12]:
                    sp_lines.append(_format_pick_bullet(r))
                sp_img: bytes | None = None
                try:
                    from .pick_card import render_digest_slate_png, render_pick_card_png

                    sp_payloads = [_build_card_payload(r) for r in sp_rows[:10]]
                    sp_img = (
                        render_pick_card_png(sp_payloads[0])
                        if len(sp_payloads) == 1
                        else render_digest_slate_png(sp_payloads, title=f"{sp_c.upper()} HIGH-CONVICTION PICKS ({len(sp_rows)} ACTIVE)")
                    )
                except Exception:
                    sp_img = None
                send_discord_message(
                    "\n".join(sp_lines),
                    webhook_url=sp_wh,
                    dry_run=dry_run,
                    image_bytes=sp_img,
                    image_filename=f"betscout_{sp_c}_picks.png",
                    also_send_to_global=False,
                )

            try:
                from .monetization import list_subscriber_webhooks

                for sub_wh in list_subscriber_webhooks(db_path, active_only=True):
                    if sub_wh.get("channel_type") == "discord" and str(sub_wh.get("target_url_or_chat") or "").startswith("https://discord"):
                        send_discord_message(
                            msg,
                            webhook_url=str(sub_wh["target_url_or_chat"]),
                            dry_run=dry_run,
                            image_bytes=pick_img_bytes,
                            image_filename="betscout_picks.png",
                            also_send_to_global=False,
                        )
            except Exception:
                pass

        if not dry_run and not res.get("ok"):
            c_rel = sqlite3.connect(db_path, timeout=15.0)
            for r in unnotified_picks:
                c_rel.execute(
                    "UPDATE paper_bets SET pick_notified_at = NULL WHERE league = ? AND event_id = ? AND pick_notified_at = ?",
                    (r["league"], r["event_id"], claim_iso),
                )
            c_rel.commit()
            c_rel.close()

        # Also ensure today's Free Daily Teaser has been posted to DISCORD_WEBHOOK_URL_FREE_TEASER
        # and mirror new pre-match pick alerts + PNG card to Telegram when configured
        if not webhook_url:
            try:
                ensure_daily_free_teaser_sent(db_path, dry_run=dry_run)
            except Exception:
                pass
            try:
                if get_telegram_env_config().get("configured"):
                    send_telegram_message(
                        discord_markdown_to_telegram_html(msg),
                        dry_run=dry_run,
                        image_bytes=pick_img_bytes,
                        image_filename="betscout_picks.png",
                    )
            except Exception:
                pass

        return {**res, "notified_picks_count": len(unnotified_picks)}


_INPLAY_NOTIFIED_MEMORY: set[str] = set()


def send_free_teaser_to_discord(
    rec: dict[str, Any] | None = None,
    db_path: Path | None = None,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Format and send a high-converting Free Daily Teaser (1 unlocked pick + PNG Pick Card + verified track record + locked VIP count)
    to `DISCORD_WEBHOOK_URL_FREE_TEASER`."""
    from .pick_card import render_pick_card_png

    load_dotenv(override=False)
    target_wh = (webhook_url or os.environ.get("DISCORD_WEBHOOK_URL_FREE_TEASER") or "").strip()
    if not target_wh.startswith("https://discord"):
        return {"ok": False, "error": "DISCORD_WEBHOOK_URL_FREE_TEASER not configured"}

    rec_obj = dict(rec or {})
    if not rec_obj and db_path and (db_path.parent / "recommendations.json").exists():
        try:
            rec_obj = json.loads((db_path.parent / "recommendations.json").read_text(encoding="utf-8"))
        except Exception:
            rec_obj = {}

    ledger = rec_obj.get("paper_ledger") or {}
    if db_path and db_path.exists():
        try:
            ledger = get_paper_ledger_summary(db_path)
        except Exception:
            pass

    s_cnt = int(ledger.get("settled_count") or 0)
    s_wins = int(ledger.get("settled_wins") or 0)
    s_loss = int(ledger.get("settled_losses") or 0)
    s_wr = (s_wins / max(1, s_cnt)) * 100.0 if s_cnt else 0.0
    s_prof = float(ledger.get("settled_profit_u") or 0.0)
    s_roi = float(ledger.get("settled_roi_best") or 0.0) * 100.0

    all_bets = build_best_bets_summary(rec_obj, min_odds=1.12, sport_filter="all") if rec_obj else []
    if not all_bets and db_path and db_path.exists():
        try:
            conn_b = sqlite3.connect(db_path, timeout=15.0)
            conn_b.row_factory = sqlite3.Row
            pend_rows = [
                dict(r)
                for r in conn_b.execute(
                    "SELECT * FROM paper_bets WHERE status = 'PENDING' AND (is_live = 0 OR is_live IS NULL) ORDER BY kickoff ASC"
                ).fetchall()
            ]
            conn_b.close()
            for r in pend_rows:
                lg_l = str(r.get("league") or "").lower()
                comp_v = float(r.get("composite_score") or 0.0)
                wp_v = (
                    comp_v
                    if lg_l in ("atp", "wta", "nba", "wnba", "nhl", "nfl", "mlb", "table_tennis", "handball", "darts") and 0.45 <= comp_v <= 0.99
                    else min(max(float(r.get("p_mkt") or 0.62) + 0.04, 0.52), 0.92)
                )
                odds_v = float(r.get("logged_best_odds") or 1.25)
                fair_o = round(1.0 / max(wp_v, 0.05), 2)
                pick_name = r["home"] if r["side"] == "H" else r["away"]
                all_bets.append({
                    "sport_cat": _league_to_sport_cat(r["league"]),
                    "competition": LEAGUE_LABELS.get(r["league"], str(r["league"]).upper()),
                    "date": r["kickoff"],
                    "date_local": _format_local_time(r["kickoff"]),
                    "announced_at_local": _format_local_time(r.get("logged_at") or r["kickoff"]),
                    "match": f"{r['home']} vs {r['away']}",
                    "pick_name": f"{pick_name} ({r['side']})",
                    "tier": r.get("tier") or "HIGH-CONF",
                    "win_prob": wp_v,
                    "odds": odds_v,
                    "odds_display": f"{odds_v:.2f} (Fair {fair_o:.2f})",
                    "min_fair_odds": fair_o,
                    "exact_score_pick": r.get("exact_score_pred") or "Moneyline Edge",
                })
        except Exception:
            pass

    if not all_bets:
        return {"ok": False, "error": "No active picks available for teaser"}

    # Prefer a pick kicking off today (in Europe/Vienna) if available
    today_ymd = datetime.now(ZoneInfo(DEFAULT_LOCAL_TZ)).strftime("%Y-%m-%d")
    today_bets = [b for b in all_bets if str(b.get("date_local") or b.get("date") or "").startswith(today_ymd)]
    teaser_pick = today_bets[0] if today_bets else all_bets[0]
    locked_cnt = max(0, len(all_bets) - 1)
    sp_cat = teaser_pick.get("sport_cat") or "soccer"
    sp_ico = SPORT_EMOJIS.get(sp_cat, "🎯")
    wp_pct = float(teaser_pick.get("win_prob") or 0.75) * 100.0
    esc_str = teaser_pick.get("exact_score_pick") or ""
    esc_suffix = f" · 🎲 Score Target: **{esc_str}**" if (esc_str and esc_str not in ("—", "Moneyline Edge")) else ""

    lines = [
        "🔓 **BETSCOUT — FREE DAILY TEASER PICK & VERIFIED TRACK RECORD**",
        f"📊 **Verified Ledger:** `{s_cnt} Graded` (`{s_wins}W – {s_loss}L` · **`{s_wr:.1f}% Win Rate`**) · **Profit:** `{s_prof:+.2f}u` (**`{s_roi:+.1f}% ROI`**)",
        "",
        f"🎁 **FREE PICK OF THE DAY (1 of {len(all_bets)} Active Picks):**",
        f"{sp_ico} **{teaser_pick.get('match')}** (*{teaser_pick.get('competition') or teaser_pick.get('sport_league')}*)",
        f"🕒 Start: `{teaser_pick.get('date_local') or teaser_pick.get('date')}`",
        f"✅ Pick: **{teaser_pick.get('pick_name') or teaser_pick.get('pick')}** (`{wp_pct:.1f}%` Model Win Prob)",
        f"💰 Odds: **{teaser_pick.get('odds_display')}**{esc_suffix}",
        "",
        f"🔒 **+{locked_cnt} More High-Conviction VIP Picks, Exact-Score Splits & 2-Leg Combos** are live right now!",
        "🚀 **Unlock Full Pro App & VIP Discord/Telegram Alerts:** <https://betscout.app>",
    ]
    msg = "\n".join(lines)
    img_bytes: bytes | None = None
    try:
        img_bytes = render_pick_card_png(teaser_pick)
    except Exception:
        img_bytes = None

    res = send_discord_message(
        text=msg,
        webhook_url=target_wh,
        dry_run=dry_run,
        image_bytes=img_bytes,
        image_filename="betscout_free_teaser.png",
        also_send_to_global=False,
    )
    if not dry_run and res.get("ok") and db_path and db_path.exists():
        try:
            conn_t = sqlite3.connect(db_path, timeout=15.0)
            conn_t.execute(
                "CREATE TABLE IF NOT EXISTS daily_teaser_log (date_ymd TEXT PRIMARY KEY, match_name TEXT, sent_at TEXT, message_id TEXT)"
            )
            conn_t.execute(
                "INSERT OR REPLACE INTO daily_teaser_log (date_ymd, match_name, sent_at, message_id) VALUES (?, ?, ?, ?)",
                (
                    today_ymd,
                    str(teaser_pick.get("match") or ""),
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    str(res.get("message_id") or ""),
                ),
            )
            conn_t.commit()
            conn_t.close()
        except Exception:
            pass
    return res


def ensure_daily_free_teaser_sent(
    db_path: Path,
    rec: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ensure that 1 Free Daily Teaser pick has been sent to `DISCORD_WEBHOOK_URL_FREE_TEASER` for today's
    local date (`Europe/Vienna`). Atomically claims today's date in `daily_teaser_log` to prevent duplicates."""
    if not db_path.exists():
        return {"ok": False, "error": "Database does not exist"}
    load_dotenv(override=False)
    target_wh = (os.environ.get("DISCORD_WEBHOOK_URL_FREE_TEASER") or "").strip()
    if not target_wh.startswith("https://discord"):
        return {"ok": False, "error": "DISCORD_WEBHOOK_URL_FREE_TEASER not configured"}

    today_ymd = datetime.now(ZoneInfo(DEFAULT_LOCAL_TZ)).strftime("%Y-%m-%d")
    with _SETTLEMENT_NOTIFY_LOCK:
        conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS daily_teaser_log (date_ymd TEXT PRIMARY KEY, match_name TEXT, sent_at TEXT, message_id TEXT)"
            )
            existing = conn.execute("SELECT * FROM daily_teaser_log WHERE date_ymd = ?", (today_ymd,)).fetchone()
            if existing:
                conn.execute("COMMIT")
                conn.close()
                return {"ok": True, "already_sent": True, "date_ymd": today_ymd, "match": existing["match_name"]}
            claim_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not dry_run:
                conn.execute(
                    "INSERT INTO daily_teaser_log (date_ymd, match_name, sent_at, message_id) VALUES (?, ?, ?, ?)",
                    (today_ymd, "CLAIMING", claim_iso, ""),
                )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            conn.close()
            raise
        conn.close()

        res = send_free_teaser_to_discord(rec=rec, db_path=db_path, webhook_url=target_wh, dry_run=dry_run)
        if not dry_run and not res.get("ok"):
            try:
                c_rel = sqlite3.connect(db_path, timeout=15.0)
                c_rel.execute("DELETE FROM daily_teaser_log WHERE date_ymd = ? AND match_name = 'CLAIMING'", (today_ymd,))
                c_rel.commit()
                c_rel.close()
            except Exception:
                pass
        return {**res, "already_sent": False, "date_ymd": today_ymd}


def notify_inplay_rebound_edges_to_discord(
    db_path: Path,
    webhook_url: str | None = None,
    dry_run: bool = False,
    global_enabled: bool = False,
    item_overrides: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Check `paper_bets` for any active in-play (`status = 'PENDING' AND is_live = 1`) match
    whose `live_momentum_json` has `is_rebound_edge == True` and has not yet been notified
    (checked against both persistent `inplay_notified_at` column and `notified_live_edge` JSON flag),
    post a one-time Halftime / In-Play Dominance Rebound alert to Discord, and stamp both."""
    if not db_path.exists():
        return {"ok": True, "notified_count": 0}
    overrides = {str(k).lower(): bool(v) for k, v in (item_overrides or {}).items()}

    with _SETTLEMENT_NOTIFY_LOCK:
        conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_bets)").fetchall()}
            if "inplay_notified_at" not in cols:
                conn.execute("ALTER TABLE paper_bets ADD COLUMN inplay_notified_at TEXT")
            rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM paper_bets WHERE status = 'PENDING' AND is_live = 1 AND live_momentum_json IS NOT NULL AND inplay_notified_at IS NULL"
                ).fetchall()
            ]
            to_notify: list[tuple[dict[str, Any], dict[str, Any]]] = []
            now_claim = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for r in rows:
                item_k = f"{r['league']}:{r['event_id']}".lower()
                if not dry_run and item_k in _INPLAY_NOTIFIED_MEMORY:
                    continue
                is_allowed = overrides.get(item_k, global_enabled)
                if not is_allowed:
                    continue
                try:
                    mom = json.loads(r["live_momentum_json"] or "{}")
                except Exception:
                    mom = {}
                if mom.get("is_rebound_edge") and not mom.get("notified_live_edge"):
                    mom["notified_live_edge"] = True
                    if not dry_run:
                        _INPLAY_NOTIFIED_MEMORY.add(item_k)
                        conn.execute(
                            "UPDATE paper_bets SET live_momentum_json = ?, inplay_notified_at = ? WHERE league = ? AND event_id = ?",
                            (json.dumps(mom), now_claim, r["league"], r["event_id"]),
                        )
                    to_notify.append((r, mom))
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            conn.close()
            raise
        conn.close()

        if not to_notify:
            return {"ok": True, "notified_count": 0}

        lines = [
            f"🔥 **BETSCOUT — LIVE IN-PLAY DOMINANCE REBOUND ALERT ({len(to_notify)} Active)**",
            "",
        ]
        for r, mom in to_notify:
            pick_team = r["home"] if r["side"] == "H" else r["away"]
            lg_lbl = LEAGUE_LABELS.get(r["league"], r["league"].upper())
            if mom.get("sport") == "tennis" or r["league"].lower() in ("atp", "wta"):
                lines.append(
                    f"• 🎾 **{r['home']} vs {r['away']}** ({lg_lbl}) — Score: **`{r.get('live_score') or 'LIVE'}`**\n"
                    f"  🎯 Backed Banker: **{pick_team}** (Pre-Match `{mom.get('pre_win_prob_pct',75):.1f}%` @ `{r['logged_best_odds']:.2f}`) | "
                    f"📊 Set-1 Comeback Trigger: Dropped tight Set 1 (`{mom.get('set1_pick_games',4)}-{mom.get('set1_opp_games',6)}`, `{mom.get('set1_total_games',10)}` games) · "
                    f"3-Set Decider Edge `{mom.get('decider_diff',0.0):+.2f}` · Game Elo `{mom.get('game_elo_diff',0.0):+.0f}`"
                )
            else:
                lines.append(
                    f"• ⚽ **{r['home']} vs {r['away']}** ({lg_lbl}) — Score: **`{r.get('live_score') or 'LIVE'}`**\n"
                    f"  🎯 Backed Favorite: **{pick_team} ({r['side']})** @ `{r['logged_best_odds']:.2f}` | "
                    f"📊 Live Telemetry: **SoT `{mom.get('sot_for_pick',0)}–{mom.get('sot_opp',0)}` (`{mom.get('sot_diff',0):+d}`)** · "
                    f"Shots `{mom.get('shots_diff',0):+d}` · Corners `{mom.get('corners_diff',0):+d}` · Possession **`{mom.get('poss_pct',50):.0f}%`**"
                )
        res = send_discord_message("\n".join(lines), webhook_url=webhook_url, dry_run=dry_run)
        if not webhook_url:
            global_wh = resolve_discord_webhook_for_sport(None)
            for r, mom in to_notify:
                sp_c = "tennis" if (mom.get("sport") == "tennis" or r["league"].lower() in ("atp", "wta")) else _league_to_sport_cat(r["league"])
                sp_wh = resolve_discord_webhook_for_sport(sp_c)
                if sp_wh and sp_wh != global_wh:
                    send_discord_message("\n".join(lines), webhook_url=sp_wh, dry_run=dry_run)
            try:
                if get_telegram_env_config().get("configured"):
                    send_telegram_message(discord_markdown_to_telegram_html("\n".join(lines)), dry_run=dry_run)
            except Exception:
                pass
        return {**res, "notified_count": len(to_notify)}


def discord_markdown_to_telegram_html(md_text: str) -> str:
    """Convert Discord Markdown (`**bold**`, `*italic*`, `` `code` ``, `<https://...>`) to safe Telegram HTML."""
    s = re.sub(r"<(https?://[^>]+)>", r"\1", str(md_text or ""))
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", s)
    return s


def get_telegram_env_config(env_path: Path | None = None) -> dict[str, Any]:
    """Reload `.env` on the fly and return current Telegram configuration status."""
    load_dotenv(env_path=env_path, override=True)
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    masked_token = (token[:6] + "..." + token[-4:]) if len(token) > 12 else ("***" if token else "")
    return {
        "configured": bool(token and chat_id),
        "has_token": bool(token),
        "masked_token": masked_token,
        "chat_id": chat_id,
    }


def send_telegram_message(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
    dry_run: bool = False,
    env_path: Path | None = None,
    image_bytes: bytes | None = None,
    image_filename: str = "betscout_pick.png",
) -> dict[str, Any]:
    """Post an HTML-formatted message (and optional PNG card photo via `sendPhoto`) to a Telegram channel/chat."""
    load_dotenv(env_path=env_path, override=True)
    token = (bot_token or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    target_chat = (chat_id or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    # Telegram HTML parse_mode only supports &lt;, &gt;, &amp;, and &quot; — convert named arrow/dash entities to direct Unicode
    text = (
        str(text or "")
        .replace("&rarr;", "→")
        .replace("&ndash;", "–")
        .replace("&mdash;", "—")
        .replace("&middot;", "·")
    )

    if dry_run or not token or not target_chat:
        return {
            "ok": True,
            "dry_run": True,
            "configured": bool(token and target_chat),
            "chat_id": target_chat or "<TELEGRAM_CHAT_ID not set>",
            "message_length": len(text),
            "has_image": bool(image_bytes),
            "preview": text,
        }

    import tempfile

    if image_bytes and len(text) <= 1020:
        photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(image_bytes)
            tmp_png = Path(tf.name)
        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "--connect-timeout", "4", "-m", "12", "-X", "POST", photo_url,
                    "-F", f"chat_id={target_chat}",
                    "-F", "parse_mode=HTML",
                    "-F", f"caption={text}",
                    "-F", f"photo=@{tmp_png};filename={image_filename};type=image/png",
                ],
                capture_output=True,
                text=True,
            )
        finally:
            tmp_png.unlink(missing_ok=True)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        safe_text = text if len(text) <= 4050 else (text[:4000].rsplit("\n", 1)[0] + "\n<i>…(see full slate at https://betscout.app)</i>")
        payload = {
            "chat_id": target_chat,
            "text": safe_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        proc = subprocess.run(
            [
                "curl", "-s", "--connect-timeout", "4", "-m", "10", "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
            ],
            capture_output=True,
            text=True,
        )
        if image_bytes:
            photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tf.write(image_bytes)
                tmp_png = Path(tf.name)
            try:
                subprocess.run(
                    [
                        "curl", "-s", "--connect-timeout", "4", "-m", "12", "-X", "POST", photo_url,
                        "-F", f"chat_id={target_chat}",
                        "-F", f"photo=@{tmp_png};filename={image_filename};type=image/png",
                    ],
                    capture_output=True,
                    text=True,
                )
            finally:
                tmp_png.unlink(missing_ok=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"ok": False, "error": proc.stderr or "Empty response from Telegram API"}
    if "<!DOCTYPE html>" in proc.stdout or "<html" in proc.stdout.lower():
        return {
            "ok": False,
            "error": "api.telegram.org is unreachable on this network. Use Discord (DISCORD_WEBHOOK_URL in .env)!",
        }
    try:
        resp = json.loads(proc.stdout)
        return resp
    except Exception as exc:
        return {"ok": False, "error": str(exc), "raw": proc.stdout[:300]}
