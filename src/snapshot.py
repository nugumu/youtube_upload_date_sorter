from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.youtube_api import VideoResult, WATCH_URL, EMBED_URL


_JST = timezone(timedelta(hours=9))


def build_snapshot_payload(
    *,
    results: Sequence[VideoResult],
    query: str,
    filters: Dict[str, Any],
    debug: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a JSON-serializable snapshot payload.

    Notes:
        - API key is intentionally NOT included.
        - `filters` is stored as-is (UI values).
    """

    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(_JST)

    items: List[Dict[str, Any]] = []
    for r in results:
        items.append(
            {
                "video_id": r.video_id,
                "title": r.title,
                "channel_title": r.channel_title,
                "published_at_utc": r.published_at,
                "published_at_jst": _format_rfc3339_to_jst(r.published_at),
                "view_count": r.view_count,
                "url": r.url,
                "embed_url": r.embed_url,
                "thumbnail_url": r.thumbnail_url,
                "description": r.description,
            }
        )

    return {
        "meta": {
            "query": query,
            "created_at_utc": now_utc.isoformat().replace("+00:00", "Z"),
            "created_at_jst": now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
            "results_count": len(items),
            "filters": filters,
            "debug": debug or {},
        },
        "items": items,
    }


def snapshot_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def snapshot_csv_bytes(
    payload: Dict[str, Any], *, include_description: bool = True
) -> bytes:
    """Create a UTF-8 CSV from the snapshot payload."""

    meta = payload.get("meta") or {}
    query = meta.get("query") or ""
    created_at_jst = meta.get("created_at_jst") or ""

    out = io.StringIO()
    writer = csv.writer(out)

    header = [
        "created_at_jst",
        "query",
        "video_id",
        "title",
        "channel_title",
        "published_at_jst",
        "published_at_utc",
        "view_count",
        "url",
        "thumbnail_url",
        "embed_url",
    ]
    if include_description:
        header.append("description")
    writer.writerow(header)

    for it in payload.get("items") or []:
        row = [
            created_at_jst,
            query,
            it.get("video_id") or "",
            it.get("title") or "",
            it.get("channel_title") or "",
            it.get("published_at_jst") or "",
            it.get("published_at_utc") or "",
            it.get("view_count") if it.get("view_count") is not None else "",
            it.get("url") or "",
            it.get("thumbnail_url") or "",
            it.get("embed_url") or "",
        ]
        if include_description:
            # Flatten newlines for easier downstream handling.
            desc = (
                (it.get("description") or "")
                .replace("\r\n", " ")
                .replace("\n", " ")
                .strip()
            )
            row.append(desc)
        writer.writerow(row)

    return out.getvalue().encode("utf-8")


def load_snapshot_payload(*, raw: bytes, filename: str) -> Dict[str, Any]:
    """Load a snapshot payload from JSON or CSV bytes.

    Args:
        raw: File content bytes.
        filename: Used to infer format by extension.

    Returns:
        Payload in the same schema as `build_snapshot_payload`.

    Raises:
        ValueError: If the content cannot be parsed.
    """

    name = (filename or "").lower().strip()
    if name.endswith(".json"):
        return _load_snapshot_json(raw)
    if name.endswith(".csv"):
        return _load_snapshot_csv(raw)

    # Fallback: try JSON then CSV
    try:
        return _load_snapshot_json(raw)
    except Exception:
        return _load_snapshot_csv(raw)


def payload_to_video_results(payload: Dict[str, Any]) -> List[VideoResult]:
    """Convert a snapshot payload to a list of VideoResult."""

    out: List[VideoResult] = []
    for it in payload.get("items") or []:
        vid = (it.get("video_id") or "").strip()
        if not vid:
            continue

        published_at = (
            it.get("published_at_utc")
            or it.get("published_at")
            or it.get("publishedAt")
            or ""
        )
        url = it.get("url") or (WATCH_URL + vid)
        embed_url = it.get("embed_url") or (EMBED_URL + vid)

        vc = it.get("view_count")
        view_count: Optional[int] = None
        if vc is not None and vc != "":
            try:
                view_count = int(vc)
            except Exception:
                view_count = None

        out.append(
            VideoResult(
                video_id=vid,
                title=it.get("title") or "",
                channel_title=it.get("channel_title") or "",
                published_at=published_at,
                description=it.get("description") or "",
                url=url,
                embed_url=embed_url,
                thumbnail_url=it.get("thumbnail_url") or None,
                view_count=view_count,
            )
        )

    return out


def save_snapshot_files(
    *,
    payload: Dict[str, Any],
    out_dir: str,
    base_name: str,
    formats: Sequence[str] = ("json", "csv"),
    include_description_csv: bool = True,
) -> List[str]:
    """Save snapshot files to the given directory.

    Args:
        out_dir: Target directory (created if missing).
        base_name: File name stem (without extension).
        formats: Any of {"json", "csv"}.
    """

    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    stem = _sanitize_filename(base_name) or "snapshot"
    saved: List[str] = []

    if "json" in formats:
        p = out_path / f"{stem}.json"
        p.write_bytes(snapshot_json_bytes(payload))
        saved.append(str(p))

    if "csv" in formats:
        p = out_path / f"{stem}.csv"
        p.write_bytes(
            snapshot_csv_bytes(payload, include_description=include_description_csv)
        )
        saved.append(str(p))

    return saved


def default_snapshot_stem(*, query: str) -> str:
    now_jst = datetime.now(timezone.utc).astimezone(_JST)
    q = _sanitize_filename(query)[:40] if query else "query"
    return f"snapshot_{now_jst.strftime('%Y%m%d_%H%M%S')}_{q}".strip("_")


def _format_rfc3339_to_jst(published_at: str) -> str:
    if not published_at:
        return ""
    try:
        dt_utc = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt_utc.astimezone(_JST).strftime("%Y-%m-%d %H:%M JST")
    except Exception:
        return published_at


_BAD_CHARS = re.compile(r"[^A-Za-z0-9._\-\u3040-\u30FF\u4E00-\u9FFF ]+")


def _sanitize_filename(name: str) -> str:
    s = (name or "").strip()
    s = _BAD_CHARS.sub("_", s)
    s = re.sub(r"\s+", "_", s)
    s = s.strip("._")
    return s


def _load_snapshot_json(raw: bytes) -> Dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"JSONとして読み込めませんでした: {e}")

    if not isinstance(payload, dict):
        raise ValueError("スナップショットJSONの形式が不正です（dictではありません）。")
    if "items" not in payload:
        raise ValueError("スナップショットJSONに items が見つかりません。")
    if "meta" not in payload:
        payload["meta"] = {}
    if not isinstance(payload.get("items"), list):
        raise ValueError("スナップショットJSONの items が配列ではありません。")

    meta = payload.get("meta") or {}
    meta.setdefault("results_count", len(payload.get("items") or []))
    meta.setdefault("filters", {})
    meta.setdefault("debug", {})
    payload["meta"] = meta
    return payload


def _load_snapshot_csv(raw: bytes) -> Dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except Exception as e:
        raise ValueError(f"CSVとして読み込めませんでした（UTF-8想定）: {e}")

    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        raise ValueError("CSVのヘッダが見つかりません。")

    items: List[Dict[str, Any]] = []
    created_at_jst = ""
    query = ""

    for row in reader:
        if not created_at_jst:
            created_at_jst = (row.get("created_at_jst") or "").strip()
        if not query:
            query = (row.get("query") or "").strip()

        vid = (row.get("video_id") or "").strip()
        if not vid:
            continue

        vc_raw = (row.get("view_count") or "").strip()
        vc_val: Optional[int] = None
        if vc_raw != "":
            try:
                vc_val = int(vc_raw)
            except Exception:
                vc_val = None

        items.append(
            {
                "video_id": vid,
                "title": row.get("title") or "",
                "channel_title": row.get("channel_title") or "",
                "published_at_jst": row.get("published_at_jst") or "",
                "published_at_utc": row.get("published_at_utc") or "",
                "view_count": vc_val,
                "url": row.get("url") or (WATCH_URL + vid),
                "thumbnail_url": (row.get("thumbnail_url") or "").strip() or None,
                "embed_url": row.get("embed_url") or (EMBED_URL + vid),
                "description": row.get("description") or "",
            }
        )

    return {
        "meta": {
            "query": query,
            "created_at_jst": created_at_jst,
            "results_count": len(items),
            # CSVにはfilters/debugが入っていないため空
            "filters": {},
            "debug": {},
        },
        "items": items,
    }
