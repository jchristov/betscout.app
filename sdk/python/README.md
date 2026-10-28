# `betscout-sdk` (`betscout_sdk`) — Python Sports Data, Player/Team Analytics & Multi-Bookmaker Odds SDK

Standalone Python SDK (`betscout-sdk` v1.1.0, package `betscout_sdk`) with **1:1 feature and method parity** with [`sdk/typescript`](../typescript/README.md) (`@betscout/sdk`).

Supports both **Pythonic `snake_case`** (`client.get_enriched_league_table(...)`, `client.get_match_center_dossier(...)`) and **TypeScript-identical `camelCase`** (`client.getEnrichedLeagueTable(...)`, `client.getMatchCenterDossier(...)`) method names.

---

## Installation, Testing & Examples

```bash
cd sdk/python

# Run pytest test suite
PYTHONPATH=src pytest

# Run CLI quickstart (56 sports, Match #76034538 Dossier, AC Milan Bundle, Enriched Standings, San Siro Venue)
PYTHONPATH=src python3 examples/quickstart.py

# Launch Python Interactive Web Showcase & Match #76034538 Replica Server (http://127.0.0.1:8789/match/76034538)
PYTHONPATH=src python3 examples/showcase_server.py
```

---

## Quickstart Usage

```python
from betscout_sdk import BetScoutClient, get_team_logo_url, get_country_flag_url

client = BetScoutClient(default_channel="eu-retail", default_timezone="Europe:Berlin")

# 1. Full Match Center Dossier (replicating /match/76034538 — Taylor Fritz vs Rinky Hijikata)
dossier = client.get_match_center_dossier(76034538)
print(dossier["match_details"]["values"]["130"])  # Aces (All Match & Set-by-Set)

# 2. Enriched League Standings + Form Table (with goal splits, rank changes & promotions)
table = client.get_enriched_league_table(140782, around_team_uid=2692, slice_size=5)

# 3. Club Intelligence Bundle (profile, 41-man squad, active missing/injured players, 3-5-2 lineup & season stats)
milan = client.get_team_intelligence_bundle(2692, season_id=130971)

# 4. Tennis Player Intelligence Bundle (profile, ATP rank & 2004–2026 surface W-L matrix)
djokovic = client.get_tennis_player_intelligence_bundle(14882)
```
