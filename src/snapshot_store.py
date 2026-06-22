"""Lightweight JSON-backed history store for influencer metrics.

Instagram does not expose historical follower counts, so monthly trends
must be built up from repeated runs of this tool over time. Each run
appends a snapshot per influencer; trend charts read back whatever
history has accumulated so far and fall back to an estimated backfill
when fewer than 3 monthly data points exist yet.
"""

import json
from datetime import datetime
from pathlib import Path

DEFAULT_STORE_PATH = Path(__file__).parent.parent / "data" / "influencer_snapshots.json"


def _load(store_path: Path) -> dict:
    if not store_path.exists():
        return {}
    try:
        return json.loads(store_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(store_path: Path, data: dict) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_snapshot(
    username: str,
    followers_count: int,
    engagement_rate: float,
    pr_rate: float,
    store_path: Path = DEFAULT_STORE_PATH,
) -> None:
    """Append today's metrics for a username, replacing any entry for today."""
    data = _load(store_path)
    history = data.setdefault(username, [])

    today = datetime.now().strftime("%Y-%m-%d")
    history[:] = [h for h in history if h.get("date") != today]
    history.append({
        "date": today,
        "followers_count": followers_count,
        "engagement_rate": engagement_rate,
        "pr_rate": pr_rate,
    })
    history.sort(key=lambda h: h["date"])

    _save(store_path, data)


def get_history(username: str, store_path: Path = DEFAULT_STORE_PATH) -> list[dict]:
    data = _load(store_path)
    return data.get(username, [])
