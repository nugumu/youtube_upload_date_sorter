from __future__ import annotations

from typing import Dict, List, Optional
from datetime import date, time, datetime, timezone, timedelta

import streamlit as st

from src.youtube_api import VideoResult

_JST = timezone(timedelta(hours=9))


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

        st.markdown(
            "**再生数フィルタ（任意）**（API側で絞り込みはできないため、取得後にフィルタします）"
        )
        vcol1, vcol2 = st.columns(2)
        with vcol1:
            use_min = st.checkbox("再生数の下限を指定", value=False)
            view_count_min: Optional[int] = None
            if use_min:
                view_count_min = int(
                    st.number_input(
                        "下限（回）",
                        min_value=0,
                        value=0,
                        step=1000,
                        help="この回数以上の動画だけ表示します",
                    )
                )
        with vcol2:
            use_max = st.checkbox("再生数の上限を指定", value=False)
            view_count_max: Optional[int] = None
            if use_max:
                view_count_max = int(
                    st.number_input(
                        "上限（回）",
                        min_value=0,
                        value=10000,
                        step=1000,
                        help="この回数以下の動画だけ表示します",
                    )
                )

        if view_count_min is not None and view_count_max is not None:
            if view_count_min > view_count_max:
                st.warning(
                    "再生数の下限が上限を上回っています（結果が0件になります）。"
                )

        st.markdown("**期間指定（日本時間/JST）**")
        col7, col8 = st.columns(2)

        with col7:
            use_after = st.checkbox("開始日時を指定", value=False)
            published_after: Optional[str] = None
            if use_after:
                d_after: date = st.date_input("開始日（JST）", value=date.today())
                t_after: time = st.time_input(
                    "開始時刻（JST）", value=time(0, 0), step=60
                )
                published_after = _to_rfc3339_jst(d_after, t_after)

        with col8:
            use_before = st.checkbox("終了日時を指定", value=False)
            published_before: Optional[str] = None
            if use_before:
                d_before: date = st.date_input("終了日（JST）", value=date.today())
                t_before: time = st.time_input(
                    "終了時刻（JST）", value=time(23, 59), step=60
                )
                published_before = _to_rfc3339_jst(d_before, t_before)

        if published_after and published_before:
            try:
                da = datetime.fromisoformat(published_after.replace("Z", "+00:00"))
                db = datetime.fromisoformat(published_before.replace("Z", "+00:00"))
                if da > db:
                    st.warning(
                        "開始日時が終了日時より後になっています（結果が0件になります）。"
                    )
            except Exception:
                pass

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
        "view_count_min": view_count_min,
        "view_count_max": view_count_max,
    }


def render_results(results: List[VideoResult]) -> None:
    st.divider()
    st.subheader(f"検索結果（新しい順）: {len(results)}件")

    for r in results:
        with st.container(border=True):
            left, right = st.columns([2, 3], vertical_alignment="top")

            with left:
                st.components.v1.iframe(r.embed_url, height=220, scrolling=False)

            with right:
                st.markdown(f"### [{_escape_md(r.title)}]({r.url})")

                published_jst = _format_published_at_jst(r.published_at)
                views = (
                    f"再生数: {r.view_count:,}"
                    if r.view_count is not None
                    else "再生数: -"
                )
                meta = " / ".join(
                    [x for x in [r.channel_title, published_jst, views] if x]
                )
                if meta:
                    st.caption(meta)

                desc = (r.description or "").strip().replace("\n", " ")
                if desc:
                    st.write(_truncate(desc, 180))
                else:
                    st.write("")


def _to_rfc3339_jst(d: date, t: time) -> str:
    dt_jst = datetime.combine(d, t).replace(tzinfo=_JST)
    dt_utc = dt_jst.astimezone(timezone.utc)
    # RFC3339 (UTC): 'YYYY-MM-DDTHH:MM:SSZ'
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_published_at_jst(published_at: str) -> str:
    if not published_at:
        return ""
    try:
        dt_utc = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        dt_jst = dt_utc.astimezone(_JST)
        return dt_jst.strftime("%Y-%m-%d %H:%M JST")
    except Exception:
        return published_at


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _escape_md(s: str) -> str:
    # Streamlit markdown link text: escape brackets
    return s.replace("[", "［").replace("]", "］")
