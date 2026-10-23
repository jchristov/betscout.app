import sqlite3
from pathlib import Path

from collections import deque
from sportdata_model.dashboard import generate_dashboard_html
from sportdata_model.decision_signal import (
    NewsSignal,
    extract_team_news_text,
    record_distillation_pair,
    score_match_news,
)
from sportdata_model.paper_trade import (
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
    from sportdata_model.decision_signal import split_match_text_by_team
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
    conn.executescript("CREATE TABLE matches (id TEXT);" + PAPER_SCHEMA)
    conn.commit()
    conn.close()
    rec_json = tmp_path / "rec.json"
    rec_json.write_text(
        '{"generated_at": "2026-10-22T06:00:00Z", '
        '"qualifying_picks": ['
        '  {"league": "ita.1", "home": "Udinese", "away": "AC Milan", "side": "A", "tier": "top_10pct", "action": "PAPER_BET", "kickoff": "2026-10-25T19:45Z", "score": 0.33, "p_mkt": 0.57, "p_model": 0.61, "ev_pct": 1.2, "quarter_kelly_pct": 0.46, "best_odds": 1.65, "primary_odds": 1.65, "synthetic_dc_odds": 1.15, "factors_tanh_z": {}}'
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
    from sportdata_model import load_dotenv
    from sportdata_model.telegram_bot import (
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

    d_msg = format_discord_digest(_json.loads(rec_json.read_text()), min_odds=1.10)
    assert "**SPORTDATA QUANT DESK" in d_msg and "Fritz" in d_msg and "`2026-10-22 15:30 CEST`" in d_msg
    d_res = send_discord_message(d_msg, dry_run=True, env_path=env_file)
    assert d_res["ok"] is True and d_res["dry_run"] is True and d_res["configured"] is True

    # 5. Exact Score & Set-Score Engine unit test
    from sportdata_model.exact_score import predict_soccer_exact_scores, predict_tennis_set_scores

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
    from sportdata_model.paper_trade import _check_exact_score_hit, build_recommended_2leg_doubles
    from sportdata_model.telegram_bot import notify_new_settlements_to_discord

    assert _check_exact_score_hit("2:0 (14.0%) | Cluster 2:0 / 1:0 / 2:1 (38.0%)", "2-0") == 1
    assert _check_exact_score_hit("Sets 0:2 (60.0%, Fair 1.67)", "0-2 (4-6, 1-6)") == 1
    assert _check_exact_score_hit("Sets 0:2 (60.0%, Fair 1.67)", "1-2 (6-4, 2-6, 4-6)") == 0

    doubles = build_recommended_2leg_doubles(
        [{"league": "ita.1", "home": "Udinese", "away": "AC Milan", "side": "A", "action": "PAPER_BET", "best_odds": 1.65, "p_model": 0.64, "kickoff": "2026-10-25T19:45Z"}],
        [{"tour": "ATP", "player_1": "Herbert", "player_2": "Fritz", "pick": "Fritz", "win_prob": 0.82, "best_odds": 1.26, "kickoff": "2026-10-25T13:30Z"}],
        [],
    )
    assert len(doubles) == 1 and round(doubles[0]["combined_odds"], 2) == round(1.65 * 1.26, 2)

    notif_res = notify_new_settlements_to_discord(db, dry_run=True)
    assert notif_res["ok"] is True


