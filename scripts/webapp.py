"""Launch the interactive Sportdata Quant Desk Web App + Telegram Social Publisher Addon.

Usage:
    uv run python scripts/webapp.py --port 8090
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.webapp import run_webapp_server  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Sportdata Quant Desk Web App & Telegram Addon server.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8090, help="Bind port (default: 8090)")
    args = parser.parse_args()
    run_webapp_server(ROOT, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
