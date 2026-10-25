import sqlite3
import subprocess
from pathlib import Path

from collections import deque
from betscout.dashboard import generate_dashboard_html
from betscout.decision_signal import (
    NewsSignal,
    extract_team_news_text,
    record_distillation_pair,
    score_match_news,
)
from betscout.paper_trade import (
    PAPER_SCHEMA,
    _upsert_paper_trade,
    evaluate_starting_xi_gate,
    get_paper_ledger_summary,
    settle_pending_paper_trades,
)


def test_extract_team_news_text_and_signal():
    summary = {
        "news": {
            "articles": [
                {
                    "headline": "AC Milan captain returns to full training ahead of Udinese trip",
                    "description": "Milan receive a major fitness boost for Sunday.",
                },
                {
                    "headline": "Unrelated Premier League transfer rumor",
                    "description": "Nothing about Serie A.",
                },
            ]
        }
    }
    text, matched = extract_team_news_text(summary, "Udinese", "AC Milan")
    assert len(matched) == 1
    assert "AC Milan captain returns" in matched[0]
    assert "Udinese (Home) vs AC Milan (Away)" in text

    sig = NewsSignal(
        backend="test",
        home_positive=0.1,
        home_negative=0.4,
        away_positive=0.8,
        away_negative=0.1,
        matched_headlines=matched,
    )
    # Away net = +0.7, Home net = -0.3 -> net_edge('A') = +1.0, net_edge('H') = -1.0
    assert round(sig.net_edge("A"), 3) == 1.0
    assert round(sig.net_edge("H"), 3) == -1.0

    neutral = score_match_news(summary, "Udinese", "AC Milan", backend="none")
    assert neutral.backend == "none" and neutral.net_edge("A") == 0.0


def test_record_distillation_pair_dedup(tmp_path: Path):
    from betscout.decision_signal import split_match_text_by_team
    pairs_file = tmp_path / "pairs.jsonl"
    ans = {"home_positive": 0.1, "home_negative": 0.85, "away_positive": 0.75, "away_negative": 0.05}
    assert record_distillation_pair("Match: Arsenal vs Chelsea\n- Saka out", "Arsenal", "Chelsea", ans, pairs_file) is True
    # Duplicate state must be skipped
    assert record_distillation_pair("Match: Arsenal vs Chelsea\n- Saka out", "Arsenal", "Chelsea", ans, pairs_file) is False
    lines = pairs_file.read_text().strip().splitlines()
    assert len(lines) == 1
    assert '"home_negative"' in lines[0] and '"expected"' in lines[0]

    # Subject-aware team attribution test
    h_txt, a_txt = split_match_text_by_team(
        "Match: Arsenal (Home) vs Chelsea (Away).\n"
        "- Arsenal star Bukayo Saka ruled out of Chelsea clash.\n"
        "- Chelsea star Cole Palmer returns fit for Arsenal trip.",
        "Arsenal",
        "Chelsea",
    )
    assert "Bukayo Saka ruled out" in h_txt and "Cole Palmer" not in h_txt
    assert "Cole Palmer returns fit" in a_txt and "Bukayo Saka" not in a_txt


