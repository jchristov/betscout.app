"""Standard I/O (stdio) MCP server runner for BetScout (`uv run betscout-mcp`).

Reads newline-delimited JSON-RPC 2.0 messages from stdin and writes JSON-RPC 2.0 responses to stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .mcp_server import handle_mcp_jsonrpc_request


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "data"
    db_path = data_dir / "betscout.db"
    rec_path = data_dir / "recommendations.json"

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            rpc_req = json.loads(line)
        except json.JSONDecodeError:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: invalid JSON on stdin."},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_mcp_jsonrpc_request(rpc_req, db_path=db_path, rec_path=rec_path)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
