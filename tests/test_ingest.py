from sportdata_model.ingest import _soccer_odds, fractional_to_decimal, _outcome


def test_fractional_to_decimal():
    assert fractional_to_decimal("8/5") == 2.6
    assert fractional_to_decimal("5/2") == 3.5
    assert fractional_to_decimal("3") is None
    assert fractional_to_decimal(None) is None


def test_outcome():
    assert _outcome(2, 1) == "H"
    assert _outcome(0, 3) == "A"
    assert _outcome(1, 1) == "D"
    assert _outcome(None, 1) is None


def test_soccer_odds_full_market():
    summary = {"odds": [{
        "provider": {"name": "Bet 365"},
        "bettingOdds": {"teamOdds": {
            "preMatchFullTimeResultHome": {"value": "8/5"},
            "preMatchFullTimeResultDraw": {"value": "5/2"},
            "preMatchFullTimeResultAway": {"value": "31/20"},
            "preMatchDoubleChanceHomeOrDraw": {"value": "1/2"},
            "preMatchDoubleChanceDrawOrAway": {"value": "1/2"},
            "preMatchDoubleChanceHomeOrAway": {"value": "2/7"},
            "preMatchOverUnderHandicap": {"value": "3"},
            "preMatchGoalLineOver": {"value": "49/50"},
            "preMatchGoalLineUnder": {"value": "23/25"},
        }}}]}
    p = _soccer_odds(summary)
    assert p["odds_home"] == 2.6 and p["odds_provider"] == "Bet 365"
    assert p["line_total"] == 3.0
    assert round(p["odds_over"], 2) == 1.98
    assert p["odds_dc_12"] == 1 + 2 / 7


def test_soccer_odds_missing_returns_none():
    p = _soccer_odds({"odds": []})
    assert p["odds_home"] is None and p["line_total"] is None


def test_american_prematch_fallback_and_rejects_inplay_flat():
    summary = {"odds": [
        {
            "provider": {"name": "Bet 365"},
            "homeTeamOdds": {"odds": {"summary": "9/1", "value": 10.0}},
            "drawOdds": {"summary": "1/16", "value": 1.063},
            "awayTeamOdds": {"odds": {"summary": "40/1", "value": 41.0}},
        },
        {
            "provider": {"name": "DraftKings"},
            "homeTeamOdds": {"moneyLine": -200.0},
            "drawOdds": {"moneyLine": 350.0},
            "awayTeamOdds": {"moneyLine": 500.0},
            "overUnder": 2.5,
            "overOdds": -125.0,
            "underOdds": 100.0,
        },
    ]}
    p = _soccer_odds(summary)
    assert p["odds_provider"] == "DraftKings"
    assert round(p["odds_home"], 2) == 1.50
    assert round(p["odds_draw"], 2) == 4.50
    assert round(p["odds_away"], 2) == 6.00
    assert p["line_total"] == 2.5
    assert round(p["odds_over"], 2) == 1.80
    assert round(p["odds_under"], 2) == 2.00


def test_flat_rejects_moneyline_only_and_off_shapes():
    summary = {"odds": [{
        "provider": {"name": "DraftKings"},
        "homeTeamOdds": {"moneyLine": 300.0},
        "drawOdds": {"moneyLine": 225.0},
        "awayTeamOdds": {"moneyLine": 1.1},
    }, {
        "provider": {"name": "Bet 365"},
        "homeTeamOdds": {"odds": {"summary": "OFF", "value": 0.0}},
        "drawOdds": {"summary": "OFF", "value": 0.0},
        "awayTeamOdds": {"odds": {"summary": "OFF", "value": 0.0}},
    }]}
    assert _soccer_odds(summary)["odds_home"] is None
