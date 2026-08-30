"""振り返り分析ページ：評価スコア × 実成績 × 出資判断の3軸で評価精度を可視化。"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.core.userdata_writer import UserDataWriter
from app.core.db_reader import DBReader

EVAL_ORDER   = ["◎", "◯", "★", "×", ""]
EVAL_COLORS  = {"◎": "#2ecc71", "◯": "#3498db", "★": "#f39c12", "×": "#e74c3c", "": "#95a5a6"}
PRIZE_BREAKS = [0, 500, 2000, 5000]  # 万円: 低/中/高

st.title("📈 振り返り分析")

ud: UserDataWriter | None = st.session_state.get("userdata")
db: DBReader | None = st.session_state.get("db")

if not ud or not ud.is_connected():
    st.warning("データ準備ページで接続テストを先に実行してください。")
    st.stop()

all_years = ud.get_all_years()
if not all_years:
    st.info("過去データ管理ページからデータをインポートすると振り返りができます。")
    st.stop()

# --- フィルタ ---
with st.sidebar:
    st.header("フィルタ")
    sel_years = st.multiselect("年度", all_years, default=all_years)
    eval_filter = st.multiselect("総合評価", ["◎", "◯", "×", "★"], default=["◎", "◯", "×", "★"])
    applied_only = st.checkbox("申込した馬のみ", value=False)

# --- データ取得 ---
all_df = ud.get_all_horses()
if sel_years:
    all_df = all_df[all_df["year"].isin(sel_years)]
if eval_filter:
    all_df = all_df[all_df["eval_overall"].isin(eval_filter)]
if applied_only:
    all_df = all_df[all_df["applied"] == 1]

if all_df.empty:
    st.info("該当するデータがありません。フィルタを調整してください。")
    st.stop()

# JRA-VAN 成績と結合
if db and db.is_connected():
    recruitment_names = all_df["horse_name"].tolist()
    with st.spinner("JRA-VANから成績を照合中..."):
        resolved_df = db.resolve_recruitment_names(recruitment_names)
        official_names = resolved_df["official_name"].tolist()
        perf_df = db.get_performance_summary(official_names)

    if not perf_df.empty:
        perf_df = perf_df.merge(
            resolved_df.rename(columns={"official_name": "horse_name"}),
            on="horse_name", how="left",
        )
        perf_df["horse_name"] = perf_df["recruitment_name"].fillna(perf_df["horse_name"])
        perf_df = perf_df.drop(columns=["recruitment_name", "resolved"], errors="ignore")
        df = all_df.merge(perf_df, on="horse_name", how="left")
    else:
        df = all_df.copy()
else:
    df = all_df.copy()
    st.warning("JRA-VAN DBに接続されていないため成績を取得できません（userdata.db の情報のみ表示）。")

for col in ["total_runs", "wins", "total_prize", "graded_wins"]:
    if col not in df.columns:
        df[col] = 0
df["total_prize"] = df["total_prize"].fillna(0)
df["total_runs"] = df["total_runs"].fillna(0)
df["wins"] = df["wins"].fillna(0)
df["graded_wins"] = df["graded_wins"].fillna(0)
df["score_total"] = df["score_total"].fillna(0)
df["applied_label"] = df["applied"].map({1: "申込", 0: "見送り"}).fillna("見送り")
df["eval_overall"] = df["eval_overall"].fillna("")

# ============================================================
# 1. KPIメトリクス
# ============================================================
st.subheader("サマリー")
total = len(df)
applied_count = int((df["applied"] == 1).sum())
won_count = int((df["won"] == 1).sum())
active = int((df["total_runs"] > 0).sum())
graded = int((df["graded_wins"] > 0).sum())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("対象馬数", total)
m2.metric("申込", applied_count)
m3.metric("当選", won_count)
m4.metric("出走済", active)
m5.metric("重賞勝利馬", graded)

st.divider()

# ============================================================
# 2. 散布図: 評価スコア × 獲得賞金
# ============================================================
st.subheader("評価スコア vs 実績（獲得賞金）")

fig = px.scatter(
    df,
    x="score_total",
    y="total_prize",
    color="eval_overall",
    symbol="applied_label",
    hover_name="horse_name",
    hover_data={"year": True, "trainer_name": True, "wins": True, "graded_wins": True,
                "score_total": ":.1f", "total_prize": ":.0f",
                "eval_overall": False, "applied_label": False},
    color_discrete_map=EVAL_COLORS,
    labels={
        "score_total": "採点時スコア（JRA-VAN）",
        "total_prize": "獲得賞金合計（万円）",
        "eval_overall": "総合評価",
        "applied_label": "申込",
        "year": "年度",
        "trainer_name": "調教師",
    },
    category_orders={"eval_overall": EVAL_ORDER},
    height=500,
)
fig.update_layout(legend_title_text="評価 / 申込")
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 3. 評価マトリクス
# ============================================================
st.subheader("評価マトリクス（評価 × 実績レベル）")

def prize_level(p: float) -> str:
    if p >= PRIZE_BREAKS[3]:
        return "高成績（5000万+）"
    elif p >= PRIZE_BREAKS[2]:
        return "中成績（2000-5000万）"
    elif p >= PRIZE_BREAKS[1]:
        return "低成績（500-2000万）"
    elif p > 0:
        return "未勝利圏（1-500万）"
    return "出走なし/0円"

df["prize_level"] = df["total_prize"].apply(prize_level)
prize_order = ["高成績（5000万+）", "中成績（2000-5000万）", "低成績（500-2000万）", "未勝利圏（1-500万）", "出走なし/0円"]

matrix = (
    df.groupby(["eval_overall", "prize_level"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=[e for e in EVAL_ORDER if e in df["eval_overall"].unique()])
)
for col in prize_order:
    if col not in matrix.columns:
        matrix[col] = 0
matrix = matrix[prize_order]
matrix.index.name = "総合評価"

def _yl_or_rd(df_m: pd.DataFrame):
    vmin = float(df_m.values.min())
    vmax = float(df_m.values.max())

    def _cell(val):
        ratio = 0.0 if vmax == vmin else (float(val) - vmin) / (vmax - vmin)
        if ratio < 0.5:
            r1, g1, b1 = 255, 255, 204
            r2, g2, b2 = 253, 141,  60
            t = ratio * 2
        else:
            r1, g1, b1 = 253, 141,  60
            r2, g2, b2 = 215,  25,  28
            t = (ratio - 0.5) * 2
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        text = "black" if ratio < 0.65 else "white"
        return f"background-color: rgb({r},{g},{b}); color: {text}"

    return df_m.style.map(_cell)

st.dataframe(_yl_or_rd(matrix), use_container_width=True)

# ============================================================
# 4. 「惜しかった馬」一覧
# ============================================================
st.subheader("惜しかった馬（高評価 or 申込したのに成績良好）")

regret_df = df[
    ((df["eval_overall"].isin(["◎", "◯"])) & (df["applied"] == 0) & (df["total_prize"] >= 2000)) |
    ((df["applied"] == 1) & (df["won"] == 0) & (df["total_prize"] >= 2000))
].copy()

if regret_df.empty:
    st.info("該当馬なし（活躍データが蓄積されると表示されます）")
else:
    regret_df["理由"] = regret_df.apply(
        lambda r: "高評価で見送り" if r["applied"] == 0 else "申込落選", axis=1
    )
    cols = ["horse_name", "year", "eval_overall", "理由", "total_runs", "wins", "total_prize", "graded_wins"]
    cols = [c for c in cols if c in regret_df.columns]
    st.dataframe(
        regret_df[cols].sort_values("total_prize", ascending=False).rename(columns={
            "horse_name": "馬名", "year": "年度", "eval_overall": "総合評価",
            "total_runs": "出走", "wins": "勝利", "total_prize": "賞金(万)", "graded_wins": "重賞勝",
        }),
        use_container_width=True,
    )

# ============================================================
# 5. 全データ表
# ============================================================
with st.expander("全データ一覧"):
    show_cols = [
        "year", "horse_name", "trainer_name", "eval_overall", "eval_video",
        "applied", "won", "score_total",
        "total_runs", "wins", "total_prize", "graded_wins",
    ]
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(
        df[show_cols].sort_values(["year", "total_prize"], ascending=[False, False])
        .rename(columns={
            "year": "年度", "horse_name": "馬名", "trainer_name": "調教師",
            "eval_overall": "総合評価", "eval_video": "動画評価",
            "applied": "申込", "won": "当選", "score_total": "採点スコア",
            "total_runs": "出走", "wins": "勝利", "total_prize": "賞金(万)", "graded_wins": "重賞勝",
        }),
        use_container_width=True,
    )
