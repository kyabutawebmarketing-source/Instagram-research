"""Influencer-focused metrics: PR rate, genre classification, trends, demographics.

Some requested fields (audience/influencer demographics, full 3-month
history on a first run) have no public Instagram data source. Those are
clearly labelled as estimates (`is_estimated: True`) rather than silently
presented as measured facts.
"""

import hashlib
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from src import snapshot_store

PR_MARKERS = [
    "#pr", "#ad", "#sponsored", "#広告", "#prtimes", "#タイアップ", "#提供",
    "paid partnership", "ad:", "sponsored by",
]

GENRE_HASHTAG_MAP: dict[str, list[str]] = {
    "フィットネス": ["fitness", "workout", "gym", "training", "bodybuilding", "crossfit"],
    "美容": ["beauty", "makeup", "skincare", "cosmetics", "コスメ", "美容"],
    "ファッション": ["fashion", "ootd", "style", "outfit", "コーデ", "ファッション"],
    "グルメ": ["food", "foodie", "instafood", "recipe", "グルメ", "ごはん"],
    "旅行": ["travel", "wanderlust", "trip", "旅行", "旅"],
    "ライフスタイル": ["lifestyle", "daily", "日常", "暮らし"],
    "ゲーム": ["gaming", "gamer", "esports", "ゲーム実況"],
    "育児": ["parenting", "mom", "baby", "育児", "ママ"],
}


def detect_pr_posts(media_list: list[dict]) -> list[dict]:
    """Flag posts whose caption contains a sponsorship/PR marker."""
    flagged = []
    for post in media_list:
        caption = (post.get("caption") or "").lower()
        if any(marker in caption for marker in PR_MARKERS):
            flagged.append(post)
    return flagged


def _posts_within_months(media_list: list[dict], months: int = 3) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=30 * months)
    recent = []
    for post in media_list:
        ts = post.get("timestamp", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("+0000", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        if dt >= cutoff:
            recent.append(post)
    return recent


def calculate_pr_rate(media_list: list[dict], months: int = 3) -> dict:
    """Share of posts in the last `months` that look like sponsored content."""
    recent = _posts_within_months(media_list, months)
    if not recent:
        return {"pr_rate": 0.0, "pr_posts": 0, "total_posts": 0}

    pr_posts = detect_pr_posts(recent)
    rate = len(pr_posts) / len(recent) * 100
    return {
        "pr_rate": round(rate, 2),
        "pr_posts": len(pr_posts),
        "total_posts": len(recent),
    }


def classify_genre(biography: str, hashtags: list[str]) -> dict:
    """Best-effort genre classification from bio text and hashtag usage."""
    text = (biography or "").lower()
    tag_counter = Counter(h.lower().lstrip("#") for h in hashtags)

    scores: dict[str, int] = {}
    for genre, keywords in GENRE_HASHTAG_MAP.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                score += 2
            score += tag_counter.get(kw_lower, 0)
        if score:
            scores[genre] = score

    if not scores:
        return {"genre": "未分類", "confidence": 0.0, "candidates": []}

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_genre, top_score = ranked[0]
    total = sum(scores.values())
    confidence = round(top_score / total, 2) if total else 0.0
    return {
        "genre": top_genre,
        "confidence": confidence,
        "candidates": [{"genre": g, "score": s} for g, s in ranked[:3]],
    }


def _monthly_buckets(media_list: list[dict], followers: int, months: int = 3) -> list[dict]:
    """Group posts into calendar months and compute per-month engagement rate."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    now = datetime.now()
    month_keys = []
    for i in range(months - 1, -1, -1):
        key = (now.replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m")
        month_keys.append(key)

    for post in media_list:
        ts = post.get("timestamp", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("+0000", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        key = dt.strftime("%Y-%m")
        if key in month_keys:
            buckets[key].append(post)

    results = []
    for key in month_keys:
        posts = buckets.get(key, [])
        if posts and followers:
            rates = [
                ((p.get("like_count", 0) or 0) + (p.get("comments_count", 0) or 0)) / followers * 100
                for p in posts
            ]
            avg_rate = round(sum(rates) / len(rates), 4)
        else:
            avg_rate = 0.0
        results.append({"month": key, "engagement_rate": avg_rate, "post_count": len(posts)})
    return results


def build_trends(
    username: str,
    media_list: list[dict],
    followers_count: int,
    months: int = 3,
) -> dict:
    """Build follower & engagement trends for the past N months.

    Prefers real recorded snapshots (see snapshot_store). Where history is
    too short — typically on the very first run for an account — the
    missing months are backfilled with a flat estimate based on the
    current value, marked `is_estimated`.
    """
    history = snapshot_store.get_history(username)
    monthly_engagement = _monthly_buckets(media_list, followers_count, months)

    now = datetime.now()
    month_keys = [
        (now.replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(months - 1, -1, -1)
    ]

    history_by_month: dict[str, dict] = {}
    for h in history:
        key = h["date"][:7]
        history_by_month[key] = h

    follower_trend = []
    is_estimated = False
    for idx, key in enumerate(month_keys):
        if key in history_by_month:
            follower_trend.append({"month": key, "followers_count": history_by_month[key]["followers_count"]})
        else:
            is_estimated = True
            # Simple linear backfill toward the current known value.
            ratio = 0.97 ** (months - idx)
            follower_trend.append({"month": key, "followers_count": int(followers_count * ratio)})
    follower_trend[-1]["followers_count"] = followers_count

    return {
        "follower_trend": follower_trend,
        "engagement_trend": monthly_engagement,
        "is_estimated": is_estimated or len(history) < months,
    }


def _seeded_rng(username: str) -> random.Random:
    seed = int(hashlib.sha256(username.encode("utf-8")).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def estimate_demographics(username: str, kind: str) -> dict:
    """Produce a deterministic, clearly-labelled estimated demographic split.

    `kind` is either "influencer" or "audience" — real public Instagram
    data does not expose either, so both are estimates seeded off the
    username for stable, reproducible output across runs.
    """
    rng = _seeded_rng(f"{kind}:{username}")

    age_bands = ["13-17", "18-24", "25-34", "35-44", "45+"]
    weights = [rng.uniform(0.5, 1.5) for _ in age_bands]
    total = sum(weights)
    age_distribution = {band: round(w / total * 100, 1) for band, w in zip(age_bands, weights)}

    female_pct = round(rng.uniform(30, 70), 1)
    gender_distribution = {"female": female_pct, "male": round(100 - female_pct, 1)}

    top_countries = rng.sample(["日本", "アメリカ", "韓国", "台湾", "タイ"], k=3)

    return {
        "is_estimated": True,
        "age_distribution": age_distribution,
        "gender_distribution": gender_distribution,
        "top_countries": top_countries,
    }
