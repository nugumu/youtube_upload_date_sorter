import streamlit as st
from src.youtube_api import YouTubeSearchClient, YouTubeAPIError
from src.ui import (
    render_results,
    render_snapshot_tools,
    render_snapshot_viewer,
    top_search_bar,
    advanced_filters_expander,
)

st.set_page_config(page_title="YouTube アップロード日順検索", layout="wide")

st.title("YouTube アップロード日順検索")
st.caption(
    "YouTube Data API v3 を使って、検索結果を「アップロード日時が新しい順」で表示します。"
)

# ----------------------------
# Session state (results persist across reruns)
# ----------------------------
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_filters" not in st.session_state:
    st.session_state.last_filters = {}
if "last_debug" not in st.session_state:
    st.session_state.last_debug = None

clear_col1, clear_col2 = st.columns([1, 5], vertical_alignment="center")
with clear_col1:
    if st.button(
        "結果をクリア",
        help="表示中の検索結果を消します（スナップショット保存もできなくなります）。",
    ):
        st.session_state.last_results = None
        st.session_state.last_query = ""
        st.session_state.last_filters = {}
        st.session_state.last_debug = None
        st.rerun()
with clear_col2:
    st.caption(
        "※ ボタン操作で再実行（rerun）されるため、結果を保持するにはセッションに保存します。"
    )

# Snapshot viewer (no API key required)
render_snapshot_viewer()

# TOP表示項目
api_key, query, submitted = top_search_bar()

# 高度な検索フィルター
filters = advanced_filters_expander()

if submitted:
    if not api_key.strip():
        st.error("APIキーが未入力です。")
        st.stop()
    if not query.strip():
        st.error("検索ワードが未入力です。")
        st.stop()

    client = YouTubeSearchClient(api_key=api_key.strip())

    with st.spinner("検索中..."):
        try:
            results = client.search_videos(
                q=query.strip(),
                total_results=filters["total_results"],
                region_code=filters["region_code"],
                relevance_language=filters["relevance_language"],
                safe_search=filters["safe_search"],
                video_duration=filters["video_duration"],
                video_definition=filters["video_definition"],
                video_type=filters["video_type"],
                event_type=filters["event_type"],
                channel_id=filters["channel_id"],
                published_after=filters["published_after"],
                published_before=filters["published_before"],
                view_count_min=filters["view_count_min"],
                view_count_max=filters["view_count_max"],
            )
        except YouTubeAPIError as e:
            st.error(f"APIエラー: {e}")
            st.stop()
        except Exception as e:
            st.error(f"予期しないエラー: {e}")
            st.stop()

    # Save to session so that snapshot saving works after reruns (e.g., pressing "保存する").
    st.session_state.last_query = query.strip()
    st.session_state.last_filters = filters
    st.session_state.last_debug = getattr(client, "last_debug", None)

    if results:
        st.session_state.last_results = results
    else:
        # Do not wipe previous results; keep them available for snapshot saving.
        st.warning(
            "結果が0件でした。条件を変えて試してください。"
            "（直前の検索結果がある場合は、そのまま表示し続けます）"
        )

# Display latest results (persisted)
results = st.session_state.last_results
if results:
    st.caption("直近の検索結果を表示中（保存ボタンを押しても消えません）。")
    render_results(results)
    render_snapshot_tools(
        results,
        query=st.session_state.last_query,
        filters=st.session_state.last_filters,
        debug=st.session_state.last_debug,
    )
else:
    st.info("上の欄にAPIキーと検索ワードを入力し、「検索」を押してください。")

# Always show debug if present
if st.session_state.last_debug:
    with st.expander("デバッグ情報（取得状況のサマリ）", expanded=False):
        st.json(st.session_state.last_debug)
