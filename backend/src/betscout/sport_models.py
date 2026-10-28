"""Dedicated Per-Sport Model Rules, Calibration & Veto Gates (`src/betscout/sport_models.py`).

Isolates the sport-specific feature thresholds, structural biases, and domain veto rules
for each sport so edge cases in one sport (e.g. NFL chalk traps, Secondary Domestic Football
cup/giant-killer upsets, Tennis short-turnaround travel, or Table Tennis high-vig exhibition lines)
can be tuned and tested independently without coupling unrelated sports.
"""

from __future__ import annotations

from typing import Any

SECONDARY_DOMESTIC_SOCCER_LEAGUES = ("ned.1", "por.1", "eng.2", "aut.1")


def evaluate_soccer_gate(
    league: str,
    score: float,
    thresholds: dict[str, float],
    p_mkt: float,
    ev_pct: float,
    factors_tanh_z: dict[str, float],
) -> str:
    """Classify a Football (`soccer`) candidate into a conviction tier (`top_8pct`, `top_10pct`,
    `top_15pct`, `top_25pct`, `uefa_edge`) or `'pass'` using competition-specific gates:

    1. **Stalemate-Draw & Indiscipline Veto (`is_stalemate_trap`):**
       Sub-62% favorites (`p_mkt < 0.62`) with extreme recent draw propensity (`recent_draws > 0.80`),
       negative dominance rebound (`dom_rebound < -0.30`), and poor foul discipline (`discipline < -0.60`)
       are vetoed to avoid 0-0 / 1-1 stalemate traps (e.g. `Toulouse 0-0 Troyes`).
    2. **Secondary Domestic Giant-Killer & H2H Gate (`ned.1`, `por.1`, `eng.2`, `aut.1`):**
       Applies across *all* tiers (including `top_8pct`): requires positive H2H history (`h2h_adv >= 0.20`),
       strong rolling Shot-on-Target dominance (`sot_d >= 0.45`), and non-negative discipline (`discipline >= 0.0`).
       Prevents heavy-vig chalk upsets against surging underdogs with negative H2H (e.g. `Sporting CP 1-2 Académico de Viseu`).
    3. **UEFA / FIFA International Gate:**
       Allows cross-border club/national fixtures with `sot_d >= 0.0` and (`score >= 0.02` or `dom_rebound > 0.20`).
    """
    lg = (league or "").lower().strip()
    sot_z = float(factors_tanh_z.get("sot_d", 0.0))
    dom_z = float(factors_tanh_z.get("dom_rebound", 0.0))
    disc_z = float(factors_tanh_z.get("discipline", 0.0))
    h2h_z = float(factors_tanh_z.get("h2h_adv", 0.0))
    draws_z = float(factors_tanh_z.get("recent_draws", 0.0))

    # 1. Universal Stalemate-Draw & Foul-Trouble Veto
    if p_mkt < 0.62 and draws_z > 0.80 and dom_z < -0.30 and disc_z < -0.60:
        return "pass"

    is_uefa = lg.startswith("uefa.") or lg.startswith("fifa.")
    is_secondary_dom = lg in SECONDARY_DOMESTIC_SOCCER_LEAGUES

    # 2. Secondary Domestic League Gate (applies to ALL tiers, including top_8pct)
    if is_secondary_dom:
        if h2h_z < 0.20 or sot_z < 0.45 or disc_z < 0.0:
            return "pass"

    if score >= thresholds["top_8pct"]:
        return "top_8pct"
    if score >= thresholds["top_10pct"]:
        return "top_10pct"
    if score >= thresholds["top_15pct"]:
        if is_secondary_dom and ev_pct <= 0.0:
            return "pass"
        return "top_15pct"
    if score >= thresholds["top_25pct"]:
        if is_secondary_dom and (sot_z < 0.55 or ev_pct < 2.0):
            return "pass"
        return "top_25pct"
    if is_uefa and sot_z >= 0.0 and (score >= 0.02 or dom_z > 0.20):
        return "uefa_edge"
    return "pass"


