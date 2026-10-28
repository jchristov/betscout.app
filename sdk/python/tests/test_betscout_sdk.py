"""Unit & Integration Test Suite for `betscout_sdk` (Python)."""

from __future__ import annotations

from typing import Any

import betscout_sdk
from betscout_sdk import (
    BOOKMAKER_IDS,
    CORRECT_SCORE_OUTCOMES,
    MARKET_IDS,
    PLAYER_STATUS_TYPES,
    SERVICE_PROFILES,
    SPORTS_CATALOG,
    BetScoutClient,
    get_adaptive_refetch_interval_ms,
    get_country_flag_url,
    get_team_logo_url,
    merge_primary_and_consensus_markets,
    names_match,
    normalize_team_name,
    parse_prematch_markets,
    parse_venue_coordinates,
    render_team_jersey_svg,
    resolve_sport_id,
)


def _envelope(data: Any, max_age: int = 10, event: str = "test_event") -> dict[str, Any]:
    return {
        "queryUrl": event,
        "doc": [
            {
                "event": event,
                "_dob": 1793200000,
                "_maxage": max_age,
                "data": data,
            }
        ],
    }


def test_white_label_public_api_surface():
    """Exposes zero upstream vendor names in exported symbols."""
    for name in betscout_sdk.__all__:
        low = name.lower()
        assert "sportradar" not in low
        assert "gismo" not in low
        assert "tipico" not in low
        assert "fishnet" not in low


def test_catalogs_and_name_normalization():
    assert len(SPORTS_CATALOG) == 56
    assert resolve_sport_id("soccer") == 1
    assert resolve_sport_id("tennis") == 5
    assert resolve_sport_id("nhl") == 4
    assert resolve_sport_id(117) == 117
    assert BOOKMAKER_IDS["EU_RETAIL"] == 176
    assert BOOKMAKER_IDS["CONSENSUS"] == 0
    assert SERVICE_PROFILES["GLOBAL_UNLIMITED"] == 69
    assert PLAYER_STATUS_TYPES["INJURED"] == 1
    assert len(CORRECT_SCORE_OUTCOMES) == 28

    assert normalize_team_name("FC Bayern München") == "bayern munchen"
    assert names_match("Internazionale", "Inter Milan") is True
    assert names_match("Djokovic, Novak", "Novak Djokovic") is True
    assert names_match("Fritz, Taylor", "Taylor Fritz") is True
    assert names_match("Real Madrid", "Barcelona") is False


def test_market_parsing_and_merging():
    sample_primary = [
        {
            "_marketId": MARKET_IDS["MATCH_1X2"],
            "_bookmakerId": 176,
            "outcomes": [
                {"_id": "1", "name": "{$competitor1}", "odds": 1.45},
                {"_id": "2", "name": "draw", "odds": 4.3},
                {"_id": "3", "name": "{$competitor2}", "odds": 6.5},
            ],
        },
        {
            "_marketId": MARKET_IDS["CORRECT_SCORE"],
            "_bookmakerId": 176,
            "outcomes": [
                {"_id": "sr:outcome:114", "name": "", "odds": 6.5},
                {"_id": "sr:outcome:130", "name": "", "odds": 8.0},
            ],
        },
    ]

    parsed = parse_prematch_markets(sample_primary, flipped=False)
    assert parsed["bookmaker"] == "Primary Bookmaker"
    assert parsed["odds_home"] == 1.45
    assert parsed["odds_draw"] == 4.3
    assert parsed["odds_away"] == 6.5
    assert parsed["correct_score_odds"] == {"1:0": 6.5, "2:1": 8.0}

    flipped = parse_prematch_markets(sample_primary, flipped=True)
    assert flipped["odds_home"] == 6.5
    assert flipped["odds_away"] == 1.45
    assert flipped["correct_score_odds"] == {"0:1": 6.5, "1:2": 8.0}

    consensus = parse_prematch_markets(
        [
            {
                "_marketId": MARKET_IDS["ASIAN_HANDICAP_2WAY"],
                "_bookmakerId": 0,
                "specifiers": {"hcp": "-1.5"},
                "outcomes": [
                    {"_id": "10", "name": "{$competitor1}", "odds": 2.15},
                    {"_id": "11", "name": "{$competitor2}", "odds": 1.68},
                ],
            }
        ],
        flipped=False,
    )
    merged = merge_primary_and_consensus_markets(parsed, consensus)
    assert merged["bookmaker"] == "Primary + Consensus"
    assert merged["odds_home"] == 1.45
    assert merged["asian_handicap_line"] == "-1.5"


