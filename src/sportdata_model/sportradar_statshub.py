"""Sportradar StatsHub (Tipico) live client for bookmaker odds (1X2, Correct Score 28-grid, Double Chance, Draw No Bet, Over/Under),
player injuries/suspensions (`stats_season_injuries`), team streaks (`stats_team_streaks`), and ATP/WTA surface win-loss records (`tennis_team_surfacestats`)."""

from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATSHUB_TIPICO_URL = "https://statshub.sportradar.com/tipico/en/"
STATSHUB_SPORTRADAR_URL = "https://statshub.sportradar.com/sportradar/en/"
DIRECT_STATS_FN_BASE_URL = "https://stats.fn.sportradar.com"
FISHNET_BASE_URL = "https://sh.fn.sportradar.com"

# Complete 56-Sport Catalog from Sportradar StatsHub (`config_sports/69/0` on /sportradar/en/ & `config_sports/67/0` on /tipico/en/)
SR_ALL_SPORTS_CATALOG: dict[int, str] = {
    1: "Soccer",
    5: "Tennis",
    4: "Ice Hockey",
    2: "Basketball",
    6: "Handball",
    23: "Volleyball",
    3: "Baseball",
    7: "Floorball",
    9: "Golf",
    12: "Rugby",
    13: "Aussie Rules",
    15: "Bandy",
    16: "American Football",
    17: "Cycling",
    18: "Specials",
    19: "Snooker",
    20: "Table Tennis",
    21: "Cricket",
    22: "Darts",
    24: "Field hockey",
    26: "Waterpolo",
    28: "Curling",
    29: "Futsal",
    31: "Badminton",
    34: "Beach Volley",
    36: "Athletics",
    37: "Squash",
    40: "Formula 1",
    43: "Alpine Skiing",
    44: "Biathlon",
    45: "Bobsleigh",
    46: "Cross-Country",
    47: "Nordic Combined",
    48: "Ski Jumping",
    49: "Snowboard",
    50: "Speed Skating",
    51: "Luge",
    52: "Swimming",
    54: "Softball",
    60: "Beach Soccer",
    61: "Pesapallo",
    71: "Padel",
    101: "Rally",
    117: "MMA",
    129: "Indy Racing",
    131: "Speedway",
    134: "ESport King of Glory",
    135: "Gaelic Football",
    137: "eSoccer",
    138: "Kabaddi",
    153: "eBasketball",
    155: "Basketball 3x3",
    188: "Touring Car Racing",
    190: "Motorcycle Racing",
    191: "Stock Car Racing",
    195: "eIce Hockey",
}

# Sportradar sportId mapping by slug/alias
SR_SPORT_IDS: dict[str, int] = {
    "soccer": 1,
    "football_soccer": 1,
    "basketball": 2,
    "baseball": 3,
    "hockey": 4,
    "ice_hockey": 4,
    "nhl": 4,
    "tennis": 5,
    "handball": 6,
    "floorball": 7,
    "golf": 9,
    "rugby": 12,
    "aussie_rules": 13,
    "bandy": 15,
    "football": 16,
    "american_football": 16,
    "nfl": 16,
    "cycling": 17,
    "specials": 18,
    "snooker": 19,
    "table_tennis": 20,
    "cricket": 21,
    "darts": 22,
    "volleyball": 23,
    "field_hockey": 24,
    "waterpolo": 26,
    "curling": 28,
    "futsal": 29,
    "badminton": 31,
    "beach_volley": 34,
    "athletics": 36,
    "squash": 37,
    "formula_1": 40,
    "f1": 40,
    "alpine_skiing": 43,
    "biathlon": 44,
    "bobsleigh": 45,
    "cross_country": 46,
    "nordic_combined": 47,
    "ski_jumping": 48,
    "snowboard": 49,
    "speed_skating": 50,
    "luge": 51,
    "swimming": 52,
    "softball": 54,
    "beach_soccer": 60,
    "pesapallo": 61,
    "padel": 71,
    "rally": 101,
    "mma": 117,
    "ufc": 117,
    "indy_racing": 129,
    "speedway": 131,
    "esport_king_of_glory": 134,
    "gaelic_football": 135,
    "esoccer": 137,
    "kabaddi": 138,
    "ebasketball": 153,
    "basketball_3x3": 155,
    "touring_car_racing": 188,
    "motorcycle_racing": 190,
    "motogp": 190,
    "stock_car_racing": 191,
    "nascar": 191,
    "eice_hockey": 195,
}

