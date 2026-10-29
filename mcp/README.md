# `@betscout/mcp-server` — BetScout Quant API & Sports Intelligence MCP Server

Production Model Context Protocol (MCP) server exposing **BetScout's** multi-sport quantitative edge engine, 2-leg/3-leg Banker Profitability Boosters, Dixon-Coles & Markov exact-score/set-score dutching, 56-sport Match Center dossiers, and verified out-of-sample Paper-Betting Ledger to LLM agents (Claude Desktop, VS Code Copilot, Cursor, and GSD).

---

## Exposed MCP Tools (7 Deep, Model-Oriented Tools)

| Tool | Purpose | Pagination / Key Inputs |
| :--- | :--- | :--- |
| **`get_daily_banker_picks`** | Retrieve active pre-match & live high-conviction banker picks across Football, Tennis, NBA, NHL, NFL, Handball, Table Tennis & Darts | `sport`, `min_odds`, `min_win_prob`, `mispriced_only`, `limit`, opaque `cursor` |
| **`get_banker_profit_boosters`** | Construct 2-leg & 3-leg high-probability (`>=72%`, `1.10–1.48` odds) combo tickets with ¼-Kelly EUR stake sizing | `budget_eur`, `max_combos` |
| **`analyze_matchup`** | On-demand live quantitative analysis (7-factor Football / 8-feature Tennis + set-score probabilities + turnaround warnings) for any `Player1 vs Player2` or `Home vs Away` | `query` (e.g. `"Medvedev vs Norrie"`) |
| **`calculate_exact_score_dutching`** | Equal-payout EUR stake split across top Football exact scores (`1:0 / 2:0 / 2:1`) or Tennis set scores (`2:0 + 2:1`) | `query`, `stake_eur` |
| **`get_match_center_dossier`** | Full Match Center dossier (`match_id` or `home`+`away`): 2-way/3-way win probabilities, 28 Correct Score markets, H2H edge, W/D/L form, surface splits & missing players | `match_id` or `home` + `away` |
| **`search_daily_fixtures`** | Search scheduled/live/finished fixtures and odds across 56 sports for a date (`YYYY-MM-DD`) | `sport`, `date_ymd`, `query`, `limit`, opaque `cursor` |
| **`get_paper_ledger_roi`** | Verified out-of-sample Paper-Betting Ledger summary (`74W–1L`, ROI%, CLV%, by-sport breakdown) & resolved match history | `status`, `sport`, `limit`, opaque `cursor` |

---

## Multi-Tier Caching Architecture (Reducing Remote Gismo Lookups)

Both `@betscout/mcp-server`, `@betscout/sdk`, and the Python `api/` backend share a **multi-tier caching architecture**:
1. **L1 In-Memory LRU Cache + Request Coalescing**: Deduplicates concurrent requests and caches responses in memory (`2,000` max entries).
2. **Smart Endpoint-Aware TTLs**:
   - **Static / Career Reference Feeds (`3,600s` / 1h)**: `config_*`, `tennis_calendar`, `stats_team_info`, `tennis_team_surfacestats`, `stats_team_versus`, `stats_season_meta`, `stats_season_venues`.
   - **Historical / Season Aggregates (`1,200s` / 20m)**: `stats_team_lastx`, `stats_team_lastxextended`, `stats_season_tables`, `stats_season_goals`, `stats_season_overunder`, `stats_season_injuries`, `stats_team_streaks`, `stats_team_squad`.
   - **Pre-Match Schedules & Markets (`600s` / 10m)**: `unified_sport_matches`, `match_info_statshub`, `match_markets/*/prematch`.
   - **Live Delta Feeds (`max(_maxage, 5s)`)**: `match_timelinedelta`, `match_detailsextended`.
3. **Negative Caching (`120s`)**: Non-existent or exception feeds (e.g. `match_markets/live` on pre-match fixtures) are cached negatively for 2 minutes so missing feeds never trigger repeated remote HTTP hits.
4. **L2 Persistent SQLite Cache (`gismo_http_cache` in `data/betscout.db`)**: Persists Gismo responses across CLI runs and server restarts, with stale-while-error fallback.

---

## Quick Start & Configuration

### 1. Build & Test (`mcp/`)

```bash
cd mcp
npm install
npm run build
npm test
```

### 2. Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `BETSCOUT_API_URL` | `http://127.0.0.1:8090` | Base URL of the BetScout API (`http://127.0.0.1:8090` locally or `https://betscout.app` in production) |
| `BETSCOUT_API_KEY` | *(optional locally)* | Tier 3 Quant API key (`bs_live_...`) for authenticated `/api/v1/*` and `/mcp` access |

### 3. Remote MCP Quick Configuration (`https://betscout.app/mcp`)

#### Claude (`Claude Code CLI` or `.mcp.json`)
```bash
claude mcp add --transport http betscout https://betscout.app/mcp \
  --header "Authorization: Bearer bs_live_YOUR_API_KEY"
```
```json
{
  "mcpServers": {
    "betscout": {
      "type": "http",
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}
```

#### VS Code GitHub Copilot (`.vscode/mcp.json`)
```json
{
  "servers": {
    "betscout": {
      "type": "http",
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}
```

#### Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "betscout": {
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}
```

#### Windsurf / Cline (`mcp_config.json`)
```json
{
  "mcpServers": {
    "betscout": {
      "serverUrl": "https://betscout.app/mcp",
      "headers": {
        "X-API-Key": "bs_live_YOUR_API_KEY"
      }
    }
  }
}
```

### 4. Streamable HTTP Endpoint (`https://betscout.app/mcp`)

- `GET https://betscout.app/mcp` — Discovery & tool catalog
- `POST https://betscout.app/mcp` — JSON-RPC 2.0 (`initialize`, `ping`, `tools/list`, `tools/call`)
- Interactive Web Docs: `https://betscout.app/api/docs`
