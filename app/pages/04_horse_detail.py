"""馬詳細ページ：血統・スコアレーダーチャート・機械的判断詳細・兄弟馬一覧・評価入力。"""
import urllib.parse

import streamlit as st
import pandas as pd

from app.components.score_radar import render_score_radar
from app.core.session_init import ensure_session
from app.core.userdata_writer import UserDataWriter
from app.scoring.context import ScoringContext
from app.scoring.rules.mj_body import MJBodyRule
from app.scoring.rules.mj_dam import MJDamRule
from app.scoring.rules.mj_trainer import MJTrainerRule

EVAL_VIDEO_OPTIONS   = ["", "◎", "◯", "▲", "△", "×"]
EVAL_OVERALL_OPTIONS = ["", "◎", "◯", "×", "★"]
MJ_GRADE_EMOJI = {"◎": "🟢", "◯": "🔵", "▲": "🟡", "△": "🟠", "×": "🔴", "★": "⭐", "判定不可": "⚪"}

ensure_session()

st.title("🔍 馬詳細")

if "scored_df" not in st.session_state:
    st.warning("先にスコアリング設定ページでスコアを計算してください")
    st.stop()

df: pd.DataFrame = st.session_state["scored_df"]
year: int = st.session_state.get("scoring_year", 0)
horse_names = df["horse_name"].tolist()

# 03_candidates.py の → リンクから来た場合、URL query params で馬名を受け取る
_query_horse = st.query_params.get("horse")
if _query_horse:
    st.session_state["detail_horse"] = urllib.parse.unquote(_query_horse)
    st.query_params.clear()

_preset = st.session_state.pop("detail_horse", None)
_default_idx = horse_names.index(_preset) if _preset in horse_names else 0
selected = st.selectbox("馬を選択", horse_names, index=_default_idx)
row = df[df["horse_name"] == selected].iloc[0]

# --- 基本情報 ---
col1, col2, col3 = st.columns(3)
col1.metric("総合スコア", f"{row['total_score']:.1f}")
col2.metric("募集総額", f"{int(row['price_total']):,}万円" if pd.notna(row.get("price_total")) else "-")
col3.metric("性別", row.get("sex", "-"))

st.markdown(f"""
| 項目 | 内容 |
|---|---|
| 父 | {row.get('sire_name', '-')} |
| 調教師 | {row.get('trainer_name', '-')} |
| 牧場 | {row.get('farm_name', '-')} |
| 所属 | {row.get('stable', '-')} |
""")

# --- 機械的判断（タブで内訳表示）---
st.subheader("機械的判断")

# 対象馬のフルデータを構築（df_horsesがあれば matched 名を優先）
horse_dict = row.to_dict()
if "df_horses" in st.session_state:
    dh = st.session_state["df_horses"]
    dh_row = dh[dh["horse_name"] == selected]
    if not dh_row.empty:
        horse_dict = {**horse_dict, **dh_row.iloc[0].to_dict()}

# ScoringContext を取得（DB接続がある場合のみ）
_context: ScoringContext | None = None
if "db" in st.session_state:
    if "scoring_context" not in st.session_state:
        st.session_state["scoring_context"] = ScoringContext(st.session_state["db"])
    _context = st.session_state["scoring_context"]

# MJルールを再実行して details を取得
_mj_results = {}
if _context is not None:
    for rule_cls in [MJBodyRule, MJDamRule, MJTrainerRule]:
        try:
            _mj_results[rule_cls.name] = rule_cls().score(horse_dict, _context)
        except Exception:
            pass

# グレードサマリー行
mj_labels = {"mj_body": "馬体", "mj_dam": "母馬", "mj_trainer": "調教師"}
mcols = st.columns(3)
for i, (rule_name, label) in enumerate(mj_labels.items()):
    grade = row.get(f"grade_{rule_name}", "")
    emoji = MJ_GRADE_EMOJI.get(grade, "")
    mcols[i].metric(label, f"{emoji} {grade}" if grade else "-")

# 判断内訳タブ
tab_body, tab_dam, tab_trainer = st.tabs(["馬体 内訳", "母馬 内訳", "調教師 内訳"])

with tab_body:
    result = _mj_results.get("mj_body")
    if result is None:
        st.caption("DBに接続されていないため内訳を表示できません")
    elif not result.data_available:
        st.info(result.details.get("note", "測尺データなし"))
    else:
        checks = result.details.get("checks", [])
        if checks:
            st.markdown("各測尺指標が基準範囲内かを判定します")
            for c in checks:
                icon = "✅" if c["ok"] else "❌"
                st.markdown(f"{icon} {c['label']}")
        else:
            st.caption(result.details.get("note", ""))

