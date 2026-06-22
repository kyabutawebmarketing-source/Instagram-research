"""Apify-backed Instagram client for influencer analysis.

Unlike the Graph API client, this does not require a Business/Creator
account or Facebook app review — it scrapes public profile and post data
via Apify's Instagram Scraper actor.
"""

import time
from typing import Optional

import requests

API_BASE = "https://api.apify.com/v2"
DEFAULT_ACTOR = "apify/instagram-scraper"


class ApifyAPIError(Exception):
    """Raised when the Apify API returns an error or the run fails."""
    pass


class ApifyInstagramClient:
    """Fetches Instagram profile/post data through an Apify actor run."""

    def __init__(self, api_token: str, actor_id: str = DEFAULT_ACTOR):
        self.api_token = api_token
        self.actor_id = actor_id
        self.session = requests.Session()

    def _run_actor(self, run_input: dict, poll_interval: float = 5.0, timeout: float = 300.0) -> list[dict]:
        """Start an actor run, wait for it to finish, and return its dataset items."""
        actor_path = self.actor_id.replace("/", "~")
        start_url = f"{API_BASE}/acts/{actor_path}/runs"

        try:
            resp = self.session.post(
                start_url,
                params={"token": self.api_token},
                json=run_input,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ApifyAPIError(f"Failed to start actor run: {e}") from e

        run = resp.json().get("data", {})
        run_id = run.get("id")
        if not run_id:
            raise ApifyAPIError("Actor run did not return an id")

        status_url = f"{API_BASE}/actor-runs/{run_id}"
        elapsed = 0.0
        status = run.get("status", "READY")
        while status in ("READY", "RUNNING"):
            if elapsed >= timeout:
                raise ApifyAPIError(f"Actor run {run_id} timed out after {timeout}s")
            time.sleep(poll_interval)
            elapsed += poll_interval
            try:
                resp = self.session.get(status_url, params={"token": self.api_token}, timeout=30)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise ApifyAPIError(f"Failed to poll actor run: {e}") from e
            status = resp.json().get("data", {}).get("status", "RUNNING")

        if status != "SUCCEEDED":
            raise ApifyAPIError(f"Actor run finished with status: {status}")

        dataset_id = resp.json().get("data", {}).get("defaultDatasetId")
        if not dataset_id:
            raise ApifyAPIError("Actor run has no dataset")

        items_url = f"{API_BASE}/datasets/{dataset_id}/items"
        try:
            resp = self.session.get(items_url, params={"token": self.api_token}, timeout=60)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ApifyAPIError(f"Failed to fetch dataset items: {e}") from e

        return resp.json()

    def get_profile(self, username: str, post_limit: int = 50) -> dict:
        """Fetch a public Instagram profile with its recent posts.

        Returns a dict shaped like InstagramClient.get_competitor_profile:
        id, name, username, followers_count, media_count, biography, media.
        """
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "details",
            "resultsLimit": post_limit,
        }
        items = self._run_actor(run_input)
        if not items:
            raise ApifyAPIError(f"No data returned for @{username}")
        return self._profile_from_raw(items[0], post_limit)

    def get_profiles_bulk(self, usernames: list[str], post_limit: int = 50) -> list[dict]:
        """Fetch multiple public profiles in a single actor run.

        Returns a list of profile dicts in the same shape as get_profile.
        Usernames that fail to resolve are silently skipped.
        """
        if not usernames:
            return []

        run_input = {
            "directUrls": [f"https://www.instagram.com/{u}/" for u in usernames],
            "resultsType": "details",
            "resultsLimit": post_limit,
        }
        items = self._run_actor(run_input)
        return [self._profile_from_raw(raw, post_limit) for raw in items if raw.get("username")]

    def discover_usernames_by_hashtag(self, hashtag: str, limit: int = 50) -> list[dict]:
        """Search recent posts under a hashtag and return unique post authors.

        Returns a list of dicts with: username, followers_count (0 — not
        known yet at this stage), used as discovery candidates before a
        full profile fetch.
        """
        tag = hashtag.lstrip("#")
        run_input = {
            "search": tag,
            "searchType": "hashtag",
            "resultsType": "posts",
            "resultsLimit": limit,
        }
        items = self._run_actor(run_input)

        seen: dict[str, dict] = {}
        for item in items:
            username = item.get("ownerUsername")
            if not username or username in seen:
                continue
            seen[username] = {"username": username, "owner_id": item.get("ownerId", "")}
        return list(seen.values())

    def _profile_from_raw(self, raw: dict, post_limit: int) -> dict:
        """Normalize a raw 'details' actor item into the analyzer's profile shape."""
        username = raw.get("username", "")
        media_raw = raw.get("latestPosts", []) or raw.get("posts", []) or []
        return {
            "id": str(raw.get("id", username)),
            "name": raw.get("fullName", "") or username,
            "username": username,
            "followers_count": raw.get("followersCount", 0) or 0,
            "media_count": raw.get("postsCount", 0) or 0,
            "biography": raw.get("biography", "") or "",
            "media": [self._normalize_post(p) for p in media_raw[:post_limit]],
        }

    @staticmethod
    def _normalize_post(raw: dict) -> dict:
        """Normalize an Apify post item to the analyzer's expected shape."""
        likes = raw.get("likesCount", 0) or 0
        comments = raw.get("commentsCount", 0) or 0
        media_type = "VIDEO" if raw.get("type") == "Video" else (
            "CAROUSEL_ALBUM" if raw.get("type") == "Sidecar" else "IMAGE"
        )
        return {
            "id": str(raw.get("id", "")),
            "timestamp": raw.get("timestamp", "") or "",
            "media_type": media_type,
            "caption": raw.get("caption", "") or "",
            "like_count": likes,
            "comments_count": comments,
            "permalink": raw.get("url", "") or "",
        }
