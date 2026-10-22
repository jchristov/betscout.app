"""Walk-forward evaluation of soccer markets on the backfilled store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sportdata_model.walkforward import run  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "data" / "matches.sqlite"

if __name__ == "__main__":
    league = sys.argv[1] if len(sys.argv) > 1 else None
    print(run(DB, league).table())
