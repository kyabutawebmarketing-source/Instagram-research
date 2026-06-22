"""Instagram Competitor Analysis Tool — CLI entrypoint."""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Mock data for demo mode
# ---------------------------------------------------------------------------

def _mock_media(seed: int, followers: int, n: int = 50) -> list[dict]:
    """Generate realistic mock media posts."""
    import random
    rng = random.Random(seed)

    hashtag_pools = [
        ["#fitness", "#workout", "#gym", "#health", "#motivation", "#fit", "#training",
         "#exercise", "#lifestyle", "#wellness", "#strong", "#bodybuilding", "#crossfit",
         "#personaltrainer", "#fitfam"],
        ["#foodie", "#food", "#instafood", "#cooking", "#recipe", "#homemade", "#delicious",
         "#eat", "#yummy", "#foodphotography", "#healthyfood", "#vegan", "#dinner", "#lunch",
         "#breakfast"],
        ["#travel", "#wanderlust", "#adventure", "#explore", "#travelphotography", "#nature",
         "#landscape", "#vacation", "#tourism", "#holiday", "#travelgram", "#roadtrip",
         "#hiking", "#outdoor", "#backpacking"],
    ]
    pool = hashtag_pools[seed % len(hashtag_pools)]

    base_date = datetime(2024, 1, 1)
    posts = []
    for i in range(n):
        days_offset = rng.randint(0, 365)
        hour = rng.choice([8, 9, 10, 12, 17, 18, 19, 20])
        minute = rng.randint(0, 59)
        dt = base_date + timedelta(days=days_offset, hours=hour, minutes=minute)

        likes = max(0, int(followers * rng.uniform(0.005, 0.08)))
        comments = max(0, int(likes * rng.uniform(0.02, 0.15)))
        tags = " ".join(rng.sample(pool, rng.randint(5, 12)))
        caption_templates = [
            f"Loving every moment of this journey! {tags}",
            f"New post is live — check it out! {tags}",
            f"Consistency is key. Stay focused. {tags}",
            f"Behind the scenes today. {tags}",
            f"Grateful for this community. {tags}",
            f"This one took weeks to perfect. Worth it! {tags}",
            f"Early morning vibes. {tags}",
            f"Weekend mode: ON {tags}",
        ]
        posts.append({
            "id": f"mock_{seed}_{i}",
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "media_type": rng.choice(["IMAGE", "IMAGE", "IMAGE", "VIDEO", "CAROUSEL_ALBUM"]),
            "caption": rng.choice(caption_templates),
            "like_count": likes,
            "comments_count": comments,
            "permalink": f"https://www.instagram.com/p/mock{seed}{i}/",
        })
    return posts


def _build_mock_data() -> list[dict]:
    """Build mock competitor data for 3 accounts."""
    accounts_cfg = [
        {"username": "fitlife_official", "name": "FitLife Official", "followers": 285_000, "seed": 0},
        {"username": "healthyhustle", "name": "Healthy Hustle", "followers": 142_500, "seed": 1},
        {"username": "wellnesswave", "name": "Wellness Wave", "followers": 67_300, "seed": 2},
    ]

    from src.analyzer import (
        analyze_hashtags,
        analyze_posting_patterns,
        calculate_engagement_rate,
        get_top_posts,
    )

    accounts = []
    for cfg in accounts_cfg:
        media = _mock_media(cfg["seed"], cfg["followers"])
        engagement = calculate_engagement_rate(media, cfg["followers"])
        hashtags = analyze_hashtags(media)
        patterns = analyze_posting_patterns(media)
        top = get_top_posts(media, n=5)

        accounts.append({
            "username": cfg["username"],
            "name": cfg["name"],
            "followers_count": cfg["followers"],
            "media_count": 500 + cfg["seed"] * 120,
            "biography": f"Official account for {cfg['name']}. Inspiring millions daily.",
            "media": media,
            "engagement_rate": engagement,
            "hashtags": hashtags,
            "posting_patterns": patterns,
            "top_posts": top,
        })
    return accounts


# ---------------------------------------------------------------------------
# Demo command
# ---------------------------------------------------------------------------

