import sqlite3
import subprocess
from pathlib import Path

from collections import deque
from betscout.dashboard import generate_dashboard_html
from betscout.paper_bet import (
    PAPER_SCHEMA,
    _evaluate_us_sport_injuries_and_news,
    _upsert_paper_bet,
    evaluate_starting_xi_gate,
    get_paper_ledger_summary,
    settle_pending_paper_bets,
)


def test_us_sport_structured_injuries_gate():
    summary_healthy = {
        "injuries": [
            {"team": {"displayName": "Boston Celtics"}, "injuries": [{"status": "Out", "athlete": {"displayName": "Player A"}}]},
            {"team": {"displayName": "New York Knicks"}, "injuries": [{"status": "Out", "athlete": {"displayName": "Player B"}}]},
        ]
    }
    res_ok = _evaluate_us_sport_injuries_and_news(summary_healthy, "Boston Celtics", "New York Knicks", "H")
    assert res_ok["vetoed"] is False and res_ok["backed_out_count"] == 1 and res_ok["opp_out_count"] == 1

    summary_depleted = {
        "injuries": [
            {
                "team": {"displayName": "Boston Celtics"},
                "injuries": [{"status": "Out", "athlete": {"displayName": f"Star {i}"}} for i in range(6)],
            },
            {"team": {"displayName": "New York Knicks"}, "injuries": []},
        ]
    }
    res_veto = _evaluate_us_sport_injuries_and_news(summary_depleted, "Boston Celtics", "New York Knicks", "H")
    assert res_veto["vetoed"] is True and res_veto["backed_out_count"] == 6


