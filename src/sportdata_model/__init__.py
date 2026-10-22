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


def main() -> None:
    load_dotenv(override=True)
    scripts_dir = MODEL_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from daily_pipeline import main as pipeline_main  # noqa: E402

    pipeline_main()

