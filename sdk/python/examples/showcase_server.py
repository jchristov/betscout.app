"""Interactive Web Showcase Server for `betscout_sdk` (Python).

Serves the shared interactive `showcase.html` and `match-center.html` (including `/match/76034538`)
backed by Python's `BetScoutClient`.

Run with: `PYTHONPATH=src python3 examples/showcase_server.py` (from `sdk/python/`)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from betscout_sdk import (
    BOOKMAKER_IDS,
    CORRECT_SCORE_OUTCOMES,
    MARKET_IDS,
    PLAYER_STATUS_TYPES,
    SERVICE_PROFILES,
    SPORTS_CATALOG,
    TENNIS_SURFACE_IDS,
    BetScoutClient,
    get_country_flag_url,
    get_team_logo_url,
    merge_primary_and_consensus_markets,
    parse_prematch_markets,
    parse_venue_coordinates,
    render_team_jersey_svg,
)

HERE = Path(__file__).resolve().parent
TS_EXAMPLES_DIR = HERE.parent.parent / "typescript" / "examples"
LOGO_SVG_PATH = HERE.parent.parent.parent / "frontend" / "public" / "betscout-logo.svg"
PORT = int(os.environ.get("PORT", "8789"))

client = BetScoutClient(default_channel="eu-retail", default_timezone="Europe:Berlin")


def _build_sport_leagues_payload(sport_id: int) -> dict[str, Any]:
    featured_raw = client.get_unique_tournaments(SERVICE_PROFILES["GLOBAL_UNLIMITED"], sport_id)
    all_raw = client.get_all_unique_tournaments(SERVICE_PROFILES["GLOBAL_UNLIMITED"], sport_id)
    tree = client.get_category_tree(SERVICE_PROFILES["GLOBAL_UNLIMITED"], 0, sport_id) or {}

    cat_map: dict[int, dict[str, Any]] = {}
    for rc in tree.get("realcategories") or []:
        if isinstance(rc, dict) and isinstance(rc.get("_id"), int):
            cat_map[rc["_id"]] = {
                "name": rc.get("name"),
                "a2": (rc.get("cc") or {}).get("a2"),
            }

    def norm_list(raw: Any) -> list[dict[str, Any]]:
        items = (
            raw
            if isinstance(raw, list)
            else list(raw.values())
            if isinstance(raw, dict)
            else []
        )
        out = []
        for t in items:
            if not isinstance(t, dict) or not t.get("_id") or not t.get("name"):
                continue
            cat = cat_map.get(t.get("_rcid") or -1, {})
            iso = t.get("a2") or cat.get("a2")
            out.append(
                {
                    **t,
                    "categoryName": cat.get("name"),
                    "a2": iso,
                    "flagSvgUrl": get_country_flag_url(str(iso), fmt="svg", ratio="4x3")
                    if iso
                    else None,
                }
            )
        return out

    featured = norm_list(featured_raw)
    leagues = norm_list(all_raw)
    return {
        "ok": True,
        "sportId": sport_id,
        "sportName": SPORTS_CATALOG.get(sport_id, f"Sport #{sport_id}"),
        "featuredCount": len(featured),
        "totalLeaguesCount": len(leagues),
        "featured": featured,
        "leagues": leagues,
    }


def _build_match_center_payload(match_id: int | str) -> dict[str, Any]:
    dossier = client.get_match_center_dossier(match_id)
    mi_match = ((dossier.get("match_info") or {}).get("match")) or (
        (dossier.get("timeline_delta") or {}).get("match")
    ) or {}
    teams = mi_match.get("teams") or {}
    h_team = teams.get("home") or {}
    a_team = teams.get("away") or {}
    h_iso = (h_team.get("cc") or {}).get("a2") or (
        ((dossier.get("home_profile") or {}).get("countrycode") or {}).get("a2")
    ) or "us"
    a_iso = (a_team.get("cc") or {}).get("a2") or (
        ((dossier.get("away_profile") or {}).get("countrycode") or {}).get("a2")
    ) or "au"
    return {
        **dossier,
        "home_flag_url": get_country_flag_url(h_iso, fmt="svg", ratio="4x3"),
        "away_flag_url": get_country_flag_url(a_iso, fmt="svg", ratio="4x3"),
    }


class ShowcaseHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        p = parsed.path
        qs = parse_qs(parsed.query)

        if p == "/betscout-logo.svg" and LOGO_SVG_PATH.exists():
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(LOGO_SVG_PATH.read_bytes())
            return

        if p == "/api/match-center":
            mid = (qs.get("matchId") or ["76034538"])[0]
            self._send_json(200, _build_match_center_payload(mid))
            return

        if p == "/api/sport-leagues":
            sid = int((qs.get("sportId") or ["1"])[0])
            self._send_json(200, _build_sport_leagues_payload(sid))
            return

        if p == "/match-center.html" or p.startswith("/match/"):
            html_file = TS_EXAMPLES_DIR / "match-center.html"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_file.read_bytes())
            return

        if p in ("/", "/showcase.html"):
            html_file = TS_EXAMPLES_DIR / "showcase.html"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_file.read_bytes())
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print(f"betscout_sdk (Python) Interactive Showcase running at http://127.0.0.1:{PORT}")
    print(f"Match #76034538 Replica available at http://127.0.0.1:{PORT}/match/76034538")
    HTTPServer(("127.0.0.1", PORT), ShowcaseHandler).serve_forever()
