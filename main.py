"""Instagram Competitor Analysis Tool — CLI entrypoint."""

import argparse
import os
import re
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
# Influencer analysis (genre-based discovery)
# ---------------------------------------------------------------------------

def _build_influencer_record(
    username: str,
    name: str,
    biography: str,
    followers_count: int,
    media_count: int,
    media: list[dict],
) -> dict:
    """Run all influencer-specific analysis steps for a single account."""
    from src import influencer_analyzer, snapshot_store
    from src.analyzer import calculate_engagement_rate

    engagement = calculate_engagement_rate(media, followers_count)
    pr_rate = influencer_analyzer.calculate_pr_rate(media, months=3)

    hashtags = []
    for post in media:
        hashtags.extend(re.findall(r"#(\w+)", (post.get("caption") or "").lower()))
    genre = influencer_analyzer.classify_genre(biography, hashtags)

    snapshot_store.record_snapshot(
        username, followers_count, engagement["average"], pr_rate["pr_rate"]
    )
    trends = influencer_analyzer.build_trends(username, media, followers_count, months=3)

    return {
        "username": username,
        "name": name or username,
        "biography": biography,
        "followers_count": followers_count,
        "media_count": media_count,
        "engagement_rate": engagement,
        "pr_rate": pr_rate,
        "genre": genre,
        "trends": trends,
        "influencer_demographics": influencer_analyzer.estimate_demographics(username, "influencer"),
        "audience_demographics": influencer_analyzer.estimate_demographics(username, "audience"),
    }


def cmd_influencer_demo(args: argparse.Namespace) -> None:
    """Generate a demo influencer report for a genre using mock accounts."""
    print(f"Generating demo influencer report for genre '{args.genre}'...")

    from src.report_generator import generate_influencer_report

    accounts_cfg = [
        {"username": "fitlife_tokyo", "name": "美咲 / FitLife Tokyo", "followers": 285_000, "seed": 0},
        {"username": "healthy_hustle_jp", "name": "健太 / Healthy Hustle JP", "followers": 142_500, "seed": 1},
        {"username": "wellness_osaka", "name": "ゆかり / Wellness Osaka", "followers": 67_300, "seed": 2},
    ]

    influencers = []
    for cfg in accounts_cfg:
        media = _mock_media(cfg["seed"], cfg["followers"])
        record = _build_influencer_record(
            username=cfg["username"],
            name=cfg["name"],
            biography=f"{cfg['name']}の公式アカウントです。日本各地で #{args.genre} の発信をしています。",
            followers_count=cfg["followers"],
            media_count=500 + cfg["seed"] * 120,
            media=media,
        )
        influencers.append(record)

    data = {
        "genre": args.genre,
        "influencers": influencers,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    output = args.output or "influencer_report.html"
    path = generate_influencer_report(data, output_path=output)
    print(f"\nReport generated: {path}")


def cmd_influencer(args: argparse.Namespace) -> None:
    """Discover and analyze real influencers in a genre via Apify."""
    from src.apify_client import ApifyAPIError, ApifyClient
    from src.report_generator import generate_influencer_report

    api_token = args.apify_token or os.environ.get("APIFY_API_TOKEN", "")
    if not api_token:
        print("Error: Apify API token required. Use --apify-token or set APIFY_API_TOKEN.")
        sys.exit(1)

    client = ApifyClient(api_token)

    usernames = list(args.username or [])
    if not usernames:
        hashtags_to_try = [args.genre]
        if not args.no_region_filter:
            # Bias discovery toward Japan-tagged posts so the later
            # is_japan_based() filter doesn't discard most candidates.
            hashtags_to_try = [f"{args.genre}japan", args.genre]

        print(f"Discovering influencers for genre '{args.genre}' via Apify...")
        seen: set[str] = set()
        for tag in hashtags_to_try:
            try:
                candidates = client.discover_by_hashtag(tag, limit=args.limit)
            except ApifyAPIError as exc:
                print(f"  Warning: discovery for #{tag} failed: {exc}")
                continue
            for c in candidates:
                seen.add(c["username"])
            if len(seen) >= args.limit:
                break
        usernames = list(seen)[: args.limit]

    if not usernames:
        print("No candidate influencers found. Exiting.")
        sys.exit(1)

    print(f"Fetching profile + posts for {len(usernames)} account(s)...")
    try:
        profiles = client.fetch_profiles(usernames, posts_per_profile=args.posts)
    except ApifyAPIError as exc:
        print(f"Error: profile fetch failed: {exc}")
        sys.exit(1)

    from src import influencer_analyzer

    influencers = []
    skipped_non_japan = 0
    for profile in profiles:
        username = profile.get("username") or profile.get("ownerUsername") or ""
        if not username:
            continue
        followers_count = profile.get("followersCount", 0) or 0
        media_count = profile.get("postsCount", 0) or 0
        biography = profile.get("biography", "") or ""
        name = profile.get("fullName", "") or username

        raw_posts = profile.get("latestPosts") or profile.get("posts") or []
        media = [
            {
                "id": p.get("id", ""),
                "timestamp": p.get("timestamp", "") or p.get("takenAtTimestamp", ""),
                "media_type": p.get("type", "IMAGE"),
                "caption": p.get("caption", "") or "",
                "like_count": p.get("likesCount", 0) or 0,
                "comments_count": p.get("commentsCount", 0) or 0,
            }
            for p in raw_posts
        ]
        locations = [p.get("locationName", "") for p in raw_posts if p.get("locationName")]

        if not args.no_region_filter and not influencer_analyzer.is_japan_based(
            biography, name, locations
        ):
            skipped_non_japan += 1
            continue

        record = _build_influencer_record(
            username, name, biography, followers_count, media_count, media
        )
        influencers.append(record)

    if skipped_non_japan:
        print(f"Skipped {skipped_non_japan} non-Japan-based account(s) (bio/location heuristic).")

    if not influencers:
        print("No influencer data could be analyzed (after Japan-region filtering). Exiting.")
        sys.exit(1)

    data = {
        "genre": args.genre,
        "influencers": influencers,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    output = args.output or "influencer_report.html"
    path = generate_influencer_report(data, output_path=output)
    print(f"\nReport generated: {path}")


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

    # influencer-demo
    inf_demo_parser = subparsers.add_parser(
        "influencer-demo", help="Generate a demo influencer report for a genre (mock data)"
    )
    inf_demo_parser.add_argument("--genre", "-g", default="fitness", help="Target genre/keyword")
    inf_demo_parser.add_argument("--output", "-o", default="influencer_report.html", help="Output HTML file path")

    # influencer
    inf_parser = subparsers.add_parser(
        "influencer", help="Discover and analyze real influencers in a genre via Apify"
    )
    inf_parser.add_argument("--genre", "-g", required=True, help="Genre/hashtag keyword to discover influencers")
    inf_parser.add_argument(
        "--username", "-u", action="append", metavar="USERNAME",
        help="Specific username to analyze (skips discovery; can be repeated)",
    )
    inf_parser.add_argument("--limit", type=int, default=10, help="Max number of influencers to discover")
    inf_parser.add_argument("--posts", type=int, default=30, help="Posts per profile to fetch")
    inf_parser.add_argument(
        "--no-region-filter", action="store_true",
        help="Disable the Japan-based heuristic filter (default: Japan only)",
    )
    inf_parser.add_argument("--apify-token", help="Apify API token")
    inf_parser.add_argument("--output", "-o", default="influencer_report.html", help="Output HTML file path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        cmd_demo(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "influencer-demo":
        cmd_influencer_demo(args)
    elif args.command == "influencer":
        cmd_influencer(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
