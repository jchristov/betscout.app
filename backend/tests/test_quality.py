import sqlite3
from pathlib import Path

from betscout.quality import CANONICAL_VIEW, SQL_CHECKS, install_view, run


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "m.sqlite"
    c = sqlite3.connect(db)
    c.executescript("""
        CREATE TABLE matches (event_id TEXT, league TEXT, sport TEXT, kickoff TEXT, home TEXT, away TEXT,
            home_score REAL, away_score REAL, outcome TEXT, odds_home REAL, odds_draw REAL, odds_away REAL,
            odds_provider TEXT, odds_dc_1x REAL, odds_dc_x2 REAL, odds_dc_12 REAL, line_total REAL,
            odds_over REAL, odds_under REAL);
        INSERT INTO matches VALUES ('1','eng.1','soccer','2025-01-01T15:00Z','A','B',2,1,'H',2.0,3.5,4.0,'x',NULL,NULL,NULL,NULL,NULL,NULL);
        INSERT INTO matches VALUES ('2','eng.1','soccer','2025-01-01 15:00','A','B',2,1,'A',2.0,3.5,4.0,'x',NULL,NULL,NULL,NULL,NULL,NULL);
        INSERT INTO matches VALUES ('3','eng.1','soccer','2025-01-02T15:00Z','A','A',1,1,'D',1.45,5.0,1.45,'x',NULL,NULL,NULL,NULL,NULL,NULL);
        INSERT INTO matches VALUES ('4','atp','tennis','2025-01-02T15:00Z','P1','P2',NULL,NULL,'D',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
    """)
    c.commit(); c.close()
    return db


def test_checks_catch_each_planted_problem(tmp_path):
    rep = run(_db(tmp_path))
    found = {i.check for i in rep.issues}
    assert "kickoff_format" in found       # row 2 has a space instead of T and no Z
    assert "score_outcome_mismatch" in found  # row 2: 2-1 recorded as away
    assert "self_match" in found           # row 3
    assert "1x2_overround_out_of_range" in found  # row 3
    assert "outcome_invalid" in found      # tennis draw


def test_canonical_view_has_capability_flags(tmp_path):
    db = _db(tmp_path)
    install_view(db)
    rows = sqlite3.connect(db).execute(
        "SELECT sport, has_draw, has_score, has_1x2 FROM matches_canonical ORDER BY event_id").fetchall()
    assert rows[0] == ("soccer", 1, 1, 1)
    assert rows[-1] == ("tennis", 0, 0, 0)