def test_visual_assets_and_venue_coordinates():
    assert get_team_logo_url(2692, size="big").endswith("/ls/crest/big/2692.png")
    assert get_team_logo_url(2509, ncaa=True, ncaa_size="ap250x188ut").endswith(
        "/ls/teams/ap250x188ut/2509.png"
    )
    assert get_country_flag_url("rs", fmt="svg", ratio="4x3").endswith("/ls/crest/4x3/rs.svg")
    assert get_country_flag_url("en", fmt="svg", ratio="4x3").endswith("/ls/crest/4x3/gb-eng.svg")

    svg = render_team_jersey_svg(
        {"base": "ff0000", "sleeve": "121212", "number": "ffffff"},
        shirt_number=16,
    )
    assert "<svg" in svg
    assert ">16</text>" in svg
    assert parse_venue_coordinates("45.478025,9.124206") == {"lat": 45.478025, "lng": 9.124206}
    assert get_adaptive_refetch_interval_ms({"_maxage": 3}) == 3000


def test_enriched_league_table_and_match_center_dossier():
    def mock_fetch(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any] | None:
        if "stats_season_tables/140782" in url:
            return _envelope(
                {
                    "_id": "140782",
                    "name": "Serie A 26/27",
                    "tables": [
                        {
                            "_id": "108262",
                            "name": "Serie A 26/27",
                            "currentround": 9,
                            "maxrounds": 38,
                            "tablerows": [
                                {
                                    "pos": 1,
                                    "changeTotal": 1,
                                    "promotion": {"_id": 1, "name": "Champions League", "shortname": "CL"},
                                    "team": {"_id": 9264, "uid": 2697, "name": "Inter", "mediumname": "Inter Milano", "abbr": "INT"},
                                    "total": 9,
                                    "home": 5,
                                    "away": 4,
                                    "winTotal": 8,
                                    "drawTotal": 1,
                                    "lossTotal": 0,
                                    "goalsForTotal": 25,
                                    "goalsAgainstTotal": 10,
                                    "goalDiffTotal": 15,
                                    "pointsTotal": 25,
                                }
                            ],
                        }
                    ],
                }
            )
        if "stats_formtable/140782" in url:
            return _envelope(
                {
                    "currentround": 9,
                    "teams": [
                        {
                            "team": {"_id": 9264, "uid": 2697, "name": "Inter"},
                            "form": {
                                "total": [
                                    {"typeid": "W", "value": "W"},
                                    {"typeid": "D", "value": "D"},
                                ]
                            },
                        }
                    ],
                }
            )
        if "match_info_statshub/76034538" in url:
            return _envelope(
                {
                    "match": {
                        "_id": 76034538,
                        "_sid": 5,
                        "teams": {
                            "home": {"_id": 7020808, "uid": 136042, "name": "Fritz, Taylor", "cc": {"a2": "us"}},
                            "away": {"_id": 9267643, "uid": 299130, "name": "Hijikata, Rinky", "cc": {"a2": "au"}},
                        },
                        "result": {"home": 1, "away": 0},
                        "periods": {"p1": {"home": 6, "away": 4}, "p2": {"home": 6, "away": 5}},
                    }
                }
            )
        if "match_detailsextended/76034538" in url:
            return _envelope(
                {
                    "_matchid": 76034538,
                    "values": {
                        "130": {"name": "Aces", "value": {"home": 18, "away": 6}},
                    },
                }
            )
        return _envelope({})

    client = BetScoutClient(fetch_fn=mock_fetch)
    table = client.get_enriched_league_table(140782)
    assert table["ok"] is True
    assert table["rows"][0]["team_name"] == "Inter Milano"
    assert table["rows"][0]["form_total"] == ["D", "W"]

    dossier = client.get_match_center_dossier(76034538)
    assert dossier["ok"] is True
    assert dossier["sport_id"] == 5
    assert dossier["match_details"]["values"]["130"]["value"]["home"] == 18
