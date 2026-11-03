"""Unit and integration tests for `betscout.funstats` adapter."""

from __future__ import annotations

from betscout.funstats import (
    _unflatten_devalue,
    build_long_term_h2h_analytics,
    extract_team_deep_splits,
    get_funstats_cache_stats,
    lookup_footystats_intel,
    resolve_funstats_league_id,
)


def test_resolve_funstats_league_id() -> None:
    assert resolve_funstats_league_id("epl") == 39
    assert resolve_funstats_league_id("Premier League") == 39
    assert resolve_funstats_league_id("ucl") == 2
    assert resolve_funstats_league_id("Champions League") == 2
    assert resolve_funstats_league_id("laliga") == 140
    assert resolve_funstats_league_id("seriea") == 135
    assert resolve_funstats_league_id("bundesliga") == 78
    assert resolve_funstats_league_id("ligue1") == 61
    assert resolve_funstats_league_id("135") == 135
    assert resolve_funstats_league_id(39) == 39
    assert resolve_funstats_league_id(None) is None


def test_build_long_term_h2h_analytics_orientation() -> None:
    sample_h2h = [
        {
            "fixture_id": 1001,
            "date": "2026-02-01T20:00:00+00:00",
            "home_team": {"id": 42, "name": "Arsenal"},
            "away_team": {"id": 49, "name": "Chelsea"},
            "goals": {"home": 3, "away": 1},
            "league_name": "Premier League",
            "season": 2026,
        },
        {
            "fixture_id": 1002,
            "date": "2025-10-15T16:30:00+00:00",
            "home_team": {"id": 49, "name": "Chelsea"},
            "away_team": {"id": 42, "name": "Arsenal"},
            "goals": {"home": 2, "away": 2},
            "league_name": "Premier League",
            "season": 2025,
        },
        {
            "fixture_id": 1003,
            "date": "2024-04-23T19:00:00+00:00",
            "home_team": {"id": 42, "name": "Arsenal"},
            "away_team": {"id": 49, "name": "Chelsea"},
            "goals": {"home": 5, "away": 0},
            "league_name": "Premier League",
            "season": 2024,
        },
        {
            "fixture_id": 1004,
            "date": "2023-10-21T16:30:00+00:00",
            "home_team": {"id": 49, "name": "Chelsea"},
            "away_team": {"id": 42, "name": "Arsenal"},
            "goals": {"home": 0, "away": 1},
            "league_name": "Premier League",
            "season": 2023,
        },
    ]

    h2h = build_long_term_h2h_analytics(
        sample_h2h,
        home_team_name="Arsenal",
        away_team_name="Chelsea",
        home_team_id=42,
        away_team_id=49,
    )
    assert h2h["total_meetings"] == 4
    assert h2h["span_years"] == "2023-2026"
    assert h2h["home_wins"] == 3
    assert h2h["draws"] == 1
    assert h2h["away_wins"] == 0
    assert h2h["home_goals_total"] == 11
    assert h2h["away_goals_total"] == 3
    assert h2h["avg_total_goals"] == 3.5
    assert h2h["btts_count"] == 2
    assert h2h["btts_pct"] == 50.0
    assert h2h["over_25_pct"] == 75.0
    assert h2h["when_home_hosted"]["meetings"] == 2
    assert h2h["when_home_hosted"]["home_wins"] == 2
    assert h2h["active_h2h_streaks"]["home_unbeaten"] == 4
    assert len(h2h["insights"]) >= 2


def test_extract_team_deep_splits() -> None:
    row = {
        "team_id": 42,
        "team_name": "Arsenal",
        "rank": 2,
        "played": 30,
        "home_played": 15,
        "away_played": 15,
        "points": 68,
        "form": "WWWDW",
        "goals_for": 64,
        "goals_against": 24,
        "over_05": 29,
        "over_15": 25,
        "over_25": 18,
        "over_35": 10,
        "over_45": 4,
        "btts": 15,
        "clean_sheets": 14,
        "failed_to_score": 2,
        "home_over_25": 10,
        "away_over_25": 8,
        "ht_over_05": 22,
        "ht_btts": 6,
        "second_half_over_05": 25,
        "htft_ww": 14,
        "htft_dw": 6,
        "corners_per_game": 10.4,
        "corners_over_95": 18,
        "cards_per_game": 3.8,
        "avg_possession": 61.2,
        "shots_per_game": 15.8,
        "sot_per_game": 5.9,
        "odds_fav_wins": 20,
        "odds_fav_draws": 5,
        "odds_fav_losses": 2,
        "odds_dog_wins": 1,
        "odds_dog_draws": 1,
        "odds_dog_losses": 1,
    }
    splits = extract_team_deep_splits(row)
    assert splits is not None
    assert splits["team_id"] == 42
    assert splits["goals_Toggle"]["over_25_pct"] == 60.0
    assert splits["goals_Toggle"]["btts_pct"] == 50.0
    assert splits["htft_matrix"]["WW"] == 14
    assert splits["corners_and_cards"]["corners_per_game"] == 10.4
    assert splits["market_role_record"]["as_favorite"]["matches"] == 27
    assert splits["market_role_record"]["as_favorite"]["wins"] == 20


def test_unflatten_devalue_and_cache_stats() -> None:
    arr = [
        {"MatchRowData": 1},
        [2],
        {"event_name_alias": 3, "percentage_Confidence": 4},
        "Arsenal v Chelsea",
        68.5,
    ]
    unflattened = _unflatten_devalue(arr, 0)
    assert unflattened == {
        "MatchRowData": [
            {"event_name_alias": "Arsenal v Chelsea", "percentage_Confidence": 68.5}
        ]
    }
    stats = get_funstats_cache_stats()
    assert "l1_hits" in stats
    assert "l2_rows" in stats
    fs = lookup_footystats_intel()
    assert fs["provider"] == "extended_league_stats"
