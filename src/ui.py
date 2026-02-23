from __future__ import annotations

from typing import Dict, List
import re
import streamlit as st
from src.youtube_api import VideoResult


def top_search_bar():
    col1, col2, col3 = st.columns([2, 3, 1], vertical_alignment="bottom")
    with col1:
        api_key = st.text_input(
            "APIキー",
            type="password",
            placeholder="この入力値は保存しません",
            help="このアプリはAPIキーをローカルに保存しません。毎回貼り付けて使う想定です。",
        )
    with col2:
        query = st.text_input("検索ワード", placeholder="例: VTuber 切り抜き")
    with col3:
        submitted = st.button("検索", type="primary", use_container_width=True)

    return api_key, query, submitted


def advanced_filters_expander() -> Dict[str, object]:
    with st.expander("検索条件（詳細）", expanded=False):
        total_results = st.slider(
            "取得件数（最大500）", min_value=10, max_value=500, value=50, step=10
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            region_code = (
                st.text_input(
                    "国コード（任意）", value="JP", help="例: JP, US など（空欄可）"
                ).strip()
                or None
            )
            channel_id = (
                st.text_input(
                    "チャンネルID（任意）",
                    value="",
                    help="@始まりではなくUCrXUs...のようなID（空欄可）",
                ).strip()
                or None
            )
        with col2:
            relevance_language = (
                st.text_input(
                    "言語（任意）",
                    value="ja",
                    help="例: ja, en（空欄可）",
                ).strip()
                or None
            )
            safe_search = st.selectbox(
                "セーフサーチ", ["none", "moderate", "strict"], index=0
            )
        with col3:
            video_duration = st.selectbox(
                "動画長",
                ["any", "short", "medium", "long"],
                index=0,
                help="short: 4分未満, medium: 4~20分, long: 20分超",
            )
            video_definition = st.selectbox(
                "解像度", ["any", "high", "standard"], index=0
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            video_type = st.selectbox(
                "ビデオタイプ",
                ["any", "episode", "movie"],
                index=0,
                help="YouTube公式提供の映画や番組エピソードに絞りたい場合（除外検索はAPIの仕様上不可）",
            )
        with col5:
            event_type = st.selectbox(
                "ライブ配信の状態",
                ["none", "completed", "live", "upcoming"],
                index=0,
                help="completed: 配信完了, live: 配信中, upcoming: 配信予定",
            )
        with col6:
            st.write("")  # spacing

        st.markdown("**期間指定（日本時間マイナス9時間）** 例: `2024-01-01T00:00:00Z`")
        col7, col8 = st.columns(2)
        with col7:
            published_after = (
                st.text_input(
                    "開始（任意）",
                    value="",
                    help="指定した日時以降を検索（空欄可）",
                ).strip()
                or None
            )
            if published_after and not _looks_like_rfc3339(published_after):
                st.warning("日時形式が正しくありません（例: 2024-01-01T00:00:00Z）")
        with col8:
            published_before = (
                st.text_input(
                    "終了日時（任意）",
                    value="",
                    help="指定した日時以前を検索（空欄可）",
                ).strip()
                or None
            )
            if published_before and not _looks_like_rfc3339(published_before):
                st.warning("日時形式が正しくありません（例: 2024-01-01T00:00:00Z）")

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