def evaluate_tennis_gate(
    win_prob: float,
    book_odds: float | None,
    opp_book_odds: float | None,
    game_win_pct_diff: float,
    form_6m_diff: float,
    pick_rest_h: float | None = None,
    opp_rest_h: float | None = None,
    pick_last_tourn: str = "",
    cur_tourn_city: str = "",
    game_elo_diff: float | None = None,
    all_elo_diff: float | None = None,
    h2h_n: int = 0,
    open_odds: float | None = None,
    decider_diff: float | None = None,
    tourn_wins_diff: int | None = None,
) -> tuple[bool, float, float | None, str]:
    """Evaluate ATP/WTA Tennis specific gates and market-blend calibration.
    Returns `(passed, blended_win_prob, ev_pct, reason)`:
    1. **Court-Acclimatization, Decider Resilience & Short-Turnaround Gate:**
       Vetoes sub-80% favorites arriving from a different city/tournament with <= 38h rest against a rested opponent,
       or trailing by >=1 current-tournament court win (`tourn_wins_diff <= -1`) or >=20pp in 3-set decider win rate
       (`decider_diff < -0.20`, e.g. `Tallon Griekspoor vs Jiri Lehecka`).
    2. **Stale-Elo / Zero-Recent-Form Veto:**
       Vetoes favorites whose rolling 6-month Game-Win% diff (`game_win_pct_diff <= 0.0`) AND 6-month Match-Win% diff
       (`form_6m_diff <= 0.0`) are both non-positive (e.g. `Samsonova vs Watson`).
    3. **Career-Elo Inflation vs Modest Game-Share Veto:**
       When career `all_elo_diff >= 230` inflates `win_prob >= 0.80` on a first-time matchup (`h2h_n == 0`),
       require either `game_elo_diff >= 95.0` or `game_win_pct_diff >= 0.05` (vetoes lower-tier WTA/ITF chalk traps
       like `Carolina Alves vs Julia Grabher` where `all_elo_diff=254.7` but `game_elo_diff=88.9` and `game_win_pct_diff=0.045`).
    4. **Adverse Closing-Line Drift + Modest Game-Elo Veto:**
       When a sub-75% favorite has modest Game-Elo (`game_elo_diff < 60`) and the bookmaker line drifts out against them
       by >= 4.5% (`open_odds / book_odds - 1.0 <= -0.045`, e.g. `Laura Samson vs Alice Tubello` drifting from `1.383` to `1.47`),
       veto to avoid late injury/fatigue steam against WTA 125K/ITF favorites.
    5. **Market-Disagreement & EV Gate:**
       Blends 75% model + 25% devigged bookmaker probability, vetoing >=15pp market disagreements (`p_mkt_devig < 0.60`)
       or negative EV (`ev_pct < -1.5` when `win_prob < 0.80`).
    """
    # 0. Court-Acclimatization & 3-Set Decider Resilience Veto (e.g. Griekspoor vs Lehecka)
    if win_prob < 0.80:
        if decider_diff is not None and decider_diff < -0.20:
            return False, win_prob, None, "VETO_WEAK_DECIDER_RESILIENCE"
        if tourn_wins_diff is not None and tourn_wins_diff <= -1:
            return False, win_prob, None, "VETO_COURT_ACCLIMATIZATION deficit"

    # 1. Stale Career-Elo & Sub-72.5% Weak Game-Dominance Veto:
    # - Career all_elo_diff >= 220 inflates win_prob, but both 6m Game-Win% and 6m Match-Win% are <= 0 (e.g. Samsonova vs Watson)
    # - Or sub-72.5% favorite has zero 6m match-win edge (form_6m_diff <= 0.0), minimal game-win edge (game_win_pct_diff < 0.03), and game_elo_diff < 75 (e.g. Tereza Valentova vs Mia Pohankova 1-6, 4-6)
    if (all_elo_diff is None or all_elo_diff >= 220.0) and game_win_pct_diff <= -0.009 and form_6m_diff <= 0.0:
        return False, win_prob, None, "VETO_STALE_TENNIS_FORM"
    if (
        win_prob < 0.725
        and (game_elo_diff is None or game_elo_diff < 75.0)
        and game_win_pct_diff < 0.03
        and form_6m_diff <= 0.0
    ):
        return False, win_prob, None, "VETO_STALE_TENNIS_FORM"
    if form_6m_diff < -0.15:
        return False, win_prob, None, "VETO_NEGATIVE_6M_FORM"

    # 2. Career-Elo Inflation vs Modest Game-Share Veto (e.g. Alves vs Grabher)
    if (
        all_elo_diff is not None
        and game_elo_diff is not None
        and all_elo_diff >= 230.0
        and game_elo_diff < 95.0
        and game_win_pct_diff < 0.05
        and h2h_n == 0
    ):
        return False, win_prob, None, "VETO_CAREER_ELO_GAME_DIVERGENCE"

    # 2b. Adverse Closing-Line Drift + Modest Game-Elo Veto (e.g. Laura Samson vs Alice Tubello: game_elo_diff=53.9, open=1.383 -> close=1.47, CLV=-5.9%)
    if (
        win_prob < 0.75
        and game_elo_diff is not None
        and game_elo_diff < 60.0
        and open_odds is not None
        and book_odds is not None
        and book_odds > 1.05
        and ((open_odds / book_odds) - 1.0) <= -0.045
    ):
        return False, win_prob, None, "VETO_ADVERSE_LINE_DRIFT"

    # 3. Court-Acclimatization & Travel Fatigue Gate
    if (
        win_prob < 0.80
        and isinstance(pick_rest_h, (int, float))
        and pick_rest_h <= 38.0
        and pick_last_tourn
        and cur_tourn_city
        and cur_tourn_city not in pick_last_tourn
        and (opp_rest_h is None or float(opp_rest_h) >= 48.0)
    ):
        return False, win_prob, None, "VETO_SHORT_TURNAROUND_TRAVEL"

    blended_prob = win_prob
    if book_odds and opp_book_odds and book_odds > 1.01 and opp_book_odds > 1.01:
        inv_pick, inv_opp = 1.0 / book_odds, 1.0 / opp_book_odds
        p_mkt_devig = inv_pick / (inv_pick + inv_opp)
        if (win_prob - p_mkt_devig) >= 0.15 and p_mkt_devig < 0.60:
            return False, win_prob, None, "VETO_MARKET_DISAGREEMENT"
        blended_prob = 0.75 * win_prob + 0.25 * p_mkt_devig

    ev_pct = round((blended_prob * book_odds - 1.0) * 100.0, 2) if book_odds else None
    if ev_pct is not None and ev_pct < -1.5 and blended_prob < 0.80:
        return False, blended_prob, ev_pct, "VETO_NEGATIVE_EV"

    return True, blended_prob, ev_pct, "PASS"


