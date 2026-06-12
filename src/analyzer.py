"""Engagement rate, hashtag, and posting pattern analysis."""

import re
from collections import Counter
from datetime import datetime
from typing import Any


def calculate_engagement_rate(media_list: list[dict], followers: int) -> dict:
    """Calculate average engagement rate across all posts.

    Engagement rate per post = (likes + comments) / followers * 100.
    Returns a dict with per-post rates and the overall average.
    """
    if not media_list or followers == 0:
        return {"per_post": [], "average": 0.0, "total_posts": 0}

    per_post = []
    for post in media_list:
        likes = post.get("like_count", 0) or 0
        comments = post.get("comments_count", 0) or 0
        rate = (likes + comments) / followers * 100
        per_post.append(round(rate, 4))

    average = sum(per_post) / len(per_post) if per_post else 0.0
    return {
        "per_post": per_post,
        "average": round(average, 4),
        "total_posts": len(media_list),
    }


def analyze_hashtags(media_list: list[dict], top_n: int = 20) -> dict:
    """Extract and count all hashtags from captions.

    Returns the top_n most common hashtags with their counts.
    """
    counter: Counter = Counter()
    pattern = re.compile(r"#(\w+)")

    for post in media_list:
        caption = post.get("caption", "") or ""
        tags = pattern.findall(caption.lower())
        counter.update(tags)

    top = counter.most_common(top_n)
    return {
        "top_hashtags": [{"tag": f"#{tag}", "count": count} for tag, count in top],
        "total_unique": len(counter),
        "total_uses": sum(counter.values()),
    }


def analyze_posting_patterns(media_list: list[dict]) -> dict:
    """Analyze when posts are published — by day of week and hour.

    Timestamps are expected in ISO 8601 format.
    Returns counts per day (0=Mon … 6=Sun) and per hour (0–23).
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days: Counter = Counter()
    hours: Counter = Counter()

    for post in media_list:
        ts = post.get("timestamp", "")
        if not ts:
            continue
        try:
            # Instagram returns e.g. "2024-03-15T12:34:56+0000"
            dt = datetime.fromisoformat(ts.replace("+0000", "+00:00"))
            days[dt.weekday()] += 1
            hours[dt.hour] += 1
        except (ValueError, TypeError):
            continue

    days_data = {day_names[i]: days.get(i, 0) for i in range(7)}
    hours_data = {str(h): hours.get(h, 0) for h in range(24)}

    best_day = max(days_data, key=lambda k: days_data[k]) if days_data else "N/A"
    best_hour_key = max(hours_data, key=lambda k: hours_data[k]) if hours_data else "0"
    best_hour = f"{int(best_hour_key):02d}:00"

    return {
        "by_day": days_data,
        "by_hour": hours_data,
        "best_day": best_day,
        "best_hour": best_hour,
    }


def get_top_posts(media_list: list[dict], n: int = 5) -> list[dict]:
    """Return the top N posts ranked by total engagement (likes + comments)."""

    def engagement(post: dict) -> int:
        return (post.get("like_count", 0) or 0) + (post.get("comments_count", 0) or 0)

    sorted_posts = sorted(media_list, key=engagement, reverse=True)
    return sorted_posts[:n]


def compare_accounts(accounts_data: list[dict]) -> dict:
    """Build a side-by-side comparison dict from a list of analysed account dicts.

    Each element of accounts_data should have keys:
        username, followers_count, engagement_rate (avg), top_hashtags,
        best_day, best_hour, total_posts.
    """
    if not accounts_data:
        return {}

    comparison: dict[str, Any] = {
        "accounts": [],
        "best_engagement": None,
        "most_followers": None,
        "most_active": None,
    }

    best_eng = -1.0
    most_followers = -1
    most_active = -1

    for acc in accounts_data:
        username = acc.get("username", "unknown")
        eng = acc.get("engagement_rate", {}).get("average", 0.0)
        followers = acc.get("followers_count", 0)
        posts = acc.get("engagement_rate", {}).get("total_posts", 0)

        comparison["accounts"].append(
            {
                "username": username,
                "followers": followers,
                "avg_engagement_rate": eng,
                "total_posts_analysed": posts,
                "best_day": acc.get("posting_patterns", {}).get("best_day", "N/A"),
                "best_hour": acc.get("posting_patterns", {}).get("best_hour", "N/A"),
                "top_hashtag": (
                    acc.get("hashtags", {}).get("top_hashtags", [{}])[0].get("tag", "N/A")
                    if acc.get("hashtags", {}).get("top_hashtags")
                    else "N/A"
                ),
            }
        )

        if eng > best_eng:
            best_eng = eng
            comparison["best_engagement"] = username
        if followers > most_followers:
            most_followers = followers
            comparison["most_followers"] = username
        if posts > most_active:
            most_active = posts
            comparison["most_active"] = username

    return comparison
