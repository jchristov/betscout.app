"""Sport outcome data and models: ESPN ingestion, goal model, walk-forward evaluation, and daily quant pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = API_ROOT
MODEL_ROOT = (
    API_ROOT.parent
    if ((API_ROOT.parent / "data").exists() or (API_ROOT.parent / "app").exists())
    else API_ROOT
)


def load_dotenv(env_path: Path | None = None, override: bool = False) -> dict[str, str]:
    """Load key=value pairs from `.env` (in repo root, `api/`, or custom `env_path`) into `os.environ`."""
    candidates = (
        [env_path]
        if env_path
        else [MODEL_ROOT / ".env", API_ROOT / ".env", MODEL_ROOT.parent / ".env"]
    )
    loaded: dict[str, str] = {}
    for path in candidates:
        if path is None or not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                val = val[1:-1]
            if not key:
                continue
            if override or key not in os.environ or not os.environ.get(key):
                if val:
                    os.environ[key] = val
                    loaded[key] = val
                elif override:
                    os.environ[key] = ""
                    loaded[key] = ""
    return loaded


load_dotenv()


def _run_script(module_name: str) -> None:
    import importlib

    load_dotenv(override=True)
    for s_dir in (BACKEND_ROOT / "scripts", MODEL_ROOT / "scripts"):
        if s_dir.is_dir() and str(s_dir) not in sys.path:
            sys.path.insert(0, str(s_dir))
    try:
        mod = __import__(module_name)
    except ModuleNotFoundError:
        mod = importlib.import_module(f"betscout.{module_name}")
    try:
        mod.main()
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user (Ctrl+C). Exiting cleanly.")
        sys.exit(0)


SUBCOMMAND_MODULES: dict[str, str] = {
    "webapp": "webapp",
    "serve": "webapp",
    "model": "daily_pipeline",
    "pipeline": "daily_pipeline",
    "ingest": "ingest",
    "quality": "quality",
    "enrich": "enrich",
    "edges": "quant_edges",
    "bet": "paper_bet",
    "scan": "paper_bet",
    "dashboard": "dashboard",
    "ledger": "ledger",
    "discord": "discord_post",
    "telegram": "telegram_post",
    "exact-score": "exact_score_eval",
    "calibrate": "calibration_report",
    "apikey": "monetization_cli",
    "monetize": "monetization_cli",
}


def cli() -> None:
    """Unified `betscout` CLI router (`uv run betscout [subcommand] [args...]`).
    Defaults to launching the interactive WebApp (`webapp`) when no subcommand is given or when flags like `--port` are passed directly."""
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        sub = sys.argv[1].lower().strip()
        if sub in SUBCOMMAND_MODULES:
            sys.argv = [f"{sys.argv[0]} {sub}", *sys.argv[2:]]
            _run_script(SUBCOMMAND_MODULES[sub])
            return
        if sub in ("help", "-h", "--help"):
            print("Usage: uv run betscout [subcommand] [options]\n")
            print("Available subcommands (defaults to 'webapp' if omitted):")
            print("  webapp       Launch interactive BetScout WebApp, SSE stream & auto-poller (default)")
            print("  pipeline     Run full 4-stage daily pipeline (ingest -> quality -> scan -> dashboard)")
            print("  ingest       Run universal config-driven incremental/historical ingestion")
            print("  quality      Run 18-point match database hygiene & anomaly audit")
            print("  enrich       Rebuild or refresh 49-column match_details table")
            print("  edges        Evaluate multi-sport 7-factor composite & walk-forward backtest")
            print("  scan         Scan upcoming fixtures across all sports & log paper bets")
            print("  dashboard    Generate standalone HTML dashboard, CSV & JSON exports")
            print("  ledger       Inspect settled & pending paper-betting ledger in terminal")
            print("  discord      Format & publish daily digest + PNG cards to Discord")
            print("  telegram     Format & publish daily digest + PNG cards to Telegram")
            print("  exact-score  Evaluate Dixon-Coles exact-score & tennis set-score calibration")
            print("  calibrate    Run out-of-sample reliability & calibration audit")
            print("  apikey       Manage paid B2B API keys, Pro subscribers & syndicate webhooks")
            return
    _run_script("webapp")


def main() -> None:
    _run_script("daily_pipeline")


def ingest_cli() -> None:
    _run_script("ingest")


def quality_cli() -> None:
    _run_script("quality")


def enrich_cli() -> None:
    _run_script("enrich")


def quant_edges_cli() -> None:
    _run_script("quant_edges")


def paper_bet_cli() -> None:
    _run_script("paper_bet")


def dashboard_cli() -> None:
    _run_script("dashboard")


def ledger_cli() -> None:
    _run_script("ledger")


def webapp_cli() -> None:
    _run_script("webapp")


def discord_cli() -> None:
    _run_script("discord_post")


def telegram_cli() -> None:
    _run_script("telegram_post")


def distill_cli() -> None:
    _run_script("distill_laya_sports")


def compare_models_cli() -> None:
    _run_script("compare_decision_models")


def exact_score_cli() -> None:
    _run_script("exact_score_eval")


def calibrate_cli() -> None:
    _run_script("calibration_report")