def cmd_demo(args: argparse.Namespace) -> None:
    """Generate a demo report with mock data."""
    print("Generating demo report with mock data...")

    from src.analyzer import compare_accounts
    from src.report_generator import generate_html_report

    accounts = _build_mock_data()
    comparison = compare_accounts(accounts)

    # Attempt AI strategy; fall back to placeholder if no key
    strategy = ""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        print("Generating AI strategy via Claude...")
        try:
            from src.ai_strategy import generate_strategy
            strategy = generate_strategy(
                {"accounts": accounts, "comparison": comparison},
                api_key=anthropic_key,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: AI strategy generation failed: {exc}")
            strategy = _placeholder_strategy()
    else:
        print("No ANTHROPIC_API_KEY found — using placeholder strategy text.")
        strategy = _placeholder_strategy()

    data = {
        "accounts": accounts,
        "comparison": comparison,
        "strategy": strategy,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    output = args.output or "report.html"
    path = generate_html_report(data, output_path=output)
    print(f"\nReport generated: {path}")


# ---------------------------------------------------------------------------
# Analyze command
# ---------------------------------------------------------------------------

def cmd_analyze(args: argparse.Namespace) -> None:
    """Fetch real data and generate a report."""
    from src.analyzer import compare_accounts
    from src.instagram_client import InstagramAPIError, InstagramClient
    from src.report_generator import generate_html_report

    token = args.token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = getattr(args, "user_id", None) or os.environ.get("INSTAGRAM_USER_ID", "")

    if not token:
        print("Error: Instagram access token required. Use --token or set INSTAGRAM_ACCESS_TOKEN.")
        sys.exit(1)
    if not user_id:
        print("Error: Instagram user ID required. Use --user-id or set INSTAGRAM_USER_ID.")
        sys.exit(1)
    if not args.username:
        print("Error: At least one --username required.")
        sys.exit(1)

    client = InstagramClient(access_token=token, user_id=user_id)

    from src.analyzer import (
        analyze_hashtags,
        analyze_posting_patterns,
        calculate_engagement_rate,
        get_top_posts,
    )

    accounts = []
    for uname in args.username:
        print(f"Fetching data for @{uname}...")
        try:
            profile = client.get_competitor_profile(uname)
        except InstagramAPIError as exc:
            print(f"  Warning: Could not fetch @{uname}: {exc}")
            continue

        media = profile.get("media", [])
        if not media:
            try:
                media = client.get_media_list(profile.get("id") or user_id, limit=50)
            except InstagramAPIError:
                media = []

        followers = profile.get("followers_count", 1)
        engagement = calculate_engagement_rate(media, followers)
        hashtags = analyze_hashtags(media)
        patterns = analyze_posting_patterns(media)
        top = get_top_posts(media, n=5)

        accounts.append({
            **profile,
            "media": media,
            "engagement_rate": engagement,
            "hashtags": hashtags,
            "posting_patterns": patterns,
            "top_posts": top,
        })

    if not accounts:
        print("No account data fetched. Exiting.")
        sys.exit(1)

    comparison = compare_accounts(accounts)

    strategy = ""
    anthropic_key = getattr(args, "anthropic_key", None) or os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        print("Generating AI strategy via Claude...")
        try:
            from src.ai_strategy import generate_strategy
            strategy = generate_strategy(
                {"accounts": accounts, "comparison": comparison},
                api_key=anthropic_key,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: AI strategy generation failed: {exc}")
            strategy = _placeholder_strategy()
    else:
        print("No ANTHROPIC_API_KEY — skipping AI strategy.")
        strategy = _placeholder_strategy()

    data = {
        "accounts": accounts,
        "comparison": comparison,
        "strategy": strategy,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    output = args.output or "report.html"
    path = generate_html_report(data, output_path=output)
    print(f"\nReport generated: {path}")


# ---------------------------------------------------------------------------
# Analyze-influencer command (Apify-backed, no Graph API auth required)
# ---------------------------------------------------------------------------

def cmd_analyze_influencer(args: argparse.Namespace) -> None:
    """Fetch public influencer data via Apify and generate a report."""
    from src.analyzer import compare_accounts
    from src.apify_client import ApifyAPIError, ApifyInstagramClient
    from src.report_generator import generate_html_report

    apify_token = args.apify_token or os.environ.get("APIFY_API_TOKEN", "")
    if not apify_token:
        print("Error: Apify API token required. Use --apify-token or set APIFY_API_TOKEN.")
        sys.exit(1)
    if not args.username:
        print("Error: At least one --username required.")
        sys.exit(1)

    client = ApifyInstagramClient(api_token=apify_token)

    from src.analyzer import (
        analyze_hashtags,
        analyze_posting_patterns,
        calculate_engagement_rate,
        get_top_posts,
    )

    accounts = []
    for uname in args.username:
        print(f"Fetching data for @{uname} via Apify...")
        try:
            profile = client.get_profile(uname, post_limit=args.post_limit)
        except ApifyAPIError as exc:
            print(f"  Warning: Could not fetch @{uname}: {exc}")
            continue

        media = profile.get("media", [])
        followers = profile.get("followers_count", 1)
        engagement = calculate_engagement_rate(media, followers)
        hashtags = analyze_hashtags(media)
        patterns = analyze_posting_patterns(media)
        top = get_top_posts(media, n=5)

        accounts.append({
            **profile,
            "engagement_rate": engagement,
            "hashtags": hashtags,
            "posting_patterns": patterns,
            "top_posts": top,
        })

    if not accounts:
        print("No account data fetched. Exiting.")
        sys.exit(1)

    comparison = compare_accounts(accounts)

    strategy = ""
    anthropic_key = getattr(args, "anthropic_key", None) or os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        print("Generating AI strategy via Claude...")
        try:
            from src.ai_strategy import generate_strategy
            strategy = generate_strategy(
                {"accounts": accounts, "comparison": comparison},
                api_key=anthropic_key,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: AI strategy generation failed: {exc}")
            strategy = _placeholder_strategy()
    else:
        print("No ANTHROPIC_API_KEY — skipping AI strategy.")
        strategy = _placeholder_strategy()

    data = {
        "accounts": accounts,
        "comparison": comparison,
        "strategy": strategy,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    output = args.output or "report.html"
    path = generate_html_report(data, output_path=output)
    print(f"\nReport generated: {path}")


# ---------------------------------------------------------------------------
# Analyze-category command — discover influencers by category, sort by
# follower count, and analyze the top N per category.
# ---------------------------------------------------------------------------

def _profiles_to_accounts(profiles: list[dict]) -> list[dict]:
    """Run engagement/hashtag/posting-pattern analysis over a list of raw profiles."""
    from src.analyzer import (
        analyze_hashtags,
        analyze_posting_patterns,
        calculate_engagement_rate,
        get_top_posts,
    )

    accounts = []
    for profile in profiles:
        media = profile.get("media", [])
        followers = profile.get("followers_count", 1)
        accounts.append({
            **profile,
            "engagement_rate": calculate_engagement_rate(media, followers),
            "hashtags": analyze_hashtags(media),
            "posting_patterns": analyze_posting_patterns(media),
            "top_posts": get_top_posts(media, n=5),
        })
    return accounts


def cmd_analyze_category(args: argparse.Namespace) -> None:
    """Discover influencers per category via hashtags, sort by followers,
    and analyze the top N for each category."""
    from src.analyzer import compare_accounts
    from src.apify_client import ApifyAPIError, ApifyInstagramClient
    from src.categories import CATEGORY_HASHTAGS, CATEGORY_LABELS_JA
    from src.report_generator import generate_html_report

    apify_token = args.apify_token or os.environ.get("APIFY_API_TOKEN", "")
    if not apify_token:
        print("Error: Apify API token required. Use --apify-token or set APIFY_API_TOKEN.")
        sys.exit(1)

    categories = args.category or list(CATEGORY_HASHTAGS.keys())
    unknown = [c for c in categories if c not in CATEGORY_HASHTAGS]
    if unknown:
        print(f"Error: Unknown category(ies): {', '.join(unknown)}. "
              f"Valid options: {', '.join(CATEGORY_HASHTAGS.keys())}")
        sys.exit(1)

    client = ApifyInstagramClient(api_token=apify_token)
    anthropic_key = getattr(args, "anthropic_key", None) or os.environ.get("ANTHROPIC_API_KEY", "")
    output_dir = Path(args.output_dir or "reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    for category in categories:
        label = CATEGORY_LABELS_JA.get(category, category)
        print(f"\n=== {label} ({category}) ===")

        hashtag = CATEGORY_HASHTAGS[category][0]
        print(f"Discovering candidates via #{hashtag} (up to {args.candidate_limit})...")
        try:
            candidates = client.discover_usernames_by_hashtag(hashtag, limit=args.candidate_limit)
        except ApifyAPIError as exc:
            print(f"  Warning: Discovery failed for {category}: {exc}")
            continue

        usernames = [c["username"] for c in candidates]
        if not usernames:
            print(f"  No candidates found for {category}. Skipping.")
            continue
        print(f"  Found {len(usernames)} unique candidate accounts.")

        print("  Fetching follower counts for candidates...")
        try:
            profiles = client.get_profiles_bulk(usernames, post_limit=args.post_limit)
        except ApifyAPIError as exc:
            print(f"  Warning: Could not fetch profiles for {category}: {exc}")
            continue

        profiles.sort(key=lambda p: p.get("followers_count", 0), reverse=True)
        top_profiles = profiles[: args.top_n]
        print(f"  Analyzing top {len(top_profiles)} by follower count: "
              f"{', '.join('@' + p['username'] for p in top_profiles)}")

        accounts = _profiles_to_accounts(top_profiles)
        comparison = compare_accounts(accounts)

        strategy = ""
        if anthropic_key:
            print("  Generating AI strategy via Claude...")
            try:
                from src.ai_strategy import generate_strategy
                strategy = generate_strategy(
                    {"accounts": accounts, "comparison": comparison},
                    api_key=anthropic_key,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: AI strategy generation failed: {exc}")
                strategy = _placeholder_strategy()
        else:
            strategy = _placeholder_strategy()

        data = {
            "accounts": accounts,
            "comparison": comparison,
            "strategy": strategy,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        report_path = output_dir / f"report_{category}.html"
        path = generate_html_report(data, output_path=str(report_path))
        print(f"  Report generated: {path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _placeholder_strategy() -> str:
    return """## Strengths & Weaknesses
Based on the competitor analysis data, larger accounts benefit from higher brand recognition and consistent posting schedules, while smaller accounts tend to achieve higher engagement rates through more niche, targeted content.

## Recommended Content Themes
1. **Educational content** — How-to guides and tips that provide immediate value
2. **Behind-the-scenes** — Authentic glimpses that build trust and relatability
3. **User-generated content** — Reposts and community spotlights to drive engagement
4. **Trending challenges** — Participating in viral formats for discoverability
5. **Data-driven stories** — Infographics and stat-based posts that get shared

## Optimal Posting Schedule
Post 5-7 times per week. Prioritise weekday evenings (6-8 PM local time) and Saturday mornings (9-11 AM) based on typical peak engagement windows observed in the data.

## Hashtag Strategy
- **Niche tags** (< 500K posts): Use 5-6 for targeted reach
- **Mid-range tags** (500K-5M posts): Use 4-5 for balanced exposure
- **Broad tags** (> 5M posts): Use 2-3 sparingly for discovery

Rotate hashtag sets across posts to avoid shadowbanning and find what works best.

## Engagement Tactics
1. Reply to every comment within the first hour of posting
2. Use Instagram Stories polls and question stickers daily
3. Collaborate with micro-influencers in the same niche
4. End every caption with a clear call-to-action question
5. Go live at least once per week to boost algorithmic reach

## Quick Wins
1. Audit and update your bio with a clear value proposition and a link
2. Schedule three posts for peak engagement times this week
3. Engage with 20 accounts in your niche daily (like + thoughtful comment)
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instagram-analyzer",
        description="Instagram Competitor Analysis Tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # demo
    demo_parser = subparsers.add_parser("demo", help="Generate a demo report with mock data")
    demo_parser.add_argument("--output", "-o", default="report.html", help="Output HTML file path")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze real competitor accounts")
    analyze_parser.add_argument(
        "--username", "-u",
        action="append",
        metavar="USERNAME",
        help="Competitor Instagram username (can be repeated)",
    )
    analyze_parser.add_argument("--token", "-t", help="Instagram Graph API access token")
    analyze_parser.add_argument("--user-id", help="Your Instagram user ID")
    analyze_parser.add_argument("--anthropic-key", help="Anthropic API key for Claude strategy")
    analyze_parser.add_argument("--output", "-o", default="report.html", help="Output HTML file path")

    # analyze-influencer
    influencer_parser = subparsers.add_parser(
        "analyze-influencer",
        help="Analyze public influencer accounts via Apify (no Graph API auth required)",
    )
    influencer_parser.add_argument(
        "--username", "-u",
        action="append",
        metavar="USERNAME",
        help="Influencer Instagram username (can be repeated)",
    )
    influencer_parser.add_argument("--apify-token", help="Apify API token")
    influencer_parser.add_argument("--post-limit", type=int, default=50, help="Number of recent posts to fetch per account")
    influencer_parser.add_argument("--anthropic-key", help="Anthropic API key for Claude strategy")
    influencer_parser.add_argument("--output", "-o", default="report.html", help="Output HTML file path")

    # analyze-category
    from src.categories import CATEGORY_HASHTAGS

    category_parser = subparsers.add_parser(
        "analyze-category",
        help="Discover influencers per category via hashtags, sort by followers, and analyze the top N",
    )
    category_parser.add_argument(
        "--category", "-c",
        action="append",
        choices=list(CATEGORY_HASHTAGS.keys()),
        help="Category to analyze (can be repeated). Defaults to all categories.",
    )
    category_parser.add_argument("--apify-token", help="Apify API token")
    category_parser.add_argument("--candidate-limit", type=int, default=50, help="Number of candidates to discover per category")
    category_parser.add_argument("--top-n", type=int, default=10, help="Number of top accounts (by followers) to analyze per category")
    category_parser.add_argument("--post-limit", type=int, default=50, help="Number of recent posts to fetch per account")
    category_parser.add_argument("--anthropic-key", help="Anthropic API key for Claude strategy")
    category_parser.add_argument("--output-dir", default="reports", help="Directory for per-category HTML reports")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        cmd_demo(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "analyze-influencer":
        cmd_analyze_influencer(args)
    elif args.command == "analyze-category":
        cmd_analyze_category(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
