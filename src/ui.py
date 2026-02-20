from __future__ import annotations

from typing import Dict, List, Optional
import re
import streamlit as st
from src.youtube_api import VideoResult


def top_search_bar():
    col1, col2, col3 = st.columns([2, 3, 1], vertical_alignment="bottom")
    with col1:
        api_key = st.text_input(
            "APIキー",
            type="password",
            placeholder="AIza...（この入力値は保存しません）",
            help="このアプリはAPIキーをローカルに保存しません。毎回貼り付けて使う想定です。",
        )
    with col2:
        query = st.text_input("検索ワード", placeholder="例: 統計検定1級 解説")
    with col3:
        submitted = st.button("検索", type="primary", use_container_width=True)

    return api_key, query, submitted


def advanced_filters_expander() -> Dict[str, object]:
    with st.expander("検索条件（詳細）", expanded=False):
        total_results = st.slider("取得件数（最大500）", min_value=10, max_value=500, value=50, step=10)

        col1, col2, col3 = st.columns(3)
        with col1:
            region_code = st.text_input("regionCode（任意）", value="JP", help="例: JP, US など（空欄可）").strip() or None
            channel_id = st.text_input("channelId（任意）", value="", help="特定チャンネル内検索（空欄可）").strip() or None
        with col2:
            relevance_language = st.text_input(
                "relevanceLanguage（任意）",
                value="ja",
                help="例: ja, en（空欄可）",
            ).strip() or None
            safe_search = st.selectbox("safeSearch", ["none", "moderate", "strict"], index=0)
        with col3:
            video_duration = st.selectbox("videoDuration", ["any", "short", "medium", "long"], index=0)
            video_definition = st.selectbox("videoDefinition", ["any", "high", "standard"], index=0)

        col4, col5, col6 = st.columns(3)
        with col4:
            video_type = st.selectbox("videoType", ["any", "episode", "movie"], index=0)
        with col5:
            event_type = st.selectbox("eventType", ["none", "completed", "live", "upcoming"], index=0)
        with col6:
            st.write("")  # spacing

        st.markdown("**期間指定** 例: `2024-01-01T00:00:00Z`")
        col7, col8 = st.columns(2)
        with col7:
            published_after = st.text_input("publishedAfter（任意）", value="", help="指定した日時以降を検索（空欄可）").strip() or None
            if published_after and not _looks_like_rfc3339(published_after):
                st.warning("publishedAfter の形式が正しくありません（例: 2024-01-01T00:00:00Z）")
        with col8:
            published_before = st.text_input("publishedBefore（任意）", value="", help="指定した日時以前を検索（空欄可）").strip() or None
            if published_before and not _looks_like_rfc3339(published_before):
                st.warning("publishedBefore の形式が正しくありません（例: 2024-01-01T00:00:00Z）")

    return {
        "total_results": int(total_results),
        "region_code": region_code,
        "relevance_language": relevance_language,
        "safe_search": safe_search,
        "video_duration": video_duration,
        "video_definition": video_definition,
        "video_type": video_type,
        "event_type": event_type,
        "channel_id": channel_id,
        "published_after": published_after,
        "published_before": published_before,
    }


def render_results(results: List[VideoResult]) -> None:
    st.divider()
    st.subheader(f"検索結果（新しい順）: {len(results)}件")

    for r in results:
        # 1件ずつカード風
        with st.container(border=True):
            left, right = st.columns([2, 3], vertical_alignment="top")

            with left:
                # Responsive-ish embed
                st.components.v1.iframe(r.embed_url, height=220, scrolling=False)

            with right:
                st.markdown(f"### [{_escape_md(r.title)}]({r.url})")
                meta = " / ".join([x for x in [r.channel_title, r.published_at] if x])
                if meta:
                    st.caption(meta)

                desc = (r.description or "").strip().replace("\n", " ")
                if desc:
                    st.write(_truncate(desc, 180))
                else:
                    st.write("")


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _escape_md(s: str) -> str:
    # Streamlit markdown link text: escape brackets
    return s.replace("[", "［").replace("]", "］")


_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _looks_like_rfc3339(s: str) -> bool:
    return bool(_RFC3339_RE.match(s))
