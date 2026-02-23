from __future__ import annotations

from typing import Dict, List, Optional
from datetime import date, time, datetime, timezone, timedelta
from pathlib import Path

import streamlit as st

from src.youtube_api import VideoResult
from src.snapshot import (
    build_snapshot_payload,
    default_snapshot_stem,
    load_snapshot_payload,
    payload_to_video_results,
    save_snapshot_files,
    snapshot_csv_bytes,
    snapshot_json_bytes,
)

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
            "取得件数（取りすぎ注意）", min_value=100, max_value=5000, value=200, step=10
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


def render_snapshot_viewer() -> None:
    """Load and re-display saved snapshots (JSON/CSV)."""

    st.divider()
    with st.expander("スナップショットを読み込んで表示", expanded=False):
        st.caption("保存済みのスナップショット（JSON/CSV）を読み込んで再表示します。")

        mode = st.radio(
            "読み込み方法",
            options=["アップロード", "ローカルフォルダから選択"],
            horizontal=True,
            index=0,
        )

        raw: Optional[bytes] = None
        name: str = ""

        if mode == "アップロード":
            up = st.file_uploader(
                "スナップショットファイル",
                type=["json", "csv"],
                accept_multiple_files=False,
                key="snap_uploader",
            )
            if up is None:
                st.info("JSON/CSVをアップロードすると、検索結果を再表示できます。")
                return
            raw = up.getvalue()
            name = up.name
        else:
            st.caption(
                "※ Streamlit Cloud等ではサーバ側のファイルになります。基本はアップロード推奨です。"
            )
            folder = st.text_input(
                "参照フォルダ",
                value="snapshots",
                key="snap_load_dir",
                help="保存先と同じフォルダを指定してください（例: snapshots）",
            )
            try:
                p = Path(folder).expanduser().resolve()
                files = []
                if p.exists() and p.is_dir():
                    files = sorted(
                        [
                            f
                            for f in p.iterdir()
                            if f.is_file() and f.suffix.lower() in (".json", ".csv")
                        ],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True,
                    )
                if not files:
                    st.warning(
                        "指定フォルダにスナップショット（.json/.csv）が見つかりません。"
                    )
                    return
                chosen = st.selectbox(
                    "ファイルを選択（更新日時が新しい順）",
                    options=files,
                    format_func=lambda x: x.name,
                    key="snap_load_file",
                )
                if st.button(
                    "このファイルを読み込む", type="primary", key="snap_load_btn"
                ):
                    raw = chosen.read_bytes()
                    name = chosen.name
                else:
                    return
            except Exception as e:
                st.error(f"ローカルフォルダからの読み込みに失敗しました: {e}")
                return

        if raw is None:
            return

        try:
            payload = load_snapshot_payload(raw=raw, filename=name)
        except Exception as e:
            st.error(f"スナップショットの読み込みに失敗しました: {e}")
            return

        meta = payload.get("meta") or {}
        st.markdown("**メタ情報**")
        st.json(
            {
                "query": meta.get("query"),
                "created_at_jst": meta.get("created_at_jst"),
                "results_count": meta.get("results_count"),
                "filters": meta.get("filters"),
            }
        )

        results = payload_to_video_results(payload)
        if not results:
            st.warning("スナップショット内に表示できる動画がありません。")
            return

        # Keep the same rendering style as live results.
        st.caption(
            "以下はスナップショットから復元した表示です（APIアクセスは行いません）。"
        )
        render_results(results)


def render_snapshot_tools(
    results: List[VideoResult],
    *,
    query: str,
    filters: Dict[str, object],
    debug: Optional[Dict[str, object]] = None,
) -> None:
    """Render snapshot save/download UI for the current results."""

    st.divider()
    with st.expander("スナップショット保存", expanded=False):
        st.caption(
            "この検索結果を JSON/CSV として保存します。"
            "（Streamlitをローカルで動かしている場合はPC上のフォルダに保存されます）"
        )

        include_desc = st.checkbox(
            "説明文（description）も含める", value=True, key="snap_include_desc"
        )

        stem_default = default_snapshot_stem(query=query)
        stem = st.text_input(
            "ファイル名（拡張子なし）",
            value=stem_default,
            key="snap_stem",
            help="例: snapshot_20260223_123045_music",
        )

        formats = st.multiselect(
            "保存形式",
            options=["json", "csv"],
            default=["json", "csv"],
            key="snap_formats",
        )

        payload = build_snapshot_payload(
            results=results,
            query=query,
            filters=filters,
            debug=debug,
        )

        if not include_desc:
            for it in payload.get("items") or []:
                it["description"] = ""

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if "json" in formats:
                st.download_button(
                    label="JSONをダウンロード",
                    data=snapshot_json_bytes(payload),
                    file_name=f"{stem}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.button("JSONをダウンロード", disabled=True, use_container_width=True)

        with dcol2:
            if "csv" in formats:
                st.download_button(
                    label="CSVをダウンロード",
                    data=snapshot_csv_bytes(payload, include_description=include_desc),
                    file_name=f"{stem}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.button("CSVをダウンロード", disabled=True, use_container_width=True)

        st.markdown("**ローカルに保存**")
        out_dir = st.text_input(
            "保存先フォルダ",
            value="snapshots",
            key="snap_out_dir",
            help="相対パスの場合、アプリを起動したフォルダ配下に作成します。例: snapshots",
        )

        if st.button("保存する", type="primary", key="snap_save"):
            if not formats:
                st.warning("保存形式が未選択です。")
            else:
                try:
                    saved = save_snapshot_files(
                        payload=payload,
                        out_dir=out_dir,
                        base_name=stem,
                        formats=formats,
                        include_description_csv=include_desc,
                    )
                    st.success("保存しました:\n" + "\n".join(saved))
                except Exception as e:
                    st.error(f"保存に失敗しました: {e}")


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
