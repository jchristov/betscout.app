"""Discord & Telegram Social Publisher (`src/sportdata_model/telegram_bot.py`).

Primary Social Integration: **Discord** (100% reachable through Zscaler via `https://discord.com/api/...`)
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
from pathlib import Path
from typing import Any

from . import load_dotenv
from .dashboard import DEFAULT_LOCAL_TZ, _format_local_time, _league_to_sport_cat, build_best_bets_summary
from .espn import LEAGUE_LABELS
from .paper_trade import (
    build_recommended_2leg_doubles,
    get_paper_ledger_summary,
    settle_pending_paper_trades,
)

SPORT_EMOJIS: dict[str, str] = {
    "soccer": "⚽",
    "tennis": "🎾",
    "basketball": "🏀",
    "hockey": "🏒",
    "football": "🏈",
    "baseball": "⚾",
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
    max_picks: int = 12,
    include_settled: bool = True,
    tz_name: str = DEFAULT_LOCAL_TZ,
) -> str:
    """Build a Telegram HTML-formatted digest of settled paper bets and top upcoming/live picks."""
    if db_path and db_path.exists():
        try:
            settle_pending_paper_trades(db_path)
            rec = {**rec, "paper_ledger": get_paper_ledger_summary(db_path)}
        except Exception:
            pass

    ledger = rec.get("paper_ledger") or {}
    best_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=sport_filter)
    gen_local = _format_local_time(rec.get("generated_at") or "", tz_name)

    lines: list[str] = [
        "📊 <b>SPORTDATA QUANT DESK — DAILY SIGNAL DIGEST</b>",
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
        settled_trades = [t for t in (ledger.get("trades") or []) if t.get("status") == "SETTLED"]
        for tr in settled_trades[-6:]:
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

    # Vetoed injury alerts (high value for followers)
    vetoed = [
        p for p in (rec.get("qualifying_picks") or [])
        if str(p.get("action", "")).startswith("VETOED")
    ]
    if vetoed and sport_filter in ("all", "soccer"):
        lines.append("🚨 <b>System-1 Injury / Lineup Vetoes (DO NOT BET):</b>")
        for v in vetoed[:4]:
            lg_lbl = LEAGUE_LABELS.get(v["league"], v["league"].upper())
            sp_emoji = SPORT_EMOJIS.get(_league_to_sport_cat(v["league"]), "⚽")
            lines.append(
                f"  ⛔ {sp_emoji} <b>{html.escape(v['home'])} vs {html.escape(v['away'])}</b> ({html.escape(lg_lbl)}) — "
                f"<code>{html.escape(v['action'])}</code>"
            )
        lines.append("")

    lines.append(
        f"🔥 <b>Top Upcoming &amp; Live Picks (Odds &gt; {min_odds:.2f} · Showing {min(len(best_bets), max_picks)} of {len(best_bets)}):</b>"
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

    doubles = rec.get("recommended_doubles") or build_recommended_2leg_doubles(
        rec.get("qualifying_picks") or [],
        rec.get("tennis_picks") or [],
        rec.get("other_sport_picks") or [],
        max_doubles=3,
    )
    if doubles and sport_filter == "all":
        lines.append("")
        lines.append("🔗 <b>Recommended Uncorrelated 2-Leg Doubles (Parlays):</b>")
        for idx_d, d in enumerate(doubles[:3], start=1):
            l1, l2 = d["leg_1"], d["leg_2"]
            e1 = SPORT_EMOJIS.get(_league_to_sport_cat(l1["league"]), "🎯")
            e2 = SPORT_EMOJIS.get(_league_to_sport_cat(l2["league"]), "🎯")
            lines.append(
                f"  <b>Double #{idx_d}</b> — Combined Odds: <b>{d['combined_odds']:.2f}</b> "
                f"(WinProb {d['combined_prob']*100:.1f}%, Fair {d['min_fair_odds']:.2f})\n"
                f"   1️⃣ {e1} {html.escape(l1['match'])} &rarr; <b>{html.escape(l1['pick'])}</b> @ {l1['odds']:.2f}\n"
                f"   2️⃣ {e2} {html.escape(l2['match'])} &rarr; <b>{html.escape(l2['pick'])}</b> @ {l2['odds']:.2f}"
            )

    lines.append("")
    lines.append("🤖 <i>Powered by 7-Factor tanh(Z) Composite + Laya-Sports System-1 Gate</i>")
    return "\n".join(lines)


def format_discord_digest(
    rec: dict[str, Any],
    db_path: Path | None = None,
    min_odds: float = 1.15,
    sport_filter: str = "all",
    max_picks: int = 12,
    include_settled: bool = True,
    tz_name: str = DEFAULT_LOCAL_TZ,
) -> str:
    """Build a Discord Markdown digest of settled paper bets, System-1 vetoes, and top upcoming/live picks."""
    html_msg = format_telegram_digest(
        rec=rec,
        db_path=db_path,
        min_odds=min_odds,
        sport_filter=sport_filter,
        max_picks=max_picks,
        include_settled=include_settled,
        tz_name=tz_name,
    )
    return html_to_discord_markdown(html_msg)


def get_discord_env_config(env_path: Path | None = None) -> dict[str, Any]:
    """Reload `.env` on the fly and return current Discord configuration status."""
    load_dotenv(env_path=env_path, override=True)
    webhook_url = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    bot_token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel_id = (os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    has_webhook = webhook_url.startswith("https://discord.com/api/webhooks/") or webhook_url.startswith(
        "https://discordapp.com/api/webhooks/"
    )
    has_bot = bool(bot_token and channel_id)
    masked_webhook = (webhook_url[:38] + "..." + webhook_url[-6:]) if len(webhook_url) > 48 else ""
    return {
        "configured": bool(has_webhook or has_bot),
        "mode": "webhook" if has_webhook else ("bot" if has_bot else "unconfigured"),
        "has_webhook": has_webhook,
        "masked_webhook": masked_webhook,
        "has_bot": has_bot,
        "channel_id": channel_id,
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
) -> dict[str, Any]:
    """Post a Markdown-formatted message to a Discord channel via Webhook URL or Bot Token + Channel ID."""
    load_dotenv(env_path=env_path, override=True)
    md_text = html_to_discord_markdown(text)
    chunks = _chunk_discord_text(md_text, max_len=1950)

    wh_url = (webhook_url or os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    b_tok = (bot_token or os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    ch_id = (channel_id or os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    configured = bool(wh_url or (b_tok and ch_id))

    if dry_run or not configured:
        return {
            "ok": True,
            "dry_run": True,
            "configured": configured,
            "channel": ch_id or ("webhook" if wh_url else "<DISCORD_WEBHOOK_URL not set>"),
            "message_length": len(md_text),
            "chunks_count": len(chunks),
            "preview": md_text,
        }

    if wh_url:
        sep = "&" if "?" in wh_url else "?"
        target_url = f"{wh_url}{sep}wait=true"
        headers = ["-H", "Content-Type: application/json"]
    else:
        target_url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
        headers = [
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bot {b_tok}",
        ]

    message_ids: list[str] = []
    last_resp: dict[str, Any] = {}
    for chunk in chunks:
        payload = {"content": chunk, "username": "Sportdata Quant Desk"} if wh_url else {"content": chunk}
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
            return {"ok": False, "error": proc.stderr or "Empty response from Discord API"}
        try:
            resp = json.loads(proc.stdout)
            if isinstance(resp, dict) and resp.get("id"):
                message_ids.append(str(resp["id"]))
                last_resp = resp
            else:
                return {"ok": False, "error": resp.get("message") or str(resp), "raw": resp}
        except Exception as exc:
            if "Zscaler" in proc.stdout:
                return {"ok": False, "error": "Blocked by Zscaler corporate proxy"}
            return {"ok": False, "error": str(exc), "raw": proc.stdout[:300]}

    return {
        "ok": True,
        "dry_run": False,
        "message_id": message_ids[0] if message_ids else None,
        "message_ids": message_ids,
        "chunks_sent": len(message_ids),
        "channel_id": last_resp.get("channel_id"),
    }


def notify_new_settlements_to_discord(
    db_path: Path,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Check `paper_trades` for any `SETTLED` rows where `notified_at IS NULL`, post a compact
    settlement recap to Discord, and stamp `notified_at` so each bet is notified at most once."""
    if not db_path.exists():
        return {"ok": True, "notified_count": 0}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_trades)").fetchall()}
    if "notified_at" not in cols:
        conn.execute("ALTER TABLE paper_trades ADD COLUMN notified_at TEXT")
        conn.commit()

    unnotified = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'SETTLED' AND notified_at IS NULL ORDER BY kickoff ASC"
        ).fetchall()
    ]
    if not unnotified:
        conn.close()
        return {"ok": True, "notified_count": 0}

    summary = get_paper_ledger_summary(db_path)
    s_cnt = summary.get("settled_count", 0)
    s_wins = summary.get("settled_wins", 0)
    s_loss = summary.get("settled_losses", 0)
    s_prof = float(summary.get("settled_profit_u") or 0.0)
    s_roi = float(summary.get("settled_roi_best") or 0.0) * 100.0

    lines: list[str] = [
        f"🔔 **NEW SETTLED PAPER-BET ALERT ({len(unnotified)} Resolved)**",
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

    msg = "\n".join(lines)
    res = send_discord_message(msg, webhook_url=webhook_url, dry_run=dry_run)
    if res.get("ok") and not res.get("dry_run"):
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for r in unnotified:
            conn.execute(
                "UPDATE paper_trades SET notified_at = ? WHERE league = ? AND event_id = ?",
                (now_iso, r["league"], r["event_id"]),
            )
        conn.commit()
    conn.close()
    return {**res, "notified_count": len(unnotified)}


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
) -> dict[str, Any]:
    """Post an HTML-formatted message to a Telegram channel/chat via `POST /bot<token>/sendMessage`."""
    load_dotenv(env_path=env_path, override=True)
    token = (bot_token or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    target_chat = (chat_id or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

    if dry_run or not token or not target_chat:
        return {
            "ok": True,
            "dry_run": True,
            "configured": bool(token and target_chat),
            "chat_id": target_chat or "<TELEGRAM_CHAT_ID not set>",
            "message_length": len(text),
            "preview": text,
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    proc = subprocess.run(
        [
            "curl", "-s", "-m", "15", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"ok": False, "error": proc.stderr or "Empty response from Telegram API"}
    if "Zscaler" in proc.stdout or "Internet Security by Zscaler" in proc.stdout:
        return {
            "ok": False,
            "error": "api.telegram.org is blocked by Zscaler on this network. Switch to Discord (DISCORD_WEBHOOK_URL in model/.env)!",
        }
    try:
        resp = json.loads(proc.stdout)
        return resp
    except Exception as exc:
        return {"ok": False, "error": str(exc), "raw": proc.stdout[:300]}
