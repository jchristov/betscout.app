"""Sportradar StatsHub (Tipico) live client for bookmaker odds (1X2, Correct Score 28-grid, Double Chance, Draw No Bet, Over/Under),
player injuries/suspensions (`stats_season_injuries`), team streaks (`stats_team_streaks`), and ATP/WTA surface win-loss records (`tennis_team_surfacestats`)."""

from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timedelta, timezone
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


_CLUB_ALIASES: dict[str, str] = {
    "paris saint germain": "psg paris saint germain",
    "psg": "psg paris saint germain",
    "internazionale": "inter internazionale milano",
    "inter milan": "inter internazionale milano",
}


def _norm_name(name: str) -> str:
    clean = "".join(c for c in unicodedata.normalize("NFKD", name or "") if not unicodedata.combining(c)).lower()
    clean = re.sub(r"\b(fc|sc|cf|ac|afc|sv|vfb|vfl|tsg|rb|ud|cd|rcd|fk|sk|bk)\b", " ", clean)
    clean = re.sub(r"[^a-z0-9]+", " ", clean).strip()
    return _CLUB_ALIASES.get(clean, clean)


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
    """Parse prematch markets from primary and consensus odds feeds."""
    bk_label = "Primary Bookmaker"
    if markets and isinstance(markets[0], dict):
        if markets[0].get("_bookmakerId") == 0 or "UOF" in str(markets[0].get("source") or ""):
            bk_label = "Market Consensus"
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
    youth_or_amateur: list[dict[str, Any]] = []
    if isinstance(u_data, dict):
        sp_obj = u_data.get("sport") or {}
        for rc in sp_obj.get("realcategories") or []:
            rc_name = str(rc.get("name") or "")
            if "simulated reality" in rc_name.lower() or "esoccer" in rc_name.lower():
                continue
            for t in rc.get("tournaments") or []:
                t_label = f"{rc_name} · {t.get('name', '')}".strip(" ·")
                t_low = t_label.lower()
                if " srl" in t_low or "simulated reality" in t_low:
                    continue
                is_sub_tier = any(w in t_low for w in ("amateur", "u19", "u20", "u21", "u18", "u17", "youth", "reserve"))
                for m in t.get("matches") or []:
                    teams = m.get("teams") or {}
                    h_nm = str((teams.get("home") or {}).get("name") or "")
                    a_nm = str((teams.get("away") or {}).get("name") or "")
                    if h_nm.endswith(" SRL") or a_nm.endswith(" SRL"):
                        continue
                    item = {
                        "match_obj": m,
                        "tournament": t_label,
                        "home": h_nm,
                        "away": a_nm,
                    }
                    if is_sub_tier:
                        youth_or_amateur.append(item)
                    else:
                        flat.append(item)
    flat.extend(youth_or_amateur)
    _RESPONSE_CACHE[cache_k] = (now, flat)
    return flat