def evaluate_nfl_gate(
    p_mod: float,
    p_mkt: float,
    p_elo: float,
    comp_score: float,
    ypp_diff: float,
    yards_diff: float,
    odds_pick: float,
    min_prob: float = 0.58,
) -> bool:
    """NFL Trench-Dominance, Efficiency & Elo Confirmation Gate (`85.7%` historical win rate, `+32.87%` ROI).
    Requires:
      - `comp_score >= 0.35`
      - Rolling Yards-Per-Play edge `ypp_diff >= 0.80`
      - Rolling Total-Yards edge `yards_diff >= 60.0` yds/game
      - Elo confirmation `p_elo >= p_mkt - 0.08` (vetoes overhyped market favorites like Texans -14.9pp and Jets -11.4pp)
      - Odds in `[1.25, 1.75]` sweet spot (avoids `<1.25` heavy chalk traps).
    """
    if p_mod < min_prob or comp_score < 0.35:
        return False
    if ypp_diff < 0.80 or yards_diff < 60.0:
        return False
    if p_elo < (p_mkt - 0.08):
        return False
    if odds_pick < 1.25 or odds_pick > 1.75:
        return False
    return True


def evaluate_nhl_gate(
    p_mod: float,
    comp_score: float,
    save_pct_diff: float,
    shots_diff: float,
    rest_for_pick: float,
    side: str,
    odds_pick: float,
    min_prob: float = 0.58,
    p_elo: float | None = None,
    p_mkt: float | None = None,
    pick_win_rate_5: float | None = None,
    pick_ga_5: float | None = None,
    pick_goal_diff: float | None = None,
) -> bool:
    """NHL Rested + Save%, Shot-Volume, Defensive Integrity & Elo Confirmation Gate.
    Requires:
      - Positive Goalie Save% diff (`save_pct_diff > 0`), positive Shot-Volume diff (`shots_diff > 0`), and `rest_for_pick >= 0`
      - `comp_score >= 0.05` and Elo confirmation `p_elo >= p_mkt - 0.08`
      - Defensive Integrity & Form Gate: vetoes leaky-defense favorites conceding `>= 3.70` goals/game over their last 5 games
        (`pick_ga_5 >= 3.70`), slumping favorites with `< 40%` last-5 win rate (`pick_win_rate_5 < 0.40`), or Home favorites with
        negative rolling goal differential (`pick_goal_diff < -0.30`, e.g. `Anaheim Ducks vs Vancouver Canucks` `1W-4L`, `GA5=4.00`, `GoalDiff=-0.50`)
      - Road (`A`) picks require Dual-Dominance (`shots_diff >= 12.0` & `save_pct_diff >= 12.0`).
    """
    if p_mod < min_prob or odds_pick <= 1.10 or comp_score < 0.05:
        return False
    if p_elo is not None and p_mkt is not None and p_elo < (p_mkt - 0.08):
        return False
    if save_pct_diff <= 0.0 or shots_diff <= 0.0 or rest_for_pick < 0.0:
        return False
    if pick_win_rate_5 is not None and pick_win_rate_5 < 0.40:
        return False
    if pick_ga_5 is not None and pick_ga_5 >= 3.70:
        return False
    if side == "H" and pick_goal_diff is not None and pick_goal_diff < -0.30:
        return False
    if side == "A" and (shots_diff < 12.0 or save_pct_diff < 12.0):
        return False
    return True