with tab_dam:
    result = _mj_results.get("mj_dam")
    if result is None:
        st.caption("DBに接続されていないため内訳を表示できません")
    elif not result.data_available:
        st.info(result.details.get("note", "母馬データなし"))
    else:
        d = result.details
        dam_age = d.get("dam_age")
        sibling_count = d.get("sibling_count", 0)

        m1, m2 = st.columns(2)
        m1.metric("母馬の出産時年齢", f"{dam_age}歳" if dam_age is not None else "-")
        m2.metric("産駒（兄弟姉妹）数", f"{sibling_count}頭")

        st.markdown("**産駒の競走成績**")
        perf_rows = [
            {"指標": "重賞勝ち産駒あり",    "結果": "✅" if d.get("has_graded_win") else "—"},
            {"指標": "重賞2着以上産駒あり",  "結果": "✅" if d.get("has_graded_placed") else "—"},
            {"指標": "オープン勝ち産駒あり", "結果": "✅" if d.get("has_open_win") else "—"},
        ]
        st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)

        st.markdown(f"**判定理由:** {d.get('note', '')}")

with tab_trainer:
    result = _mj_results.get("mj_trainer")
    if result is None:
        st.caption("DBに接続されていないため内訳を表示できません")
    elif not result.data_available:
        st.info(result.details.get("note", "調教師データなし"))
    else:
        d = result.details
        career_years = d.get("career_years")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("開業年数",           f"{career_years}年" if career_years is not None else "-")
        m2.metric("直近3年 top10回数",  f"{d.get('top10_3y', 0)}回")
        m3.metric("5年平均勝利数",      f"{d.get('avg_wins', 0):.1f}勝")
        m4.metric("重賞勝利数(2024+)",  f"{d.get('graded_wins', 0)}勝")

        st.markdown(f"**判定理由:** {d.get('note', '')}")

# --- スコアレーダーチャート ---
score_cols = {c.replace("score_", ""): row[c] for c in df.columns if c.startswith("score_")}
if score_cols:
    st.subheader("スコア内訳")
    render_score_radar(score_cols, selected)

# --- 各ルール詳細 ---
st.subheader("観点別スコア")
score_data = []
for col, val in score_cols.items():
    avail = row.get(f"avail_{col}", True)
    grade = row.get(f"grade_{col}", "")
    score_data.append({
        "観点": col,
        "スコア": round(val, 1),
        "判定": grade,
        "データあり": "✅" if avail else "⚠️ データなし",
    })
st.dataframe(pd.DataFrame(score_data), use_container_width=True)

# --- 評価・出資記録入力 ---
ud: UserDataWriter | None = st.session_state.get("userdata")
if ud and year:
    st.subheader("主観評価・出資記録")
    saved_df = ud.get_horses_by_year(year)
    saved_row = {}
    if not saved_df.empty:
        match = saved_df[saved_df["horse_name"] == selected]
        if not match.empty:
            saved_row = match.iloc[0].to_dict()

    ev_col1, ev_col2 = st.columns(2)
    with ev_col1:
        ev_video = st.selectbox(
            "動画/現場評価",
            EVAL_VIDEO_OPTIONS,
            index=EVAL_VIDEO_OPTIONS.index(saved_row.get("eval_video") or ""),
        )
        ev_overall = st.selectbox(
            "総合評価（◎=出資候補 ◯=検討 ×=見送り ★=悩み中）",
            EVAL_OVERALL_OPTIONS,
            index=EVAL_OVERALL_OPTIONS.index(saved_row.get("eval_overall") or ""),
        )
    with ev_col2:
        applied = st.checkbox("申込した", value=bool(saved_row.get("applied", 0)))
        won = st.checkbox("当選・確定した", value=bool(saved_row.get("won", 0)))
        notes = st.text_area("メモ", value=saved_row.get("notes") or "", height=80)

    if st.button("💾 保存", type="primary"):
        ud.update_eval(year, selected, {
            "eval_video": ev_video,
            "eval_overall": ev_overall,
            "applied": int(applied),
            "won": int(won),
            "notes": notes,
        })
        st.success("保存しました")

# --- 兄弟馬 ---
if "db" in st.session_state:
    dam_name = ""
    if "df_horses" in st.session_state:
        matched = st.session_state["df_horses"]
        dam_col = "dam_name_matched" if "dam_name_matched" in matched.columns else "dam_name"
        horse_row = matched[matched["horse_name"] == selected]
        if not horse_row.empty:
            dam_name = str(horse_row.iloc[0].get(dam_col, ""))

    if dam_name:
        siblings = st.session_state["db"].get_siblings(dam_name)
        st.subheader(f"兄弟馬（母: {dam_name}）")
        if siblings.empty:
            st.info("兄弟馬のデータがありません（初仔 or データ未取得）")
        else:
            st.dataframe(siblings, use_container_width=True)
