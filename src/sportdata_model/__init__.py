"""Sport outcome data and models: ESPN ingestion, goal model, walk-forward evaluation, and daily quant pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(env_path: Path | None = None, override: bool = False) -> dict[str, str]:
    """Load key=value pairs from `.env` (in `model/` or custom `env_path`) into `os.environ`."""
    candidates = [env_path] if env_path else [MODEL_ROOT / ".env", MODEL_ROOT.parent / ".env"]
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
    return loaded


load_dotenv()


def _run_script(module_name: str) -> None:
    load_dotenv(override=True)
    scripts_dir = str(MODEL_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    mod = __import__(module_name)
    mod.main()


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
    _run_script("paper_trade")


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