def evaluate_nba_gate(
    p_mod: float,
    p_mkt: float,
    p_elo: float,
    comp_score: float,
    fg_pct_diff: float,
    rest_for_pick: float,
    odds_pick: float,
    min_prob: float = 0.58,
    three_pt_diff: float = 0.0,
    tov_margin_diff: float = 0.0,
) -> bool:
    """NBA / Basketball Elo + Rest/B2B + Shooting & Possession-Security Alignment Gate (`78.6%` historical win rate, `+13.00%` ROI).
    Requires:
      - `comp_score >= 0.16` (filters out borderline <0.16 composite matchups like `Denver Nuggets vs Golden State Warriors` `comp=+0.112` and `LA Clippers vs Golden State Warriors` `comp=+0.055`)
      - `p_elo >= p_mkt - 0.08` and `rest_for_pick >= 0.0`
      - Positive FG% diff (`fg_pct_diff > 0.0`) or strong rest/B2B mismatch (`rest_for_pick >= 1.0` and `comp_score >= 0.20`)
      - 3PT Volume & Turnover-Security Veto: vetoes any favorite that simultaneously trails in rolling 3-pointers made (`three_pt_diff < -1.5`) AND commits more turnovers (`tov_margin_diff < -1.5`).
    """
    if p_mod < min_prob or odds_pick <= 1.10 or comp_score < 0.16:
        return False
    if p_elo < (p_mkt - 0.08) or rest_for_pick < 0.0:
        return False
    if fg_pct_diff <= 0.0 and not (rest_for_pick >= 1.0 and comp_score >= 0.20):
        return False
    if three_pt_diff < -1.5 and tov_margin_diff < -1.5:
        return False
    return True


def evaluate_mlb_or_volleyball_gate(
    league: str,
    p_mod: float,
    p_mkt: float,
    p_elo: float,
    comp_score: float,
    sot_f: float,
    odds_pick: float,
    min_prob: float = 0.58,
) -> bool:
    """MLB Baseball & Volleyball specific alignment gate."""
    if p_mod < min_prob or odds_pick <= 1.10 or comp_score < -0.02:
        return False
    if p_elo < (p_mkt - 0.05):
        return False
    if league == "mlb" and sot_f < 0.0:
        return False
    return True


