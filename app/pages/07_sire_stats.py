"""種牡馬成績分析：年度・年齢別ランキング（行クリックで詳細展開）。"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.core.db_reader import DBReader
from app.core.session_init import ensure_session

ensure_session()

st.title("🐎 種牡馬成績分析")

db: DBReader | None = st.session_state.get("db")
db_path: str | None = st.session_state.get("db_path")

if db is None or db_path is None:
    st.warning("jravan.db が接続されていません。「データ準備」ページで DB パスを設定してください。")
    st.stop()


# --- キャッシュ付きクエリ関数 ---

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_available_years(db_path: str) -> list[int]:
    r = DBReader(db_path)
    r.connect()
    try:
        return r.get_sire_available_years()
    finally:
        r.disconnect()


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_sire_ranking(db_path: str, year: int, age_filter) -> pd.DataFrame:
    r = DBReader(db_path)
    r.connect()
    try:
        return r.get_sire_ranking(year, age_filter)
    finally:
        r.disconnect()


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_by_condition(db_path: str, sire_code: str, year: int, age_filter) -> pd.DataFrame:
    r = DBReader(db_path)
    r.connect()
    try:
        return r.get_sire_by_condition(sire_code, year, age_filter)
    finally:
        r.disconnect()


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_top_bms(db_path: str, sire_code: str, year: int, age_filter, limit: int) -> pd.DataFrame:
    r = DBReader(db_path)
    r.connect()
    try:
        return r.get_sire_top_broodmare_sires(sire_code, year, age_filter, limit)
    finally:
        r.disconnect()


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_top_offspring(db_path: str, sire_code: str, year: int, age_filter, limit: int) -> pd.DataFrame:
    r = DBReader(db_path)
    r.connect()
    try:
        return r.get_sire_top_offspring(sire_code, year, age_filter, limit)
    finally:
        r.disconnect()


# --- 年度データ確認 ---

years = _cached_available_years(db_path)
if not years:
    st.info("レースデータが取り込まれていません（`--race-setup` を実行してください）。")
    st.stop()


# --- コントロール ---

ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])
with ctrl1:
    selected_year = st.selectbox("年度", years, index=0)
with ctrl2:
    rank_limit = st.number_input("ランキング表示件数", min_value=10, max_value=500, value=50, step=10)
with ctrl3:
    detail_limit = st.slider("母父・産駒の表示件数", min_value=5, max_value=15, value=10)


# --- ユーティリティ ---

def _fmt_prize(val_sen_yen: float) -> str:
    man = val_sen_yen / 10
    if man >= 10000:
        return f"{man / 10000:.1f}億円"
    return f"{man:,.0f}万円"


_SHOW_COLS = [
    "sire_name", "offspring_count", "winners_count",
    "total_runs", "wins", "places", "shows",
    "win_rate_pct", "place_rate_pct", "show_rate_pct",
    "win_up_rate_pct", "graded_wins",
    "prize_per_off_man", "total_prize_man",
]

_COL_CFG = {
    "sire_name":         st.column_config.TextColumn("種牡馬名"),
    "offspring_count":   st.column_config.NumberColumn("産駒頭数",         format="%d"),
    "winners_count":     st.column_config.NumberColumn("勝上り頭数",       format="%d"),
    "total_runs":        st.column_config.NumberColumn("出走",             format="%d"),
    "wins":              st.column_config.NumberColumn("勝利",             format="%d"),
    "places":            st.column_config.NumberColumn("2着",              format="%d"),
    "shows":             st.column_config.NumberColumn("3着",              format="%d"),
    "win_rate_pct":      st.column_config.NumberColumn("勝率%",            format="%.1f"),
    "place_rate_pct":    st.column_config.NumberColumn("連対率%",          format="%.1f"),
    "show_rate_pct":     st.column_config.NumberColumn("複勝率%",          format="%.1f"),
    "win_up_rate_pct":   st.column_config.NumberColumn("勝上り率%",        format="%.1f"),
    "graded_wins":       st.column_config.NumberColumn("重賞勝利",         format="%d"),
    "prize_per_off_man": st.column_config.NumberColumn("1頭あたり賞金(万)", format="%.1f"),
    "total_prize_man":   st.column_config.NumberColumn("総賞金(万)",       format="%.0f"),
}


def _prep_display(ranking_df: pd.DataFrame) -> pd.DataFrame:
    disp = ranking_df.copy()
    disp["win_rate_pct"]      = (disp["win_rate"]          * 100).round(1)
    disp["place_rate_pct"]    = (disp["place_rate"]        * 100).round(1)
    disp["show_rate_pct"]     = (disp["show_rate"]         * 100).round(1)
    disp["win_up_rate_pct"]   = (disp["win_up_rate"]       * 100).round(1)
    disp["total_prize_man"]   = (disp["total_prize"]       / 10).round(0)
    disp["prize_per_off_man"] = (disp["prize_per_offspring"] / 10).round(1)
    return disp


_SORT_OPTIONS: dict[str, str] = {
    "総賞金":        "total_prize_man",
    "1頭あたり賞金": "prize_per_off_man",
    "勝上り率":      "win_up_rate_pct",
    "勝率":          "win_rate_pct",
    "産駒頭数":      "offspring_count",
    "出走数":        "total_runs",
    "重賞勝利":      "graded_wins",
}


def _apply_filters(disp: pd.DataFrame, label: str) -> pd.DataFrame:
    """フィルタ・ソートUIを描画し、適用後の DataFrame を返す。"""
    with st.expander("🔍 フィルタ / ソート", expanded=False):
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            min_offspring = st.number_input(
                "産駒頭数（最小）", min_value=0, value=0, step=1,
                key=f"filt_offspring_{label}")
        with fc2:
            min_prize_per = st.number_input(
                "1頭あたり賞金（万円以上）", min_value=0, value=0, step=10,
                key=f"filt_prize_per_{label}")
        with fc3:
            min_winup = st.number_input(
                "勝上り率%（以上）", min_value=0.0, max_value=100.0,
                value=0.0, step=1.0, format="%.1f",
                key=f"filt_winup_{label}")
        with fc4:
            sort_label = st.selectbox(
                "ソート列", list(_SORT_OPTIONS.keys()),
                key=f"sort_col_{label}")
        with fc5:
            sort_asc = st.checkbox("昇順", value=False, key=f"sort_asc_{label}")

    mask = (
        (disp["offspring_count"].fillna(0)    >= min_offspring) &
        (disp["prize_per_off_man"].fillna(0)  >= min_prize_per) &
        (disp["win_up_rate_pct"].fillna(0)    >= min_winup)
    )
    return disp[mask].sort_values(_SORT_OPTIONS[sort_label], ascending=sort_asc)


def _build_condition_display(df: pd.DataFrame) -> pd.DataFrame:
    """track_type ごとに小計行を先頭に挿入したテーブルを返す。"""
    if df.empty:
        return df
    rows: list[pd.DataFrame] = []
    for track in [t for t in ["芝", "ダート", "その他"] if t in df["track_type"].values]:
        grp = df[df["track_type"] == track]
        sub = pd.DataFrame([{
            "track_type":      track,
            "distance_bucket": "【小計】",
            "runs":    grp["runs"].sum(),
            "wins":    grp["wins"].sum(),
            "places":  grp["places"].sum(),
            "shows":   grp["shows"].sum(),
            "total_prize": grp["total_prize"].sum(),
        }])
        rows.extend([sub, grp])
    combined = pd.concat(rows, ignore_index=True)
    denom = combined["runs"].replace(0, float("nan"))
    combined["win_rate_pct"]   = (combined["wins"]   / denom * 100).round(1)
    combined["place_rate_pct"] = (combined["places"] / denom * 100).round(1)
    combined["show_rate_pct"]  = (combined["shows"]  / denom * 100).round(1)
    combined["total_prize_man"] = (combined["total_prize"] / 10).round(0).astype("Int64")
    return combined[[
        "track_type", "distance_bucket", "runs", "wins",
        "win_rate_pct", "place_rate_pct", "show_rate_pct", "total_prize_man",
    ]].rename(columns={
        "track_type":       "馬場",
        "distance_bucket":  "距離",
        "runs":             "出走",
        "wins":             "勝利",
        "win_rate_pct":     "勝率%",
        "place_rate_pct":   "連対率%",
        "show_rate_pct":    "複勝率%",
        "total_prize_man":  "総賞金(万円)",
    })


def _render_detail(sire_code: str, row: pd.Series, year: int, age_filter) -> None:
    """詳細セクション（サマリー・条件別・母父・産駒）を描画する。"""
    st.divider()
    st.subheader(f"📊 {row['sire_name']} — {year}年 詳細")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("出走数",          f"{int(row['total_runs']):,}")
    m2.metric("勝率",            f"{float(row['win_rate'] or 0) * 100:.1f}%")
    m3.metric("連対率",          f"{float(row['place_rate'] or 0) * 100:.1f}%")
    m4.metric("勝上がり率",      f"{float(row['win_up_rate'] or 0) * 100:.1f}%")
    m5.metric("総賞金",          _fmt_prize(float(row["total_prize"] or 0)))
    m6.metric("1頭あたり賞金",   _fmt_prize(float(row["prize_per_offspring"] or 0)))

    st.subheader("条件別成績")
    with st.spinner("集計中…"):
        cond_df = _cached_by_condition(db_path, sire_code, year, age_filter)
    if cond_df.empty:
        st.info("条件別データなし")
    else:
        st.dataframe(_build_condition_display(cond_df), use_container_width=True, hide_index=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("主要母父")
        with st.spinner("集計中…"):
            bms_df = _cached_top_bms(db_path, sire_code, year, age_filter, detail_limit)
        if bms_df.empty:
            st.info("母父データなし")
        else:
            total_p = bms_df["total_prize"].sum()
            bms_df = bms_df.copy()
            bms_df["pct"]          = (bms_df["total_prize"] / total_p * 100).round(1) if total_p else 0.0
            bms_df["win_rate_pct"] = (bms_df["win_rate"] * 100).round(1)
            bms_df["total_prize_man"] = (bms_df["total_prize"] / 10).round(0).astype("Int64")
            st.dataframe(
                bms_df[[
                    "broodmare_sire_name", "offspring_count", "runs",
                    "wins", "win_rate_pct", "total_prize_man", "pct",
                ]].rename(columns={
                    "broodmare_sire_name": "母父名",
                    "offspring_count":     "産駒頭数",
                    "runs":                "出走",
                    "wins":                "勝利",
                    "win_rate_pct":        "勝率%",
                    "total_prize_man":     "総賞金(万円)",
                    "pct":                 "賞金構成比%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    with col_right:
        st.subheader("主要産駒")
        with st.spinner("集計中…"):
            off_df = _cached_top_offspring(db_path, sire_code, year, age_filter, detail_limit)
        if off_df.empty:
            st.info("産駒データなし")
        else:
            off_df = off_df.copy()
            off_df["total_prize_man"] = (off_df["total_prize"] / 10).round(0).astype("Int64")
            st.dataframe(
                off_df[[
                    "horse_name", "runs", "wins", "graded_wins", "total_prize_man",
                ]].rename(columns={
                    "horse_name":      "馬名",
                    "runs":            "出走",
                    "wins":            "勝利",
                    "graded_wins":     "重賞勝利",
                    "total_prize_man": "総賞金(万円)",
                }),
                use_container_width=True,
                hide_index=True,
            )


# --- 年齢タブ ---

AGE_CONFIGS: list[tuple[str, int | tuple | None]] = [
    ("2歳",     2),
    ("3歳",     3),
    ("2歳+3歳", (2, 3)),
    ("全体",    None),
]

tabs = st.tabs([label for label, _ in AGE_CONFIGS])

for tab, (label, age_filter) in zip(tabs, AGE_CONFIGS):
    with tab:
        with st.spinner(f"{label}戦データを集計中…"):
            ranking_df = _cached_sire_ranking(db_path, selected_year, age_filter)

        if ranking_df.empty:
            st.info(f"{selected_year}年の{label}戦データがありません。")
            continue

        disp_all = _prep_display(ranking_df)
        disp = _apply_filters(disp_all, label)
        disp = disp.head(int(rank_limit))

        if disp.empty:
            st.info("フィルタ条件に一致する種牡馬がいません。")
            continue

        st.caption(
            f"{len(disp):,}件 / 全{len(disp_all):,}件  ｜  行をクリックすると詳細が展開されます"
        )
        event = st.dataframe(
            disp,
            column_order=_SHOW_COLS,
            column_config=_COL_CFG,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"ranking_table_{label}",
        )

        if event.selection.rows:
            idx = event.selection.rows[0]
            row = disp.iloc[idx]
            _render_detail(str(row["sire_code"]), row, selected_year, age_filter)
