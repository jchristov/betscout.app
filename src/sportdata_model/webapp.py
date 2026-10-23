"""Interactive Web App Server & Social Publishing Addon (`src/sportdata_model/webapp.py`).

Serves:
  - `GET  /`                  -> Enhanced Quant Desk Web App (`data/dashboard.html`) with live controls
  - `GET  /api/data`          -> JSON payload of `recommendations.json` + live `paper_ledger` + `best_bets`
  - `GET  /api/stream`        -> Server-Sent Events (SSE) live stream pushing ledger, live scores & best bets
  - `GET  /api/best-bets.csv` -> Downloadable CSV (with header) of current best bets
  - `GET  /api/settled.csv`   -> Downloadable CSV (with header) of settled paper bets
  - `POST /api/settle`        -> Trigger immediate live settlement against ESPN & refresh `dashboard.html`
  - `POST /api/sync`          -> Sync & settle ledger + optionally rescan live/upcoming fixtures
  - `POST /api/telegram`      -> Preview or post the formatted Telegram Channel digest (`send_telegram_message`)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .dashboard import (
    DEFAULT_LOCAL_TZ,
    _format_local_time,
    _league_to_sport_cat,
    build_best_bets_summary,
    generate_dashboard_html,
)
from .espn import LEAGUE_LABELS
from .paper_trade import (
    get_paper_ledger_summary,
    scan_upcoming_and_log_paper_trades,
    settle_pending_paper_trades,
)
from .telegram_bot import (
    format_discord_digest,
    format_telegram_digest,
    get_discord_env_config,
    get_telegram_env_config,
    notify_new_settlements_to_discord,
    send_discord_message,
    send_telegram_message,
)
from .universal_ingest import ingest_universal

_PIPELINE_STATUS: dict[str, Any] = {
    "running": False,
    "step": "Idle",
    "updated_at": None,
}


def _build_live_snapshot(
    rec_path: Path,
    db_path: Path,
    min_odds: float = 1.10,
    sport: str = "all",
    run_settle: bool = False,
) -> dict[str, Any]:
    newly_settled = 0
    if run_settle and db_path.exists():
        try:
            newly_settled = settle_pending_paper_trades(db_path)
            if newly_settled > 0:
                notify_new_settlements_to_discord(db_path)
        except Exception:
            newly_settled = 0

    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
    ledger = get_paper_ledger_summary(db_path) if db_path.exists() else {}
    for tr in ledger.get("trades") or []:
        tr["kickoff_local"] = _format_local_time(tr.get("kickoff") or "", DEFAULT_LOCAL_TZ)
        tr["league_label"] = LEAGUE_LABELS.get(tr["league"], tr["league"].upper())
        tr["sport_cat"] = _league_to_sport_cat(tr["league"])
    rec["paper_ledger"] = ledger
    best_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=sport)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "server_time_utc": now_utc,
        "server_time_local": _format_local_time(now_utc, DEFAULT_LOCAL_TZ),
        "generated_at": rec.get("generated_at"),
        "generated_at_local": _format_local_time(rec.get("generated_at") or "", DEFAULT_LOCAL_TZ),
        "timezone": DEFAULT_LOCAL_TZ,
        "discord_env": get_discord_env_config(),
        "telegram_env": get_telegram_env_config(),
        "pipeline_status": dict(_PIPELINE_STATUS),
        "newly_settled": newly_settled,
        "paper_ledger": ledger,
        "best_bets_count": len(best_bets),
        "best_bets": best_bets,
        "qualifying_picks": rec.get("qualifying_picks", []),
        "tennis_picks": rec.get("tennis_picks", []),
        "other_sport_picks": rec.get("other_sport_picks", []),
    }


def build_webapp_handler(root_dir: Path) -> type[BaseHTTPRequestHandler]:
    data_dir = root_dir / "data"
    rec_path = data_dir / "recommendations.json"
    db_path = data_dir / "matches.sqlite"
    dash_path = data_dir / "dashboard.html"
    best_csv_path = data_dir / "best_bets.csv"
    best_json_path = data_dir / "best_bets.json"
    settled_csv_path = data_dir / "settled_bets.csv"

    class QuantDeskRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any] | list[Any], status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            min_odds = float((qs.get("min_odds") or ["1.10"])[0])
            sport = (qs.get("sport") or ["all"])[0]

            if parsed.path in ("/", "/index.html", "/dashboard.html"):
                generate_dashboard_html(
                    rec_path,
                    db_path,
                    dash_path,
                    min_odds=min_odds,
                    sport_filter=sport,
                    csv_export_path=best_csv_path,
                    json_export_path=best_json_path,
                )
                html_bytes = dash_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
                return

            if parsed.path == "/api/data":
                snap = _build_live_snapshot(rec_path, db_path, min_odds=min_odds, sport=sport, run_settle=False)
                self._send_json(snap)
                return

            if parsed.path in ("/api/telegram/status", "/api/social/status", "/api/discord/status"):
                self._send_json({
                    "discord": get_discord_env_config(),
                    "telegram": get_telegram_env_config(),
                })
                return

            if parsed.path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                tick = 0
                try:
                    while True:
                        # Run live ESPN settlement every 3rd tick (~45s), fast DB snapshot every 15s
                        snap = _build_live_snapshot(
                            rec_path,
                            db_path,
                            min_odds=min_odds,
                            sport=sport,
                            run_settle=(tick % 3 == 0),
                        )
                        msg = f"event: update\ndata: {json.dumps(snap)}\n\n"
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                        tick += 1
                        time.sleep(15)
                except (BrokenPipeError, ConnectionResetError, Exception):
                    return

            if parsed.path == "/api/best-bets.csv":
                if not best_csv_path.exists():
                    generate_dashboard_html(rec_path, db_path, dash_path, min_odds=min_odds, csv_export_path=best_csv_path)
                data = best_csv_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="best_bets.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if parsed.path == "/api/settled.csv" and settled_csv_path.exists():
                data = settled_csv_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="settled_bets.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            self._send_json({"error": "Not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or "0")
            raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                body = json.loads(raw_body) if raw_body.strip() else {}
            except Exception:
                body = {}

            if parsed.path in ("/api/settle", "/api/sync", "/api/pipeline"):
                is_full_pipeline = parsed.path == "/api/pipeline" or bool(body.get("full_pipeline", False))
                rescan = is_full_pipeline or bool(body.get("rescan", False))
                min_odds = float(body.get("min_odds") or 1.10)
                new_ingested_count = 0
                try:
                    _PIPELINE_STATUS["running"] = True
                    if is_full_pipeline:
                        _PIPELINE_STATUS["step"] = "[1/4] Running incremental config-driven ingestion & quality check..."
                        ing_res = ingest_universal(
                            db_path=db_path,
                            cache_dir=data_dir / "cache",
                            config_path=root_dir / "ingestion_config.json",
                            mode="incremental",
                        )
                        new_ingested_count = sum(ing_res.get("new_ingested", {}).values())
                    if rescan:
                        _PIPELINE_STATUS["step"] = "[2/4] Settling paper bets & scanning upcoming fixtures across all sports..."
                        scan_upcoming_and_log_paper_trades(
                            db_path=db_path,
                            days_ahead=int(body.get("days") or 3),
                            decision_backend="laya",
                            export_json_path=rec_path,
                        )
                        newly_settled = 0
                    else:
                        _PIPELINE_STATUS["step"] = "Syncing & settling paper-betting ledger against ESPN..."
                        newly_settled = settle_pending_paper_trades(db_path)

                    _PIPELINE_STATUS["step"] = "[3/4] Sending Discord settlement alerts & regenerating dashboard..."
                    notify_new_settlements_to_discord(db_path)
                    generate_dashboard_html(
                        rec_path,
                        db_path,
                        dash_path,
                        min_odds=min_odds,
                        csv_export_path=best_csv_path,
                        json_export_path=best_json_path,
                    )
                    app_pub = root_dir.parent / "app" / "public" / "model"
                    if (root_dir.parent / "app" / "public").exists():
                        import shutil
                        app_pub.mkdir(parents=True, exist_ok=True)
                        for sp in (best_json_path, best_csv_path, rec_path, dash_path):
                            if sp.exists():
                                shutil.copy2(sp, app_pub / sp.name)
                finally:
                    _PIPELINE_STATUS["running"] = False
                    _PIPELINE_STATUS["step"] = "Idle"

                snap = _build_live_snapshot(rec_path, db_path, min_odds=min_odds, sport="all", run_settle=False)
                snap["newly_settled"] = newly_settled
                snap["new_ingested_count"] = new_ingested_count
                self._send_json({"ok": True, **snap})
                return

            if parsed.path == "/api/discord":
                rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                custom_text = (body.get("text") or "").strip()
                msg = custom_text or format_discord_digest(
                    rec=rec,
                    db_path=db_path,
                    min_odds=float(body.get("min_odds") or 1.15),
                    sport_filter=str(body.get("sport") or "all"),
                    max_picks=int(body.get("max_picks") or 12),
                )
                res = send_discord_message(
                    text=msg,
                    webhook_url=body.get("webhook_url"),
                    bot_token=body.get("bot_token"),
                    channel_id=body.get("channel_id"),
                    dry_run=bool(body.get("dry_run", False)),
                )
                self._send_json({**res, "formatted_message": msg})
                return

            if parsed.path == "/api/telegram":
                rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                custom_text = (body.get("text") or "").strip()
                msg = custom_text or format_telegram_digest(
                    rec=rec,
                    db_path=db_path,
                    min_odds=float(body.get("min_odds") or 1.15),
                    sport_filter=str(body.get("sport") or "all"),
                    max_picks=int(body.get("max_picks") or 12),
                )
                res = send_telegram_message(
                    text=msg,
                    bot_token=body.get("bot_token"),
                    chat_id=body.get("chat_id"),
                    dry_run=bool(body.get("dry_run", False)),
                )
                self._send_json({**res, "formatted_message": msg})
                return

            self._send_json({"error": "Unknown endpoint"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return QuantDeskRequestHandler


class _DaemonThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_webapp_server(root_dir: Path, host: str = "127.0.0.1", port: int = 8090) -> None:
    handler_cls = build_webapp_handler(root_dir)
    server = _DaemonThreadingHTTPServer((host, port), handler_cls)
    print(f"🚀 Sportdata Quant Desk Web App, SSE Stream & Social Addon running at http://{host}:{port}")
    print(f"   - Dashboard UI:       http://{host}:{port}/")
    print(f"   - Live SSE Stream:    http://{host}:{port}/api/stream")
    print(f"   - Sync & Settle API:  http://{host}:{port}/api/sync")
    print(f"   - Discord POST API:   http://{host}:{port}/api/discord")
    print(f"   - Telegram POST API:  http://{host}:{port}/api/telegram")
    print("   (Press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Sportdata Quant Desk Web App server...")
    finally:
        server.server_close()
