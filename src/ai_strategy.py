"""Claude API integration for generating content strategy recommendations."""

import json
import os
from typing import Any

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]


MODEL = "claude-haiku-4-5-20251001"


class AIStrategyError(Exception):
    """Raised when strategy generation fails."""
    pass


def _build_prompt(analysis_results: dict[str, Any]) -> str:
    """Build a structured prompt summarising the analysis for Claude."""
    accounts = analysis_results.get("accounts", [])
    comparison = analysis_results.get("comparison", {})

    accounts_summary = []
    for acc in accounts:
        username = acc.get("username", "unknown")
        followers = acc.get("followers_count", 0)
        eng_avg = acc.get("engagement_rate", {}).get("average", 0.0)
        top_tags = [
            h["tag"]
            for h in acc.get("hashtags", {}).get("top_hashtags", [])[:10]
        ]
        best_day = acc.get("posting_patterns", {}).get("best_day", "N/A")
        best_hour = acc.get("posting_patterns", {}).get("best_hour", "N/A")

        accounts_summary.append(
            f"- @{username}: {followers:,} followers, {eng_avg:.2f}% avg engagement rate, "
            f"best posting time: {best_day} at {best_hour}, "
            f"top hashtags: {', '.join(top_tags) if top_tags else 'none detected'}"
        )

    comp_note = ""
    if comparison:
        comp_note = (
            f"\nBenchmark highlights:\n"
            f"  - Highest engagement: @{comparison.get('best_engagement', 'N/A')}\n"
            f"  - Largest audience: @{comparison.get('most_followers', 'N/A')}\n"
            f"  - Most active poster: @{comparison.get('most_active', 'N/A')}"
        )

    prompt = f"""You are a senior social media strategist specialising in Instagram growth.
Below is a competitor analysis for Instagram accounts in the same niche.

COMPETITOR DATA
===============
{chr(10).join(accounts_summary)}
{comp_note}

Based on this analysis, write a concise but actionable content strategy report in Markdown.
Structure your response with these exact sections:

## Strengths & Weaknesses
Identify what each competitor does well and where they fall short.

## Recommended Content Themes
Suggest 4–6 specific content themes or pillars to differentiate from competitors.

## Optimal Posting Schedule
Recommend the best days and times to post, with reasoning from the data.

## Hashtag Strategy
Suggest a tiered hashtag approach (niche, mid-range, broad) informed by competitor usage.

## Engagement Tactics
List 5 concrete tactics to improve engagement rate above the competitors.

## Quick Wins
List 3 actions that can be implemented this week.

Be specific, data-driven, and practical. Avoid generic advice.
"""
    return prompt


def generate_strategy(
    analysis_results: dict[str, Any],
    api_key: str | None = None,
) -> str:
    """Send the analysis summary to Claude and return a markdown strategy.

    Parameters
    ----------
    analysis_results:
        The combined analysis dict produced by the analyzer module.
    api_key:
        Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns
    -------
    str
        Markdown-formatted strategy text.
    """
    if anthropic is None:
        raise AIStrategyError(
            "The 'anthropic' package is not installed. "
            "Run: pip install anthropic"
        )

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise AIStrategyError(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY or pass api_key."
        )

    client = anthropic.Anthropic(api_key=key)
    prompt = _build_prompt(analysis_results)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except anthropic.APIConnectionError as e:
        raise AIStrategyError(f"Connection error: {e}") from e
    except anthropic.RateLimitError as e:
        raise AIStrategyError(f"Rate limit exceeded: {e}") from e
    except anthropic.APIStatusError as e:
        raise AIStrategyError(f"API error {e.status_code}: {e.message}") from e
