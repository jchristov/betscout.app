"""Decision-model signal extractor for pre-match injury, lineup, and morale news.

Default backend: `laya` (`data/laya_sports_ckpt` sports-distilled checkpoint, or hosted
Firebase / GCP Cloud Function via `LAYA_REMOTE_URL`, with fallback to `typed-decisions`).
Also supports `ms-decision-1` (Azure AI Foundry via `rbi-sl-token token --env uat` -> POST /v1/decisions).
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LAYA_DIR = Path.home() / "models" / "convaiinnovations" / "laya"
LAYA_RUN = LAYA_DIR / "run.sh"
LAYA_CKPT = LAYA_DIR / "models" / "typed-decisions"
_DECISION_PKG_ROOT = Path(__file__).resolve().parents[2]
_DECISION_REPO_ROOT = (
    _DECISION_PKG_ROOT.parent
    if ((_DECISION_PKG_ROOT.parent / "data").exists() or (_DECISION_PKG_ROOT.parent / "frontend").exists())
    else _DECISION_PKG_ROOT
)
PROJECT_DATA_DIR = _DECISION_REPO_ROOT / "data"
LAYA_SPORTS_CKPT = PROJECT_DATA_DIR / "laya_sports_ckpt"
DEFAULT_TRAINING_PAIRS_PATH = PROJECT_DATA_DIR / "decision_training_pairs.jsonl"
RBI_TOKEN_BIN = Path.home() / ".rbi" / "bin" / "rbi-sl-token"
MS_DECISION_URL = "https://genai-uat.rbi.tech/v1/decisions"

_LAYA_WORKERS: dict[str, subprocess.Popen[str]] = {}


def _cleanup_laya_workers() -> None:
    for proc in list(_LAYA_WORKERS.values()):
        try:
            proc.terminate()
        except Exception:
            pass
    _LAYA_WORKERS.clear()


atexit.register(_cleanup_laya_workers)


def build_laya_match_questions(home: str = "", away: str = "") -> dict[str, dict[str, Any]]:
    """Build Laya-compatible `noul` questions for match-level positive/negative news.
    Note: The text state already prefixes `Match: {home} (Home) vs {away} (Away).`, so keeping
    canonical question instructions ensures zero schema conflicts during Laya training & caching.
    """
    return {
        "home_positive": {
            "type": "noul",
            "instructions": "Does the news report a key player returning, fitness boost, or positive momentum for the Home team?",
        },
        "home_negative": {
            "type": "noul",
            "instructions": "Does the news report a key player injured, suspended, ruled out, or crisis for the Home team?",
        },
        "away_positive": {
            "type": "noul",
            "instructions": "Does the news report a key player returning, fitness boost, or positive momentum for the Away team?",
        },
        "away_negative": {
            "type": "noul",
            "instructions": "Does the news report a key player injured, suspended, ruled out, or crisis for the Away team?",
        },
    }


def record_distillation_pair(
    text: str,
    home: str,
    away: str,
    ans: dict[str, float],
    pairs_path: Path = DEFAULT_TRAINING_PAIRS_PATH,
) -> bool:
    """Append a deduplicated ms-decision-1 teacher record in Laya `{state, questions, gold, expected}` format."""
    try:
        pairs_path.parent.mkdir(parents=True, exist_ok=True)
        if pairs_path.exists():
            with pairs_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        if json.loads(line).get("state") == text:
                            return False
                    except Exception:
                        continue
        questions = build_laya_match_questions(home, away)
        gold = {}
        expected = {}
        for k in ("home_positive", "home_negative", "away_positive", "away_negative"):
            p = max(0.0, min(1.0, float(ans.get(k, 0.0))))
            gold[k] = {"probabilities": {"false": round(1.0 - p, 6), "true": round(p, 6)}}
            expected[k] = bool(p >= 0.5)
        row = {
            "state": text,
            "questions": questions,
            "gold": gold,
            "expected": expected,
            "meta": {"teacher": "ms-decision-1", "home": home, "away": away},
        }
        with pairs_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class NewsSignal:
    backend: str
    home_positive: float
    home_negative: float
    away_positive: float
    away_negative: float
    matched_headlines: list[str]

    def net_edge(self, side: str) -> float:
        """Net news edge in [-1, +1] from `side` ('H' or 'A') perspective."""
        h_net = self.home_positive - self.home_negative
        a_net = self.away_positive - self.away_negative
        return (h_net - a_net) if side == "H" else (a_net - h_net)


TEAM_ALIASES: dict[str, set[str]] = {
    "paris saint-germain": {"psg", "paris"},
    "manchester united": {"man united", "man utd", "united"},
    "manchester city": {"man city", "city"},
    "tottenham hotspur": {"tottenham", "spurs"},
    "newcastle united": {"newcastle", "magpies"},
    "nottingham forest": {"forest"},
    "wolverhampton wanderers": {"wolves", "wolverhampton"},
    "brighton & hove albion": {"brighton"},
    "west ham united": {"west ham"},
    "bayern munich": {"bayern"},
    "borussia dortmund": {"dortmund", "bvb"},
    "borussia mönchengladbach": {"gladbach", "mönchengladbach", "monchengladbach"},
    "bayer leverkusen": {"leverkusen"},
    "rb leipzig": {"leipzig"},
    "eintracht frankfurt": {"frankfurt"},
    "internazionale": {"inter milan", "inter"},
    "ac milan": {"milan", "rossoneri"},
    "juventus": {"juve", "bianconeri"},
    "atletico madrid": {"atlético", "atletico", "atleti"},
    "real sociedad": {"sociedad"},
    "athletic club": {"athletic bilbao", "bilbao"},
    "celta vigo": {"celta"},
}


def _team_search_terms(team_name: str) -> set[str]:
    low = team_name.lower().strip()
    terms = {low}
    for k, aliases in TEAM_ALIASES.items():
        if k in low or low in k:
            terms |= aliases
    for tok in low.replace("-", " ").split():
        if len(tok) >= 4 and tok not in {"united", "city", "club", "real", "sporting", "borussia", "eintracht"}:
            terms.add(tok)
    return terms


def extract_team_news_text(
    summary: dict[str, Any],
    home: str,
    away: str,
    kickoff: str | None = None,
) -> tuple[str, list[str]]:
    """Filter summary news articles strictly relevant to `home` or `away` (and published before `kickoff` if given)."""
    articles = ((summary.get("news") or {}).get("articles")) or []
    h_tokens = _team_search_terms(home)
    a_tokens = _team_search_terms(away)
    matched: list[str] = []
    snippets: list[str] = []

    for art in articles:
        pub = (art.get("published") or "").strip()
        if kickoff and pub and pub[:16] >= kickoff[:16]:
            continue
        hl = (art.get("headline") or "").strip()
        desc = (art.get("description") or "").strip()
        combined = f"{hl}. {desc}".strip()
        low = combined.lower()
        if any(tok in low for tok in (h_tokens | a_tokens)):
            matched.append(hl)
            snippets.append(combined)

    # Only include summary['article'] if the match is not yet completed (pre-match preview)
    hdr_comps = (summary.get("header") or {}).get("competitions") or []
    is_completed = bool(hdr_comps and ((hdr_comps[0].get("status") or {}).get("type") or {}).get("completed"))
    if not is_completed:
        preview = ((summary.get("article") or {}).get("headline") or "").strip()
        if preview and preview not in matched:
            matched.append(preview)
            snippets.append(preview)

    text = f"Match: {home} (Home) vs {away} (Away).\n" + "\n".join(f"- {s}" for s in snippets[:5])
    return text, matched[:5]


def _get_rbi_token(env: str = "uat") -> str | None:
    cmd = str(RBI_TOKEN_BIN) if RBI_TOKEN_BIN.exists() else shutil.which("rbi-sl-token")
    if not cmd:
        return None
    try:
        proc = subprocess.run([cmd, "token", "--env", env], capture_output=True, text=True, timeout=15)
        if proc.returncode == 0 and proc.stdout.strip():
            out = proc.stdout.strip()
            if out.startswith("{"):
                return json.loads(out).get("token")
            return out
    except Exception:
        return None
    return None


def score_with_ms_decision_1(
    text: str,
    home: str,
    away: str,
    token: str | None = None,
    log_training_pair: bool = True,
    pairs_path: Path = DEFAULT_TRAINING_PAIRS_PATH,
) -> NewsSignal | None:
    """Call Microsoft-Decision-1 (`ms-decision-1`) to get calibrated news predicates."""
    tok = token or _get_rbi_token("uat")
    if not tok:
        return None
    payload = {
        "model": "ms-decision-1",
        "input": text,
        "questions": [
            {
                "type": "predicate",
                "name": "home_positive",
                "instructions": f"Does the news report a key player returning, fitness boost, or positive momentum for {home}?",
            },
            {
                "type": "predicate",
                "name": "home_negative",
                "instructions": f"Does the news report a key player injured, suspended, ruled out, or managerial crisis for {home}?",
            },
            {
                "type": "predicate",
                "name": "away_positive",
                "instructions": f"Does the news report a key player returning, fitness boost, or positive momentum for {away}?",
            },
            {
                "type": "predicate",
                "name": "away_negative",
                "instructions": f"Does the news report a key player injured, suspended, ruled out, or managerial crisis for {away}?",
            },
        ],
    }
    try:
        proc = subprocess.run(
            [
                "curl", "-s", "-f", "-m", "20", "-X", "POST", MS_DECISION_URL,
                "-H", f"Authorization: Bearer {tok}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        ans = {a["name"]: float(a["probability"]) for a in data.get("answers", [])}
        if log_training_pair:
            record_distillation_pair(text, home, away, ans, pairs_path=pairs_path)
        return NewsSignal(
            backend="ms-decision-1",
            home_positive=ans.get("home_positive", 0.0),
            home_negative=ans.get("home_negative", 0.0),
            away_positive=ans.get("away_positive", 0.0),
            away_negative=ans.get("away_negative", 0.0),
            matched_headlines=[],
        )
    except Exception:
        return None


def _has_laya_ckpt(path: Path) -> bool:
    return path.exists() and (
        (path / "rl_agent_config.json").exists()
        or (path / "config.json").exists()
        or (path / "model.safetensors").exists()
    )


def _get_or_start_laya_worker(ckpt_str: str) -> subprocess.Popen[str] | None:
    proc = _LAYA_WORKERS.get(ckpt_str)
    if proc is not None and proc.poll() is None:
        return proc
    if not LAYA_RUN.exists():
        return None
    worker_code = (
        "import json, sys\n"
        "from laya import Agent\n"
        f"agent = Agent({json.dumps(ckpt_str)})\n"
        "sys.stdout.write('READY\\n')\n"
        "sys.stdout.flush()\n"
        "for line in sys.stdin:\n"
        "    line = line.strip()\n"
        "    if not line:\n"
        "        continue\n"
        "    req = json.loads(line)\n"
        "    r = agent.predict(req['text'], req['questions'])\n"
        "    out = {}\n"
        "    for k, v in r['answers'].items():\n"
        "        if 'noul' in v:\n"
        "            out[k] = float(v['noul'])\n"
        "        else:\n"
        "            out[k] = v\n"
        "    sys.stdout.write('LAYA_JSON:' + json.dumps(out) + '\\n')\n"
        "    sys.stdout.flush()\n"
    )
    try:
        proc = subprocess.Popen(
            [str(LAYA_RUN), "-c", worker_code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        while True:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                proc.terminate()
                return None
            if line.strip() == "READY":
                break
        _LAYA_WORKERS[ckpt_str] = proc
        return proc
    except Exception:
        return None


def score_with_remote_laya(
    text: str,
    home: str,
    away: str,
    remote_url: str | None = None,
) -> NewsSignal | None:
    """Call a hosted Laya Firebase / GCP Cloud Function endpoint (`LAYA_REMOTE_URL`)."""
    url = (remote_url or os.environ.get("LAYA_REMOTE_URL") or "").strip()
    if not url:
        return None
    questions = build_laya_match_questions(home, away)
    payload = {"state": text, "questions": questions}
    headers = ["-H", "Content-Type: application/json"]
    api_key = os.environ.get("LAYA_REMOTE_TOKEN", "").strip()
    if api_key:
        headers.extend(["-H", f"Authorization: Bearer {api_key}"])
    try:
        proc = subprocess.run(
            ["curl", "-s", "-f", "-m", "15", "-X", "POST", url, *headers, "-d", json.dumps(payload)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        answers = data.get("answers") or {}
        ans = {
            k: float(v["noul"] if isinstance(v, dict) and "noul" in v else v)
            for k, v in answers.items()
        }
        return NewsSignal(
            backend="laya-cloud",
            home_positive=ans.get("home_positive", 0.0),
            home_negative=ans.get("home_negative", 0.0),
            away_positive=ans.get("away_positive", 0.0),
            away_negative=ans.get("away_negative", 0.0),
            matched_headlines=[],
        )
    except Exception:
        return None


LAYA_SINGLE_TEAM_QUESTIONS: dict[str, dict[str, Any]] = {
    "negative_impact": {
        "type": "noul",
        "instructions": "Does this news report a key player injured, suspended, ruled out, or team crisis that hurts win probability?",
    },
    "positive_impact": {
        "type": "noul",
        "instructions": "Does this news report a key player returning fit, lineup boost, or strong positive momentum?",
    },
}


def split_match_text_by_team(text: str, home: str, away: str) -> tuple[str, str]:
    """Split match news bullets into Home-relevant and Away-relevant snippets so single-encoder
    classifiers (like Laya) evaluate each team's news without cross-team interference."""
    h_tokens = _team_search_terms(home)
    a_tokens = _team_search_terms(away)
    h_lines: list[str] = []
    a_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("match:"):
            continue
        clean = line.lstrip("- ").strip()
        low = clean.lower()
        # Attribute to the team whose token appears earliest in the sentence (subject attribution)
        h_pos = min((low.find(t) for t in h_tokens if t in low), default=999999)
        a_pos = min((low.find(t) for t in a_tokens if t in low), default=999999)
        if h_pos < 999999 and a_pos < 999999:
            if h_pos <= a_pos:
                h_lines.append(clean)
            else:
                a_lines.append(clean)
        elif h_pos < 999999:
            h_lines.append(clean)
        elif a_pos < 999999:
            a_lines.append(clean)
        else:
            h_lines.append(clean)
            a_lines.append(clean)
    return " ".join(h_lines).strip(), " ".join(a_lines).strip()


