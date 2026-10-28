"""BetScout Sports Data & Odds SDK (`betscout_sdk`) — Catalogs, Market Identifiers & Outcome Mappings."""

from __future__ import annotations

import re

BOOKMAKER_IDS: dict[str, int] = {
    "CONSENSUS": 0,
    "EU_RETAIL": 176,
}

SERVICE_PROFILES: dict[str, int] = {
    "STATISTICS": 41,
    "EU_RETAIL": 67,
    "GLOBAL_UNLIMITED": 69,
}

MARKET_IDS: dict[str, int] = {
    "MATCH_1X2": 1,
    "DOUBLE_CHANCE": 10,
    "DRAW_NO_BET": 11,
    "EUROPEAN_HANDICAP_3WAY": 14,
    "ASIAN_HANDICAP_2WAY": 16,
    "TOTAL_GOALS": 18,
    "CORRECT_SCORE": 41,
    "CORRECT_SCORE_NAMED": 45,
    "FIRST_HALF_1X2": 60,
    "FIRST_HALF_HANDICAP": 65,
    "FIRST_HALF_TOTAL": 68,
    "SECOND_HALF_HANDICAP": 87,
    "TENNIS_MATCH_WINNER": 186,
    "TENNIS_TOTAL_GAMES": 189,
    "TENNIS_SET_WINNER": 202,
    "US_SPORTS_WINNER_OT": 219,
    "US_SPORTS_SPREAD_OT": 223,
    "US_SPORTS_TOTAL_OT": 225,
    "HOCKEY_WINNER_OT_SO": 406,
}

TENNIS_SURFACE_IDS: dict[str, int] = {
    "ALL_SURFACES": 0,
    "CLAY": 1,
    "HARD_OUTDOOR": 2,
    "INDOOR": 3,
    "GRASS": 4,
}

STAGE_SPORT_IDS: tuple[int, ...] = (
    17,
    40,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    101,
    129,
    131,
    188,
    190,
    191,
)


def is_stage_sport(sport_or_id: str | int) -> bool:
    return resolve_sport_id(sport_or_id) in STAGE_SPORT_IDS


isStageSport = is_stage_sport

PLAYER_STATUS_TYPES: dict[str, int] = {
    "OTHER": 0,
    "INJURED": 1,
    "ILLNESS": 2,
    "YELLOW_CARD_SUSPENSION": 11,
    "YELLOW_RED_CARD_SUSPENSION": 12,
    "RED_CARD_SUSPENSION": 13,
}

SPORTS_CATALOG: dict[int, str] = {
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

SPORT_IDS: dict[str, int] = {
    "soccer": 1,
    "football_soccer": 1,
    "basketball": 2,
    "nba": 2,
    "wnba": 2,
    "baseball": 3,
    "mlb": 3,
    "hockey": 4,
    "ice_hockey": 4,
    "nhl": 4,
    "tennis": 5,
    "atp": 5,
    "wta": 5,
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

CORRECT_SCORE_OUTCOMES: dict[str, str] = {
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


def resolve_sport_id(sport_or_id: str | int) -> int:
    """Resolve a sport slug ('soccer', 'tennis', 'nhl') or numeric ID (1, 5) to a canonical sport_id."""
    if isinstance(sport_or_id, int) and not isinstance(sport_or_id, bool):
        return sport_or_id
    clean = re.sub(r"[\s-]+", "_", str(sport_or_id or "").strip().lower())
    if clean.isdigit():
        return int(clean)
    return SPORT_IDS.get(clean, 1)


resolveSportId = resolve_sport_id