def test_paper_bet_upsert_clv_and_settlement(tmp_path: Path):
    db = tmp_path / "pt.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE matches (
            event_id TEXT, league TEXT, sport TEXT, kickoff TEXT,
            home TEXT, away TEXT, home_score REAL, away_score REAL, outcome TEXT
        );
        """
        + PAPER_SCHEMA
    )
    conn.commit()
    conn.close()

    pick = {
        "league": "ita.1",
        "event_id": "999",
        "kickoff": "2026-10-25T19:45Z",
        "home": "Udinese",
        "away": "AC Milan",
        "side": "A",
        "tier": "top_10pct",
        "score": 0.35,
        "p_mkt": 0.58,
        "open_odds": 1.60,
        "best_odds": 1.65,
        "primary_odds": 1.62,
        "close_odds": 1.65,
        "synthetic_dc_odds": 1.15,
        "factors_tanh_z": {"p_mkt": 0.7, "sot_d": 0.8},
        "news_signal": {"backend": "ms-decision-1", "net_edge_for_pick": 0.79},
    }
    _upsert_paper_bet(db, pick, "2026-10-21T20:00:00Z")

    # Simulate closing line steaming from 1.65 down to 1.50 before kickoff (positive CLV!)
    pick_steamed = {**pick, "close_odds": 1.50}
    _upsert_paper_bet(db, pick_steamed, "2026-10-25T19:40:00Z")

    summary = get_paper_ledger_summary(db)
    assert summary["total_logged"] == 1
    assert summary["pending_count"] == 1
    # CLV = 1.65 / 1.50 - 1.0 = +0.10 (+10%)
    assert round(summary["mean_clv_pct"], 4) == 0.1000

    # Now insert finished match outcome 'A' into `matches` and run settlement
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO matches VALUES ('999','ita.1','soccer','2026-10-25T19:45Z','Udinese','AC Milan',0,2,'A')")
    conn.commit()
    conn.close()

    settled_n = settle_pending_paper_bets(db)
    assert settled_n == 1
    summary_after = get_paper_ledger_summary(db)
    assert summary_after["settled_count"] == 1
    assert summary_after["pending_count"] == 0
    assert round(summary_after["settled_roi_best"], 2) == 0.65
    assert round(summary_after["settled_roi_primary"], 2) == 0.62


def test_starting_xi_gate_and_dashboard(tmp_path: Path):
    # 1. When rosters have < 11 starters announced, status is AWAITING_T60M_LINEUPS
    xi_hist = {("eng.1", "Arsenal"): deque([{"p1": 3.0, "p2": 1.0}], maxlen=6)}
    g_wait = evaluate_starting_xi_gate({"rosters": []}, "eng.1", "Arsenal", "H", xi_hist)
    assert g_wait["status"] == "AWAITING_T60M_LINEUPS" and not g_wait["vetoed"]

    # 2. When 11 starters are announced but star scorer p1 (75% of attack) is missing -> VETOED_DEPLETED_XI
    xi_hist_3 = {("eng.1", "Arsenal"): deque([{"p1": 3.0, "p2": 1.0}] * 3, maxlen=6)}
    roster_missing_star = [{"athlete": {"id": f"p{i}"}, "starter": True} for i in range(2, 13)]
    g_veto = evaluate_starting_xi_gate(
        {"rosters": [{"homeAway": "home", "roster": roster_missing_star}]},
        "eng.1", "Arsenal", "H", xi_hist_3,
    )
    assert g_veto["status"] == "VETOED_DEPLETED_XI" and g_veto["vetoed"] is True

    # 2b. Position-specific GK + Defensive Spine continuity veto:
    # Even if attack share is 100% (p1 & p2 start), if primary GK (gk1) AND >=50% of defensive spine (d1..d4) are missing -> VETOED_DEPLETED_XI
    xi_hist_pos = {
        ("eng.1", "Arsenal"): deque(
            [
                {"_contrib": {"p1": 3.0, "p2": 1.0}, "_gk": {"gk1"}, "_df": {"d1", "d2", "d3", "d4"}},
                {"_contrib": {"p1": 2.0, "p2": 1.0}, "_gk": {"gk1"}, "_df": {"d1", "d2", "d3", "d4"}},
                {"_contrib": {"p1": 2.0, "p2": 1.0}, "_gk": {"gk1"}, "_df": {"d1", "d2", "d3", "d4"}},
            ],
            maxlen=6,
        )
    }
    roster_backup_gk_and_depleted_def = [
        {"athlete": {"id": "p1"}, "starter": True},
        {"athlete": {"id": "p2"}, "starter": True},
        {"athlete": {"id": "gk_backup"}, "starter": True},
        {"athlete": {"id": "d1"}, "starter": True},
        *[
            {"athlete": {"id": f"sub_{i}"}, "starter": True}
            for i in range(7)
        ],
    ]
    g_def_veto = evaluate_starting_xi_gate(
        {"rosters": [{"homeAway": "home", "roster": roster_backup_gk_and_depleted_def}]},
        "eng.1", "Arsenal", "H", xi_hist_pos,
    )
    assert g_def_veto["status"] == "VETOED_DEPLETED_DEFENSE" and g_def_veto["vetoed"] is True
    assert g_def_veto["gk_starting"] is False and g_def_veto["def_spine_share"] == 0.25

    # 3. Dashboard generation smoke test (including soft min_odds filter and sorted Best Bets table)
    db = tmp_path / "d.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript("CREATE TABLE matches (id TEXT, league TEXT, event_id TEXT, kickoff TEXT, home TEXT, away TEXT, outcome TEXT, home_score REAL, away_score REAL);" + PAPER_SCHEMA)
    conn.commit()
    conn.close()
    rec_json = tmp_path / "rec.json"
    rec_json.write_text(
        '{"generated_at": "2026-10-22T06:00:00Z", "backtest_risk": {"post25_bets": 4, "post25_cum_pnl": [0.0, 0.5, 1.2, 2.0]}, '
        '"qualifying_picks": ['
        '  {"league": "ita.1", "home": "Udinese", "away": "AC Milan", "side": "A", "tier": "top_10pct", "action": "PAPER_BET", "kickoff": "2026-10-25T19:45Z", "score": 0.33, "p_mkt": 0.57, "p_model": 0.63, "ev_pct": 3.95, "quarter_kelly_pct": 0.46, "best_odds": 1.65, "primary_odds": 1.65, "synthetic_dc_odds": 1.15, "factors_tanh_z": {"sot_d": 0.85, "dom_rebound": 0.62}}'
        '], '
        '"tennis_picks": ['
        '  {"tour": "WTA", "tournament": "Tokyo", "surface": "hard", "kickoff": "2026-10-22T11:00Z", "player_1": "Rybakina", "player_2": "Kudermetova", "pick": "Rybakina", "tier": "banker_70pct", "win_prob": 0.92, "min_fair_odds": 1.08, "target_ev3_odds": 1.12, "factors": {}},'
        '  {"tour": "ATP", "tournament": "Basel", "surface": "hard", "kickoff": "2026-10-22T13:30Z", "player_1": "Herbert", "player_2": "Fritz", "pick": "Fritz", "tier": "banker_70pct", "win_prob": 0.82, "min_fair_odds": 1.22, "target_ev3_odds": 1.26, "factors": {}}'
        '], '
        '"other_sport_picks": ['
        '  {"sport": "basketball", "league": "NBA", "league_name": "NBA", "kickoff": "2026-10-23T00:00Z", "home": "Celtics", "away": "Knicks", "side": "H", "pick": "Celtics", "tier": "high_conf", "p_model": 0.66, "p_mkt": 0.64, "best_odds": 1.52, "ev_pct": 0.3}'
        '], '
        '"paper_ledger": {}}'
    )
    out_html = tmp_path / "dashboard.html"
    out_csv = tmp_path / "best_bets.csv"
    out_json = tmp_path / "best_bets.json"
    generate_dashboard_html(rec_json, db, out_html, min_odds=1.10, csv_export_path=out_csv, json_export_path=out_json)
    html_text = out_html.read_text()
    assert "Best Bets Summary Table" in html_text
    assert "Export CSV (with Header)" in html_text
    assert "Filter by Sport:" in html_text
    assert 'data-sport-btn="tennis"' in html_text
    assert 'class="sortable-table"' in html_text
    assert 'onclick="sortTable(this)"' in html_text
    assert "Competition" in html_text
    assert 'class="sport-icon"' in html_text
    assert "Win Prob" in html_text
    assert "Min Fair Odds" in html_text
    assert "Score Projection" in html_text
    assert "Odds / CLV" in html_text
    assert 'id="liveBetsTable"' in html_text
    # Ensure embedded <script> block in dashboard.html has zero JavaScript syntax errors!
    script_body = html_text.split("<script>", 1)[1].split("</script>", 1)[0]
    node_chk = subprocess.run(["node", "--check"], input=script_body, text=True, capture_output=True)
    assert node_chk.returncode == 0, f"Dashboard JS syntax error: {node_chk.stderr}"
    # Rybakina (1.08 <= 1.10) must be filtered out by the soft filter!
    assert "Rybakina" not in html_text
    # Fritz (2026-10-22T13:30Z) must appear BEFORE Celtics (2026-10-23T00:00Z) and AC Milan (2026-10-25T19:45Z) in Best Bets table!
    bt_section = html_text.split("id=\"bestBetsTable\"", 1)[1]
    assert bt_section.index("Fritz") < bt_section.index("Celtics") < bt_section.index("AC Milan")

    # Test sport_filter='tennis' exports only tennis bets
    out_tennis_csv = tmp_path / "tennis_bets.csv"
    generate_dashboard_html(rec_json, db, out_html, min_odds=1.10, sport_filter="tennis", csv_export_path=out_tennis_csv)
    t_lines = out_tennis_csv.read_text().strip().splitlines()
    assert len(t_lines) == 2 and "Fritz" in t_lines[1]

    # Verify exported CSV (with header) and JSON
    csv_lines = out_csv.read_text().strip().splitlines()
    assert csv_lines[0] == "date,date_local,sport_league,match,pick,odds,odds_display"
    assert len(csv_lines) == 4  # header + 3 bets (Fritz, Celtics, AC Milan)
    assert "Fritz" in csv_lines[1] and "Celtics" in csv_lines[2] and "AC Milan" in csv_lines[3]
    assert "2026-10-22 15:30 CEST" in csv_lines[1]

    import json as _json
    exported_json = _json.loads(out_json.read_text())
    assert len(exported_json) == 3
    assert [r["date"] for r in exported_json] == ["2026-10-22T13:30Z", "2026-10-23T00:00Z", "2026-10-25T19:45Z"]

    # 4. Discord & Telegram digest formatter, .env loader & dry-run publisher test
    from betscout import load_dotenv
    from betscout.telegram_bot import (
        format_discord_digest,
        format_telegram_digest,
        get_discord_env_config,
        get_telegram_env_config,
        send_discord_message,
        send_telegram_message,
    )

    env_file = tmp_path / ".env"
    env_file.write_text(
        'DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/111222333/secret_webhook_tok"\n'
        'TELEGRAM_BOT_TOKEN="123456789:ABCDEF_test_token"\n'
        'TELEGRAM_CHAT_ID="@test_quant_channel"\n'
    )
    loaded = load_dotenv(env_path=env_file, override=True)
    assert loaded["TELEGRAM_CHAT_ID"] == "@test_quant_channel"
    d_cfg = get_discord_env_config(env_path=env_file)
    assert d_cfg["configured"] is True and d_cfg["mode"] == "webhook"
    tg_cfg = get_telegram_env_config(env_path=env_file)
    assert tg_cfg["configured"] is True and tg_cfg["chat_id"] == "@test_quant_channel"

    d_msg = format_discord_digest(_json.loads(rec_json.read_text()), min_odds=1.10, day_filter="all")
    assert "**BETSCOUT" in d_msg and "Fritz" in d_msg and "`2026-10-22 15:30 CEST`" in d_msg
    assert "BetScout · Sports Edge & Score Intelligence" in d_msg
    d_res = send_discord_message(d_msg, dry_run=True, env_path=env_file)
    assert d_res["ok"] is True and d_res["dry_run"] is True and d_res["configured"] is True

    # Verify day_filter='2026-10-22' only includes 2026-10-22 picks (Fritz) and excludes 2026-10-25 (AC Milan)
    d_msg_day = format_discord_digest(_json.loads(rec_json.read_text()), min_odds=1.10, day_filter="2026-10-22")
    assert "Fritz" in d_msg_day and "AC Milan" not in d_msg_day

    # 5. Exact Score & Set-Score Engine unit test
    from betscout.exact_score import predict_soccer_exact_scores, predict_tennis_set_scores

    s_pred = predict_soccer_exact_scores(
        ph=0.58, pd=0.24, pa=0.18, side="H", line_total=2.5, p_model=0.62, sot_z=0.75, dom_rebound_z=0.40
    )
    assert ":" in s_pred["top_exact_score"]
    assert s_pred["cluster_3_prob"] > s_pred["cluster_2_prob"] > s_pred["top_exact_prob"] > 0.08
    assert len(s_pred["top_3_breakdown"]) == 3

    t_pred_bo3 = predict_tennis_set_scores(win_prob=0.80, side="A", game_win_pct_diff=0.08, form_6m_diff=0.15, best_of=3)
    assert t_pred_bo3["straight_sets_score"] == "0:2"
    assert t_pred_bo3["decider_sets_score"] == "1:2"
    assert round(t_pred_bo3["straight_sets_prob"] + t_pred_bo3["decider_sets_prob"], 4) == 0.80

    t_pred_bo5 = predict_tennis_set_scores(win_prob=0.82, side="H", game_win_pct_diff=0.10, form_6m_diff=0.10, best_of=5)
    assert t_pred_bo5["straight_sets_score"] == "3:0" and t_pred_bo5["best_of"] == 5

    # 6. Exact-score hit grader, 2-leg doubles builder & automated settlement notification deduplication test
    from betscout.paper_bet import _check_exact_score_hit, build_recommended_2leg_doubles
    from betscout.telegram_bot import notify_new_settlements_to_discord

    assert _check_exact_score_hit("2:0 (14.0%) | Cluster 2:0 / 1:0 / 2:1 (38.0%)", "2-0") == 1
    assert _check_exact_score_hit("Sets 0:2 (60.0%, Fair 1.67)", "0-2 (4-6, 1-6)") == 1
    assert _check_exact_score_hit("Sets 0:2 (60.0%, Fair 1.67)", "1-2 (6-4, 2-6, 4-6)") == 0

    doubles = build_recommended_2leg_doubles(
        [{
            "league": "ita.1", "home": "Udinese", "away": "AC Milan", "side": "A", "action": "PAPER_BET",
            "best_odds": 1.65, "synthetic_dc_odds": 1.24, "p_model": 0.64, "kickoff": "2026-10-25T19:45Z",
            "exact_score_prediction": {"lambda_home": 1.0, "mu_away": 1.9, "cluster_3_scores": "0:1 / 0:2 / 1:2", "cluster_3_prob": 0.42, "cluster_3_fair_odds": 2.38},
        }],
        [{
            "tour": "ATP", "player_1": "Herbert", "player_2": "Fritz", "pick": "Fritz", "win_prob": 0.82,
            "best_odds": 1.26, "kickoff": "2026-10-25T13:30Z",
            "set_score_prediction": {"straight_sets_score": "0:2", "straight_sets_prob": 0.56, "straight_sets_fair_odds": 1.79},
            "totals_market": {"expected_games": 20.1, "games_line": 21.5, "recommended": "Under 21.5", "prob": 0.62, "fair_odds": 1.61},
        }],
        [],
    )
    assert len(doubles) >= 3
    assert round(doubles[0]["combined_odds"], 2) == round(1.65 * 1.26, 2)
    combo_types = {d["combo_type"] for d in doubles}
    assert "CROSS_SPORT_BANKER" in combo_types
    assert "DOUBLE_CHANCE_SHIELD" in combo_types
    assert "GOALS_GAMES_TOTALS" in combo_types

    # 7. Bit-for-bit Equivalence Regression Test for Performance Optimizations
    import numpy as np
    from betscout.goals import fit_rates, markets, score_grid
    from betscout.paper_bet import _build_team_player_attack_history

    def _fit_rates_scalar_ref(total_goals_line: float, home_p: float, away_p: float, draw_p: float, rho: float = -0.1):
        best, best_err = (1.3, 1.1), float("inf")
        for lam in np.arange(0.2, 3.6, 0.1):
            for mu in np.arange(0.2, 3.6, 0.1):
                m = markets(score_grid(lam, mu, rho))
                err = (m["home"] - home_p) ** 2 + (m["draw"] - draw_p) ** 2 + (m["away"] - away_p) ** 2
                if total_goals_line is not None:
                    err += 0.25 * (lam + mu - total_goals_line) ** 2 / (total_goals_line**2)
                if err < best_err:
                    best, best_err = (float(lam), float(mu)), err
        return best

    for line_v, ph_v, pa_v, pd_v, rho_v in [
        (2.5, 0.55, 0.20, 0.25, -0.10),
        (2.75, 0.68, 0.14, 0.18, -0.14),
        (2.25, 0.35, 0.35, 0.30, -0.08),
    ]:
        assert fit_rates(line_v, ph_v, pa_v, pd_v, rho_v) == _fit_rates_scalar_ref(line_v, ph_v, pa_v, pd_v, rho_v)

    real_db = (
        (Path(__file__).resolve().parents[2] / "data" / "betscout.db")
        if (Path(__file__).resolve().parents[2] / "data" / "betscout.db").exists()
        else (Path(__file__).resolve().parents[1] / "data" / "betscout.db")
    )
    if real_db.exists():
        xi_fast = _build_team_player_attack_history(real_db, real_db.parent / "cache", leagues=("eng.1", "uefa.champions"), full_history=False)
        xi_full = _build_team_player_attack_history(real_db, real_db.parent / "cache", leagues=("eng.1", "uefa.champions"), full_history=True)
        assert set(xi_fast.keys()) == set(xi_full.keys())
        for k in xi_full:
            assert list(xi_fast[k]) == list(xi_full[k]), f"Mismatch on {k}"

    # 8. Provisional / Unconfirmed Kickoff Time (`*` indicator + auto-update from provisional to confirmed)
    from betscout.dashboard import _format_local_time, _match_day_key, _time_span
    from betscout.paper_bet import _upsert_paper_bet, get_paper_ledger_summary

    assert _format_local_time("2026-10-23T12:00Z", time_valid=True) == "2026-10-23 14:00 CEST"
    assert _format_local_time("2026-10-24T09:30Z", time_valid=False) == "2026-10-24 11:30 CEST*"
    assert _format_local_time("2026-10-24T04:00Z", time_valid=False) == "2026-10-24 06:00 CEST* (TBD)"
    assert "*" in _time_span("2026-10-24T09:30Z", time_valid=False)
    # Verify 04:00 AM local slate cutoff keeps Boston Bruins vs San Jose Sharks (2026-10-24T23:00Z -> 2026-10-25 01:00 CEST) on 2026-10-24 ("Today")
    assert _match_day_key("2026-10-24T23:00Z") == "2026-10-24"
    assert _match_day_key("2026-10-25T11:30Z") == "2026-10-25"

    # First log with provisional time (`time_valid=False`, `2026-10-23T04:00Z`)
    _upsert_paper_bet(
        db,
        {
            "league": "atp",
            "event_id": "999001",
            "kickoff": "2026-10-23T04:00Z",
            "time_valid": False,
            "home": "Clement Chidekh",
            "away": "Francisco Cerundolo",
            "side": "A",
            "tier": "banker_70pct",
            "score": 0.80,
            "p_mkt": 0.80,
            "open_odds": 1.30,
            "best_odds": 1.32,
            "primary_odds": 1.25,
            "close_odds": 1.32,
            "synthetic_dc_odds": None,
            "factors_tanh_z": {"form_6m_diff": 0.15},
            "news_signal": {"backend": "tennis"},
        },
        "2026-10-22T20:00:00Z",
    )
    sum1 = get_paper_ledger_summary(db)
    tr1 = next(t for t in sum1["bets"] if t["event_id"] == "999001")
    assert tr1["kickoff"] == "2026-10-23T04:00Z" and tr1["time_valid"] is False

    # Now ESPN confirms the official court time (`2026-10-23T12:00Z`, `time_valid=True`): verify `_upsert_paper_bet` updates it!
    _upsert_paper_bet(
        db,
        {
            "league": "atp",
            "event_id": "999001",
            "kickoff": "2026-10-23T12:00Z",
            "time_valid": True,
            "home": "Clement Chidekh",
            "away": "Francisco Cerundolo",
            "side": "A",
            "tier": "banker_70pct",
            "score": 0.80,
            "p_mkt": 0.80,
            "open_odds": 1.30,
            "best_odds": 1.32,
            "primary_odds": 1.25,
            "close_odds": 1.30,
            "synthetic_dc_odds": None,
            "factors_tanh_z": {"form_6m_diff": 0.15},
            "news_signal": {"backend": "tennis"},
        },
        "2026-10-23T08:00:00Z",
    )
    sum2 = get_paper_ledger_summary(db)
    tr2 = next(t for t in sum2["bets"] if t["event_id"] == "999001")
    assert tr2["kickoff"] == "2026-10-23T12:00Z" and tr2["time_valid"] is True

    # 9. Prospective 2-Leg Combo Ledger (`paper_combos`), Auto-Grader, Calibration Attribution & Matchup Inspector
    from betscout.paper_bet import _upsert_paper_combo, settle_pending_paper_combos
    from betscout.webapp import _lookup_matchup_detail

    for d_c in doubles[:2]:
        d_c_past = {
            **d_c,
            "leg_1": {**d_c["leg_1"], "kickoff": "2026-10-20T19:45Z", "date_day": "2026-10-20"},
            "leg_2": {**d_c["leg_2"], "kickoff": "2026-10-20T13:30Z", "date_day": "2026-10-20"},
        }
        _upsert_paper_combo(db, d_c_past, "2026-10-20T08:00:00Z")
    sum_c1 = get_paper_ledger_summary(db)
    assert sum_c1["combos_total"] >= 2 and sum_c1["combos_pending"] >= 2

    # Insert settled outcomes for Udinese vs AC Milan (0-2 -> Away Win, X2 hit, Over 1.5 hit) and Herbert vs Fritz (0-2 -> Fritz Win, +1.5 Sets hit)
    conn_c = sqlite3.connect(db)
    conn_c.execute(
        "INSERT OR REPLACE INTO matches (id, league, event_id, kickoff, home, away, outcome, home_score, away_score) VALUES ('m1', 'ita.1', 'e1', '2026-10-20T19:45Z', 'Udinese', 'AC Milan', 'A', 0, 2)"
    )
    conn_c.execute(
        "INSERT OR REPLACE INTO paper_bets (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, settled_outcome, settled_score, pnl_best, pnl_primary) "
        "VALUES ('ita.1', 'e1', '2026-10-20T19:45Z', 'Udinese', 'AC Milan', 'A', 'top_10pct', 0.64, 0.58, 1.65, 1.65, 1.58, 0.044, '{}', '2026-10-20T08:00Z', '2026-10-20T22:00Z', 'SETTLED', 'A', '0-2', 0.65, 0.65)"
    )
    conn_c.execute(
        "INSERT OR REPLACE INTO paper_bets (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, settled_outcome, settled_score, pnl_best, pnl_primary) "
        "VALUES ('atp', 'e2', '2026-10-20T13:30Z', 'Herbert', 'Fritz', 'A', 'banker_70pct', 0.82, 0.82, 1.26, 1.22, 1.24, 0.016, '{}', '2026-10-20T08:00Z', '2026-10-20T16:00Z', 'SETTLED', 'A', '0-2 (4-6, 3-6)', 0.26, 0.22)"
    )
    conn_c.commit()
    conn_c.close()

    settled_combos_n = settle_pending_paper_combos(db)
    assert settled_combos_n >= 2
    sum_c2 = get_paper_ledger_summary(db)
    assert sum_c2["combos_settled"] >= 2 and sum_c2["combos_wins"] >= 2 and sum_c2["combos_profit_u"] > 0
    assert len(sum_c2["by_tier"]) >= 2

    m_detail = _lookup_matchup_detail(db, rec_json, "Udinese", "AC Milan", "ita.1")
    assert m_detail["ok"] is True and m_detail["home"] == "Udinese"

    # 10. Concurrent settlement notification deduplication test (atomically claims notified_at so concurrent threads send at most once)
    import threading
    from unittest.mock import patch

    conn_n = sqlite3.connect(db)
    conn_n.execute("UPDATE paper_bets SET notified_at = NULL WHERE status = 'SETTLED'")
    conn_n.commit()
    conn_n.close()

    send_calls = []

    def _fake_send_discord(msg_txt, **kwargs):
        import time
        time.sleep(0.05)
        send_calls.append(msg_txt)
        return {"ok": True, "dry_run": False, "message_id": "m1"}

    with patch("betscout.telegram_bot.send_discord_message", side_effect=_fake_send_discord):
        threads = [threading.Thread(target=notify_new_settlements_to_discord, args=(db,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(send_calls) >= 1 and sum(
        1 for m in send_calls if "NEW SETTLED PAPER-BET ALERT (" in m and "BETSCOUT (" not in m and "Unlock all daily VIP picks" not in m
    ) == 1, (
        f"Expected exactly 1 global Discord notification across 4 concurrent threads, got {len(send_calls)}"
    )

    # 11. Diacritic-insensitive SofaScore tennis matching & Indoor Hard surface split test
    from betscout.enrich import infer_surface
    from betscout.paper_bet import _strip_accents
    assert _strip_accents("Jiri Lehečka") == "jiri lehecka"
    assert _strip_accents("Tomáš Macháč") == "tomas machac"
    assert infer_surface("Swiss Indoors Basel") == "hard_indoor"
    assert infer_surface("Erste Bank Open Vienna") == "hard_indoor"
    assert infer_surface("Australian Open") == "hard"
    assert infer_surface("Roland Garros") == "clay"
    assert infer_surface("Wimbledon") == "grass"
    assert len(sum_c2["kelly_cum_pnl"]) == sum_c2["settled_count"]

    # 12. Live In-Play Momentum & Halftime / Second-Half Dominance Rebound Scanner test
    from betscout.paper_bet import _evaluate_inplay_soccer_momentum

    fake_live_summary = {
        "boxscore": {
            "teams": [
                {
                    "homeAway": "home",
                    "statistics": [
                        {"name": "shotsOnTarget", "displayValue": "6"},
                        {"name": "totalShots", "displayValue": "14"},
                        {"name": "wonCorners", "displayValue": "7"},
                        {"name": "possessionPct", "displayValue": "64.2"},
                    ],
                },
                {
                    "homeAway": "away",
                    "statistics": [
                        {"name": "shotsOnTarget", "displayValue": "1"},
                        {"name": "totalShots", "displayValue": "4"},
                        {"name": "wonCorners", "displayValue": "1"},
                        {"name": "possessionPct", "displayValue": "35.8"},
                    ],
                },
            ]
        }
    }
    mom = _evaluate_inplay_soccer_momentum(fake_live_summary, "H", 0, 0, "HT")
    assert mom["is_rebound_edge"] is True and mom["signal"] == "DOMINANCE_REBOUND_EDGE" and mom["sot_diff"] == 5

    # 13. Calibration Monitor & Live In-Play Dominance Rebound Discord Notifier test
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from calibration_report import compute_calibration_report
    from betscout.telegram_bot import notify_inplay_rebound_edges_to_discord

    cal_rep = compute_calibration_report(db)
    assert cal_rep["settled_count"] >= 2 and "brier_skill_vs_market" in cal_rep and "ece" in cal_rep

    conn_rb = sqlite3.connect(db)
    conn_rb.execute(
        "INSERT OR REPLACE INTO paper_bets (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, is_live, live_score, live_pnl, live_momentum_json) "
        "VALUES ('eng.2', 'live99', '2026-10-23T19:00Z', 'Bolton', 'Middlesbrough', 'A', 'top_8pct', 0.48, 0.62, 1.59, 1.59, 1.55, 0.025, '{}', '2026-10-23T10:00Z', '2026-10-23T19:45Z', 'PENDING', 1, '0-0 (HT)', 0.0, '{\"is_rebound_edge\": true, \"sot_for_pick\": 6, \"sot_opp\": 1, \"sot_diff\": 5, \"shots_diff\": 10, \"corners_diff\": 5, \"poss_pct\": 64.0}')"
    )
    conn_rb.commit()
    conn_rb.close()

    rb_res = notify_inplay_rebound_edges_to_discord(db, dry_run=True, global_enabled=True)
    assert rb_res["ok"] is True and rb_res["notified_count"] == 1
    # Also verify that _evaluate_inplay_soccer_momentum preserves notified_live_edge across subsequent polls!
    soc_mom_after = _evaluate_inplay_soccer_momentum(
        fake_live_summary, "H", 0, 0, "HT", prev_mom_json='{"notified_live_edge": true}'
    )
    assert soc_mom_after.get("notified_live_edge") is True
    assert "smartBetPlannerSection" in html_text and "buildSmartBetPlan" in html_text
    assert "custom-bet-chk" in html_text and "recalcModalDutching" in html_text

    # 14. Tennis Live Set-1 Deficit Rebound Edge test
    from betscout.paper_bet import _evaluate_inplay_tennis_momentum

    t_mom = _evaluate_inplay_tennis_momentum(
        t_sc="1-0 (7-6, 1-1)",
        side="A",
        win_prob=0.80,
        factor_json='{"decider_diff": 0.15, "game_elo_diff": 115.0}',
        live_status_desc="2nd Set",
    )
    assert t_mom["is_rebound_edge"] is True and t_mom["signal"] == "SET1_DEFICIT_REBOUND_EDGE"
    assert t_mom["set1_pick_games"] == 6 and t_mom["set1_opp_games"] == 7
    assert "liveAnalyzerModal" in html_text and "switchWorkspaceTab" in html_text and "walkForwardAuditPanel" in html_text

    from betscout.webapp import _analyze_live_matchup
    with patch("betscout.paper_bet._fetch_sofascore_tennis_odds", return_value={
        "odds_p1": 1.44, "odds_p2": 2.75, "games_line": 22.5,
        "p1_last5_win_rate": 0.80, "p2_last5_win_rate": 0.60,
        "p1_rest_hours": 28.0, "p2_rest_hours": 24.0,
        "p1_last_tourn": "Almaty", "p2_last_tourn": "Almaty",
    }):
        an_res = _analyze_live_matchup(db, rec_json, "Udinese vs AC Milan")
        assert an_res["ok"] is True and "verdict" in an_res and "market_recommendations" in an_res
    assert "mispricingRadarSection" in html_text and "printSmartBetTicket" in html_text and "saveSlipPrefsToStorage" in html_text
    assert "inplayAlertsToggleBtn" in html_text and "🔕 Live Alerts: OFF" in html_text

    from betscout.telegram_bot import resolve_discord_webhook_for_sport
    from betscout.webapp import _load_webapp_settings, _save_webapp_settings
    assert _load_webapp_settings(tmp_path)["inplay_alerts_enabled"] is False
    _save_webapp_settings(tmp_path, inplay_alerts_enabled=True)
    assert _load_webapp_settings(tmp_path)["inplay_alerts_enabled"] is True
    _save_webapp_settings(tmp_path, inplay_alerts_enabled=False, item_key="ger.1:401884763", item_enabled=True)
    cfg_after = _load_webapp_settings(tmp_path)
    assert cfg_after["inplay_alerts_enabled"] is False and cfg_after["inplay_alert_items"]["ger.1:401884763"] is True
    assert "toggleInplayItemAlert" in html_text
    assert "exactScoreSplitterSection" in html_text and "recalcStandaloneDutchSplitter" in html_text
    assert "settingsModal" in html_text and "openSettingsModal" in html_text
    assert "EMBEDDED_MATCHUP_DETAILS" in html_text
    assert "Monthly Walk-Forward Profit &amp; Consistency" in html_text
    assert "pageLoadingOverlay" in html_text and "topLoadingBar" in html_text and "showPageLoader" in html_text
    assert "pickCardCanvas" in html_text and "renderCanvasPickCard" in html_text and "attachPngCardChk" in html_text

    # Test PNG Pick Card & Slate rendering + dry-run attachment in Discord/Telegram
    from betscout.pick_card import render_digest_slate_png, render_pick_card_png

    single_png = render_pick_card_png({
        "sport_cat": "tennis",
        "competition": "ATP Tour · Erste Bank Open",
        "date_local": "2026-10-25 14:00 CET",
        "match": "Alexander Zverev vs Martin Landaluce",
        "pick_name": "Alexander Zverev (Win Prob 88.1%)",
        "tier": "banker_70pct",
        "win_prob": 0.8808,
        "min_fair_odds": 1.14,
        "odds": 1.18,
        "odds_display": "1.18",
        "exact_score_pick": "Sets 2:0 (65.6%, Fair 1.52)",
    })
    assert single_png.startswith(b"\x89PNG\r\n\x1a\n") and len(single_png) > 4000
    slate_png = render_digest_slate_png([
        {"date_local": "2026-10-25 14:00", "match": "Zverev vs Landaluce", "pick_name": "Zverev", "win_prob": 0.88, "odds_display": "1.18"},
        {"date_local": "2026-10-25 19:45", "match": "Udinese vs AC Milan", "pick_name": "AC Milan", "win_prob": 0.63, "odds_display": "1.65"},
    ])
    assert slate_png.startswith(b"\x89PNG\r\n\x1a\n") and len(slate_png) > 4000
    d_img_res = send_discord_message("Test with PNG", dry_run=True, env_path=env_file, image_bytes=single_png)
    assert d_img_res["ok"] is True and d_img_res["has_image"] is True
    tg_img_res = send_telegram_message("Test with PNG", dry_run=True, env_path=env_file, image_bytes=single_png)
    assert tg_img_res["ok"] is True and tg_img_res["has_image"] is True

    # Test Sportradar StatsHub (Tipico) prematch markets & 28-score Correct Score parser
    from betscout.sportradar_statshub import SR_ALL_SPORTS_CATALOG, parse_tipico_prematch_markets

    assert len(SR_ALL_SPORTS_CATALOG) == 56 and SR_ALL_SPORTS_CATALOG[1] == "Soccer" and SR_ALL_SPORTS_CATALOG[5] == "Tennis"
    parsed_sr = parse_tipico_prematch_markets([
        {"_marketId": 1, "outcomes": [{"name": "{$competitor1}", "odds": 1.32}, {"name": "draw", "odds": 5.5}, {"name": "{$competitor2}", "odds": 8.2}]},
        {"_marketId": 10, "outcomes": [{"name": "{$competitor1} or draw", "odds": 1.03}, {"name": "draw or {$competitor2}", "odds": 3.3}]},
        {"_marketId": 11, "outcomes": [{"name": "{$competitor1}", "odds": 1.10}, {"name": "{$competitor2}", "odds": 6.5}]},
        {"_marketId": 41, "outcomes": [{"_id": "sr:outcome:114", "odds": 12.0}, {"_id": "sr:outcome:116", "odds": 8.2}, {"_id": "sr:outcome:130", "odds": 7.8}]},
    ])
    assert parsed_sr["odds_home"] == 1.32 and parsed_sr["double_chance_1x"] == 1.03 and parsed_sr["draw_no_bet_home"] == 1.10
    assert parsed_sr["correct_score_odds"]["1:0"] == 12.0 and parsed_sr["correct_score_odds"]["2:0"] == 8.2 and parsed_sr["correct_score_odds"]["2:1"] == 7.8

    # Test Sportradar Injury Gate, 15-Min Goal Intervals & European Sports Scanner
    from betscout.sportradar_statshub import (
        evaluate_sportradar_injury_gate,
        fetch_live_match_situations_pressure,
        fetch_team_goal_intervals,
    )
    with patch("betscout.sportradar_statshub.fetch_statshub_gismo") as mock_gismo:
        mock_gismo.return_value = [
            {"uniqueteam": {"_id": 100}, "player": {"name": "Star Striker 1", "position": {"shortname": "FWD"}}, "status": {"name": "Injured"}},
            {"uniqueteam": {"_id": 100}, "player": {"name": "Star Striker 2", "position": {"shortname": "FWD"}}, "status": {"name": "Injured"}},
            {"uniqueteam": {"_id": 100}, "player": {"name": "Starting GK", "position": {"shortname": "GK"}}, "status": {"name": "Injured"}},
        ]
        ig_res = evaluate_sportradar_injury_gate(140782, 100, 200)
        assert ig_res["veto_recommended"] is True and ig_res["backed_fwd_out"] == 2 and ig_res["prob_adjustment"] < 0

        mock_gismo.return_value = {
            "stats": {
                "totalmatches": {"total": 7},
                "scoring": {
                    "goalsscoredfirsthalfaverage": {"total": 1.25},
                    "scoringathalftimeaverage": {"total": 0.72},
                    "bothteamsscoredaverage": {"total": 0.65},
                    "goalsbyminutes": {"76-90": {"total": 0.75}, "0-15": {"total": 0.40}},
                },
                "conceding": {
                    "goalsconcededfirsthalfaverage": {"total": 0.50},
                    "goalsbyminutes": {"76-90": {"total": 0.25}, "0-15": {"total": 0.20}},
                },
            }
        }
        gi_res = fetch_team_goal_intervals(140782, 100, limit=10)
        assert gi_res["scoring_in_1h_pct"] == 72.0 and gi_res["late_76_90_total_avg"] == 1.0

        mock_gismo.return_value = {
            "situations": [
                {"team": "home", "situation": "dangerous_attack"},
                {"team": "home", "situation": "dangerous_attack"},
                {"team": "away", "situation": "dangerous_attack"},
            ]
        }
        lp_res = fetch_live_match_situations_pressure(71945334)
        assert lp_res["home_dangerous_attacks"] == 2 and lp_res["home_danger_share_pct"] == 66.7

    # Test PWA manifest, service worker, install button & version update toast in dashboard.html
    assert 'rel="manifest" href="/manifest.webmanifest"' in html_text
    assert "pwaInstallBtn" in html_text and "triggerPwaInstall" in html_text
    assert "pwaUpdateToast" in html_text and "applyPwaUpdateNow" in html_text and "initPwaAndVersionWatcher" in html_text
    assert "cfgDefaultSortSelect" in html_text and "applyGlobalDefaultSort" in html_text
    assert "event-stream-dot" in html_text and "triggerStreamPulseDots" in html_text


    # Test 3-second real-time match_timelinedelta parser (sets, games, point score & serving indicator)
    from betscout.sportradar_statshub import fetch_live_match_timelinedelta
    with patch("betscout.sportradar_statshub.get_daily_tipico_match_index", return_value=[
        {"home": "Mpetshi Perricard, Giovanni", "away": "Kovacevic, Aleksandar", "tournament": "ATP Basel", "match_obj": {"_id": 75992888}}
    ]), patch("betscout.sportradar_statshub.fetch_statshub_gismo", return_value={
        "match": {
            "_id": 75992888,
            "status": {"_id": 8, "name": "1st set", "shortName": "S1"},
            "result": {"home": 0, "away": 0, "winner": None},
            "periods": {"p1": {"home": 6, "away": 5}},
            "gamescore": {"home": 0, "away": 15, "service": "2"},
        },
        "events": [{"type": "score_change_tennis"}],
    }):
        td_live = fetch_live_match_timelinedelta("Giovanni Mpetshi Perricard", "Aleksandar Kovacevic", sport="tennis")
        assert td_live["state"] == "in" and "6-5" in td_live["score_str"] and "Pt 0-15🎾" in td_live["score_str"]









    # Test per-sport Discord webhook resolution via .env and UI overrides
    env_file.write_text(
        'DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/111/global_wh"\n'
        'DISCORD_WEBHOOK_URL_TENNIS="https://discord.com/api/webhooks/222/tennis_wh"\n'
        'DISCORD_WEBHOOK_URL_SOCCER="https://discord.com/api/webhooks/333/soccer_wh"\n'
        'DISCORD_WEBHOOK_URL_HOCKEY=""\n'
        'DISCORD_WEBHOOK_URL_NHL=""\n'
        'DISCORD_WEBHOOK_URL_US_SPORTS=""\n'
    )
    assert resolve_discord_webhook_for_sport("wta", env_path=env_file) == "https://discord.com/api/webhooks/222/tennis_wh"
    assert resolve_discord_webhook_for_sport("ger.1", env_path=env_file) == "https://discord.com/api/webhooks/333/soccer_wh"
    assert resolve_discord_webhook_for_sport("nhl", env_path=env_file) == "https://discord.com/api/webhooks/111/global_wh"
    assert resolve_discord_webhook_for_sport(
        "nhl", env_path=env_file, custom_sport_webhooks={"hockey": "https://discord.com/api/webhooks/444/hockey_ui"}
    ) == "https://discord.com/api/webhooks/444/hockey_ui"
    load_dotenv(override=True)


def test_per_sport_isolated_gates():
    from betscout.sport_models import (
        evaluate_european_sport_gate,
        evaluate_nfl_gate,
        evaluate_soccer_gate,
        evaluate_tennis_gate,
    )

    thrs = {"top_8pct": 0.3661, "top_10pct": 0.3246, "top_15pct": 0.2565, "top_25pct": 0.1579}

    # 1. Soccer: Toulouse vs Troyes stalemate-draw trap is vetoed ('pass')
    assert (
        evaluate_soccer_gate(
            "fra.1",
            0.344,
            thrs,
            0.5914,
            1.5,
            {"p_mkt": 0.908, "vig_neg": 0.286, "sot_d": 0.584, "discipline": -0.79, "h2h_adv": 0.941, "dom_rebound": -0.408, "recent_draws": 0.887},
        )
        == "pass"
    )
    # 2. Soccer: Sporting CP vs Académico de Viseu (por.1 secondary domestic with negative h2h_adv=-0.189) is vetoed ('pass') even at top_8pct score
    assert (
        evaluate_soccer_gate(
            "por.1",
            0.4572,
            thrs,
            0.7558,
            -1.2,
            {"p_mkt": 0.993, "vig_neg": -0.8, "sot_d": 0.924, "discipline": 0.889, "h2h_adv": -0.189, "dom_rebound": 0.944, "recent_draws": 0.438},
        )
        == "pass"
    )
    # 3. Soccer: Bayern Munich at Freiburg (ger.1) passes at top_10pct
    assert (
        evaluate_soccer_gate(
            "ger.1",
            0.3261,
            thrs,
            0.6886,
            2.1,
            {"p_mkt": 0.914, "vig_neg": -0.965, "sot_d": 0.934, "discipline": -0.459, "h2h_adv": 0.984, "dom_rebound": 0.437, "recent_draws": 0.438},
        )
        == "top_10pct"
    )

    # 4. Tennis: Samsonova vs Watson (game_win_pct_diff=-0.01, form_6m_diff=0.0) and Valentova vs Pohankova (win_prob=0.710, game_elo_diff=72.3, game_win_pct_diff=0.016, form_6m_diff=0.0) are vetoed by stale-form gate
    t_ok, _, _, t_reason = evaluate_tennis_gate(0.80, 1.30, 3.50, game_win_pct_diff=-0.01, form_6m_diff=0.0)
    assert t_ok is False and t_reason == "VETO_STALE_TENNIS_FORM"
    t_val_ok, _, _, t_val_reason = evaluate_tennis_gate(
        0.710, 1.40, 2.80, game_win_pct_diff=0.016, form_6m_diff=0.0, game_elo_diff=72.3, all_elo_diff=157.0
    )
    assert t_val_ok is False and t_val_reason == "VETO_STALE_TENNIS_FORM"
    # Paula Badosa vs Young Suh Lee (win_prob=0.741, game_elo_diff=78.2, game_win_pct_diff=0.062, form_6m_diff=0.0) still passes!
    t_bad_ok, _, _, _ = evaluate_tennis_gate(
        0.741, 1.346, None, game_win_pct_diff=0.062, form_6m_diff=0.0, game_elo_diff=78.2, all_elo_diff=172.9
    )
    assert t_bad_ok is True

    # 5. NFL: Steelers (+69.2 yds, +1.22 ypp, comp=0.425) and Vikings (+68.7 yds, +1.20 ypp, comp=0.595) pass;
    #    Texans (1.20 odds, +18 yds, -14.9pp Elo gap) and Jets (-11.4pp Elo gap) are vetoed
    assert evaluate_nfl_gate(0.60, 0.593, 0.589, 0.425, 1.22, 69.2, 1.571) is True
    assert evaluate_nfl_gate(0.72, 0.741, 0.690, 0.595, 1.20, 68.7, 1.360) is True
    assert evaluate_nfl_gate(0.77, 0.804, 0.655, 0.503, 0.98, 18.0, 1.200) is False
    assert evaluate_nfl_gate(0.64, 0.657, 0.543, 0.378, 1.08, 72.0, 1.420) is False

    # 6. Table Tennis: <1.28 negative-EV chalk or losing-streak favorite (Klocek vs Rudomina) is vetoed; 1.36 favorite with +0.30 form diff & Elo edge passes
    tt_bad, _, _ = evaluate_european_sport_gate("table_tennis", 0.78, 0.50, 0.0, 1.20, False, 5, 5)
    # 6. Table Tennis: <1.28 negative-EV chalk, losing-streak favorite (Klocek vs Rudomina), or >48h cold-session rust (Warzecha vs Pyrek 107.8h) is vetoed; 1.36 warmed-up favorite passes
    tt_bad, _, _ = evaluate_european_sport_gate("table_tennis", 0.78, 0.50, 0.0, 1.20, False, 5, 5)
    tt_streak_bad, _, _ = evaluate_european_sport_gate(
        "table_tennis", 0.7119, 0.50, 0.10, 1.38, False, 10, 10, recent3_diff_fav=-1.0, fav_loss_streak=3, dog_win_streak=4
    )
    tt_cold_bad, _, _ = evaluate_european_sport_gate(
        "table_tennis", 0.7432, 0.55, 0.30, 1.32, False, 10, 10, recent3_diff_fav=0.333, fav_loss_streak=0, dog_win_streak=0, fav_hours_since_last=107.8, dog_hours_since_last=83.5
    )
    tt_good, p_mod_tt, ev_tt = evaluate_european_sport_gate(
        "table_tennis", 0.72, 0.62, 0.30, 1.36, True, 5, 5, recent3_diff_fav=0.333, fav_loss_streak=0, dog_win_streak=0, fav_hours_since_last=1.5, dog_hours_since_last=1.2
    )
    assert tt_bad is False and tt_streak_bad is False and tt_cold_bad is False
    assert tt_good is True and p_mod_tt >= 0.72 and ev_tt >= 0.0

    # 6b. Tennis Career-Elo Inflation vs Modest Game-Share Veto (Alves vs Grabher) & Adverse Line Drift Veto (Laura Samson vs Alice Tubello)
    t_alves, _, _, t_alves_reason = evaluate_tennis_gate(
        0.8244, 1.249, 3.80, game_win_pct_diff=0.045, form_6m_diff=0.5, game_elo_diff=88.9, all_elo_diff=254.7, h2h_n=0
    )
    assert t_alves is False and t_alves_reason == "VETO_CAREER_ELO_GAME_DIVERGENCE"
    t_samson, _, _, t_samson_reason = evaluate_tennis_gate(
        0.7135, 1.47, 2.55, game_win_pct_diff=0.063, form_6m_diff=0.4, game_elo_diff=53.9, all_elo_diff=170.2, h2h_n=0, open_odds=1.383
    )
    assert t_samson is False and t_samson_reason == "VETO_ADVERSE_LINE_DRIFT"

    # 7. NBA & NHL gates (vetoes Denver vs GSW comp=0.112, 3pt=-2.67, tov=-3.67; vetoes Dallas Stars vs Montreal Canadiens p_mod=0.5886 after 1-5 blowout vs 3-0 goalie wall; vetoes Savehof vs Amo non-Tipico handball loss-streak chalk)
    from betscout.dashboard import build_best_bets_summary
    from betscout.sport_models import evaluate_nba_gate, evaluate_nhl_gate

    assert evaluate_nba_gate(0.683, 0.692, 0.734, 0.112, 8.17, 0.0, 1.38, three_pt_diff=-2.67, tov_margin_diff=-3.67) is False
    assert evaluate_nba_gate(0.763, 0.783, 0.785, 0.242, 3.17, 0.0, 1.22, three_pt_diff=0.0, tov_margin_diff=1.50) is True
    assert evaluate_nba_gate(0.65, 0.66, 0.66, 0.24, -2.1, 1.33, 1.49) is True
    # Dallas Stars vs Montreal Canadiens (p_mod=0.5886, p_elo=0.5391, p_mkt=0.5934, last_margin=-4.0, opp_wr3=1.0, opp_ga3=0.67) -> Vetoed!
    assert (
        evaluate_nhl_gate(
            0.5886,
            0.3644,
            9.33,
            12.0,
            0.0,
            "H",
            1.617,
            p_elo=0.5391,
            p_mkt=0.5934,
            pick_win_rate_5=0.80,
            pick_ga_5=2.40,
            pick_goal_diff=1.50,
            pick_last_margin=-4.0,
            opp_win_rate_3=1.0,
            opp_ga_3=0.67,
        )
        is False
    )
    # Tampa Bay Lightning vs Winnipeg Jets (p_mod=0.6659, p_elo=0.645, p_mkt=0.675, last_margin=-1.0, opp_wr3=0.0, opp_ga3=3.33) -> Passes!
    assert (
        evaluate_nhl_gate(
            0.6659,
            0.2291,
            6.83,
            6.67,
            0.0,
            "H",
            1.408,
            p_elo=0.645,
            p_mkt=0.675,
            pick_win_rate_5=0.80,
            pick_ga_5=2.20,
            pick_goal_diff=1.50,
            pick_last_margin=-1.0,
            opp_win_rate_3=0.0,
            opp_ga_3=3.33,
        )
        is True
    )
    # Savehof vs Amo (handball, is_tipico=False, fav_loss_streak=1) -> Vetoed!
    hb_bad, _, _ = evaluate_european_sport_gate(
        "handball", 0.8096, 0.50, 0.20, 1.21, False, 10, 10, recent3_diff_fav=0.0, fav_loss_streak=1
    )
    assert hb_bad is False
    sample_rec = {
        "qualifying_picks": [],
        "tennis_picks": [],
        "other_sport_picks": [
            {"sport": "basketball", "league": "NBA", "league_name": "NBA", "kickoff": "2026-10-26T23:30Z", "home": "Celtics", "away": "Bulls", "side": "H", "pick": "Celtics", "tier": "high_conf", "p_model": 0.82, "p_mkt": 0.84, "best_odds": 1.16, "ev_pct": 1.2},
            {"sport": "hockey", "league": "NHL", "league_name": "NHL", "kickoff": "2026-10-26T23:00Z", "home": "Stars", "away": "Islanders", "side": "H", "pick": "Stars", "tier": "solid", "p_model": 0.65, "p_mkt": 0.64, "best_odds": 1.50, "ev_pct": 1.5},
        ],
    }
    all_bb = build_best_bets_summary(sample_rec, min_odds=1.10)
    dis_bb = build_best_bets_summary(sample_rec, min_odds=1.10, disabled_sports={"basketball"})
    assert len(all_bb) == 2 and len(dis_bb) == 1 and dis_bb[0]["sport_cat"] == "hockey"

    # 8. Option D Cloud Run & Firebase Auth RBAC verification
    import os
    from betscout.webapp import get_firebase_auth_config, verify_admin_request_auth

    # Default local mode (no FIREBASE_WEB_API_KEY / FIREBASE_ADMIN_EMAILS): all requests allowed
    os.environ.pop("FIREBASE_WEB_API_KEY", None)
    os.environ.pop("VITE_FIREBASE_API_KEY", None)
    os.environ.pop("FIREBASE_ADMIN_EMAILS", None)
    os.environ.pop("BETSCOUT_ADMIN_EMAILS", None)
    assert get_firebase_auth_config()["enabled"] is False
    ok_local, actor_local, _ = verify_admin_request_auth(None)
    assert ok_local is True and actor_local == "local_admin"

    # Cloud Run mode with FIREBASE_WEB_API_KEY + FIREBASE_ADMIN_EMAILS + BETSCOUT_CRON_SECRET
    os.environ["FIREBASE_WEB_API_KEY"] = "AIzaSy_test_key"
    os.environ["FIREBASE_ADMIN_EMAILS"] = "support@betscout.app"
    os.environ["BETSCOUT_CRON_SECRET"] = "secret_scheduler_token_123"
    try:
        assert get_firebase_auth_config()["enabled"] is True
        ok_unauth, _, err_unauth = verify_admin_request_auth(None)
        assert ok_unauth is False and "Authentication required" in err_unauth
        ok_cron, actor_cron, _ = verify_admin_request_auth("Bearer secret_scheduler_token_123")
        assert ok_cron is True and actor_cron == "cloud_scheduler"
    finally:
        os.environ.pop("FIREBASE_WEB_API_KEY", None)
        os.environ.pop("FIREBASE_ADMIN_EMAILS", None)
        os.environ.pop("BETSCOUT_CRON_SECRET", None)


def test_monetization_api_keys_subscribers_and_redaction(tmp_path: Path):
    from betscout.monetization import (
        add_subscriber_webhook,
        build_openapi_v1_spec,
        check_is_active_subscriber,
        create_api_key,
        handle_stripe_webhook_event,
        list_api_keys,
        list_subscriber_webhooks,
        redact_recommendations_for_free_tier,
        revoke_api_key,
        upsert_subscriber,
        validate_and_meter_api_key,
    )

    db_m = tmp_path / "betscout.db"
    # 1. API Key creation, tier enforcement, metering, and revocation
    created = create_api_key(db_m, owner_email="client@syndicate.io", plan_tier="starter", daily_limit=2)
    assert created["ok"] is True and created["api_key"].startswith("bs_live_")
    raw_k = created["api_key"]

    # Starter key passes starter endpoint (1/2 used)
    ok1, info1, hdr1, st1 = validate_and_meter_api_key(db_m, raw_k, required_tier="starter")
    assert ok1 is True and st1 == 200 and hdr1["X-RateLimit-Remaining"] == "1"

    # Starter key rejected on 'pro' endpoint (403)
    ok_pro, err_pro, _, st_pro = validate_and_meter_api_key(db_m, raw_k, required_tier="pro")
    assert ok_pro is False and st_pro == 403 and "requires 'pro'" in err_pro["error"]

    # 2nd starter call succeeds (2/2 used); 3rd call hits 429 quota limit
    ok2, _, hdr2, st2 = validate_and_meter_api_key(db_m, raw_k, required_tier="starter")
    assert ok2 is True and st2 == 200 and hdr2["X-RateLimit-Remaining"] == "0"
    ok3, err3, _, st3 = validate_and_meter_api_key(db_m, raw_k, required_tier="starter")
    assert ok3 is False and st3 == 429 and "Daily API quota exceeded" in err3["error"]

    # Revoke key
    assert revoke_api_key(db_m, created["key_id"]) is True
    ok_rev, _, _, st_rev = validate_and_meter_api_key(db_m, raw_k, required_tier="starter")
    assert ok_rev is False and st_rev == 401
    assert len(list_api_keys(db_m)) == 1

    # 2. Subscribers & Stripe Webhook auto-provisioning
    upsert_subscriber(db_m, email="pro_user@gmail.com", plan_tier="pro", status="active")
    is_sub, tier_sub = check_is_active_subscriber(db_m, "pro_user@gmail.com")
    assert is_sub is True and tier_sub == "pro"

    stripe_payload = b'{"type": "checkout.session.completed", "data": {"object": {"customer_email": "buyer@quant.com", "customer": "cus_123", "subscription": "sub_456", "metadata": {"plan_tier": "api_pro"}}}}'
    wh_res = handle_stripe_webhook_event(db_m, stripe_payload)
    assert wh_res["ok"] is True and wh_res["action"] == "provisioned" and wh_res["api_key"]["plan_tier"] == "pro"
    assert check_is_active_subscriber(db_m, "buyer@quant.com")[0] is True

    # 3. B2B Subscriber Webhooks
    add_subscriber_webhook(db_m, "buyer@quant.com", "discord", "https://discord.com/api/webhooks/999/b2b_wh", "tennis")
    assert len(list_subscriber_webhooks(db_m)) == 1

    # 4. Server-side Free-tier Redaction (keeps settled rows & N preview picks, locks remaining picks)
    raw_rec = {
        "qualifying_picks": [
            {"action": "PAPER_BET", "kickoff": "2026-10-26T12:00Z", "home": "Team A", "away": "Team B", "best_odds": 1.45},
            {"action": "PAPER_BET", "kickoff": "2026-10-26T18:00Z", "home": "Secret Team C", "away": "Secret Team D", "best_odds": 1.65},
        ],
        "tennis_picks": [
            {"kickoff": "2026-10-26T20:00Z", "player_1": "Secret Player E", "player_2": "Secret Player F", "pick": "Secret Player E", "win_prob": 0.82},
        ],
        "other_sport_picks": [],
        "recommended_doubles": [{"leg_1": {"match": "Secret C vs D", "pick": "Secret C"}, "leg_2": {"match": "Secret E vs F", "pick": "Secret E"}}],
        "paper_ledger": {
            "bets": [
                {"status": "SETTLED", "home": "Bayern Munich", "away": "Freiburg", "logged_best_odds": 1.38},
                {"status": "PENDING", "home": "Secret Team C", "away": "Secret Team D", "logged_best_odds": 1.65},
            ]
        },
    }
    redacted = redact_recommendations_for_free_tier(raw_rec, free_preview_count=1)
    # 1st earliest pick (Team A vs Team B) stays unlocked
    assert redacted["qualifying_picks"][0]["home"] == "Team A"
    # 2nd pick & tennis pick are server-side redacted
    assert "🔒 Pro" in redacted["qualifying_picks"][1]["home"]
    assert "🔒 Pro" in redacted["tennis_picks"][0]["player_1"]
    # Settled ledger row remains 100% visible, while pending non-preview row is redacted
    assert redacted["paper_ledger"]["bets"][0]["home"] == "Bayern Munich"
    assert "🔒 Pro" in redacted["paper_ledger"]["bets"][1]["home"]
    assert build_openapi_v1_spec()["openapi"] == "3.1.0"


def test_nhl_table_tennis_and_tennis_loss_veto_gates():
    from betscout.sport_models import (
        evaluate_european_sport_gate,
        evaluate_nhl_gate,
        evaluate_tennis_gate,
        route_major_league_gate,
    )

    # 1. NHL Leaky-Defense & Slumping-Form Veto (Anaheim Ducks vs Vancouver Canucks: 1W-4L last 5, GA5=4.00, GoalDiff=-0.50, EV=-6.58%)
    assert (
        evaluate_nhl_gate(
            p_mod=0.6579,
            comp_score=0.12,
            save_pct_diff=8.0,
            shots_diff=5.0,
            rest_for_pick=0.33,
            side="H",
            odds_pick=1.42,
            p_elo=0.52,
            p_mkt=0.6468,
            pick_win_rate_5=0.20,
            pick_ga_5=4.00,
            pick_goal_diff=-0.50,
        )
        is False
    )
    assert (
        route_major_league_gate(
            league="nhl",
            p_mod=0.6579,
            p_mkt=0.6468,
            p_elo=0.62,
            comp_score=0.18,
            sot_f=8.0,
            vol_f=5.0,
            rest_for_pick=0.33,
            side="H",
            odds_pick=1.42,
            pick_win_rate_5=0.60,
            pick_ga_5=2.40,
            pick_goal_diff=1.20,
        )
        is False  # EV = (0.6579 * 1.42 - 1) * 100 = -6.58% < -3.5%
    )
    # Strong NHL favorite with solid defense & fair 2-way price passes
    assert (
        route_major_league_gate(
            league="nhl",
            p_mod=0.66,
            p_mkt=0.64,
            p_elo=0.62,
            comp_score=0.18,
            sot_f=8.0,
            vol_f=5.0,
            rest_for_pick=0.33,
            side="H",
            odds_pick=1.52,
            pick_win_rate_5=0.60,
            pick_ga_5=2.40,
            pick_goal_diff=1.20,
        )
        is True
    )

    # 2. Table Tennis Session Workload (>=13 sets in 3.5h) & 5-Set Decider Hangover Veto (Machelski vs Nocun 22:05Z)
    passed_tt_loss, _, _ = evaluate_european_sport_gate(
        sport_slug="table_tennis",
        p_mkt=0.7524,
        p_elo_fav=0.55,
        form_diff_fav=0.30,
        best_odds=1.30,
        is_tipico=True,
        n_form_home=10,
        n_form_away=10,
        recent3_diff_fav=0.0,
        fav_wr=0.60,
        fav_session_sets_3h=14,
        fav_last_lost_5set=True,
    )
    assert passed_tt_loss is False

    # Rested next-session rematch (9 sets in 3.5h, no 5-set decider loss, positive Last-3 form) passes
    passed_tt_win, _, _ = evaluate_european_sport_gate(
        sport_slug="table_tennis",
        p_mkt=0.762,
        p_elo_fav=0.55,
        form_diff_fav=0.25,
        best_odds=1.29,
        is_tipico=True,
        n_form_home=10,
        n_form_away=10,
        recent3_diff_fav=0.333,
        fav_wr=0.60,
        fav_session_sets_3h=9,
        fav_last_lost_5set=False,
    )
    assert passed_tt_win is True

    # 3. Tennis Court-Acclimatization Veto (Griekspoor vs Lehecka: win_prob=0.754 < 0.80, tourn_wins_diff=-1)
    t_ok, _, _, t_reason = evaluate_tennis_gate(
        win_prob=0.7542,
        book_odds=1.372,
        opp_book_odds=3.10,
        game_win_pct_diff=0.102,
        form_6m_diff=0.333,
        game_elo_diff=72.6,
        all_elo_diff=182.1,
        h2h_n=0,
        decider_diff=0.0,
        tourn_wins_diff=-1,
    )
    # 4. Darts Immediate H2H Loss Veto (Coulson, Derek vs Davies, David: Davies beat Coulson 4-2 in their immediately preceding match)
    passed_darts_loss, _, _ = evaluate_european_sport_gate(
        sport_slug="darts",
        p_mkt=0.6575,
        p_elo_fav=0.55,
        form_diff_fav=0.30,
        best_odds=1.35,
        is_tipico=True,
        n_form_home=10,
        n_form_away=10,
        recent3_diff_fav=0.0,
        fav_loss_streak=1,
        dog_win_streak=1,
        fav_lost_last_h2h=True,
    )
    assert passed_darts_loss is False

    # 5. Handball Fresh-Defeat & Consensus-Only Heavy Chalk Veto (Savehof vs Amo: Savehof lost prior match, fav_loss_streak=1, is_tipico=False)
    passed_hb_loss, _, _ = evaluate_european_sport_gate(
        sport_slug="handball",
        p_mkt=0.8096,
        p_elo_fav=0.55,
        form_diff_fav=0.30,
        best_odds=1.21,
        is_tipico=False,
        n_form_home=10,
        n_form_away=10,
        recent3_diff_fav=0.0,
        fav_loss_streak=1,
        dog_win_streak=0,
        fav_wr=0.80,
    )
    assert passed_hb_loss is False

    # 6. Football Stalemate-Draw & Weak-Shot-Dominance Vetoes (Bayern Munich W vs Real Madrid W 2-2 & AC Milan vs Bologna 2-4)
    from betscout.sport_models import evaluate_soccer_gate

    thresholds_sample = {"top_8pct": 0.36, "top_10pct": 0.31, "top_15pct": 0.26, "top_25pct": 0.17}
    assert (
        evaluate_soccer_gate(
            league="uefa.wchampions",
            score=0.244,
            thresholds=thresholds_sample,
            p_mkt=0.6277,
            ev_pct=2.5,
            factors_tanh_z={
                "p_mkt": 0.904,
                "vig_neg": -0.925,
                "sot_d": 0.982,
                "discipline": -0.673,
                "h2h_adv": 0.941,
                "dom_rebound": -0.408,
                "recent_draws": 0.887,
            },
        )
        == "pass"
    )
    assert (
        evaluate_soccer_gate(
            league="ita.1",
            score=0.3436,
            thresholds=thresholds_sample,
            p_mkt=0.5818,
            ev_pct=1.8,
            factors_tanh_z={
                "p_mkt": 0.766,
                "vig_neg": -0.167,
                "sot_d": 0.226,
                "discipline": 0.481,
                "h2h_adv": 0.621,
                "dom_rebound": -0.408,
                "recent_draws": 0.887,
            },
        )
        == "pass"
    )



def test_notify_new_picks_to_discord_dry_run(tmp_path: Path):
    from betscout.telegram_bot import notify_new_picks_to_discord

    db = tmp_path / "picks_notify.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE matches (
            event_id TEXT, league TEXT, sport TEXT, kickoff TEXT,
            home TEXT, away TEXT, home_score REAL, away_score REAL, outcome TEXT
        );
        """
        + PAPER_SCHEMA
    )
    conn.commit()
    conn.close()

    _upsert_paper_bet(
        db,
        {
            "league": "ita.1",
            "event_id": "401874988",
            "kickoff": "2026-10-28T19:45Z",
            "home": "Genoa",
            "away": "Juventus",
            "side": "A",
            "tier": "top_8pct",
            "score": 0.5016,
            "p_mkt": 0.60,
            "open_odds": 1.65,
            "best_odds": 1.65,
            "primary_odds": 1.65,
            "close_odds": 1.65,
            "synthetic_dc_odds": 1.15,
            "factors_tanh_z": {"p_mkt": 0.77, "sot_d": 0.868},
            "news_signal": {"backend": "none"},
            "exact_score_pred": "0:2 (16.2%) · Cluster 0:1 / 0:2 / 1:2",
        },
        "2026-10-28T08:00:00Z",
    )

    res = notify_new_picks_to_discord(db, webhook_url="https://discord.com/api/webhooks/123/abc", dry_run=True)
    assert res["ok"] is True and res["notified_picks_count"] == 1
    assert "NEW HIGH-CONVICTION PRE-MATCH PICK" in res["preview"]
    assert "Genoa vs Juventus" in res["preview"]

