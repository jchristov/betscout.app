"""Universal config-driven ingestion, enrichment, and on-the-fly quality normalization engine.

Features:
  * Reads `ingestion_config.json` by default.
  * Automatically registers any new sport/league ingested on demand into `ingestion_config.json`.
  * Prevents duplicate work and re-ingestion: skips any `event_id` already completed in `matches`,
    and in periodic incremental mode only queries matchdays from the league's watermark date forward.
  * Populates both `matches` and `match_details` for 3-way soccer, 2-way team sports (NBA, NHL, NFL, MLB),
    and ATP/WTA tennis, then runs `adjust_and_normalize_db` and `quality.run` on the fly.
"""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .enrich import DETAILS_SCHEMA, _extract_soccer_details, _extract_two_way_details, infer_surface
from .espn import LEAGUE_LABELS, EspnClient, League, resolve_league
from .ingest import (
     _competitor,
    _parse_soccer_event,
    _parse_tennis_event,
    calendar_days,
    deduplicate_same_day,
    open_store,
    upsert,
)
from .quality import adjust_and_normalize_db, run as run_quality

DEFAULT_SOURCES: list[dict[str, Any]] = [
    {"sport": "soccer", "league": "eng.1", "name": "Premier League", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "esp.1", "name": "La Liga", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "ger.1", "name": "Bundesliga", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "ita.1", "name": "Serie A", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "fra.1", "name": "Ligue 1", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "aut.1", "name": "Austrian Bundesliga", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "soccer", "league": "ned.1", "name": "Eredivisie", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "soccer", "league": "por.1", "name": "Primeira Liga", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "soccer", "league": "uefa.champions", "name": "UEFA Champions League", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "soccer", "league": "uefa.europa", "name": "UEFA Europa League", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "soccer", "league": "uefa.europa.conf", "name": "UEFA Conference League", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "tennis", "league": "atp", "name": "ATP Tour", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "tennis", "league": "wta", "name": "WTA Tour", "enabled": True, "default_years": [2022, 2023, 2024, 2025, 2026]},
    {"sport": "basketball", "league": "nba", "name": "NBA", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "hockey", "league": "nhl", "name": "NHL", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "football", "league": "nfl", "name": "NFL", "enabled": True, "default_years": [2025, 2026]},
    {"sport": "baseball", "league": "mlb", "name": "MLB", "enabled": True, "default_years": [2025, 2026]},
]


def load_or_init_config(config_path: Path, db_path: Path | None = None) -> dict[str, Any]:
    """Load `ingestion_config.json` or initialize it with DEFAULT_SOURCES and current DB watermarks."""
    if config_path.exists():
        cfg = json.loads(config_path.read_text())
    else:
        cfg = {
            "version": 1,
            "description": "Descriptor of all configured sports and leagues for periodic & historical ingestion.",
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": DEFAULT_SOURCES,
        }
    if db_path and db_path.exists():
        _sync_config_watermarks(cfg, db_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2))
    return cfg