def score_with_laya(
    text: str,
    home: str,
    away: str,
    ckpt_path: Path | None = None,
) -> NewsSignal | None:
    """Call sports-tuned Laya (`LAYA_REMOTE_URL` if set, else local `laya_sports_ckpt` or `typed-decisions`).
    Routes Home-relevant and Away-relevant bullets separately through `LAYA_SINGLE_TEAM_QUESTIONS`
    so single-encoder pooling never conflates Home and Away injury/boost signals.
    """
    if ckpt_path is None and os.environ.get("LAYA_REMOTE_URL"):
        remote_sig = score_with_remote_laya(text, home, away)
        if remote_sig is not None:
            return remote_sig

    active_ckpt = (ckpt_path or (LAYA_SPORTS_CKPT if _has_laya_ckpt(LAYA_SPORTS_CKPT) else LAYA_CKPT)).resolve()
    if not (LAYA_RUN.exists() and _has_laya_ckpt(active_ckpt)):
        return None
    ckpt_str = str(active_ckpt)
    backend_name = "laya-sports" if active_ckpt == LAYA_SPORTS_CKPT.resolve() else "laya-base"

    h_text, a_text = split_match_text_by_team(text, home, away)
    worker = _get_or_start_laya_worker(ckpt_str)
    if worker is None or not worker.stdin or not worker.stdout:
        return None

    def _query_side(snippet: str) -> tuple[float, float]:
        if not snippet:
            return 0.0, 0.0
        worker.stdin.write(json.dumps({"text": snippet, "questions": LAYA_SINGLE_TEAM_QUESTIONS}) + "\n")
        worker.stdin.flush()
        while True:
            line = worker.stdout.readline()
            if not line:
                raise RuntimeError("Laya worker closed stdout")
            if line.startswith("LAYA_JSON:"):
                ans = json.loads(line.split("LAYA_JSON:", 1)[1])
                return float(ans.get("positive_impact", 0.0)), float(ans.get("negative_impact", 0.0))

    try:
        h_pos, h_neg = _query_side(h_text)
        a_pos, a_neg = _query_side(a_text)
        return NewsSignal(
            backend=backend_name,
            home_positive=h_pos,
            home_negative=h_neg,
            away_positive=a_pos,
            away_negative=a_neg,
            matched_headlines=[],
        )
    except Exception:
        _LAYA_WORKERS.pop(ckpt_str, None)
        return None


def score_match_news(
    summary: dict[str, Any],
    home: str,
    away: str,
    backend: str = "laya",
) -> NewsSignal:
    """Score match news using `laya` (`laya-sports` default) or `ms-decision-1`."""
    text, headlines = extract_team_news_text(summary, home, away)
    if not headlines or backend == "none":
        return NewsSignal("none", 0.0, 0.0, 0.0, 0.0, [])

    sig: NewsSignal | None = None
    if backend in ("laya", "laya-sports", "auto"):
        sig = score_with_laya(text, home, away)
    elif backend == "laya-base":
        sig = score_with_laya(text, home, away, ckpt_path=LAYA_CKPT)
    elif backend == "ms-decision-1":
        sig = score_with_ms_decision_1(text, home, away)

    if sig is None and backend == "auto":
        sig = score_with_ms_decision_1(text, home, away)
    if sig is None:
        return NewsSignal("none", 0.0, 0.0, 0.0, 0.0, headlines)

    return NewsSignal(
        backend=sig.backend,
        home_positive=sig.home_positive,
        home_negative=sig.home_negative,
        away_positive=sig.away_positive,
        away_negative=sig.away_negative,
        matched_headlines=headlines,
    )