# Sportradar OddsAPI marketId=41 (Correct Score) standard outcome ID -> "H:A" score mapping
SR_CORRECT_SCORE_OUTCOMES: dict[str, str] = {
    "sr:outcome:110": "0:0",
    "sr:outcome:114": "1:0",
    "sr:outcome:116": "2:0",
    "sr:outcome:118": "3:0",
    "sr:outcome:120": "4:0",
    "sr:outcome:122": "5:0",
    "sr:outcome:124": "6:0",
    "sr:outcome:126": "0:1",
    "sr:outcome:128": "1:1",
    "sr:outcome:130": "2:1",
    "sr:outcome:132": "3:1",
    "sr:outcome:134": "4:1",
    "sr:outcome:136": "5:1",
    "sr:outcome:138": "0:2",
    "sr:outcome:140": "1:2",
    "sr:outcome:142": "2:2",
    "sr:outcome:144": "3:2",
    "sr:outcome:146": "4:2",
    "sr:outcome:148": "0:3",
    "sr:outcome:150": "1:3",
    "sr:outcome:152": "2:3",
    "sr:outcome:154": "3:3",
    "sr:outcome:156": "0:4",
    "sr:outcome:158": "1:4",
    "sr:outcome:160": "2:4",
    "sr:outcome:162": "0:5",
    "sr:outcome:164": "1:5",
    "sr:outcome:166": "0:6",
}

_TOKEN_CACHE: dict[str, Any] = {"token": None, "fetched_at": 0.0}
_RESPONSE_CACHE: dict[str, tuple[float, Any]] = {}


def _norm_name(name: str) -> str:
    clean = "".join(c for c in unicodedata.normalize("NFKD", name or "") if not unicodedata.combining(c)).lower()
    clean = re.sub(r"\b(fc|sc|cf|ac|afc|sv|vfb|vfl|tsg|rb|ud|cd|rcd|fk|sk|bk)\b", " ", clean)
    clean = re.sub(r"[^a-z0-9]+", " ", clean).strip()
    return clean


def _team_tokens(name: str) -> set[str]:
    return {t for t in _norm_name(name).split() if len(t) >= 3}


def _names_match(a: str, b: str) -> bool:
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta, tb = _team_tokens(a), _team_tokens(b)
    if ta and tb and (ta & tb):
        # For tennis "Lastname, Firstname" vs "Firstname Lastname", last name token intersection is sufficient
        return True
    return False


