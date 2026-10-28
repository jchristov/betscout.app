"""Type definitions and TypedDicts for the BetScout Python SDK (`betscout_sdk`)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

ProviderChannel = Literal["global", "eu-retail", "neutral"]


class SportCatalogItem(TypedDict):
    sportId: int
    name: str


class ParsedPrematchMarkets(TypedDict):
    bookmaker: str
    odds_home: float | None
    odds_draw: float | None
    odds_away: float | None
    double_chance_1x: float | None
    double_chance_x2: float | None
    draw_no_bet_home: float | None
    draw_no_bet_away: float | None
    asian_handicap_line: str | None
    asian_handicap_home: float | None
    asian_handicap_away: float | None
    total_line: float | None
    odds_over: float | None
    odds_under: float | None
    correct_score_odds: dict[str, float]


class TeamMissingPlayerEntry(TypedDict):
    player_id: int
    name: str
    position: str
    shirt_number: str | int | None
    cause: str
    status: str
    status_id: int
    start_date: str | None
    end_date: str | None
    start_uts: int | None
    end_uts: int | None
    is_active: bool


class EnrichedStandingsRow(TypedDict):
    pos: int
    pos_home: int | None
    pos_away: int | None
    change_total: int
    change_home: int
    change_away: int
    team_id: int
    team_uid: int
    team_name: str
    team_abbr: str
    promotion: str | None
    promotion_short: str | None
    played: dict[str, int]
    win: dict[str, int]
    draw: dict[str, int]
    loss: dict[str, int]
    goals_for: dict[str, int]
    goals_against: dict[str, int]
    goal_diff: dict[str, int]
    points: dict[str, int]
    form_total: list[str]
    form_home: list[str]
    form_away: list[str]
    form_entries_total: list[dict[str, Any]]


class EnrichedLeagueTableBundle(TypedDict):
    ok: bool
    season_id: str | int
    season_name: str | None
    current_round: int | None
    max_rounds: int | None
    tiebreak_rules: str | None
    rows: list[EnrichedStandingsRow]
