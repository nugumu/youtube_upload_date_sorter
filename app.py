import streamlit as st
from src.youtube_api import YouTubeSearchClient, YouTubeAPIError
from src.ui import render_results, top_search_bar, advanced_filters_expander

st.set_page_config(page_title="YouTube 日付順検索", layout="wide")

st.title("YouTube 日付順検索")
st.caption(
    "YouTube Data API v3 を使って、検索結果を「アップロード日時が新しい順」で表示します。"
)

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

    if not results:
        st.warning("結果が0件でした。条件を変えて試してください。")
        st.stop()

    render_results(results)
else:
    st.info("上の欄にAPIキーと検索ワードを入力し、「検索」を押してください。")