def get_daily_sportradar_markets_map(sport: str = "soccer", date_ymd: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch and cache the bulk daily markets (`unified_sport_matches_markets/{sportId}/{date_ymd}/0`)
    for both `tipico` (`_bookmakerId=176`) and `sportradar` (`_bookmakerId=0`) in a single pair of requests."""
    if not date_ymd:
        date_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_k = f"daily_mkts:{sport.lower()}:{date_ymd}"
    now = time.time()
    if cache_k in _RESPONSE_CACHE and (now - _RESPONSE_CACHE[cache_k][0] < 600.0):
        return _RESPONSE_CACHE[cache_k][1]
    sport_id = SR_SPORT_IDS.get(sport.lower(), 1)
    mkt_tip = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sport_id}/{date_ymd}/0", client_alias="tipico", ttl_sec=600.0) or {}).get("matches") or {}
    mkt_uof = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sport_id}/{date_ymd}/0", client_alias="sportradar", ttl_sec=600.0) or {}).get("matches") or {}
    pair = (mkt_tip, mkt_uof)
    _RESPONSE_CACHE[cache_k] = (now, pair)
    return pair


def lookup_sportradar_daily_odds(
    home: str,
    away: str,
    sport: str = "soccer",
    date_ymd: str | None = None,
) -> dict[str, Any]:
    """Primary fast pre-match odds & totals lookup from Sportradar (`Tipico` + `UOF` bulk daily feed).
    Automatically checks both `date_ymd` and `date_ymd + 1 day` (so late-night UTC games that fall on the
    next `Europe:Berlin` calendar day are matched seamlessly without per-event HTTP roundtrips)."""
    if not date_ymd:
        date_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_candidates = [date_ymd]
    try:
        dt_base = datetime.strptime(date_ymd[:10], "%Y-%m-%d")
        date_candidates.append((dt_base + timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass

    matched_m = None
    matched_ymd = date_ymd
    flipped = False
    for d_cand in date_candidates:
        flat = get_daily_tipico_match_index(sport=sport, date_ymd=d_cand)
        for entry in flat:
            th, ta = entry["home"], entry["away"]
            if _names_match(home, th) and _names_match(away, ta):
                matched_m = entry["match_obj"]
                matched_ymd = d_cand
                flipped = False
                break
            if _names_match(home, ta) and _names_match(away, th):
                matched_m = entry["match_obj"]
                matched_ymd = d_cand
                flipped = True
                break
        if matched_m:
            break

    if not matched_m:
        return {}

    mid = str(matched_m.get("_id") or "")
    if not mid:
        return {}
    mkt_tip, mkt_uof = get_daily_sportradar_markets_map(sport=sport, date_ymd=matched_ymd)
    tip_raw = (mkt_tip.get(mid) or {}).get("markets") or []
    uof_raw = (mkt_uof.get(mid) or {}).get("markets") or []
    p_tip = parse_tipico_prematch_markets(tip_raw, flipped=flipped) if tip_raw else {}
    p_uof = parse_tipico_prematch_markets(uof_raw, flipped=flipped) if uof_raw else {}

    merged = dict(p_tip)
    for k, v in p_uof.items():
        if k == "bookmaker":
            continue
        if not merged.get(k) and v is not None:
            merged[k] = v

    dt_uts = ((matched_m.get("_dt") or {}).get("uts")) or 0
    start_utc = (
        datetime.fromtimestamp(int(dt_uts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        if dt_uts
        else None
    )
    teams_m = matched_m.get("teams") or {}
    h_team_m = teams_m.get("away" if flipped else "home") or {}
    a_team_m = teams_m.get("home" if flipped else "away") or {}
    return {
        "sr_match_id": mid,
        "start_utc": start_utc,
        "start_uts": int(dt_uts) if dt_uts else None,
        "home_uid": h_team_m.get("uid") or h_team_m.get("_id"),
        "away_uid": a_team_m.get("uid") or a_team_m.get("_id"),
        "odds_home": merged.get("odds_home"),
        "odds_draw": merged.get("odds_draw"),
        "odds_away": merged.get("odds_away"),
        "line_total": merged.get("total_line"),
        "odds_over": merged.get("odds_over"),
        "odds_under": merged.get("odds_under"),
        "correct_score_odds": merged.get("correct_score_odds") or {},
        "odds_provider": "sportradar_tipico" if tip_raw else ("sportradar_uof" if uof_raw else "sportradar"),
    }


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


def backfill_sportradar_european_sports_to_db(
    db_path: Path,
    days_back: int = 7,
) -> dict[str, int]:
    """Backfill completed historical matches for Handball (`sportId=6`), Darts (`sportId=22`), and Table Tennis (`sportId=20`)
    from `unified_sport_matches` + `unified_sport_matches_markets` into `data/betscout.db` for Elo & H2H calibration."""
    import sqlite3

    target_sports = [
        (6, "handball"),
        (22, "darts"),
        (20, "table_tennis"),
    ]
    conn = sqlite3.connect(db_path, timeout=20.0)
    inserted_by_sport: dict[str, int] = {sp_slug: 0 for _, sp_slug in target_sports}
    now_utc = datetime.now(timezone.utc)

    for sp_id, sp_slug in target_sports:
        rows_to_upsert: list[tuple[Any, ...]] = []
        for d_back in range(1, days_back + 1):
            ymd = (now_utc - timedelta(days=d_back)).strftime("%Y-%m-%d")
            u_doc = fetch_statshub_gismo("unified_sport_matches", f"{sp_id}/{ymd}/1", ttl_sec=86400.0) or {}
            mkt_tip = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sp_id}/{ymd}/1", client_alias="tipico", ttl_sec=86400.0) or {}).get("matches") or {}
            mkt_uof = (fetch_statshub_gismo("unified_sport_matches_markets", f"{sp_id}/{ymd}/1", client_alias="sportradar", ttl_sec=86400.0) or {}).get("matches") or {}

            for rc in (u_doc.get("sport") or {}).get("realcategories") or []:
                for t in rc.get("tournaments") or []:
                    for m in t.get("matches") or []:
                        st = m.get("status")
                        st_id = int(st.get("_id") or 0) if isinstance(st, dict) else 0
                        if st_id not in (100, 110, 120):
                            continue
                        mid = str(m.get("_id") or "")
                        res_obj = m.get("result") or {}
                        h_sc = res_obj.get("home")
                        a_sc = res_obj.get("away")
                        if not mid or h_sc is None or a_sc is None:
                            continue
                        teams = m.get("teams") or {}
                        h_name = (teams.get("home") or {}).get("name") or ""
                        a_name = (teams.get("away") or {}).get("name") or ""
                        dt_uts = ((m.get("_dt") or {}).get("uts")) or 0
                        if not h_name or not a_name or not dt_uts:
                            continue
                        ko_iso = datetime.fromtimestamp(int(dt_uts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        h_int, a_int = int(h_sc), int(a_sc)
                        outcome = "H" if h_int > a_int else ("A" if a_int > h_int else "D")

                        tip_entry = mkt_tip.get(mid) or {}
                        uof_entry = mkt_uof.get(mid) or {}
                        raw_mkts = (tip_entry.get("markets") or []) or (uof_entry.get("markets") or [])
                        parsed_m = parse_tipico_prematch_markets(raw_mkts, flipped=False) if raw_mkts else {}
                        rows_to_upsert.append((
                            f"sr_{mid}",
                            sp_slug,
                            sp_slug,
                            ko_iso,
                            h_name,
                            a_name,
                            h_int,
                            a_int,
                            outcome,
                            parsed_m.get("odds_home"),
                            parsed_m.get("odds_draw"),
                            parsed_m.get("odds_away"),
                            "primary" if tip_entry.get("markets") else ("consensus" if uof_entry.get("markets") else None),
                        ))
        if rows_to_upsert:
            conn.executemany(
                """
                INSERT OR REPLACE INTO matches
                (event_id, league, sport, kickoff, home, away, home_score, away_score, outcome, odds_home, odds_draw, odds_away, odds_provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows_to_upsert,
            )
            inserted_by_sport[sp_slug] = len(rows_to_upsert)

    conn.commit()
    conn.close()
    return inserted_by_sport


def scan_sportradar_european_sports(
    date_ymd: str | None = None,
    min_prob: float = 0.68,
    max_picks_per_sport: int = 5,
    elo_by_lg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Scan high-frequency European sports on Sportradar StatsHub (`Handball=6`, `Darts=22`, `Table Tennis=20`, `Snooker=19`, `MMA=117`)
    combining Tipico (`_bookmakerId=176`) + Sportradar Main UOF (`_bookmakerId=0`) odds with historical SQLite Elo (`elo_by_lg`) and Last-10 Form (`stats_match_form`)."""
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
                    st = m.get("status")
                    st_id = int(st.get("_id") or 0) if isinstance(st, dict) else 0
                    if st_id not in (0, 61):  # Skip finished or in-play matches
                        continue
                    mid = str(m.get("_id") or "")
                    if not mid:
                        continue
                    tip_entry = mkt_tip.get(mid) or {}
                    uof_entry = mkt_uof.get(mid) or {}
                    is_tipico_src = bool(tip_entry.get("markets"))
                    # For Handball (or any sport where Tipico's bookmaker feed is active), strictly require
                    # Tipico market availability so we never recommend unbettable UOF-only minor leagues (e.g. Swedish Handbollsligan)
                    if (sp_slug == "handball" or mkt_tip) and not is_tipico_src:
                        continue
                    raw_mkts = (tip_entry.get("markets") or []) or (uof_entry.get("markets") or [])
                    if not raw_mkts:
                        continue
                    parsed_m = parse_tipico_prematch_markets(raw_mkts, flipped=False)
                    oh = parsed_m.get("odds_home")
                    oa = parsed_m.get("odds_away")
                    od = parsed_m.get("odds_draw")
                    if not oh or not oa or min(oh, oa) < 1.12 or min(oh, oa) > 1.72:
                        continue

                    # Compute vig-free market probability (in 3-way Handball, cap draw weight at 6.5% so 3-way draw vig doesn't distort 1X2 favorites)
                    inv_h = 1.0 / float(oh)
                    inv_a = 1.0 / float(oa)
                    inv_d = (
                        min(1.0 / float(od), 0.065)
                        if (od and sp_slug == "handball")
                        else ((1.0 / float(od)) if od else 0.0)
                    )
                    overround = inv_h + inv_a + inv_d
                    p_mkt_h = inv_h / overround
                    p_mkt_a = inv_a / overround
                    side = "H" if p_mkt_h >= p_mkt_a else "A"
                    p_mkt_fav = p_mkt_h if side == "H" else p_mkt_a
                    best_o = float(oh if side == "H" else oa)
                    min_mkt_floor = 0.59 if sp_slug == "handball" else (min_prob - 0.04)
                    if p_mkt_fav < min_mkt_floor:
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
                        "ko_uts": int(dt_uts),
                        "home": h_name,
                        "away": a_name,
                        "h_uid": (teams.get("home") or {}).get("uid"),
                        "a_uid": (teams.get("away") or {}).get("uid"),
                        "side": side,
                        "pick": h_name if side == "H" else a_name,
                        "p_mkt": round(p_mkt_fav, 4),
                        "best_odds": round(best_o, 2),
                        "is_tipico": is_tipico_src,
                    })

        # Sort by highest market conviction & Tipico availability, then enrich top candidates with `stats_match_form` + SQLite Elo + Per-Sport Gate
        from .sport_models import evaluate_european_sport_gate

        sport_cands.sort(key=lambda x: (1 if x["is_tipico"] else 0, x["p_mkt"]), reverse=True)
        lg_elo = (elo_by_lg or {}).get(sp_slug)
        for cand in sport_cands[: max_picks_per_sport * 3]:
            if len([p for p in picks_out if p["sport"] == sp_slug]) >= max_picks_per_sport:
                break
            mf = fetch_statshub_gismo("stats_match_form", cand["mid"], ttl_sec=1800.0) or {}
            t_forms = mf.get("teams") or {}
            h_f_obj = t_forms.get("home") or {}
            a_f_obj = t_forms.get("away") or {}
            h_f_list = h_f_obj.get("form") or []
            a_f_list = a_f_obj.get("form") or []
            h_wr = (sum(1.0 for x in h_f_list if x.get("type") == "W") / len(h_f_list)) if h_f_list else 0.5
            a_wr = (sum(1.0 for x in a_f_list if x.get("type") == "W") / len(a_f_list)) if a_f_list else 0.5
            fav_wr = h_wr if cand["side"] == "H" else a_wr
            form_diff_fav = (h_wr - a_wr) if cand["side"] == "H" else (a_wr - h_wr)
            # In Sportradar `stats_match_form`, `form[0]` is the most recent match (`form[:3]` are the 3 most recent matches, matching `streak`)
            h_r3 = (sum(1.0 for x in h_f_list[:3] if x.get("type") == "W") / len(h_f_list[:3])) if len(h_f_list) >= 3 else 0.5
            a_r3 = (sum(1.0 for x in a_f_list[:3] if x.get("type") == "W") / len(a_f_list[:3])) if len(a_f_list) >= 3 else 0.5
            recent3_diff_fav = ((h_r3 - a_r3) if cand["side"] == "H" else (a_r3 - h_r3)) if (len(h_f_list) >= 3 and len(a_f_list) >= 3) else None
            fav_st_obj = (h_f_obj.get("streak") if cand["side"] == "H" else a_f_obj.get("streak")) or {}
            dog_st_obj = (a_f_obj.get("streak") if cand["side"] == "H" else h_f_obj.get("streak")) or {}
            fav_loss_streak = int(fav_st_obj.get("value") or 0) if fav_st_obj.get("type") == "L" else 0
            dog_win_streak = int(dog_st_obj.get("value") or 0) if dog_st_obj.get("type") == "W" else 0

            # Check `stats_team_lastx/{uid}/10` for Table Tennis & Darts to measure hours since last match,
            # 3.5h session set workload, 5-set decider hangover, and direct head-to-head result vs today's opponent
            fav_hours_since_last: float | None = None
            dog_hours_since_last: float | None = None
            fav_session_sets_3h: int | None = None
            fav_last_lost_5set: bool = False
            fav_lost_last_h2h: bool = False
            if sp_slug in ("table_tennis", "darts", "snooker") and cand.get("ko_uts"):
                fav_uid = cand.get("h_uid") if cand["side"] == "H" else cand.get("a_uid")
                dog_uid = cand.get("a_uid") if cand["side"] == "H" else cand.get("h_uid")
                for is_fav_u, p_uid in ((True, fav_uid), (False, dog_uid)):
                    if not p_uid:
                        continue
                    lx_d = fetch_statshub_gismo("stats_team_lastx", f"{p_uid}/10", ttl_sec=1800.0) or {}
                    prior_ms = [
                        m_x
                        for m_x in (lx_d.get("matches") or [])
                        if int(((m_x.get("time") or {}).get("uts")) or 0) < int(cand["ko_uts"])
                        and str(m_x.get("_id")) != str(cand["mid"])
                    ]
                    prior_ms.sort(key=lambda m_x: int(((m_x.get("time") or {}).get("uts")) or 0), reverse=True)
                    if prior_ms:
                        max_prev_uts = int(((prior_ms[0].get("time") or {}).get("uts")) or 0)
                        hrs_gap = round((int(cand["ko_uts"]) - max_prev_uts) / 3600.0, 2)
                        if is_fav_u:
                            fav_hours_since_last = hrs_gap
                            sess_sets = 0
                            seen_h2h = False
                            for idx_m, m_x in enumerate(prior_ms):
                                m_uts = int(((m_x.get("time") or {}).get("uts")) or 0)
                                tms_x = m_x.get("teams") or {}
                                h_uid_x = (tms_x.get("home") or {}).get("uid")
                                a_uid_x = (tms_x.get("away") or {}).get("uid")
                                is_h_x = (h_uid_x == p_uid)
                                opp_uid_x = a_uid_x if is_h_x else h_uid_x
                                rh_x = int(((m_x.get("result") or {}).get("home")) or 0)
                                ra_x = int(((m_x.get("result") or {}).get("away")) or 0)
                                my_s = rh_x if is_h_x else ra_x
                                op_s = ra_x if is_h_x else rh_x
                                if idx_m == 0 and my_s < op_s and (my_s + op_s) == 5 and sp_slug == "table_tennis":
                                    fav_last_lost_5set = True
                                if not seen_h2h and dog_uid and opp_uid_x == dog_uid:
                                    seen_h2h = True
                                    if my_s < op_s:
                                        fav_lost_last_h2h = True
                                if (int(cand["ko_uts"]) - m_uts) <= int(3.5 * 3600):
                                    sess_sets += (my_s + op_s)
                            fav_session_sets_3h = sess_sets
                        else:
                            dog_hours_since_last = hrs_gap

            p_elo_fav = 0.50
            if lg_elo is not None:
                p_elo_h = float(lg_elo.p_home_win_or_draw_free(cand["home"], cand["away"]))
                p_elo_fav = p_elo_h if cand["side"] == "H" else (1.0 - p_elo_h)
            passed, p_model, ev_pct = evaluate_european_sport_gate(
                sport_slug=sp_slug,
                p_mkt=cand["p_mkt"],
                p_elo_fav=p_elo_fav,
                form_diff_fav=form_diff_fav,
                best_odds=cand["best_odds"],
                is_tipico=cand["is_tipico"],
                n_form_home=len(h_f_list),
                n_form_away=len(a_f_list),
                min_prob=min_prob,
                recent3_diff_fav=recent3_diff_fav,
                fav_loss_streak=fav_loss_streak,
                dog_win_streak=dog_win_streak,
                fav_hours_since_last=fav_hours_since_last,
                dog_hours_since_last=dog_hours_since_last,
                fav_wr=fav_wr,
                fav_session_sets_3h=fav_session_sets_3h,
                fav_last_lost_5set=fav_last_lost_5set,
                fav_lost_last_h2h=fav_lost_last_h2h,
            )
            if not passed:
                continue
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
                "tier": "banker_70pct" if cand["is_tipico"] else "high_conf",
                "p_model": round(p_model, 4),
                "p_mkt": cand["p_mkt"],
                "best_odds": cand["best_odds"],
                "ev_pct": ev_pct,
                "composite_score": round(p_model, 4),
                "bookmaker_source": "Primary" if cand["is_tipico"] else "Consensus",
                "form_diff_fav": round(form_diff_fav, 3),
            })
    return picks_out


def fetch_live_match_timelinedelta(
    home: str,
    away: str,
    sport: str = "tennis",
    date_ymd: str | None = None,
) -> dict[str, Any]:
    """Query Sportradar's 3-second real-time `match_timelinedelta/{matchId}` stream for an ongoing or finished match.
    Returns live sets/goals, period breakdown (`p1`..`p5`), current tennis point score (`gamescore`: `15-30`, server `1`/`2`),
    live status (`1st set`, `2nd half`, `Ended`), and final winner (`H`/`A`/`D`) when completed."""
    base_ymd = date_ymd or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_candidates = [base_ymd]
    try:
        dt_b = datetime.strptime(base_ymd[:10], "%Y-%m-%d")
        date_candidates.append((dt_b + timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass
    matched_m = None
    flipped = False
    for d_cand in date_candidates:
        flat = get_daily_tipico_match_index(sport=sport, date_ymd=d_cand)
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
        if matched_m:
            break
    if not matched_m:
        return {}

    mid = matched_m.get("_id")
    if not mid:
        return {}
    td = fetch_statshub_gismo("match_timelinedelta", str(mid), client_alias="sportradar", ttl_sec=3.0)
    if not isinstance(td, dict) or not isinstance(td.get("match"), dict):
        td = {"match": matched_m, "events": []}

    m = td["match"]
    st_obj = m.get("status") or {}
    st_id = int(st_obj.get("_id") or 0)
    st_name = str(st_obj.get("name") or st_obj.get("shortName") or "LIVE")
    dt_uts_m = ((m.get("_dt") or matched_m.get("_dt") or {}).get("uts")) or 0
    start_utc_m = (
        datetime.fromtimestamp(int(dt_uts_m), tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        if dt_uts_m
        else None
    )
    if st_id == 70:  # cancelled
        return {}
    if st_id in (0, 60, 61):  # not_started / postponed / delayed
        return {
            "sr_match_id": mid,
            "sr_season_id": matched_m.get("_seasonid"),
            "status_id": st_id,
            "state": "pre",
            "status_desc": st_name,
            "start_utc": start_utc_m,
            "outcome": None,
        }

    is_finished = st_id in (91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 110, 111, 120)
    res_obj = m.get("result") or {}
    raw_h = res_obj.get("away" if flipped else "home")
    raw_a = res_obj.get("home" if flipped else "away")
    # Status 22 = "About to start" (players not yet playing points; result is None). Treat as pre-match ('pre') until first point/game starts!
    if st_id == 22 and raw_h is None and raw_a is None and not m.get("periods"):
        return {
            "sr_match_id": mid,
            "sr_season_id": matched_m.get("_seasonid"),
            "status_id": st_id,
            "state": "pre",
            "status_desc": st_name,
            "start_utc": start_utc_m,
            "outcome": None,
        }
    h_main = int(raw_h) if raw_h is not None else 0
    a_main = int(raw_a) if raw_a is not None else 0

    periods = m.get("periods") or {}
    period_strs: list[str] = []
    if isinstance(periods, dict):
        for pk in ("p1", "p2", "p3", "p4", "p5", "ft", "ap"):
            p_val = periods.get(pk)
            if isinstance(p_val, dict) and p_val.get("home") is not None and p_val.get("away") is not None:
                if pk in ("ft", "ap") and sport == "soccer":
                    continue
                ph = int(p_val["away" if flipped else "home"])
                pa = int(p_val["home" if flipped else "away"])
                period_strs.append(f"{ph}-{pa}")

    gs = m.get("gamescore") or {}
    pt_str = ""
    if not is_finished and isinstance(gs, dict) and (gs.get("home") is not None or gs.get("away") is not None):
        g_h = gs.get("away" if flipped else "home", 0)
        g_a = gs.get("home" if flipped else "away", 0)
        srv = str(gs.get("service") or "")
        srv_h = "🎾" if ((srv == "1" and not flipped) or (srv == "2" and flipped)) else ""
        srv_a = "🎾" if ((srv == "2" and not flipped) or (srv == "1" and flipped)) else ""
        if str(g_h) != "0" or str(g_a) != "0" or srv_h or srv_a:
            pt_str = f" · Pt {srv_h}{g_h}-{g_a}{srv_a}"

    if period_strs:
        score_str = f"{h_main}-{a_main} ({', '.join(period_strs)}{pt_str})"
    else:
        score_str = f"{h_main}-{a_main} ({st_name})" if not is_finished else f"{h_main}-{a_main}"

    outcome: str | None = None
    if is_finished:
        win_raw = res_obj.get("winner")
        if win_raw == "home":
            outcome = "A" if flipped else "H"
        elif win_raw == "away":
            outcome = "H" if flipped else "A"
        elif h_main != a_main:
            outcome = "H" if h_main > a_main else "A"
        elif sport == "soccer":
            outcome = "D"

    return {
        "sr_match_id": mid,
        "sr_season_id": matched_m.get("_seasonid"),
        "status_id": st_id,
        "home_uid": ((matched_m.get("teams") or {}).get("away" if flipped else "home") or {}).get("uid"),
        "away_uid": ((matched_m.get("teams") or {}).get("home" if flipped else "away") or {}).get("uid"),
        "state": "post" if is_finished else "in",
        "status_desc": st_name,
        "score_str": score_str,
        "home_score": h_main,
        "away_score": a_main,
        "periods": period_strs,
        "point_score": pt_str.strip(" ·"),
        "outcome": outcome,
    }


def evaluate_inplay_goal_timing_edge(
    season_id: int | str | None,
    h_uid: int | str | None,
    a_uid: int | str | None,
    match_id: int | str | None,
    status_id: int = 0,
    home_score: int = 0,
    away_score: int = 0,
) -> dict[str, Any]:
    """Combine 15-minute goal interval profiles (`stats_season_teamscoringconceding`) and live dangerous-attack pressure (`match_situations`)
    to detect 1st-Half Goal (`1H_GOAL_EDGE`) or Late-Goal (`76-90m` `LATE_GOAL_SURGE_EDGE`) opportunities on ongoing Football matches."""
    if not season_id or not h_uid or not a_uid:
        return {}
    gi_h = fetch_team_goal_intervals(season_id, h_uid, limit=10)
    gi_a = fetch_team_goal_intervals(season_id, a_uid, limit=10)
    if not gi_h or not gi_a:
        return {}
    lp = fetch_live_match_situations_pressure(match_id) if match_id else {}
    tot_da = int(lp.get("home_dangerous_attacks") or 0) + int(lp.get("away_dangerous_attacks") or 0)
    h_1h_pct = float(gi_h.get("scoring_in_1h_pct") or 0.0)
    a_1h_pct = float(gi_a.get("scoring_in_1h_pct") or 0.0)
    comb_1h_pct = round(100.0 * (1.0 - (1.0 - h_1h_pct / 100.0) * (1.0 - a_1h_pct / 100.0)), 1)
    comb_late_avg = round(float(gi_h.get("late_76_90_total_avg") or 0.0) + float(gi_a.get("late_76_90_total_avg") or 0.0), 2)

    signal = None
    badge_label = ""
    # Status 6 = 1st half, Status 31 = Halftime, Status 7 = 2nd half
    if status_id == 6 and (home_score + away_score == 0) and comb_1h_pct >= 78.0:
        signal = "1H_GOAL_EDGE"
        badge_label = f"⏱️ 1H GOAL EDGE ({comb_1h_pct:.0f}% 1H Rate)"
    elif status_id in (7, 31) and abs(home_score - away_score) <= 1 and comb_late_avg >= 0.85:
        signal = "LATE_GOAL_SURGE_EDGE"
        da_str = f" · {tot_da} Danger Att" if tot_da > 0 else ""
        badge_label = f"🔥 76–90m LATE GOAL EDGE ({comb_late_avg:.2f}g Avg{da_str})"
    return {
        "signal": signal,
        "badge_label": badge_label,
        "combined_1h_goal_pct": comb_1h_pct,
        "combined_76_90_goal_avg": comb_late_avg,
        "total_dangerous_attacks": tot_da,
    }


def fetch_player_lastx_form(team_uid: int | str | None, limit: int = 6) -> list[dict[str, Any]]:
    """Fetch a player's or team's last `limit` matches directly from Sportradar `stats_team_lastx/{uid}/{limit}`
    when the player has no prior matches in our local `betscout.db` database (e.g. ITF/WTA 125K qualifiers)."""
    if not team_uid:
        return []
    data = fetch_statshub_gismo(f"stats_team_lastx/{team_uid}/{limit}", ttl_sec=1800.0)
    if not isinstance(data, dict):
        return []
    out: list[dict[str, Any]] = []
    for m in (data.get("matches") or [])[:limit]:
        res = m.get("result") or {}
        if res.get("home") is None or res.get("away") is None:
            continue
        teams = m.get("teams") or {}
        th = (teams.get("home") or {}).get("name") or ""
        ta = (teams.get("away") or {}).get("name") or ""
        h_uid_m = (teams.get("home") or {}).get("uid")
        is_h = str(h_uid_m) == str(team_uid)
        opp_raw = ta if is_h else th
        if "," in opp_raw:
            p_last, p_first = [x.strip() for x in opp_raw.split(",", 1)]
            opp_name = f"{p_first} {p_last}".strip()
        else:
            opp_name = opp_raw
        hs, as_ = int(res["home"]), int(res["away"])
        w_side = res.get("winner")
        if w_side in ("home", "away"):
            won = (is_h and w_side == "home") or (not is_h and w_side == "away")
            res_char = "W" if won else "L"
        else:
            res_char = "D" if hs == as_ else ("W" if ((is_h and hs > as_) or (not is_h and as_ > hs)) else "L")
        uts = ((m.get("_dt") or {}).get("uts")) or 0
        dt_str = datetime.fromtimestamp(int(uts), tz=timezone.utc).strftime("%Y-%m-%d") if uts else "Recent"
        out.append({
            "date": dt_str,
            "opp": opp_name,
            "venue": "H" if is_h else "A",
            "result": res_char,
            "score": f"{hs}-{as_}",
        })
    return out


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
    date_candidates = [date_ymd]
    try:
        dt_b = datetime.strptime(date_ymd[:10], "%Y-%m-%d")
        date_candidates.append((dt_b + timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass

    matched_m: dict[str, Any] | None = None
    matched_tourn = ""
    flipped = False

    for d_cand in date_candidates:
        flat = get_daily_tipico_match_index(sport=sport, date_ymd=d_cand)
        for entry in flat:
            th, ta = entry["home"], entry["away"]
            if _names_match(home, th) and _names_match(away, ta):
                matched_m = entry["match_obj"]
                matched_tourn = entry["tournament"]
                flipped = False
                break
            if _names_match(home, ta) and _names_match(away, th):
                matched_m = entry["match_obj"]
                matched_tourn = entry["tournament"]
                flipped = True
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
        markets_parsed["bookmaker"] = "Primary + Consensus"
    elif has_tipico:
        markets_parsed["bookmaker"] = "Primary Bookmaker"
    elif has_sr_uof:
        markets_parsed["bookmaker"] = "Market Consensus"

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
        "home_uid": h_uid,
        "away_uid": a_uid,
        "tournament": matched_tourn,
        "primary_markets": markets_parsed,
        "consensus_markets": sr_uof_parsed,
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
