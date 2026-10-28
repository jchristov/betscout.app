"""Comprehensive CLI Showcase for `betscout_sdk` (Python).

Exercises all 9 functional domains of `BetScoutClient` plus the Match #76034538 Dossier.
Run with: `PYTHONPATH=src python3 examples/quickstart.py` (from `sdk/python/`)
"""

from __future__ import annotations

import json

from betscout_sdk import (
    SERVICE_PROFILES,
    BetScoutClient,
    get_country_flag_url,
    get_team_logo_url,
    parse_venue_coordinates,
    render_team_jersey_svg,
)


def main() -> None:
    client = BetScoutClient(default_channel="eu-retail", default_timezone="Europe:Berlin")

    print("=== 1. Sports Catalog (56 Sports) & Leagues ===")
    sports = client.list_all_sports(SERVICE_PROFILES["GLOBAL_UNLIMITED"], 0, "global")
    soccer_leagues = client.get_all_unique_tournaments(SERVICE_PROFILES["GLOBAL_UNLIMITED"], 1)
    print(
        json.dumps(
            {
                "sportsCount": len(sports),
                "top5Sports": sports[:5],
                "soccerLeaguesCount": len(soccer_leagues) if isinstance(soccer_leagues, list) else 0,
            },
            indent=2,
        )
    )

    print("\n=== 2. Match #76034538 Full Dossier (Taylor Fritz vs Rinky Hijikata) ===")
    dossier = client.get_match_center_dossier(76034538)
    mi_match = (dossier.get("match_info") or {}).get("match") or {}
    md_vals = (dossier.get("match_details") or {}).get("values") or {}
    print(
        json.dumps(
            {
                "matchId": dossier["match_id"],
                "sport": dossier["sport_name"],
                "home": ((mi_match.get("teams") or {}).get("home") or {}).get("name"),
                "away": ((mi_match.get("teams") or {}).get("away") or {}).get("name"),
                "status": (mi_match.get("status") or {}).get("name"),
                "result": mi_match.get("result"),
                "periods": mi_match.get("periods"),
                "aces": (md_vals.get("130") or {}).get("value"),
                "pointsWon": (md_vals.get("136") or {}).get("value"),
                "marketsCount": len(dossier.get("raw_markets") or []),
            },
            indent=2,
        )
    )

    print("\n=== 3. Club Intelligence, Missing Players & Squad (ID: 2692 — AC Milan) ===")
    milan = client.get_team_intelligence_bundle(
        2692, season_id=130971, last_matches_limit=5, next_matches_limit=3
    )
    print(
        json.dumps(
            {
                "club": ((milan.get("profile") or {}).get("team") or {}).get("mediumname"),
                "formation": (milan.get("usual_lineup") or {}).get("formation"),
                "squadSize": milan.get("squad_count"),
                "missingPlayers": [
                    f"{p['name']} ({p['position']}, {p['cause']} until {p['end_date']})"
                    for p in milan.get("missing_players") or []
                ],
                "logoUrl": get_team_logo_url(2692, size="big"),
                "flagUrl": get_country_flag_url("it", fmt="svg", ratio="4x3"),
                "gkJerseySvgLen": len(
                    render_team_jersey_svg(
                        (milan.get("profile") or {}).get("gkjersey"), shirt_number=16
                    )
                ),
            },
            indent=2,
        )
    )

    print("\n=== 4. Enriched League Standings & Form Table (Serie A 26/27 — Season ID: 140782) ===")
    table = client.get_enriched_league_table(140782, around_team_uid=2692, slice_size=5)
    print(
        json.dumps(
            {
                "season": table.get("season_name"),
                "round": f"{table.get('current_round')}/{table.get('max_rounds')}",
                "slice": [
                    {
                        "pos": r["pos"],
                        "change": r["change_total"],
                        "team": r["team_name"],
                        "pts": r["points"]["total"],
                        "form": "-".join(r["form_total"]),
                    }
                    for r in table.get("rows") or []
                ],
            },
            indent=2,
        )
    )

    print("\n=== 5. Venue Stats (San Siro 647) & Season Goal Timing ===")
    san_siro = client.get_venue_season_stats(647, 130971) or {}
    st_info = san_siro.get("stadium") or {}
    print(
        json.dumps(
            {
                "stadium": st_info.get("name"),
                "capacity": st_info.get("capacity"),
                "coords": parse_venue_coordinates(st_info.get("googlecoords")),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
