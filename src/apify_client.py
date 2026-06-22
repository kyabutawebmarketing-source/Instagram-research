"""Apify API client for Instagram influencer discovery and profile scraping.

Apify provides actors (scrapers) that crawl public Instagram data. This
client is intentionally thin: it knows how to run an actor synchronously
and read back its dataset items. The actor IDs and input shapes are
configurable via environment variables since Apify's marketplace actors
occasionally change their input schema.
"""

import os
import requests

APIFY_BASE_URL = "https://api.apify.com/v2"

# Default actors (can be overridden via env vars). These are well-known
# public Instagram scrapers on the Apify store.
DEFAULT_HASHTAG_ACTOR = "apify~instagram-hashtag-scraper"
DEFAULT_PROFILE_ACTOR = "apify~instagram-scraper"


class ApifyAPIError(Exception):
    """Raised when the Apify API returns an error or unexpected response."""
    pass


class ApifyClient:
    """Minimal client for running Apify actors and fetching their results."""

    def __init__(self, api_token: str, timeout: int = 180):
        if not api_token:
            raise ApifyAPIError("Apify API token is required.")
        self.api_token = api_token
        self.timeout = timeout
        self.session = requests.Session()

    def run_actor(self, actor_id: str, run_input: dict) -> list[dict]:
        """Run an actor synchronously and return its dataset items.

        actor_id uses the Apify "~" separated form, e.g. "apify~instagram-scraper".
        """
        url = f"{APIFY_BASE_URL}/acts/{actor_id}/run-sync-get-dataset-items"
        try:
            response = self.session.post(
                url,
                params={"token": self.api_token},
                json=run_input,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ApifyAPIError(f"Apify actor {actor_id} timed out.")
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = str(e)
            raise ApifyAPIError(f"Apify actor {actor_id} failed: {detail}") from e
        except requests.exceptions.RequestException as e:
            raise ApifyAPIError(f"Apify request failed: {e}") from e

        try:
            items = response.json()
        except ValueError as e:
            raise ApifyAPIError(f"Apify returned invalid JSON: {e}") from e

        if not isinstance(items, list):
            raise ApifyAPIError(f"Unexpected Apify response shape from {actor_id}.")
        return items

    def discover_by_hashtag(self, genre_keyword: str, limit: int = 20) -> list[dict]:
        """Find candidate influencer usernames posting under a genre hashtag."""
        actor_id = os.environ.get("APIFY_HASHTAG_ACTOR", DEFAULT_HASHTAG_ACTOR)
        run_input = {
            "hashtags": [genre_keyword.lstrip("#")],
            "resultsLimit": limit,
        }
        items = self.run_actor(actor_id, run_input)
        usernames: list[str] = []
        seen = set()
        for item in items:
            uname = (
                item.get("ownerUsername")
                or item.get("username")
                or (item.get("owner") or {}).get("username")
            )
            if uname and uname not in seen:
                seen.add(uname)
                usernames.append(uname)
            if len(usernames) >= limit:
                break
        return [{"username": u} for u in usernames]

    def fetch_profiles(self, usernames: list[str], posts_per_profile: int = 30) -> list[dict]:
        """Scrape full profile + recent posts for each given username."""
        actor_id = os.environ.get("APIFY_PROFILE_ACTOR", DEFAULT_PROFILE_ACTOR)
        run_input = {
            "directUrls": [f"https://www.instagram.com/{u}/" for u in usernames],
            "resultsType": "details",
            "resultsLimit": posts_per_profile,
            "addParentData": False,
        }
        return self.run_actor(actor_id, run_input)