def _sync_config_watermarks(cfg: dict[str, Any], db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    stats = {}
    for lg, sp, cnt, min_ko, max_ko, p_cnt in conn.execute(
        """
        SELECT league, sport, COUNT(*), MIN(kickoff), MAX(kickoff), SUM(odds_home IS NOT NULL)
        FROM matches
        WHERE outcome IS NOT NULL
        GROUP BY league, sport
        """
    ).fetchall():
        stats[lg] = {
            "sport": sp,
            "total_records": cnt,
            "priced_records": p_cnt or 0,
            "first_kickoff": min_ko,
            "last_ingested_kickoff": max_ko,
            "last_ingested_ymd": max_ko[:10].replace("-", "") if max_ko else None,
        }
    conn.close()

    by_league = {s["league"]: s for s in cfg.get("sources", [])}
    for lg, st in stats.items():
        if lg not in by_league:
            entry = {
                "sport": st["sport"],
                "league": lg,
                "name": LEAGUE_LABELS.get(lg, lg),
                "enabled": True,
                "default_years": [2025, 2026],
            }
            cfg.setdefault("sources", []).append(entry)
            by_league[lg] = entry
        by_league[lg].update({
            "total_records": st["total_records"],
            "priced_records": st["priced_records"],
            "first_kickoff": st["first_kickoff"],
            "last_ingested_kickoff": st["last_ingested_kickoff"],
            "last_ingested_ymd": st["last_ingested_ymd"],
        })
    cfg["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_leagues_in_config(config_path: Path, db_path: Path, leagues: list[League]) -> dict[str, Any]:
    """Ensure any on-demand League objects are registered in `ingestion_config.json`."""
    cfg = load_or_init_config(config_path, db_path)
    existing = {s["league"]: s for s in cfg.get("sources", [])}
    for lg in leagues:
        if lg.key not in existing:
            entry = {
                "sport": lg.sport,
                "league": lg.key,
                "name": LEAGUE_LABELS.get(lg.key, lg.key),
                "enabled": True,
                "default_years": [2025, 2026],
                "total_records": 0,
                "priced_records": 0,
                "first_kickoff": None,
                "last_ingested_kickoff": None,
                "last_ingested_ymd": None,
            }
            cfg.setdefault("sources", []).append(entry)
            existing[lg.key] = entry
        else:
            existing[lg.key]["enabled"] = True
    config_path.write_text(json.dumps(cfg, indent=2))
    return cfg


def _resolve_days_for_league(
    client: EspnClient,
    league: League,
    source_cfg: dict[str, Any],
    existing_count: int,
    last_ymd: str | None,
    mode: str,
    years: list[int] | None,
    days_back: int | None,
    from_ymd: str | None,
    to_ymd: str | None,
) -> list[str]:
    """Determine exact YYYYMMDD dates to query for `league` without redundant re-scanning."""
    today_dt = datetime.now(timezone.utc)
    today_ymd = today_dt.strftime("%Y%m%d")

    if mode == "days" and days_back:
        start_ymd = (today_dt - timedelta(days=days_back)).strftime("%Y%m%d")
        end_ymd = today_ymd
        cand_years = sorted({int(start_ymd[:4]), int(end_ymd[:4]), int(start_ymd[:4]) - 1})
        cal = sorted({d for d in cand_years for d in calendar_days(client, league, d)})
        matched = [d for d in cal if start_ymd <= d <= end_ymd]
        if len(matched) < max(5, days_back // 3) and days_back <= 90:
            return [(today_dt - timedelta(days=d)).strftime("%Y%m%d") for d in range(days_back, 0, -1)]
        return matched

    if mode == "range" and from_ymd:
        end_ymd = to_ymd or today_ymd
        y0, y1 = int(from_ymd[:4]), int(end_ymd[:4])
        cand_years = list(range(y0 - 1, y1 + 1))
        cal = sorted({d for y in cand_years for d in calendar_days(client, league, y)})
        return [d for d in cal if from_ymd <= d <= end_ymd]

    if mode == "all_history":
        target_years = [2022, 2023, 2024, 2025, 2026]
        return sorted({d for y in target_years for d in calendar_days(client, league, y)})

    if mode == "years" and years:
        return sorted({d for y in years for d in calendar_days(client, league, y)})

    # Default mode == "incremental":
    # If the league already has ingested records and a watermark `last_ymd`, only scan from `last_ymd - 2 days` forward!
    # If the league is newly added (`existing_count == 0`), scan its `default_years` (or last 60 days if configured).
    if existing_count > 0 and last_ymd:
        wm_dt = datetime.strptime(last_ymd, "%Y%m%d") - timedelta(days=2)
        start_ymd = wm_dt.strftime("%Y%m%d")
        cand_years = sorted({wm_dt.year - 1, wm_dt.year, today_dt.year})
        cal = sorted({d for y in cand_years for d in calendar_days(client, league, y)})
        return [d for d in cal if start_ymd <= d <= today_ymd]

    def_years = source_cfg.get("default_years") or [2025, 2026]
    return sorted({d for y in def_years for d in calendar_days(client, league, y)})


def ingest_universal(
    db_path: Path,
    cache_dir: Path,
    config_path: Path,
    leagues: list[League] | None = None,
    mode: str = "incremental",
    years: list[int] | None = None,
    days_back: int | None = None,
    from_ymd: str | None = None,
    to_ymd: str | None = None,
    workers: int = 8,
) -> dict[str, Any]:
    """Universal ingestion entrypoint:
      1. Loads/updates `ingestion_config.json`
      2. Skips already-ingested `event_id`s to prevent duplicate work
      3. Ingests both `matches` and `match_details` concurrently
      4. Runs `adjust_and_normalize_db` and `quality.run` on the fly
      5. Updates `ingestion_config.json` watermarks & record counts
    """
    conn = open_store(db_path)
    conn.executescript(DETAILS_SCHEMA)
    conn.close()

    if leagues:
        cfg = ensure_leagues_in_config(config_path, db_path, leagues)
        target_keys = {lg.key for lg in leagues}
    else:
        cfg = load_or_init_config(config_path, db_path)
        target_keys = {s["league"] for s in cfg.get("sources", []) if s.get("enabled", True)}

    sources_by_key = {s["league"]: s for s in cfg.get("sources", [])}
    target_leagues = [
        League(k, sources_by_key[k]["sport"], k)
        for k in [s["league"] for s in cfg.get("sources", []) if s["league"] in target_keys]
    ]

    client = EspnClient(cache_dir)
    new_ingested: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for lg in target_leagues:
            conn = sqlite3.connect(db_path)
            existing_ids = {
                str(r[0])
                for r in conn.execute(
                    "SELECT event_id FROM matches WHERE league = ? AND outcome IS NOT NULL",
                    (lg.key,),
                ).fetchall()
            }
            max_ko_row = conn.execute(
                "SELECT MAX(kickoff) FROM matches WHERE league = ? AND outcome IS NOT NULL",
                (lg.key,),
            ).fetchone()
            conn.close()

            last_ymd = max_ko_row[0][:10].replace("-", "") if (max_ko_row and max_ko_row[0]) else None
            src_cfg = sources_by_key.get(lg.key, {})
            days = _resolve_days_for_league(
                client=client,
                league=lg,
                source_cfg=src_cfg,
                existing_count=len(existing_ids),
                last_ymd=last_ymd,
                mode=mode,
                years=years,
                days_back=days_back,
                from_ymd=from_ymd,
                to_ymd=to_ymd,
            )
            if not days:
                new_ingested[lg.key] = 0
                continue

            boards = list(pool.map(lambda d: client.scoreboard(lg, d), days))
            new_matches = []
            new_details = []

            if lg.sport != "tennis":
                finished_evs = []
                seen_batch: set[str] = set()
                for b in boards:
                    for ev in b.get("events") or []:
                        eid = str(ev.get("id") or "")
                        if not eid or eid in existing_ids or eid in seen_batch:
                            continue
                        if (ev.get("status") or {}).get("type", {}).get("completed"):
                            seen_batch.add(eid)
                            finished_evs.append(ev)

                def _safe_sum(ev: dict[str, Any]) -> dict[str, Any]:
                    try:
                        return client.summary(lg, str(ev["id"]))
                    except Exception:
                        return {}

                summaries = list(pool.map(_safe_sum, finished_evs))
                for ev, summary in zip(finished_evs, summaries):
                    m = _parse_soccer_event(lg, ev, summary)
                    if not m:
                        continue
                    new_matches.append(m)
                    if lg.sport == "soccer":
                        new_details.append(_extract_soccer_details(lg.key, m.event_id, m.kickoff, summary))
                    else:
                        new_details.append(_extract_two_way_details(lg.sport, lg.key, m.event_id, m.kickoff, summary))
            else:
                wanted = {"atp": "mens-singles", "wta": "womens-singles"}.get(lg.key)
                seen_batch = set()
                for b in boards:
                    for tourn in b.get("events") or []:
                        surf = infer_surface(tourn.get("name") or "")
                        is_maj = 1 if tourn.get("major") else 0
                        for grp in tourn.get("groupings") or []:
                            if (grp.get("grouping") or {}).get("slug") != wanted:
                                continue
                            for comp in grp.get("competitions") or []:
                                cid = str(comp.get("id") or "")
                                if not cid or cid in existing_ids or cid in seen_batch:
                                    continue
                                m = _parse_tennis_event(lg, tourn, grp, comp)
                                if not m:
                                    continue
                                seen_batch.add(cid)
                                new_matches.append(m)
                                p1, p2 = _competitor(comp, "home"), _competitor(comp, "away")
                                g1 = sum(float(x.get("value") or 0) for x in ((p1 or {}).get("linescores") or []) if x.get("value") is not None)
                                g2 = sum(float(x.get("value") or 0) for x in ((p2 or {}).get("linescores") or []) if x.get("value") is not None)
                                rnd = (comp.get("round") or {}).get("displayName")
                                new_details.append((
                                    lg.key, m.event_id, "tennis", m.kickoff,
                                    None, None, None, None, None, None, None, None, None, None, None, None, 0,
                                    None, None, None, None, None, None, None, None, None,
                                    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
                                    surf, is_maj, rnd, g1 if (g1 or g2) else None, g2 if (g1 or g2) else None,
                                ))

            if new_matches:
                conn = open_store(db_path)
                conn.executescript(DETAILS_SCHEMA)
                upsert(conn, new_matches)
                if new_details:
                    conn.executemany(
                        "INSERT OR REPLACE INTO match_details VALUES (" + ",".join("?" * 49) + ")",
                        new_details,
                    )
                conn.commit()
                conn.close()
            new_ingested[lg.key] = len(new_matches)

    norm_stats = adjust_and_normalize_db(db_path)
    q_rep = run_quality(db_path)
    _sync_config_watermarks(cfg, db_path)
    config_path.write_text(json.dumps(cfg, indent=2))

    return {
        "mode": mode,
        "new_ingested": new_ingested,
        "normalization": norm_stats,
        "quality_errors": [i for i in q_rep.issues if i.severity == "error"],
        "stats": q_rep.stats,
    }
