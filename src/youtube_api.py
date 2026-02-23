from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
WATCH_URL = "https://www.youtube.com/watch?v="
EMBED_URL = "https://www.youtube.com/embed/"


class YouTubeAPIError(RuntimeError):
    pass


@dataclass
class VideoResult:
    video_id: str
    title: str
    channel_title: str
    published_at: str  # RFC3339 string (usually ends with 'Z')
    description: str
    url: str
    embed_url: str
    thumbnail_url: Optional[str]
    view_count: Optional[int] = None


class YouTubeSearchClient:
    """
    Minimal client for YouTube Data API v3 search.list.

    Notes:
        - order is fixed to 'date' (newest-first).
        - search.list returns up to 50 per request; we page until total_results (capped).
        - viewCount filtering is done client-side via videos.list(part=statistics).
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
        view_count_min: Optional[int] = None,
        view_count_max: Optional[int] = None,
    ) -> List[VideoResult]:
        if total_results < 1:
            return []

        # YouTube Search API hard-cap: 500 results (10 pages)
        total_results = min(total_results, 500)

        results: List[VideoResult] = []
        page_token: Optional[str] = None
        page_count = 0

        # When view-count filtering is enabled, we may need more candidates than `total_results`.
        need_more_candidates = (view_count_min is not None) or (
            view_count_max is not None
        )

        while len(results) < total_results:
            page_count += 1
            if page_count > 10:
                break  # 500 results max via search.list paging

            batch_size = (
                50 if need_more_candidates else min(50, total_results - len(results))
            )

            params: Dict[str, Any] = {
                "part": "snippet",
                "type": "video",
                "q": q,
                "order": "date",  # newest-first
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
                params["publishedAfter"] = published_after
            if published_before:
                params["publishedBefore"] = published_before

            if page_token:
                params["pageToken"] = page_token

            r = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=self.timeout_s)
            if r.status_code != 200:
                raise YouTubeAPIError(f"HTTP {r.status_code}: {r.text}")

            data = r.json()
            if "error" in data:
                raise YouTubeAPIError(str(data["error"]))

            # Build candidates for this page
            candidates: List[VideoResult] = []
            candidate_ids: List[str] = []

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

                candidates.append(
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
                candidate_ids.append(vid)

            # No more results
            if not candidates:
                break

            # Fetch viewCount for this page (max 50 ids)
            view_counts = self._fetch_view_counts(candidate_ids)

            for c in candidates:
                c.view_count = view_counts.get(c.video_id)

                if view_count_min is not None:
                    if c.view_count is None or c.view_count < view_count_min:
                        continue
                if view_count_max is not None:
                    if c.view_count is None or c.view_count > view_count_max:
                        continue

                results.append(c)
                if len(results) >= total_results:
                    break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return results

    def _fetch_view_counts(self, video_ids: List[str]) -> Dict[str, int]:
        """
        Fetch statistics.viewCount for up to 50 video IDs via videos.list.

        Returns:
            {videoId: viewCount_int}
        """
        if not video_ids:
            return {}

        params: Dict[str, Any] = {
            "part": "statistics",
            "id": ",".join(video_ids[:50]),
            "key": self.api_key,
        }

        r = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=self.timeout_s)
        if r.status_code != 200:
            raise YouTubeAPIError(f"HTTP {r.status_code}: {r.text}")

        data = r.json()
        if "error" in data:
            raise YouTubeAPIError(str(data["error"]))

        out: Dict[str, int] = {}
        for it in data.get("items", []):
            vid = it.get("id")
            stats = it.get("statistics") or {}
            vc = stats.get("viewCount")
            if vid and vc is not None:
                try:
                    out[str(vid)] = int(vc)
                except Exception:
                    # ignore unparsable
                    pass

        return out