def get_statshub_token(force_refresh: bool = False) -> str | None:
    """Extract the signed `fishnetToken` (`exp=...~acl=/*~hmac=...`) from `https://statshub.sportradar.com/tipico/en/`."""
    now = time.time()
    if not force_refresh and _TOKEN_CACHE.get("token") and (now - float(_TOKEN_CACHE.get("fetched_at") or 0.0) < 3600.0):
        return str(_TOKEN_CACHE["token"])
    try:
        proc = subprocess.run(
            [
                "curl", "-sS", "-L", "--max-time", "12",
                "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                STATSHUB_TIPICO_URL,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        html = proc.stdout
        m = re.search(r"(exp=\d+~acl=[^\"\\]+~hmac=[a-fA-F0-9]+)", html)
        if m:
            tok = m.group(1)
            _TOKEN_CACHE["token"] = tok
            _TOKEN_CACHE["fetched_at"] = now
            return tok
    except Exception:
        return None
    return None


def fetch_statshub_gismo(
    endpoint: str,
    params_path: str = "",
    client_alias: str = "tipico",
    lang: str = "en",
    tz: str = "Europe:Berlin",
    ttl_sec: float = 300.0,
) -> Any:
    """Query Sportradar's direct tokenless Gismo API (`https://stats.fn.sportradar.com/{client}/{lang}/{tz}/gismo/{endpoint}/{params_path}`)
    without any HTML page parsing! Falls back to `sh.fn.sportradar.com` with token only if needed."""
    cache_key = f"{client_alias}:{endpoint}:{params_path}"
    now = time.time()
    if cache_key in _RESPONSE_CACHE:
        ts, cached_val = _RESPONSE_CACHE[cache_key]
        if now - ts < ttl_sec:
            return cached_val

    clean_params = params_path.strip("/")
    rel_path = f"{client_alias}/{lang}/{tz}/gismo/{endpoint}"
    if clean_params:
        rel_path = f"{rel_path}/{clean_params}"

    # 1. Primary path: Direct tokenless JSON API via stats.fn.sportradar.com (no HTML page parsing required!)
    direct_url = f"{DIRECT_STATS_FN_BASE_URL}/{rel_path}"
    try:
        proc = subprocess.run(
            [
                "curl", "-sS", "-L", "--max-time", "12",
                "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "-H", "Origin: https://statshub.sportradar.com",
                "-H", "Referer: https://statshub.sportradar.com/tipico/en/",
                direct_url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        doc_list = payload.get("doc") or []
        if doc_list and isinstance(doc_list[0], dict) and doc_list[0].get("event") != "exception":
            data = doc_list[0].get("data")
            _RESPONSE_CACHE[cache_key] = (now, data)
            return data
    except Exception:
        pass

    # 2. Fallback: sh.fn.sportradar.com with token
    tok = get_statshub_token()
    if not tok:
        return None
    fallback_url = f"{FISHNET_BASE_URL}/{rel_path}?T={tok}"
    try:
        proc = subprocess.run(
            [
                "curl", "-sS", "-L", "--max-time", "12",
                "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "-H", "Origin: https://statshub.sportradar.com",
                "-H", "Referer: https://statshub.sportradar.com/tipico/en/",
                fallback_url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        doc_list = payload.get("doc") or []
        if doc_list and isinstance(doc_list[0], dict):
            data = doc_list[0].get("data")
            _RESPONSE_CACHE[cache_key] = (now, data)
            return data
    except Exception:
        return None
    return None


def list_all_sportradar_sports(service_id: int = 69, client_alias: str = "sportradar") -> list[dict[str, Any]]:
    """Query `config_sports/{service_id}/0` directly via `stats.fn.sportradar.com` (the API behind the 'All Sports' modal on `/sportradar/en/`)."""
    data = fetch_statshub_gismo("config_sports", f"{service_id}/0", client_alias=client_alias, tz="Etc:UTC", ttl_sec=3600.0)
    if isinstance(data, list):
        return [{"sport_id": int(s["_id"]), "name": str(s["name"])} for s in data if isinstance(s, dict) and "_id" in s]
    return [{"sport_id": k, "name": v} for k, v in SR_ALL_SPORTS_CATALOG.items()]


def parse_tipico_prematch_markets(markets: list[dict[str, Any]], flipped: bool = False) -> dict[str, Any]:
    """Parse Sportradar prematch markets from either Tipico (`_bookmakerId: 176`) or Sportradar UOF (`_bookmakerId: 0`)."""
    bk_label = "Tipico (Sportradar)"
    if markets and isinstance(markets[0], dict):
        if markets[0].get("_bookmakerId") == 0 or "UOF" in str(markets[0].get("source") or ""):
            bk_label = "Sportradar UOF Consensus"
    out: dict[str, Any] = {
        "bookmaker": bk_label,
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
        "double_chance_1x": None,
        "double_chance_x2": None,
        "draw_no_bet_home": None,
        "draw_no_bet_away": None,
        "asian_handicap_line": None,
        "asian_handicap_home": None,
        "asian_handicap_away": None,
        "total_line": None,
        "odds_over": None,
        "odds_under": None,
        "correct_score_odds": {},
    }
    for mk in markets or []:
        mid = mk.get("_marketId")
        outcomes = mk.get("outcomes") or []
        spec = mk.get("specifiers") or {}
        if mid in (1, 186, 219, 406):  # 1x2 or 2-way Winner
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    out["odds_away" if flipped else "odds_home"] = val
                elif "competitor2" in nm:
                    out["odds_home" if flipped else "odds_away"] = val
                elif nm == "draw":
                    out["odds_draw"] = val
        elif mid == 10:  # Double chance
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm and "draw" in nm:
                    out["double_chance_x2" if flipped else "double_chance_1x"] = val
                elif "competitor2" in nm and "draw" in nm:
                    out["double_chance_1x" if flipped else "double_chance_x2"] = val
        elif mid == 11:  # Draw no bet
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    out["draw_no_bet_away" if flipped else "draw_no_bet_home"] = val
                elif "competitor2" in nm:
                    out["draw_no_bet_home" if flipped else "draw_no_bet_away"] = val
        elif mid in (16, 223):  # 2-Way Asian Handicap / Point Spread
            out["asian_handicap_line"] = spec.get("hcp")
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    out["asian_handicap_away" if flipped else "asian_handicap_home"] = val
                elif "competitor2" in nm:
                    out["asian_handicap_home" if flipped else "asian_handicap_away"] = val
        elif mid in (18, 189, 225):  # Total goals / games / points
            t_str = spec.get("total")
            try:
                out["total_line"] = float(t_str) if t_str is not None else None
            except Exception:
                pass
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if nm.startswith("over"):
                    out["odds_over"] = val
                elif nm.startswith("under"):
                    out["odds_under"] = val
        elif mid in (41, 45):  # Correct score (28 outcomes)
            if out["correct_score_odds"] and mid == 45:
                continue
            cs_map: dict[str, float] = {}
            for o in outcomes:
                oid = str(o.get("_id") or "")
                nm_sc = str(o.get("name") or "").strip()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                raw_sc = nm_sc if (":" in nm_sc and len(nm_sc) <= 5) else SR_CORRECT_SCORE_OUTCOMES.get(oid, "")
                if raw_sc and ":" in raw_sc:
                    if flipped:
                        p_h, p_a = raw_sc.split(":", 1)
                        raw_sc = f"{p_a}:{p_h}"
                    cs_map[raw_sc] = val
            if cs_map:
                out["correct_score_odds"] = cs_map
    return out


def get_daily_tipico_match_index(sport: str = "soccer", date_ymd: str | None = None) -> list[dict[str, Any]]:
    """Fetch and cache the flattened list of matches (`home`, `away`, `_id`, `_seasonid`, `tournament`) for `sport` on `date_ymd`."""
    if not date_ymd:
        date_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_k = f"daily_idx:{sport}:{date_ymd}"
    now = time.time()
    if cache_k in _RESPONSE_CACHE and (now - _RESPONSE_CACHE[cache_k][0] < 600.0):
        return _RESPONSE_CACHE[cache_k][1]
    sport_id = SR_SPORT_IDS.get(sport.lower(), 1)
    u_data = fetch_statshub_gismo("unified_sport_matches", f"{sport_id}/{date_ymd}/0", ttl_sec=600.0)
    flat: list[dict[str, Any]] = []
    if isinstance(u_data, dict):
        sp_obj = u_data.get("sport") or {}
        for rc in sp_obj.get("realcategories") or []:
            for t in rc.get("tournaments") or []:
                t_label = f"{rc.get('name', '')} · {t.get('name', '')}".strip(" ·")
                for m in t.get("matches") or []:
                    teams = m.get("teams") or {}
                    flat.append({
                        "match_obj": m,
                        "tournament": t_label,
                        "home": (teams.get("home") or {}).get("name") or "",
                        "away": (teams.get("away") or {}).get("name") or "",
                    })
    _RESPONSE_CACHE[cache_k] = (now, flat)
    return flat


def lookup_tipico_correct_score_and_1x2(home: str, away: str, date_ymd: str | None = None, sport: str = "soccer") -> dict[str, Any]:
    """Fast lookup of Tipico (`_bookmakerId=176`) + Sportradar UOF (`_bookmakerId=0`) prematch markets for `(home, away)` on `date_ymd`."""
    flat = get_daily_tipico_match_index(sport=sport, date_ymd=date_ymd)
    matched_m = None
    flipped = False
    for entry in flat:
        th, ta = entry["home"], entry["away"]
        if _names_match(home, th) and _names_match(away, ta):
            matched_m = entry["match_obj"]
            flipped = False
            break
        if _names_match(home, ta) and _names_match(away, th):
            matched_m = entry["match_obj"]
            flipped = True
            break
    if not matched_m:
        return {}
    mid = matched_m.get("_id")
    mm_tipico = fetch_statshub_gismo("match_markets", f"{mid}/prematch", client_alias="tipico", ttl_sec=600.0) or {}
    mm_sr = fetch_statshub_gismo("match_markets", f"{mid}/prematch", client_alias="sportradar", ttl_sec=600.0) or {}
    p_tip = parse_tipico_prematch_markets(mm_tipico.get("markets") or [], flipped=flipped)
    p_sr = parse_tipico_prematch_markets(mm_sr.get("markets") or [], flipped=flipped)
    merged = dict(p_tip)
    for k, v in p_sr.items():
        if k != "bookmaker" and not merged.get(k) and v:
            merged[k] = v
    return merged


def fetch_team_goal_intervals(season_id: int | str, team_uid: int | str, limit: int = 10) -> dict[str, Any]:
    """Query `stats_season_teamscoringconceding/{seasonId}/{teamUid}/{limit}` and return 15-minute goal scoring/conceding rates,
    1st-half scoring rate (`scoringathalftimeaverage`), and late-goal (`76-90'`) intensity."""
    data = fetch_statshub_gismo("stats_season_teamscoringconceding", f"{season_id}/{team_uid}/{limit}", client_alias="common", ttl_sec=1800.0)
    if not isinstance(data, dict) or "stats" not in data:
        return {}
    st = data["stats"] or {}
    sc = st.get("scoring") or {}
    co = st.get("conceding") or {}
    sc_mins = sc.get("goalsbyminutes") or {}
    co_mins = co.get("goalsbyminutes") or {}
    intervals: dict[str, dict[str, float]] = {}
    for bucket in ("0-15", "16-30", "31-45", "46-60", "61-75", "76-90"):
        s_v = float((sc_mins.get(bucket) or {}).get("total") or 0.0)
        c_v = float((co_mins.get(bucket) or {}).get("total") or 0.0)
        intervals[bucket] = {
            "scored_per_match": round(s_v, 3),
            "conceded_per_match": round(c_v, 3),
            "combined_per_match": round(s_v + c_v, 3),
        }
    fh_scored = float((sc.get("goalsscoredfirsthalfaverage") or {}).get("total") or 0.0)
    fh_conceded = float((co.get("goalsconcededfirsthalfaverage") or {}).get("total") or 0.0)
    ht_score_rate = float((sc.get("scoringathalftimeaverage") or {}).get("total") or 0.0)
    btts_rate = float((sc.get("bothteamsscoredaverage") or {}).get("total") or 0.0)
    late_76_90_scored = intervals.get("76-90", {}).get("scored_per_match", 0.0)
    late_76_90_conceded = intervals.get("76-90", {}).get("conceded_per_match", 0.0)
    return {
        "matches_sampled": int((st.get("totalmatches") or {}).get("total") or 0),
        "first_half_scored_avg": round(fh_scored, 2),
        "first_half_conceded_avg": round(fh_conceded, 2),
        "scoring_in_1h_pct": round(ht_score_rate * 100.0, 1),
        "btts_pct": round(btts_rate * 100.0, 1),
        "late_76_90_scored_avg": round(late_76_90_scored, 2),
        "late_76_90_conceded_avg": round(late_76_90_conceded, 2),
        "late_76_90_total_avg": round(late_76_90_scored + late_76_90_conceded, 2),
        "intervals": intervals,
    }


def fetch_live_match_situations_pressure(match_id: int | str) -> dict[str, Any]:
    """Query `match_situations/{matchId}` and compute live attack / dangerous-attack territorial pressure for both sides."""
    data = fetch_statshub_gismo("match_situations", str(match_id), client_alias="common", ttl_sec=45.0)
    if not isinstance(data, dict) or not data.get("situations"):
        return {}
    sits = data.get("situations") or []
    cnt: dict[str, dict[str, int]] = {
        "home": {"attack": 0, "dangerous_attack": 0, "safe": 0},
        "away": {"attack": 0, "dangerous_attack": 0, "safe": 0},
    }
    for s in sits:
        tm = str(s.get("team") or "")
        st_type = str(s.get("situation") or "")
        if tm in cnt and st_type in cnt[tm]:
            cnt[tm][st_type] += 1
    h_da = cnt["home"]["dangerous_attack"]
    a_da = cnt["away"]["dangerous_attack"]
    tot_da = max(1, h_da + a_da)
    return {
        "home_attacks": cnt["home"]["attack"],
        "away_attacks": cnt["away"]["attack"],
        "home_dangerous_attacks": h_da,
        "away_dangerous_attacks": a_da,
        "home_danger_share_pct": round((h_da / tot_da) * 100.0, 1),
        "away_danger_share_pct": round((a_da / tot_da) * 100.0, 1),
    }


def evaluate_sportradar_injury_gate(
    season_id: int | str | None,
    backed_uid: int | str | None,
    opp_uid: int | str | None,
) -> dict[str, Any]:
    """Evaluate pre-match Sportradar `stats_season_injuries` for a Football match before T-60m lineups drop.
    Counts missing forwards (`FWD`/`F`), midfielders (`MID`/`M`), defenders (`DEF`/`D`), and goalkeepers (`GK`/`G`),
    and computes a net injury impact score (`injury_penalty_prob`) and warning status."""
    if not season_id or not backed_uid:
        return {"status": "NO_SEASON_DATA", "backed_out": [], "opp_out": [], "veto_recommended": False, "prob_adjustment": 0.0}
    inj_list = fetch_statshub_gismo("stats_season_injuries", str(season_id), ttl_sec=1800.0) or []
    if not isinstance(inj_list, list):
        return {"status": "NO_INJURY_FEED", "backed_out": [], "opp_out": [], "veto_recommended": False, "prob_adjustment": 0.0}

    backed_out: list[str] = []
    opp_out: list[str] = []
    backed_fwd_out = 0
    backed_gk_out = 0
    opp_fwd_out = 0

    for item in inj_list:
        ut_id = (item.get("uniqueteam") or {}).get("_id")
        if ut_id not in (backed_uid, opp_uid):
            continue
        p_obj = item.get("player") or {}
        p_nm = p_obj.get("name") or ""
        pos_s = ((p_obj.get("position") or {}).get("shortname")) or ""
        st_obj = item.get("status") or {}
        st_nm = st_obj.get("name") or st_obj.get("status") or "Out"
        if not p_nm:
            continue
        entry = f"{p_nm} ({pos_s}, {st_nm})" if pos_s else f"{p_nm} ({st_nm})"
        if ut_id == backed_uid:
            backed_out.append(entry)
            if pos_s in ("FWD", "F"):
                backed_fwd_out += 1
            elif pos_s in ("GK", "G"):
                backed_gk_out += 1
        elif ut_id == opp_uid:
            opp_out.append(entry)
            if pos_s in ("FWD", "F"):
                opp_fwd_out += 1

    net_out_diff = len(backed_out) - len(opp_out)
    # Penalize win probability when backed club has >=2 forwards missing or >=4 more players out than opponent
    prob_adj = 0.0
    if backed_fwd_out >= 2 or net_out_diff >= 3:
        prob_adj -= min(0.06, 0.015 * backed_fwd_out + 0.008 * max(0, net_out_diff))
    elif opp_fwd_out >= 2 or net_out_diff <= -3:
        prob_adj += min(0.04, 0.012 * opp_fwd_out + 0.006 * max(0, -net_out_diff))

    veto_rec = bool(backed_fwd_out >= 3 or (backed_fwd_out >= 2 and backed_gk_out >= 1) or net_out_diff >= 5)
    status = (
        f"ALERT_DEPLETED_SQUAD ({len(backed_out)} Out, {backed_fwd_out} FWD)"
        if veto_rec
        else (f"TRACKED ({len(backed_out)} Out vs {len(opp_out)} Opp)" if (backed_out or opp_out) else "CLEAN_SQUAD")
    )
    return {
        "status": status,
        "backed_out": backed_out[:8],
        "opp_out": opp_out[:8],
        "backed_fwd_out": backed_fwd_out,
        "backed_gk_out": backed_gk_out,
        "prob_adjustment": round(prob_adj, 4),
        "veto_recommended": veto_rec,
    }


def scan_sportradar_european_sports(
    date_ymd: str | None = None,
    min_prob: float = 0.68,
    max_picks_per_sport: int = 5,
) -> list[dict[str, Any]]:
    """Scan high-frequency European sports on Sportradar StatsHub (`Handball=6`, `Darts=22`, `Table Tennis=20`, `Snooker=19`, `MMA=117`)
    combining Tipico (`_bookmakerId=176`) + Sportradar Main UOF (`_bookmakerId=0`) odds with Last-10 Form (`stats_match_form`) and Streak momentum."""
    if not date_ymd:
        date_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    target_sports = [
        (6, "handball", "Handball"),
        (22, "darts", "Darts"),
        (20, "table_tennis", "Table Tennis"),
        (19, "snooker", "Snooker"),
        (117, "mma", "MMA"),
    ]
    picks_out: list[dict[str, Any]] = []

    for sp_id, sp_slug, sp_label in target_sports:
        u_matches = fetch_statshub_gismo("unified_sport_matches", f"{sp_id}/{date_ymd}/0", ttl_sec=600.0) or {}
        mkt_tip = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sp_id}/{date_ymd}/0", client_alias="tipico", ttl_sec=600.0) or {}).get("matches") or {}
        mkt_uof = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sp_id}/{date_ymd}/0", client_alias="sportradar", ttl_sec=600.0) or {}).get("matches") or {}

        sport_cands: list[dict[str, Any]] = []
        for rc in (u_matches.get("sport") or {}).get("realcategories") or []:
            rc_name = rc.get("name") or ""
            for t in rc.get("tournaments") or []:
                t_name = t.get("name") or ""
                comp_label = f"{rc_name} · {t_name}".strip(" ·")
                for m in t.get("matches") or []:
                    st_id = int(((m.get("status") or {}).get("_id")) or 0)
                    if st_id not in (0, 61):  # Skip finished or in-play matches
                        continue
                    mid = str(m.get("_id") or "")
                    if not mid:
                        continue
                    tip_entry = mkt_tip.get(mid) or {}
                    uof_entry = mkt_uof.get(mid) or {}
                    raw_mkts = (tip_entry.get("markets") or []) or (uof_entry.get("markets") or [])
                    if not raw_mkts:
                        continue
                    is_tipico_src = bool(tip_entry.get("markets"))
                    parsed_m = parse_tipico_prematch_markets(raw_mkts, flipped=False)
                    oh = parsed_m.get("odds_home")
                    oa = parsed_m.get("odds_away")
                    od = parsed_m.get("odds_draw")
                    if not oh or not oa or min(oh, oa) < 1.12 or min(oh, oa) > 1.72:
                        continue

                    # Compute vig-free market probability
                    inv_h = 1.0 / float(oh)
                    inv_a = 1.0 / float(oa)
                    inv_d = (1.0 / float(od)) if od else 0.0
                    overround = inv_h + inv_a + inv_d
                    p_mkt_h = inv_h / overround
                    p_mkt_a = inv_a / overround
                    side = "H" if p_mkt_h >= p_mkt_a else "A"
                    p_mkt_fav = p_mkt_h if side == "H" else p_mkt_a
                    best_o = float(oh if side == "H" else oa)
                    if p_mkt_fav < min_prob - 0.04:
                        continue

                    teams = m.get("teams") or {}
                    h_name = (teams.get("home") or {}).get("name") or ""
                    a_name = (teams.get("away") or {}).get("name") or ""
                    dt_uts = ((m.get("_dt") or {}).get("uts")) or 0
                    if not h_name or not a_name or not dt_uts:
                        continue
                    ko_iso = datetime.fromtimestamp(int(dt_uts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
                    sport_cands.append({
                        "mid": mid,
                        "sp_slug": sp_slug,
                        "sp_label": sp_label,
                        "comp_label": comp_label,
                        "kickoff": ko_iso,
                        "home": h_name,
                        "away": a_name,
                        "side": side,
                        "pick": h_name if side == "H" else a_name,
                        "p_mkt": round(p_mkt_fav, 4),
                        "best_odds": round(best_o, 2),
                        "is_tipico": is_tipico_src,
                    })

        # Sort by highest market conviction & Tipico availability, then enrich top candidates with `stats_match_form`
        sport_cands.sort(key=lambda x: (1 if x["is_tipico"] else 0, x["p_mkt"]), reverse=True)
        for cand in sport_cands[:max_picks_per_sport]:
            mf = fetch_statshub_gismo("stats_match_form", cand["mid"], ttl_sec=1800.0) or {}
            t_forms = mf.get("teams") or {}
            h_f_list = (t_forms.get("home") or {}).get("form") or []
            a_f_list = (t_forms.get("away") or {}).get("form") or []
            h_wr = (sum(1.0 for x in h_f_list if x.get("type") == "W") / len(h_f_list)) if h_f_list else 0.5
            a_wr = (sum(1.0 for x in a_f_list if x.get("type") == "W") / len(a_f_list)) if a_f_list else 0.5
            form_diff_fav = (h_wr - a_wr) if cand["side"] == "H" else (a_wr - h_wr)
            # Veto if backed favorite has significantly worse rolling form than underdog
            if len(h_f_list) >= 4 and len(a_f_list) >= 4 and form_diff_fav < -0.25:
                continue
            p_model = min(0.94, max(0.52, cand["p_mkt"] + 0.06 * form_diff_fav + (0.015 if cand["is_tipico"] else 0.0)))
            if p_model < min_prob:
                continue
            ev_pct = round((p_model * cand["best_odds"] - 1.0) * 100.0, 2)
            picks_out.append({
                "sport": sp_slug,
                "league": sp_slug,
                "league_name": f"{cand['sp_label']} · {cand['comp_label']}",
                "event_id": f"sr_{cand['mid']}",
                "kickoff": cand["kickoff"],
                "time_valid": True,
                "home": cand["home"],
                "away": cand["away"],
                "side": cand["side"],
                "pick": cand["pick"],
                "tier": "tipico_banker" if cand["is_tipico"] else "sr_uof_banker",
                "p_model": round(p_model, 4),
                "p_mkt": cand["p_mkt"],
                "best_odds": cand["best_odds"],
                "ev_pct": ev_pct,
                "composite_score": round(p_model, 4),
                "bookmaker_source": "Tipico #176" if cand["is_tipico"] else "Sportradar UOF",
                "form_diff_fav": round(form_diff_fav, 3),
            })
    return picks_out


def lookup_statshub_match_intel(
    home: str,
    away: str,
    sport: str = "soccer",
    date_ymd: str | None = None,
) -> dict[str, Any]:
    """Find a match on Sportradar StatsHub (Tipico) and return Tipico bookmaker markets (including 28 Correct Score odds),
    missing/injured players (`stats_season_injuries`), team streaks (`stats_team_streaks`), or tennis surface records."""
    if not date_ymd:
        date_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sport_id = SR_SPORT_IDS.get(sport.lower(), 1)
    u_data = fetch_statshub_gismo("unified_sport_matches", f"{sport_id}/{date_ymd}/0")
    if not isinstance(u_data, dict):
        return {"ok": False, "found": False}

    sp_obj = u_data.get("sport") or {}
    matched_m: dict[str, Any] | None = None
    matched_tourn = ""
    flipped = False

    for rc in sp_obj.get("realcategories") or []:
        for t in rc.get("tournaments") or []:
            t_label = f"{rc.get('name', '')} · {t.get('name', '')}".strip(" ·")
            for m in t.get("matches") or []:
                teams = m.get("teams") or {}
                th = (teams.get("home") or {}).get("name") or ""
                ta = (teams.get("away") or {}).get("name") or ""
                if _names_match(home, th) and _names_match(away, ta):
                    matched_m = m
                    matched_tourn = t_label
                    flipped = False
                    break
                if _names_match(home, ta) and _names_match(away, th):
                    matched_m = m
                    matched_tourn = t_label
                    flipped = True
                    break
            if matched_m:
                break
        if matched_m:
            break

    if not matched_m:
        return {"ok": True, "found": False}

    mid = matched_m.get("_id")
    season_id = matched_m.get("_seasonid")
    teams_obj = matched_m.get("teams") or {}
    h_team = teams_obj.get("away" if flipped else "home") or {}
    a_team = teams_obj.get("home" if flipped else "away") or {}
    h_uid = h_team.get("uid") or h_team.get("_id")
    a_uid = a_team.get("uid") or a_team.get("_id")

    # 1. Fetch Tipico prematch markets (`client_alias="tipico"`, `_bookmakerId: 176`) + Sportradar Main Site UOF (`client_alias="sportradar"`, `_bookmakerId: 0`)
    mm_tipico = fetch_statshub_gismo("match_markets", f"{mid}/prematch", client_alias="tipico") or {}
    mm_sr_main = fetch_statshub_gismo("match_markets", f"{mid}/prematch", client_alias="sportradar") or {}
    tipico_parsed = parse_tipico_prematch_markets(mm_tipico.get("markets") or [], flipped=flipped)
    sr_uof_parsed = parse_tipico_prematch_markets(mm_sr_main.get("markets") or [], flipped=flipped)

    # Merge: prefer real Tipico retail odds (`_bookmakerId: 176`) whenever available, and automatically fill any missing markets (e.g. Asian Handicap or unpriced matches) from Sportradar Main Site UOF!
    markets_parsed = dict(tipico_parsed)
    has_tipico = bool(tipico_parsed.get("odds_home") or tipico_parsed.get("correct_score_odds"))
    has_sr_uof = bool(sr_uof_parsed.get("odds_home") or sr_uof_parsed.get("correct_score_odds"))
    for k, v in sr_uof_parsed.items():
        if k == "bookmaker":
            continue
        if not markets_parsed.get(k) and v:
            markets_parsed[k] = v
    if has_tipico and has_sr_uof:
        markets_parsed["bookmaker"] = "Tipico + Sportradar UOF"
    elif has_tipico:
        markets_parsed["bookmaker"] = "Tipico (Bookmaker #176)"
    elif has_sr_uof:
        markets_parsed["bookmaker"] = "Sportradar Main (UOF)"

    # 2. Fetch season injuries or tennis surface stats
    home_injuries: list[str] = []
    away_injuries: list[str] = []
    tennis_surface_records: dict[str, Any] = {}

    if sport_id == 1 and season_id:
        inj_list = fetch_statshub_gismo("stats_season_injuries", str(season_id), ttl_sec=1800.0) or []
        if isinstance(inj_list, list):
            for item in inj_list:
                ut_id = (item.get("uniqueteam") or {}).get("_id")
                p_obj = item.get("player") or {}
                p_nm = p_obj.get("name") or ""
                pos_s = ((p_obj.get("position") or {}).get("shortname")) or ""
                st_obj = item.get("status") or {}
                st_nm = st_obj.get("name") or st_obj.get("status") or "Out"
                if not p_nm:
                    continue
                entry_s = f"{p_nm} ({pos_s}, {st_nm})" if pos_s else f"{p_nm} ({st_nm})"
                if h_uid and ut_id == h_uid and len(home_injuries) < 8:
                    home_injuries.append(entry_s)
                elif a_uid and ut_id == a_uid and len(away_injuries) < 8:
                    away_injuries.append(entry_s)
    elif sport_id == 5:
        for side_lbl, p_uid in (("home", h_uid), ("away", a_uid)):
            if p_uid:
                s_data = fetch_statshub_gismo("tennis_team_surfacestats", str(p_uid), client_alias="common", ttl_sec=3600.0) or {}
                singles_yr = (s_data.get("singles") or {}).get("2026") or (s_data.get("singles") or {}).get("2025") or {}
                if isinstance(singles_yr, dict):
                    all_rec = singles_yr.get("0") or {}
                    hard_rec = singles_yr.get("2") or {}
                    clay_rec = singles_yr.get("1") or {}
                    indoor_rec = singles_yr.get("4") or {}
                    tennis_surface_records[side_lbl] = {
                        "season_wl": f"{all_rec.get('wins', 0)}-{all_rec.get('losses', 0)}",
                        "hard_wl": f"{hard_rec.get('wins', 0)}-{hard_rec.get('losses', 0)}",
                        "clay_wl": f"{clay_rec.get('wins', 0)}-{clay_rec.get('losses', 0)}",
                        "indoor_wl": f"{indoor_rec.get('wins', 0)}-{indoor_rec.get('losses', 0)}",
                    }

    # 3. Fetch team streaks (`stats_team_streaks`), 15-minute goal intervals (`stats_season_teamscoringconceding`), and live attack situations (`match_situations`)
    streaks_summary: dict[str, list[str]] = {"home": [], "away": []}
    goal_intervals: dict[str, Any] = {}
    live_pressure: dict[str, Any] = {}
    injury_gate: dict[str, Any] = {}
    if sport_id != 5:
        for side_lbl, t_uid in (("home", h_uid), ("away", a_uid)):
            if t_uid:
                st_data = fetch_statshub_gismo("stats_team_streaks", str(t_uid), client_alias="common", ttl_sec=1800.0) or {}
                st_dict = st_data.get("streaks") or {}
                if isinstance(st_dict, dict):
                    for st_type, scope_obj in st_dict.items():
                        if isinstance(scope_obj, dict):
                            tot_v = (scope_obj.get("total") or scope_obj.get(side_lbl) or {}).get("value")
                            if tot_v and int(tot_v) >= 3:
                                streaks_summary[side_lbl].append(f"{st_type}: {tot_v} matches")
        if sport_id == 1 and season_id and h_uid and a_uid:
            goal_intervals = {
                "home": fetch_team_goal_intervals(season_id, h_uid, limit=10),
                "away": fetch_team_goal_intervals(season_id, a_uid, limit=10),
            }
            injury_gate = evaluate_sportradar_injury_gate(season_id, h_uid, a_uid)
            st_code = int(((matched_m.get("status") or {}).get("_id")) or 0)
            if 0 < st_code < 90:
                live_pressure = fetch_live_match_situations_pressure(mid)

    return {
        "ok": True,
        "found": True,
        "sr_match_id": mid,
        "sr_season_id": season_id,
        "tournament": matched_tourn,
        "tipico_markets": markets_parsed,
        "sportradar_uof_markets": sr_uof_parsed,
        "home_injuries": home_injuries,
        "away_injuries": away_injuries,
        "injury_gate": injury_gate,
        "goal_intervals": goal_intervals,
        "live_pressure": live_pressure,
        "streaks": streaks_summary,
        "tennis_surface_records": tennis_surface_records,
    }
