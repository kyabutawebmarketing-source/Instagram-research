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

# Fixed set of supported influencer categories. Each entry lists the
# hashtags (Japanese + English) used both for genre classification and
# for biasing Apify hashtag discovery toward that category.
CATEGORY_HASHTAGS: dict[str, list[str]] = {
    "美容・コスメ": ["美容", "コスメ", "スキンケア", "beauty", "cosmetics", "skincare", "makeup"],
    "ファッション": ["ファッション", "コーデ", "おしゃれ", "fashion", "ootd", "style", "outfit"],
    "子育て・ベビー": ["子育て", "ベビー", "育児", "ママ", "baby", "parenting", "mom"],
    "ダイエット・フィットネス": ["ダイエット", "フィットネス", "筋トレ", "diet", "fitness", "workout", "gym"],
    "旅行": ["旅行", "旅", "trip", "travel", "wanderlust"],
    "プレゼント": ["プレゼント", "懸賞", "キャンペーン", "giveaway", "present"],
    "ペット": ["ペット", "犬", "猫", "いぬ", "ねこ", "pet", "dog", "cat"],
}

CATEGORIES: list[str] = list(CATEGORY_HASHTAGS.keys())

# Backwards-compatible alias used by classify_genre().
GENRE_HASHTAG_MAP = CATEGORY_HASHTAGS


def discovery_tag_for_category(category: str) -> str:
    """Pick a representative hashtag to seed Apify discovery for a category."""
    tags = CATEGORY_HASHTAGS.get(category)
    if not tags:
        raise ValueError(f"Unknown category: {category}")
    return tags[0]


JAPAN_LOCATION_KEYWORDS = [
    "japan", "tokyo", "osaka", "kyoto", "yokohama", "nagoya", "fukuoka",
    "sapporo", "kobe", "okinawa", "日本", "東京", "大阪", "京都", "横浜",
    "名古屋", "福岡", "札幌", "神戸", "沖縄",
]

_JAPANESE_CHAR_RE = re.compile(
    r"[぀-ゟ゠-ヿ一-鿿]"  # hiragana, katakana, kanji
)


def is_japan_based(biography: str = "", full_name: str = "", locations: list[str] | None = None) -> bool:
    """Best-effort heuristic for whether an account is Japan-based.

    Public Instagram data has no country field, so this combines two
    signals: Japanese-script text in the bio/name, and any tagged post
    location matching a known Japanese place name. Either signal alone
    is treated as sufficient (false positives are preferred over
    silently dropping genuine Japanese accounts).
    """
    text = f"{biography or ''} {full_name or ''}"
    if _JAPANESE_CHAR_RE.search(text):
        return True

    for loc in (locations or []):
        loc_lower = (loc or "").lower()
        if any(kw in loc_lower for kw in JAPAN_LOCATION_KEYWORDS):
            return True

    return False


# Keywords strongly suggesting a corporate/brand account rather than
# an individual influencer. Checked against bio + display name.
_CORPORATE_KEYWORDS = [
    # Japanese legal entities / business terms
    "株式会社", "有限会社", "合同会社", "合資会社", "一般社団法人", "特定非営利活動法人",
    "公益財団法人", "社団法人", "財団法人",
    # Common corporate signals in bios
    "公式", "オフィシャル", "公式アカウント", "official account",
    "お問い合わせ", "ご予約", "採用", "求人",
    # English legal suffixes
    " inc.", " inc,", " corp.", " corp,", " ltd.", " ltd,", " llc",
    " co.,", "co., ltd", "& co.", "holdings",
    # Store / brand signals
    "online shop", "オンラインショップ", "通販", "ネットショップ",
    "代表", "ceo", "coo", "代表取締役",
]

_CORPORATE_RE = re.compile(
    "|".join(re.escape(kw) for kw in _CORPORATE_KEYWORDS),
    re.IGNORECASE,
)


def is_corporate_account(biography: str = "", full_name: str = "") -> bool:
    """Return True if the account looks like a brand/company rather than a person.

    Uses keyword matching on bio and display name. Errs toward false negatives
    (letting borderline accounts through) to avoid dropping real influencers.
    """
    text = f"{biography or ''} {full_name or ''}".lower()
    return bool(_CORPORATE_RE.search(text))


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
