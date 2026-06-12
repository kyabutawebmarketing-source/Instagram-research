"""HTML report generation using Jinja2 templates."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    Environment = None  # type: ignore[assignment,misc]


class ReportGenerationError(Exception):
    """Raised when report generation fails."""
    pass


def _serialize(obj: Any) -> Any:
    """Make objects JSON-serialisable for embedding in templates."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def generate_html_report(
    data: dict[str, Any],
    output_path: str = "report.html",
    template_dir: str | None = None,
) -> str:
    """Render and write the HTML report.

    Parameters
    ----------
    data:
        Full analysis data dict (accounts, comparison, strategy, generated_at).
    output_path:
        Destination path for the HTML file.
    template_dir:
        Directory containing report.html. Defaults to ../templates relative
        to this file.

    Returns
    -------
    str
        The absolute path of the written report.
    """
    if Environment is None:
        raise ReportGenerationError(
            "Jinja2 is not installed. Run: pip install jinja2"
        )

    if template_dir is None:
        template_dir = str(Path(__file__).parent.parent / "templates")

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )

    template = env.get_template("report.html")

    # Pre-serialise heavy data for Chart.js
    chart_data = _build_chart_data(data)

    html = template.render(
        accounts=data.get("accounts", []),
        comparison=data.get("comparison", {}),
        strategy=data.get("strategy", ""),
        generated_at=data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M")),
        chart_data_json=json.dumps(chart_data, default=_serialize),
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


def _build_chart_data(data: dict[str, Any]) -> dict:
    """Prepare chart-ready data structures."""
    accounts = data.get("accounts", [])

    # Engagement rate bar chart
    eng_labels = [a.get("username", "") for a in accounts]
    eng_values = [a.get("engagement_rate", {}).get("average", 0.0) for a in accounts]

    # Hashtag frequency (first account or merged)
    hashtag_labels: list[str] = []
    hashtag_values: list[int] = []
    if accounts:
        top_tags = accounts[0].get("hashtags", {}).get("top_hashtags", [])[:10]
        hashtag_labels = [h["tag"] for h in top_tags]
        hashtag_values = [h["count"] for h in top_tags]

    # Posting pattern heatmap data (all accounts combined)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    combined_days: dict[str, int] = {d: 0 for d in day_names}
    combined_hours: dict[str, int] = {str(h): 0 for h in range(24)}

    for acc in accounts:
        patterns = acc.get("posting_patterns", {})
        for day, count in patterns.get("by_day", {}).items():
            combined_days[day] = combined_days.get(day, 0) + count
        for hour, count in patterns.get("by_hour", {}).items():
            combined_hours[hour] = combined_hours.get(hour, 0) + count

    hour_labels = [f"{int(h):02d}:00" for h in range(24)]
    hour_values = [combined_hours.get(str(h), 0) for h in range(24)]

    # Top posts per account
    top_posts_data = []
    for acc in accounts:
        for post in acc.get("top_posts", []):
            likes = post.get("like_count", 0) or 0
            comments = post.get("comments_count", 0) or 0
            top_posts_data.append(
                {
                    "username": acc.get("username", ""),
                    "likes": likes,
                    "comments": comments,
                    "engagement": likes + comments,
                    "caption_preview": (post.get("caption", "") or "")[:120],
                    "media_type": post.get("media_type", "IMAGE"),
                    "timestamp": post.get("timestamp", "")[:10],
                    "permalink": post.get("permalink", "#"),
                }
            )

    return {
        "engagement": {"labels": eng_labels, "values": eng_values},
        "hashtags": {"labels": hashtag_labels, "values": hashtag_values},
        "posting_days": {
            "labels": list(combined_days.keys()),
            "values": list(combined_days.values()),
        },
        "posting_hours": {"labels": hour_labels, "values": hour_values},
        "top_posts": top_posts_data,
    }
