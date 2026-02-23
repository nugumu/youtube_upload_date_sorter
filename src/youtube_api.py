from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
WATCH_URL = "https://www.youtube.com/watch?v="
EMBED_URL = "https://www.youtube.com/embed/"


class YouTubeAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoResult:
    video_id: str
    title: str
    channel_title: str
    published_at: str  # RFC3339 string
    description: str
    url: str
    embed_url: str
    thumbnail_url: Optional[str]


class YouTubeSearchClient:
    """
    Minimal client for YouTube Data API v3 search.list.

    Notes:
        - order is fixed to 'date' (newest-first).
        - search.list returns up to 50 per request; we page until total_results (capped).
    """

    def __init__(self, api_key: str, timeout_s: int = 30) -> None:
        self.api_key = api_key
        self.timeout_s = timeout_s

    def search_videos(
        self,
        q: str,
        total_results: int = 50,
        region_code: Optional[str] = "JP",
        relevance_language: Optional[str] = "ja",
        safe_search: str = "none",
        video_duration: str = "any",
        video_definition: str = "any",
        video_type: str = "any",
        event_type: str = "none",
        channel_id: Optional[str] = None,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> List[VideoResult]:
        if total_results < 1:
            return []

        total_results = min(total_results, 500)  # 上限は500件（10ページ）
        per_page = 50

        items: List[VideoResult] = []
        page_token: Optional[str] = None

        while len(items) < total_results:
            batch_size = min(per_page, total_results - len(items))
            params: Dict[str, Any] = {
                "part": "snippet",
                "type": "video",
                "q": q,
                "order": "date",  # 必ず日付順で表示
                "maxResults": batch_size,
                "key": self.api_key,
            }

            # Optional filters
            if region_code:
                params["regionCode"] = region_code
            if relevance_language:
                params["relevanceLanguage"] = relevance_language
            if safe_search and safe_search != "none":
                params["safeSearch"] = safe_search  # moderate|strict
            if video_duration and video_duration != "any":
                params["videoDuration"] = video_duration  # short|medium|long
            if video_definition and video_definition != "any":
                params["videoDefinition"] = video_definition  # high|standard
            if video_type and video_type != "any":
                params["videoType"] = video_type  # episode|movie
            if event_type and event_type != "none":
                params["eventType"] = event_type  # completed|live|upcoming
            if channel_id:
                params["channelId"] = channel_id
            if published_after:
                params["publishedAfter"] = published_after  # この日以後
            if published_before:
                params["publishedBefore"] = published_before  # この日以前

            if page_token:
                params["pageToken"] = page_token

            r = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=self.timeout_s)
            if r.status_code != 200:
                raise YouTubeAPIError(f"HTTP {r.status_code}: {r.text}")

            data = r.json()
            if "error" in data:
                raise YouTubeAPIError(str(data["error"]))

            for it in data.get("items", []):
                vid = (it.get("id") or {}).get("videoId")
                sn = it.get("snippet") or {}
                if not vid:
                    continue

                thumbs = sn.get("thumbnails") or {}
                thumb_url = None
                for k in ("high", "medium", "default"):
                    if (
                        k in thumbs
                        and isinstance(thumbs[k], dict)
                        and thumbs[k].get("url")
                    ):
                        thumb_url = thumbs[k]["url"]
                        break

                items.append(
                    VideoResult(
                        video_id=vid,
                        title=sn.get("title") or "",
                        channel_title=sn.get("channelTitle") or "",
                        published_at=sn.get("publishedAt") or "",
                        description=sn.get("description") or "",
                        url=WATCH_URL + vid,
                        embed_url=EMBED_URL + vid,
                        thumbnail_url=thumb_url,
                    )
                )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return items