def test_paper_trade_upsert_clv_and_settlement(tmp_path: Path):
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
    _upsert_paper_trade(db, pick, "2026-10-21T20:00:00Z")

    # Simulate closing line steaming from 1.65 down to 1.50 before kickoff (positive CLV!)
    pick_steamed = {**pick, "close_odds": 1.50}
    _upsert_paper_trade(db, pick_steamed, "2026-10-25T19:40:00Z")

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

    settled_n = settle_pending_paper_trades(db)
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
    assert 'id="liveTradesTable"' in html_text
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
    from betscout.paper_trade import _check_exact_score_hit, build_recommended_2leg_doubles
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
    from betscout.paper_trade import _build_team_player_attack_history

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

    real_db = Path(__file__).resolve().parents[1] / "data" / "matches.sqlite"
    if real_db.exists():
        xi_fast = _build_team_player_attack_history(real_db, real_db.parent / "cache", leagues=("eng.1", "uefa.champions"), full_history=False)
        xi_full = _build_team_player_attack_history(real_db, real_db.parent / "cache", leagues=("eng.1", "uefa.champions"), full_history=True)
        assert set(xi_fast.keys()) == set(xi_full.keys())
        for k in xi_full:
            assert list(xi_fast[k]) == list(xi_full[k]), f"Mismatch on {k}"

    # 8. Provisional / Unconfirmed Kickoff Time (`*` indicator + auto-update from provisional to confirmed)
    from betscout.dashboard import _format_local_time, _match_day_key, _time_span
    from betscout.paper_trade import _upsert_paper_trade, get_paper_ledger_summary

    assert _format_local_time("2026-10-23T12:00Z", time_valid=True) == "2026-10-23 14:00 CEST"
    assert _format_local_time("2026-10-24T09:30Z", time_valid=False) == "2026-10-24 11:30 CEST*"
    assert _format_local_time("2026-10-24T04:00Z", time_valid=False) == "2026-10-24 06:00 CEST* (TBD)"
    assert "*" in _time_span("2026-10-24T09:30Z", time_valid=False)
    # Verify 04:00 AM local slate cutoff keeps Boston Bruins vs San Jose Sharks (2026-10-24T23:00Z -> 2026-10-25 01:00 CEST) on 2026-10-24 ("Today")
    assert _match_day_key("2026-10-24T23:00Z") == "2026-10-24"
    assert _match_day_key("2026-10-25T11:30Z") == "2026-10-25"

    # First log with provisional time (`time_valid=False`, `2026-10-23T04:00Z`)
    _upsert_paper_trade(
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
    tr1 = next(t for t in sum1["trades"] if t["event_id"] == "999001")
    assert tr1["kickoff"] == "2026-10-23T04:00Z" and tr1["time_valid"] is False

    # Now ESPN confirms the official court time (`2026-10-23T12:00Z`, `time_valid=True`): verify `_upsert_paper_trade` updates it!
    _upsert_paper_trade(
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
    tr2 = next(t for t in sum2["trades"] if t["event_id"] == "999001")
    assert tr2["kickoff"] == "2026-10-23T12:00Z" and tr2["time_valid"] is True

    # 9. Prospective 2-Leg Combo Ledger (`paper_combos`), Auto-Grader, Calibration Attribution & Matchup Inspector
    from betscout.paper_trade import _upsert_paper_combo, settle_pending_paper_combos
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
        "INSERT OR REPLACE INTO paper_trades (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, settled_outcome, settled_score, pnl_best, pnl_primary) "
        "VALUES ('ita.1', 'e1', '2026-10-20T19:45Z', 'Udinese', 'AC Milan', 'A', 'top_10pct', 0.64, 0.58, 1.65, 1.65, 1.58, 0.044, '{}', '2026-10-20T08:00Z', '2026-10-20T22:00Z', 'SETTLED', 'A', '0-2', 0.65, 0.65)"
    )
    conn_c.execute(
        "INSERT OR REPLACE INTO paper_trades (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, settled_outcome, settled_score, pnl_best, pnl_primary) "
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
    conn_n.execute("UPDATE paper_trades SET notified_at = NULL WHERE status = 'SETTLED'")
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

    assert len(send_calls) >= 1 and sum(1 for m in send_calls if "NEW SETTLED PAPER-BET ALERT (" in m and "BETSCOUT (" not in m) == 1, (
        f"Expected exactly 1 global Discord notification across 4 concurrent threads, got {len(send_calls)}"
    )

    # 11. Diacritic-insensitive SofaScore tennis matching & Indoor Hard surface split test
    from betscout.enrich import infer_surface
    from betscout.paper_trade import _strip_accents
    assert _strip_accents("Jiri Lehečka") == "jiri lehecka"
    assert _strip_accents("Tomáš Macháč") == "tomas machac"
    assert infer_surface("Swiss Indoors Basel") == "hard_indoor"
    assert infer_surface("Erste Bank Open Vienna") == "hard_indoor"
    assert infer_surface("Australian Open") == "hard"
    assert infer_surface("Roland Garros") == "clay"
    assert infer_surface("Wimbledon") == "grass"
    assert len(sum_c2["kelly_cum_pnl"]) == sum_c2["settled_count"]

    # 12. Live In-Play Momentum & Halftime / Second-Half Dominance Rebound Scanner test
    from betscout.paper_trade import _evaluate_inplay_soccer_momentum

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
        "INSERT OR REPLACE INTO paper_trades (league, event_id, kickoff, home, away, side, tier, composite_score, p_mkt, logged_best_odds, logged_primary_odds, latest_close_odds, clv_pct, factor_breakdown_json, logged_at, updated_at, status, is_live, live_score, live_pnl, live_momentum_json) "
        "VALUES ('eng.2', 'live99', '2026-10-23T19:00Z', 'Bolton', 'Middlesbrough', 'A', 'top_8pct', 0.48, 0.62, 1.59, 1.59, 1.55, 0.025, '{}', '2026-10-23T10:00Z', '2026-10-23T19:45Z', 'PENDING', 1, '0-0 (HT)', 0.0, '{\"is_rebound_edge\": true, \"sot_for_pick\": 6, \"sot_opp\": 1, \"sot_diff\": 5, \"shots_diff\": 10, \"corners_diff\": 5, \"poss_pct\": 64.0}')"
    )
    conn_rb.commit()
    conn_rb.close()

    rb_res = notify_inplay_rebound_edges_to_discord(db, dry_run=True)
    assert rb_res["ok"] is True and rb_res["notified_count"] == 1
    assert "smartBetPlannerSection" in html_text and "buildSmartBetPlan" in html_text
    assert "custom-bet-chk" in html_text and "recalcModalDutching" in html_text

    # 14. Tennis Live Set-1 Deficit Rebound Edge test
    from betscout.paper_trade import _evaluate_inplay_tennis_momentum

    t_mom = _evaluate_inplay_tennis_momentum(
        t_sc="1-0 (7-6, 1-1)",
        side="A",
        win_prob=0.80,
        factor_json='{"decider_diff": 0.15, "game_elo_diff": 115.0}',
        live_status_desc="2nd Set",
    )
    assert t_mom["is_rebound_edge"] is True and t_mom["signal"] == "SET1_DEFICIT_REBOUND_EDGE"
    assert t_mom["set1_pick_games"] == 6 and t_mom["set1_opp_games"] == 7
    assert "liveMatchupAnalyzerSection" in html_text and "walkForwardAuditPanel" in html_text

    from betscout.webapp import _analyze_live_matchup
    with patch("betscout.paper_trade._fetch_sofascore_tennis_odds", return_value={
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



















