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

    # 3. Fetch team streaks (`stats_team_streaks`) for soccer/team sports
    streaks_summary: dict[str, list[str]] = {"home": [], "away": []}
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
        "streaks": streaks_summary,
        "tennis_surface_records": tennis_surface_records,
    }