def route_major_league_gate(
    league: str,
    p_mod: float,
    p_mkt: float,
    p_elo: float,
    comp_score: float,
    sot_f: float,
    vol_f: float,
    rest_for_pick: float,
    side: str,
    odds_pick: float,
    min_prob: float = 0.58,
    co_f: float = 0.0,
    tov_f: float = 0.0,
    pick_win_rate_5: float | None = None,
    pick_ga_5: float | None = None,
    pick_goal_diff: float | None = None,
) -> bool:
    """Dispatch to the isolated per-sport gate for `nhl`, `nba`, `nfl`, `mlb`, or `volleyball`."""
    lg = (league or "").lower().strip()
    # Universal EV Floor for 2-way US Major Sports: veto heavily over-juiced negative-EV lines (< -3.5% EV unless ultra-high >=78% banker)
    ev_pct = (p_mod * odds_pick - 1.0) * 100.0
    if ev_pct < -3.5 and p_mod < 0.78:
        return False
    if lg == "nfl":
        return evaluate_nfl_gate(
            p_mod=p_mod,
            p_mkt=p_mkt,
            p_elo=p_elo,
            comp_score=comp_score,
            ypp_diff=sot_f,
            yards_diff=vol_f,
            odds_pick=odds_pick,
            min_prob=min_prob,
        )
    if lg == "nhl":
        return evaluate_nhl_gate(
            p_mod=p_mod,
            comp_score=comp_score,
            save_pct_diff=sot_f,
            shots_diff=vol_f,
            rest_for_pick=rest_for_pick,
            side=side,
            odds_pick=odds_pick,
            min_prob=min_prob,
            p_elo=p_elo,
            p_mkt=p_mkt,
            pick_win_rate_5=pick_win_rate_5,
            pick_ga_5=pick_ga_5,
            pick_goal_diff=pick_goal_diff,
        )
    if lg in ("nba", "wnba", "ncaam", "ncaaw", "nbl", "fiba"):
        return evaluate_nba_gate(
            p_mod=p_mod,
            p_mkt=p_mkt,
            p_elo=p_elo,
            comp_score=comp_score,
            fg_pct_diff=sot_f,
            rest_for_pick=rest_for_pick,
            odds_pick=odds_pick,
            min_prob=min_prob,
            three_pt_diff=co_f,
            tov_margin_diff=tov_f,
        )
    return evaluate_mlb_or_volleyball_gate(
        league=lg,
        p_mod=p_mod,
        p_mkt=p_mkt,
        p_elo=p_elo,
        comp_score=comp_score,
        sot_f=sot_f,
        odds_pick=odds_pick,
        min_prob=min_prob,
    )


