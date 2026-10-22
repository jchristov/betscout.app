"""Multi-factor invariant edge discovery for soccer and game-dominance surface modeling for tennis."""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .elo import Elo

CONFIRM_FROM = "2025-07-01"
FRESH_FROM = "2026-08-01"
BIG5_LEAGUES = ("eng.1", "esp.1", "ger.1", "ita.1", "fra.1")
ALL_SOCCER_LEAGUES = ("eng.1", "esp.1", "ger.1", "ita.1", "fra.1", "aut.1")


def settle_asian_total(tot_goals: float, line: float, odds: float, side: str) -> float:
    """Exact Asian Over/Under unit PnL settlement (handles .0 pushes and .25/.75 half-win/half-loss)."""
    diff = (tot_goals - line) if side == "OVER" else (line - tot_goals)
    if diff >= 0.5:
        return odds - 1.0
    if abs(diff - 0.25) < 1e-6:
        return 0.5 * (odds - 1.0)
    if abs(diff) < 1e-6:
        return 0.0
    if abs(diff + 0.25) < 1e-6:
        return -0.5
    return -1.0


def build_soccer_feature_rows(db_path: Path, leagues: tuple[str, ...] = ALL_SOCCER_LEAGUES) -> list[dict[str, Any]]:
    """Build point-in-time soccer records with opponent-adjusted boxscore, H2H, and multi-book features."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(leagues))
    rows = [
        dict(r)
        for r in conn.execute(
            f"""
            SELECT m.*,
                   d.open_home, d.open_draw, d.open_away,
                   d.close_home, d.close_draw, d.close_away,
                   d.best_home, d.best_draw, d.best_away,
                   d.cons_home, d.cons_draw, d.cons_away, d.num_books,
                   d.open_line, d.open_over, d.open_under,
                   d.close_line, d.close_over, d.close_under,
                   d.best_over, d.best_under, d.cons_over,
                   d.home_sot, d.away_sot, d.home_shots, d.away_shots,
                   d.home_corners, d.away_corners, d.home_poss, d.away_poss,
                   d.home_fouls, d.away_fouls, d.home_yellow, d.away_yellow,
                   d.home_red, d.away_red, d.home_pen_goals, d.away_pen_goals,
                   d.ht_home, d.ht_away
            FROM matches m
            JOIN match_details d ON m.league = d.league AND m.event_id = d.event_id
            WHERE m.sport = 'soccer' AND m.outcome IS NOT NULL AND m.home_score IS NOT NULL
                  AND m.league IN ({placeholders})
            ORDER BY m.kickoff
            """,
            leagues,
        ).fetchall()
    ]
    conn.close()

    elo_g: dict[str, Elo] = {}
    elo_s: dict[str, Elo] = {}
    hist: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=6))
    h2h: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0.0, 0, 0.0, 0])

    for r in rows:
        lg = r["league"]
        eg = elo_g.setdefault(lg, Elo(k=20, home_adv=55))
        es = elo_s.setdefault(lg, Elo(k=20, home_adv=55))
        hk, ak = (lg, r["home"]), (lg, r["away"])

        r["elo_g_d"] = (eg.ratings[r["home"]] - eg.ratings[r["away"]]) / 400.0
        r["elo_s_d"] = (es.ratings[r["home"]] - es.ratings[r["away"]]) / 400.0

        pair = (lg, min(r["home"], r["away"]), max(r["home"], r["away"]))
        pts_p, n_p, g_p, dr_p = h2h[pair]
        r["h2h_n"] = n_p
        r["h2h_h"] = ((pts_p + 1.0) / (n_p + 2.0)) if r["home"] < r["away"] else (((n_p - pts_p) + 1.0) / (n_p + 2.0))
        r["h2h_draw_rate"] = (dr_p + 0.5) / (n_p + 2.0)

        oh, oa = hist[hk], hist[ak]
        if len(oh) >= 4 and len(oa) >= 4 and r["odds_home"]:
            r["ready"] = True
            for k_stat in ("s_gd", "sot_d", "poss", "fouls", "draw"):
                r[f"h_{k_stat}"] = float(np.mean([x[k_stat] for x in oh]))
                r[f"a_{k_stat}"] = float(np.mean([x[k_stat] for x in oa]))
                r[f"d_{k_stat}"] = r[f"h_{k_stat}"] - r[f"a_{k_stat}"]
        else:
            r["ready"] = False

        sc = {"H": 1.0, "D": 0.5, "A": 0.0}[r["outcome"]]
        eg.update(r["home"], r["away"], sc)
        hs, as_ = r["home_score"], r["away_score"]
        gd = hs - as_
        if r["odds_home"]:
            inv = [1.0 / r["odds_home"], 1.0 / r["odds_draw"], 1.0 / r["odds_away"]]
            s = sum(inv)
            pdiff = (inv[0] - inv[2]) / s
            s_gd = gd - 2.59 * pdiff
        else:
            s_gd = 0.0

        if r["home_sot"] is not None and r["away_sot"] is not None:
            sot_d = r["home_sot"] - r["away_sot"]
            sh_d = (r["home_shots"] or 0) - (r["away_shots"] or 0)
            co_d = (r["home_corners"] or 0) - (r["away_corners"] or 0)
            xgd = 0.25 * sot_d + 0.03 * sh_d + 0.025 * co_d
            es.update(r["home"], r["away"], 1.0 / (1.0 + math.exp(-1.1 * xgd)))
        else:
            sot_d = 0.0
            es.update(r["home"], r["away"], sc)

        hist[hk].append({
            "s_gd": s_gd,
            "sot_d": sot_d,
            "poss": (r["home_poss"] or 50.0) - 50.0,
            "fouls": r["home_fouls"] or 11.0,
            "draw": 1.0 if gd == 0 else 0.0,
        })
        hist[ak].append({
            "s_gd": -s_gd,
            "sot_d": -sot_d,
            "poss": (r["away_poss"] or 50.0) - 50.0,
            "fouls": r["away_fouls"] or 11.0,
            "draw": 1.0 if gd == 0 else 0.0,
        })
        h2h[pair][0] += sc if r["home"] < r["away"] else (1.0 - sc)
        h2h[pair][1] += 1
        h2h[pair][2] += hs + as_
        h2h[pair][3] += 1 if gd == 0 else 0

    return [r for r in rows if r["ready"]]


def evaluate_invariant_soccer_composite(db_path: Path, leagues: tuple[str, ...] = BIG5_LEAGUES) -> dict[str, Any]:
    """Evaluate the 7-Factor Orthogonal Invariant Composite (tanh(Z)) with strict Discovery standardization."""
    ready = build_soccer_feature_rows(db_path, leagues=leagues)
    samples: list[dict[str, Any]] = []
    for idx_m, r in enumerate(ready):
        inv = [1.0 / r["odds_home"], 1.0 / r["odds_draw"], 1.0 / r["odds_away"]]
        s = sum(inv)
        ph, _, pa = inv[0] / s, inv[1] / s, inv[2] / s
        best_h = r["best_home"] or r["odds_home"]
        best_a = r["best_away"] or r["odds_away"]
        best_d = r["best_draw"] or r["odds_draw"]
        vig_neg = 1.0 - (1.0 / best_h + 1.0 / best_d + 1.0 / best_a)
        for side in ("H", "A"):
            sgn = 1.0 if side == "H" else -1.0
            o_bst = best_h if side == "H" else best_a
            o_pri = r["odds_home"] if side == "H" else r["odds_away"]
            if not (1.35 <= o_bst <= 3.40):
                continue
            p_mkt = ph if side == "H" else pa
            sot_d = sgn * r["d_sot_d"]
            poss_d = sgn * r["d_poss"]
            s_gd_neg = max(0.0, -sgn * r["d_s_gd"])
            dom_rebound = (max(0.0, sot_d) + max(0.0, poss_d / 3.0)) * s_gd_neg
            discipline = -sgn * r["d_fouls"]
            h2h_adv = sgn * (r["h2h_h"] - 0.5) - 0.5 * r["h2h_draw_rate"]
            recent_draws = r["h_draw"] if side == "H" else r["a_draw"]
            won = 1.0 if r["outcome"] == side else 0.0
            samples.append({
                "match_idx": idx_m,
                "kickoff": r["kickoff"],
                "year": r["kickoff"][:4],
                "league": r["league"],
                "side": side,
                "o_bst": o_bst,
                "o_pri": o_pri,
                "p_mkt": p_mkt,
                "won": won,
                "pnl_bst": (o_bst - 1.0) if won else -1.0,
                "pnl_pri": (o_pri - 1.0) if won else -1.0,
                "feats": [p_mkt, vig_neg, sot_d, discipline, h2h_adv, dom_rebound, recent_draws],
            })

    disc = [x for x in samples if x["kickoff"] < CONFIRM_FROM]
    scaler = StandardScaler().fit(np.array([x["feats"] for x in disc]))
    for x in samples:
        z = scaler.transform([x["feats"]])[0]
        x["score"] = float(np.tanh(z).mean())

    # Enforce at most 1 pick per match
    by_match: dict[int, dict[str, Any]] = {}
    for x in samples:
        mid = x["match_idx"]
        if mid not in by_match or x["score"] > by_match[mid]["score"]:
            by_match[mid] = x
    unique_samples = [by_match[k] for k in sorted(by_match)]

    summary: dict[str, Any] = {}
    for q_pct in (85, 90, 92):
        thr = float(np.percentile([x["score"] for x in disc], q_pct))
        picks = [x for x in unique_samples if x["score"] >= thr]
        d_sub = [x for x in picks if x["kickoff"] < CONFIRM_FROM]
        c_sub = [x for x in picks if CONFIRM_FROM <= x["kickoff"] < FRESH_FROM]
        f_sub = [x for x in picks if x["kickoff"] >= FRESH_FROM]
        p_sub = [x for x in picks if x["kickoff"] >= CONFIRM_FROM]

        bp = np.array([x["pnl_bst"] for x in p_sub])
        rng = np.random.default_rng(0)
        boots = bp[rng.integers(0, len(bp), size=(4000, len(bp)))].mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        p_val = float((boots <= 0).mean())

        summary[f"top_{100 - q_pct}pct"] = {
            "disc_roi": float(np.mean([x["pnl_bst"] for x in d_sub])),
            "disc_n": len(d_sub),
            "conf_roi": float(np.mean([x["pnl_bst"] for x in c_sub])),
            "conf_n": len(c_sub),
            "fresh_roi": float(np.mean([x["pnl_bst"] for x in f_sub])),
            "fresh_n": len(f_sub),
            "post_roi_best": float(bp.mean()),
            "post_roi_pri": float(np.mean([x["pnl_pri"] for x in p_sub])),
            "post_ci": (float(lo), float(hi)),
            "post_p": p_val,
            "all_roi_best": float(np.mean([x["pnl_bst"] for x in picks])),
            "all_n": len(picks),
        }
    return summary


def evaluate_tennis_surface_game_model(db_path: Path) -> dict[str, dict[str, float]]:
    """Out-of-sample evaluation of the 7-feature Surface + Game-Dominance Tennis model on ATP & WTA."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT m.*, d.surface, d.is_major, d.round_name, d.home_games, d.away_games
            FROM matches m
            LEFT JOIN match_details d ON m.league = d.league AND m.event_id = d.event_id
            WHERE m.sport = 'tennis' AND m.outcome IS NOT NULL
            ORDER BY m.kickoff
            """
        ).fetchall()
    ]
    conn.close()

    elo_all: dict[str, Elo] = {}
    elo_surf: dict[tuple[str, str], Elo] = {}
    elo_games: dict[str, Elo] = {}
    game_hist: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=10))
    last_match: dict[tuple[str, str], tuple[datetime, str, float]] = {}
    h2h: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0.0, 0])
    by_tour: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for r in rows:
        lg = r["league"]
        surf = r["surface"] or "hard"
        dt = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
        ea = elo_all.setdefault(lg, Elo(k=28, home_adv=0.0))
        es = elo_surf.setdefault((lg, surf), Elo(k=28, home_adv=0.0))
        eg = elo_games.setdefault(lg, Elo(k=28, home_adv=0.0))
        h, a = r["home"], r["away"]
        hk, ak = (lg, h), (lg, a)

        d_elo_all = (ea.ratings[h] - ea.ratings[a]) / 400.0
        d_elo_surf = (es.ratings[h] - es.ratings[a]) / 400.0
        d_elo_games = (eg.ratings[h] - eg.ratings[a]) / 400.0
        gh, ga = game_hist[hk], game_hist[ak]
        d_game_pct = (float(np.mean(gh)) if len(gh) >= 3 else 0.5) - (float(np.mean(ga)) if len(ga) >= 3 else 0.5)

        def _tf(k: tuple[str, str]) -> tuple[float, float]:
            if k not in last_match:
                return 0.0, 0.0
            p_dt, p_surf, p_gms = last_match[k]
            days = (dt - p_dt).total_seconds() / 86400.0
            return (1.0 if (days <= 12.0 and p_surf != surf) else 0.0), ((p_gms / 30.0) if days <= 2.0 else 0.0)

        th, fh = _tf(hk)
        ta, fa = _tf(ak)
        pair = (lg, min(h, a), max(h, a))
        pts_p, n_p = h2h[pair]
        h2h_p = ((pts_p + 1.0) / (n_p + 2.0)) if h < a else (((n_p - pts_p) + 1.0) / (n_p + 2.0))

        won_h = 1 if r["outcome"] == "H" else 0
        by_tour[lg].append({
            "y": won_h,
            "x_base": [d_elo_all],
            "x_rich": [d_elo_all, d_elo_surf, d_elo_games, d_game_pct, ta - th, fa - fh, h2h_p - 0.5],
        })

        ea.update(h, a, float(won_h))
        es.update(h, a, float(won_h))
        hg, ag = r["home_games"], r["away_games"]
        if hg is not None and ag is not None and (hg + ag) > 0:
            g_share = hg / (hg + ag)
            eg.update(h, a, 1.0 / (1.0 + math.exp(-6.0 * (g_share - 0.5))))
            game_hist[hk].append(g_share)
            game_hist[ak].append(1.0 - g_share)
            tot_gms = hg + ag
        else:
            eg.update(h, a, float(won_h))
            tot_gms = 20.0
        last_match[hk] = (dt, surf, tot_gms)
        last_match[ak] = (dt, surf, tot_gms)
        h2h[pair][0] += float(won_h) if h < a else float(1 - won_h)
        h2h[pair][1] += 1

    out: dict[str, dict[str, float]] = {}
    for lg, sub in sorted(by_tour.items()):
        cut = len(sub) // 2
        tr, te = sub[:cut], sub[cut:]
        y_tr = np.array([x["y"] for x in tr])
        y_te = np.array([x["y"] for x in te])
        m_b = LogisticRegression(C=1.0).fit(np.array([x["x_base"] for x in tr]), y_tr)
        p_b = np.clip(m_b.predict_proba(np.array([x["x_base"] for x in te]))[:, 1], 1e-9, 1 - 1e-9)
        m_r = LogisticRegression(C=1.0).fit(np.array([x["x_rich"] for x in tr]), y_tr)
        p_r = np.clip(m_r.predict_proba(np.array([x["x_rich"] for x in te]))[:, 1], 1e-9, 1 - 1e-9)
        hc = np.abs(p_r - 0.5) >= 0.20
        out[lg] = {
            "n_test": float(len(te)),
            "base_log_loss": float(-np.mean(y_te * np.log(p_b) + (1 - y_te) * np.log(1 - p_b))),
            "rich_log_loss": float(-np.mean(y_te * np.log(p_r) + (1 - y_te) * np.log(1 - p_r))),
            "base_acc": float(np.mean((p_b >= 0.5) == y_te)),
            "rich_acc": float(np.mean((p_r >= 0.5) == y_te)),
            "high_conf_acc": float(np.mean((p_r[hc] >= 0.5) == y_te[hc])) if hc.any() else 0.0,
            "high_conf_n": float(hc.sum()),
        }
    return out


def evaluate_us_major_sports_composite(db_path: Path) -> dict[str, dict[str, float]]:
    """Out-of-sample evaluation of the 7-Factor Boxscore + Rest/B2B + Rebound Composite on NBA, NHL, NFL & MLB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT m.*,
                   d.open_home, d.open_away, d.close_home, d.close_away,
                   d.best_home, d.best_away,
                   d.home_sot, d.away_sot, d.home_shots, d.away_shots,
                   d.home_corners, d.away_corners, d.home_poss, d.away_poss,
                   d.home_fouls, d.away_fouls
            FROM matches m
            JOIN match_details d ON m.league = d.league AND m.event_id = d.event_id
            WHERE m.sport IN ('basketball', 'hockey', 'football', 'baseball')
                  AND m.outcome IS NOT NULL AND m.home_score IS NOT NULL
            ORDER BY m.kickoff
            """
        ).fetchall()
    ]
    conn.close()

    hist: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=6))
    last_dt: dict[tuple[str, str], datetime] = {}
    margin_scale = {"nba": 12.0, "nhl": 2.5, "nfl": 14.0, "mlb": 3.5}
    samples_by_lg: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for idx_m, r in enumerate(rows):
        lg = r["league"]
        hk, ak = (lg, r["home"]), (lg, r["away"])
        dt = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
        rh = min((dt - last_dt[hk]).days, 10) if hk in last_dt else 4
        ra = min((dt - last_dt[ak]).days, 10) if ak in last_dt else 4
        b2b_adv = (1.0 if ra <= 1 else 0.0) - (1.0 if rh <= 1 else 0.0)
        rest_adv = (rh - ra) / 3.0 + b2b_adv

        oh, oa = hist[hk], hist[ak]
        if len(oh) >= 3 and len(oa) >= 3 and r["odds_home"] and r["odds_away"]:
            inv_h, inv_a = 1.0 / r["odds_home"], 1.0 / r["odds_away"]
            ph = inv_h / (inv_h + inv_a)
            pa = 1.0 - ph
            d_sot = float(np.mean([x["sot_d"] for x in oh]) - np.mean([x["sot_d"] for x in oa]))
            d_sh = float(np.mean([x["sh_d"] for x in oh]) - np.mean([x["sh_d"] for x in oa]))
            d_co = float(np.mean([x["co_d"] for x in oh]) - np.mean([x["co_d"] for x in oa]))
            d_fo = float(np.mean([x["fo_d"] for x in oh]) - np.mean([x["fo_d"] for x in oa]))
            d_sm = float(np.mean([x["s_m"] for x in oh]) - np.mean([x["s_m"] for x in oa]))
            for side in ("H", "A"):
                sgn = 1.0 if side == "H" else -1.0
                o_bst = (r["best_home"] or r["odds_home"]) if side == "H" else (r["best_away"] or r["odds_away"])
                if not (1.25 <= o_bst <= 2.90):
                    continue
                p_mkt = ph if side == "H" else pa
                sot_f = sgn * d_sot
                vol_f = sgn * d_sh
                cre_f = sgn * d_co
                disc_f = -sgn * d_fo
                r_adv = sgn * rest_adv
                sm_neg = max(0.0, -sgn * d_sm)
                rebound_f = max(0.0, sot_f) * sm_neg
                won = 1.0 if r["outcome"] == side else 0.0
                samples_by_lg[lg].append({
                    "match_idx": idx_m,
                    "o_bst": o_bst,
                    "p_mkt": p_mkt,
                    "won": won,
                    "pnl": (o_bst - 1.0) if won else -1.0,
                    "feats": [p_mkt, sot_f, vol_f, cre_f, disc_f, r_adv, rebound_f],
                })

        last_dt[hk] = last_dt[ak] = dt
        if r["home_sot"] is not None and r["away_sot"] is not None:
            m_act = float(r["home_score"] - r["away_score"]) / margin_scale.get(lg, 5.0)
            if r["odds_home"] and r["odds_away"]:
                ih, ia = 1.0 / r["odds_home"], 1.0 / r["odds_away"]
                pdiff = (ih - ia) / (ih + ia)
            else:
                pdiff = 0.0
            s_m = m_act - pdiff
            sot_d = float(r["home_sot"] - r["away_sot"])
            sh_d = float((r["home_shots"] or 0) - (r["away_shots"] or 0))
            co_d = float((r["home_corners"] or 0) - (r["away_corners"] or 0))
            fo_d = float((r["home_fouls"] or 0) - (r["away_fouls"] or 0))
            hist[hk].append({"sot_d": sot_d, "sh_d": sh_d, "co_d": co_d, "fo_d": fo_d, "s_m": s_m})
            hist[ak].append({"sot_d": -sot_d, "sh_d": -sh_d, "co_d": -co_d, "fo_d": -fo_d, "s_m": -s_m})

    out: dict[str, dict[str, float]] = {}
    all_p15: list[dict[str, Any]] = []
    for lg, samps in sorted(samples_by_lg.items()):
        cut = len(samps) // 2
        tr, te = samps[:cut], samps[cut:]
        scaler = StandardScaler().fit(np.array([x["feats"] for x in tr]))
        for x in samps:
            x["score"] = float(np.tanh(scaler.transform([x["feats"]])[0]).mean())
        by_m: dict[int, dict[str, Any]] = {}
        for x in te:
            mid = x["match_idx"]
            if mid not in by_m or x["score"] > by_m[mid]["score"]:
                by_m[mid] = x
        uniq_te = [by_m[k] for k in sorted(by_m)]
        thr_85 = float(np.percentile([x["score"] for x in tr], 85))
        p15 = [x for x in uniq_te if x["score"] >= thr_85]
        all_p15.extend(p15)
        if p15:
            out[lg] = {
                "n_test_picks": float(len(p15)),
                "roi_top15": float(np.mean([x["pnl"] for x in p15])),
                "hit_rate": float(np.mean([x["won"] for x in p15])),
                "mkt_implied": float(np.mean([x["p_mkt"] for x in p15])),
            }
    if all_p15:
        out["POOLED"] = {
            "n_test_picks": float(len(all_p15)),
            "roi_top15": float(np.mean([x["pnl"] for x in all_p15])),
            "hit_rate": float(np.mean([x["won"] for x in all_p15])),
            "mkt_implied": float(np.mean([x["p_mkt"] for x in all_p15])),
        }
    return out
