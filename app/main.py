"""Streamlitアプリのエントリーポイント。"""
import streamlit as st

from app.core.session_init import ensure_session

st.set_page_config(
    page_title="一口馬主検討ツール",
    page_icon="🐴",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_session()

st.title("🐴 一口馬主検討ツール")
st.markdown("""
JRA-VANデータをもとに募集馬をスコアリングし、投資候補を絞り込むツールです。

### 使い方
1. **データ準備** ページでDB接続確認と募集馬CSVをアップロード
2. **スコアリング設定** ページで重みを調整してスコアを計算
3. **候補一覧** ページでランキングを確認
4. 気になった馬は **馬詳細** ページで深掘り
""")

with st.sidebar:
    st.markdown("### ステータス")
    if "df_horses" in st.session_state:
        st.success(f"募集馬: {len(st.session_state.df_horses)}頭 読み込み済み")
    else:
        st.warning("募集馬CSVが未読み込みです")

    if "scored_df" in st.session_state:
        source = "（DBから自動読込）" if st.session_state.get("DATA_LOADED_FROM_DB") else ""
        st.success(f"スコアリング完了{source}")
    else:
        st.info("スコアリング未実行")