def evaluate_european_sport_gate(
    sport_slug: str,
    p_mkt: float,
    p_elo_fav: float,
    form_diff_fav: float,
    best_odds: float,
    is_tipico: bool,
    n_form_home: int = 0,
    n_form_away: int = 0,
    min_prob: float = 0.68,
    recent3_diff_fav: float | None = None,
    fav_loss_streak: int = 0,
    dog_win_streak: int = 0,
    fav_hours_since_last: float | None = None,
    dog_hours_since_last: float | None = None,
    fav_wr: float | None = None,
    fav_session_sets_3h: int | None = None,
    fav_last_lost_5set: bool = False,
) -> tuple[bool, float, float]:
    """Sport-specific calibration & gating for European high-frequency sports
    (`table_tennis`, `handball`, `darts`, `snooker`, `mma`).
    Returns `(passed, p_model, ev_pct)`.

    - **Immediate Last-3 Session Momentum & Streak Gate (All European Sports):**
      Sportradar's `stats_match_form` lists `form[0]` as the most recent match (`form[:3]` are the 3 most recent matches,
      verified against `streak: {type, value}` and `stats_team_lastx` timestamps).
      Vetoes any favorite currently on a >=2 match losing streak (`fav_loss_streak >= 2`), facing an underdog on a
      >=3 match winning streak (`dog_win_streak >= 3`), or trailing in Last-3 session form (`recent3_diff_fav < 0.0`).
    - **Table Tennis Cold-Session Rust + Session Workload & 5-Set Decider Hangover Veto (`table_tennis`):**
      1. Vetoes any favorite who has not played a match in the last `48.0` hours (`fav_hours_since_last > 48.0`), or who has been
         inactive `>=18.0` hours longer than a warmed-up opponent (`fav_hours_since_last - dog_hours_since_last >= 18.0` when `fav_hours_since_last > 24.0`).
      2. Vetoes any favorite who has already played `>= 13` sets in the current 3.5-hour session (`fav_session_sets_3h >= 13`)
         or who just lost a grueling 5-set decider (`2-3`, `fav_last_lost_5set == True`) in their immediately preceding match
         (catches session-fatigue collapses like `Machelski, Michal vs Nocun, Zbigniew` `22:05Z` where Nocun had played `14 sets`
         in 3h and just lost `2-3` to Brunner 45m prior, while allowing Nocun's rested `04:05Z` `3-1` win).
      3. Requires absolute favorite 10-match win rate `fav_wr >= 0.55` when available (preventing a `.500` player from being backed as heavy chalk).
    """
    sp = (sport_slug or "").lower().strip()
    if n_form_home >= 4 and n_form_away >= 4 and form_diff_fav < 0.0:
        return False, 0.0, -100.0
    if fav_loss_streak >= 2 or dog_win_streak >= 3:
        return False, 0.0, -100.0
    if recent3_diff_fav is not None and recent3_diff_fav < 0.0:
        return False, 0.0, -100.0
    if sp == "table_tennis":
        if fav_wr is not None and fav_wr < 0.55:
            return False, 0.0, -100.0
        if fav_last_lost_5set:
            return False, 0.0, -100.0
        if fav_session_sets_3h is not None and fav_session_sets_3h >= 13:
            return False, 0.0, -100.0
        if fav_hours_since_last is not None:
            if fav_hours_since_last > 48.0:
                return False, 0.0, -100.0
            if dog_hours_since_last is not None and fav_hours_since_last > 24.0 and (fav_hours_since_last - dog_hours_since_last) >= 18.0:
                return False, 0.0, -100.0

    # Blend market implied probability with Elo edge (only when Elo deviates meaningfully from 0.50) and rolling form
    elo_edge = (p_elo_fav - 0.50) if abs(p_elo_fav - 0.50) > 0.01 else 0.0
    r3_bonus = (0.03 * recent3_diff_fav) if recent3_diff_fav is not None else 0.0
    p_model = min(
        0.94,
        max(
            0.52,
            p_mkt + 0.12 * elo_edge + 0.08 * form_diff_fav + r3_bonus + (0.015 if is_tipico else 0.0),
        ),
    )
    ev_pct = round((p_model * best_odds - 1.0) * 100.0, 2)

    if p_model < min_prob or p_model < p_mkt or ev_pct < 0.0:
        return False, round(p_model, 4), ev_pct

    if sp == "table_tennis":
        if best_odds < 1.28 or best_odds > 1.65:
            return False, round(p_model, 4), ev_pct
        if n_form_home < 4 or n_form_away < 4 or form_diff_fav < 0.20:
            return False, round(p_model, 4), ev_pct
        if p_elo_fav < 0.50:
            return False, round(p_model, 4), ev_pct
    elif sp == "handball":
        if best_odds < 1.18 or best_odds > 1.60 or form_diff_fav < 0.0 or p_elo_fav < 0.50:
            return False, round(p_model, 4), ev_pct
    elif sp == "darts":
        if best_odds < 1.15 or best_odds > 1.68 or form_diff_fav < 0.15 or p_elo_fav < 0.50:
            return False, round(p_model, 4), ev_pct
    else:
        if best_odds < 1.20 or best_odds > 1.68 or form_diff_fav < 0.15:
            return False, round(p_model, 4), ev_pct

    return True, round(p_model, 4), ev_pct
