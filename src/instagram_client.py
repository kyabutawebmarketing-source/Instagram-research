"""Instagram Graph API client for fetching competitor account data."""

import requests
from typing import Optional


BASE_URL = "https://graph.instagram.com/v21.0"


class InstagramAPIError(Exception):
    """Raised when the Instagram API returns an error."""
    pass


class InstagramClient:
    """Client for the Instagram Graph API."""

    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request."""
        if params is None:
            params = {}
        params["access_token"] = self.access_token

        url = f"{BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise InstagramAPIError(f"Request timed out for {url}")
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                msg = error_data.get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise InstagramAPIError(f"HTTP error: {msg}") from e
        except requests.exceptions.RequestException as e:
            raise InstagramAPIError(f"Request failed: {e}") from e

        data = response.json()
        if "error" in data:
            raise InstagramAPIError(data["error"].get("message", "Unknown API error"))
        return data

    def get_user_profile(self, user_id: Optional[str] = None) -> dict:
        """Fetch user profile information.

        Returns a dict with: id, name, username, followers_count,
        media_count, biography.
        """
        uid = user_id or self.user_id
        fields = "id,name,username,followers_count,media_count,biography,profile_picture_url"
        data = self._get(uid, {"fields": fields})
        return {
            "id": data.get("id", uid),
            "name": data.get("name", ""),
            "username": data.get("username", ""),
            "followers_count": data.get("followers_count", 0),
            "media_count": data.get("media_count", 0),
            "biography": data.get("biography", ""),
            "profile_picture_url": data.get("profile_picture_url", ""),
        }

    def get_competitor_profile(self, competitor_username: str) -> dict:
        """Fetch a competitor's profile via the Business Discovery API.

        Requires the authenticated user to be a Business/Creator account.
        """
        fields = (
            "business_discovery.fields("
            "id,name,username,followers_count,media_count,biography,"
            "media{id,timestamp,media_type,caption,like_count,comments_count}"
            ")"
        )
        data = self._get(
            self.user_id,
            {"fields": fields, "username": competitor_username},
        )
        discovery = data.get("business_discovery", {})
        profile = {
            "id": discovery.get("id", ""),
            "name": discovery.get("name", competitor_username),
            "username": discovery.get("username", competitor_username),
            "followers_count": discovery.get("followers_count", 0),
            "media_count": discovery.get("media_count", 0),
            "biography": discovery.get("biography", ""),
        }
        media_raw = discovery.get("media", {}).get("data", [])
        profile["media"] = [self._normalize_media(m) for m in media_raw]
        return profile

    def get_media_list(self, user_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Fetch a list of media posts for the given user.

        Returns a list of dicts with: id, timestamp, media_type, caption,
        like_count, comments_count.
        """
        uid = user_id or self.user_id
        fields = "id,timestamp,media_type,caption,like_count,comments_count,permalink"
        data = self._get(f"{uid}/media", {"fields": fields, "limit": limit})
        return [self._normalize_media(m) for m in data.get("data", [])]

    def get_media_insights(self, media_id: str) -> dict:
        """Fetch insights (impressions, reach, engagement) for a single media post."""
        metrics = "impressions,reach,engagement,saved"
        data = self._get(f"{media_id}/insights", {"metric": metrics})
        result: dict = {}
        for item in data.get("data", []):
            result[item["name"]] = item.get("values", [{}])[0].get("value", 0)
        return result

    @staticmethod
    def _normalize_media(raw: dict) -> dict:
        """Normalize a raw media dict to a consistent structure."""
        return {
            "id": raw.get("id", ""),
            "timestamp": raw.get("timestamp", ""),
            "media_type": raw.get("media_type", "IMAGE"),
            "caption": raw.get("caption", "") or "",
            "like_count": raw.get("like_count", 0),
            "comments_count": raw.get("comments_count", 0),
            "permalink": raw.get("permalink", ""),
        }
