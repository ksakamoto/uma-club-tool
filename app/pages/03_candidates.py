"""候補馬一覧ページ：テーブル表示・フィルタ・詳細ページ導線・主観評価インライン入力・CSVエクスポート。"""
import urllib.parse

import streamlit as st
import pandas as pd

from app.core.session_init import ensure_session
from app.core.userdata_writer import UserDataWriter

EVAL_VIDEO_OPTIONS   = ["", "◎", "◯", "▲", "△", "×"]
EVAL_OVERALL_OPTIONS = ["", "◎", "◯", "×", "★"]
MJ_OPTIONS           = ["◎", "◯", "▲", "△", "×"]

EVAL_COLS = ["eval_video", "eval_overall", "applied", "won", "notes"]

COLUMN_ORDER = [
    "detail_url",
    "recruit_no", "horse_name",
    "sex", "sire_name", "broodmare_sire_name",
    "stable", "trainer_name", "price_total",
    "birth_date",
    "weight_kg", "weight_kg_latest", "weight_diff",
    "height_cm", "chest_cm", "cannon_cm",
    "total_score",
    "grade_mj_body", "grade_mj_dam", "grade_mj_trainer",
    "score_sire", "score_trainer", "score_farm",
    "score_siblings", "score_physical", "score_physical_latest",
    "eval_video", "eval_overall", "applied", "won",
    "notes",
]


def _eval_snapshot(df: pd.DataFrame, cols: list[str]) -> dict[str, dict]:
    def _norm(v):
        return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
    return {
        row["horse_name"]: {c: _norm(row[c]) for c in cols if c in df.columns}
        for _, row in df.iterrows()
    }


ensure_session()

st.title("🏆 候補馬一覧")

if "scored_df" not in st.session_state:
    st.warning("先にスコアリング設定ページでスコアを計算してください")
    st.stop()

df: pd.DataFrame = st.session_state["scored_df"].copy()
year: int = st.session_state.get("scoring_year", 0)

# eval列がない場合（アップロード直後）は userdata.db から補完
_ud = st.session_state.get("userdata")
if _ud and year and any(c not in df.columns for c in EVAL_COLS):
    try:
        _saved = _ud.get_horses_by_year(year)
        if not _saved.empty:
            _eval_df = _saved.set_index("horse_name")[
                [c for c in EVAL_COLS if c in _saved.columns]
            ]
            for col in EVAL_COLS:
                if col not in df.columns:
                    df[col] = df["horse_name"].map(_eval_df[col]) if col in _eval_df.columns else None
    except Exception:
        for col in EVAL_COLS:
            if col not in df.columns:
                df[col] = None

# --- フィルタ（ページ上部に統合） ---
sex_options     = ["全て"] + sorted(df["sex"].dropna().unique().tolist())
stable_options  = ["全て"] + sorted(df["stable"].dropna().unique().tolist()) if "stable" in df.columns else ["全て"]
sire_options    = ["全て"] + sorted(df["sire_name"].dropna().unique().tolist()) if "sire_name" in df.columns else ["全て"]
bms_options     = ["全て"] + sorted(df["broodmare_sire_name"].dropna().unique().tolist()) if "broodmare_sire_name" in df.columns else ["全て"]
trainer_options = ["全て"] + sorted(df["trainer_name"].dropna().unique().tolist()) if "trainer_name" in df.columns else ["全て"]

# 行1: 基本情報
fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([3, 1, 1, 2, 2, 2])
with fc1:
    name_query = st.text_input("馬名/父名で検索", placeholder="検索ワードを入力")
with fc2:
    selected_sex = st.selectbox("性別", sex_options)
with fc3:
    selected_stable = st.selectbox("所属", stable_options)
with fc4:
    selected_sire = st.selectbox("父名", sire_options)
with fc5:
    selected_bms = st.selectbox("母父名", bms_options)
with fc6:
    selected_trainer = st.selectbox("調教師名", trainer_options)

# 行2: 評価フィルタ
fc1, fc2, fc3, fc4, fc5 = st.columns(5)
with fc1:
    eval_video_filter = st.multiselect("動画/現場", options=EVAL_VIDEO_OPTIONS[1:], default=[], help="未選択=全て")
with fc2:
    eval_overall_filter = st.multiselect("総合評価", options=EVAL_OVERALL_OPTIONS[1:], default=[], help="未選択=全て")
with fc3:
    mj_body_filter = st.multiselect("馬体判定", options=MJ_OPTIONS, default=[], help="未選択=全て")
with fc4:
    mj_dam_filter = st.multiselect("母馬判定", options=MJ_OPTIONS, default=[], help="未選択=全て")
with fc5:
    mj_trainer_filter = st.multiselect("調教師判定", options=MJ_OPTIONS, default=[], help="未選択=全て")

# 行3: スコア・ソート
fc1, fc2, fc3 = st.columns([2, 3, 2])
with fc1:
    price_max = st.number_input("最大募集額（万円）", min_value=0, value=0, step=500)
with fc2:
    score_min = st.slider("最低スコア", 0, 100, 0)
with fc3:
    sort_col = st.selectbox(
        "初期ソート",
        options=["recruit_no", "total_score"] + [sc for sc in df.columns if sc.startswith("score_")],
        format_func=lambda sc: {"recruit_no": "募集番号"}.get(sc, sc.replace("score_", "").replace("total_score", "総合")),
    )

# --- フィルタ適用 ---
if name_query:
    mask = (
        df["horse_name"].str.contains(name_query, na=False)
        | df["sire_name"].str.contains(name_query, na=False)
    )
    df = df[mask]
if selected_sex != "全て":
    df = df[df["sex"] == selected_sex]
if selected_stable != "全て" and "stable" in df.columns:
    df = df[df["stable"] == selected_stable]
if selected_sire != "全て" and "sire_name" in df.columns:
    df = df[df["sire_name"] == selected_sire]
if selected_bms != "全て" and "broodmare_sire_name" in df.columns:
    df = df[df["broodmare_sire_name"] == selected_bms]
if selected_trainer != "全て" and "trainer_name" in df.columns:
    df = df[df["trainer_name"] == selected_trainer]
if price_max > 0:
    df = df[df["price_total"].isna() | (df["price_total"] <= price_max)]
df = df[df["total_score"] >= score_min]
if eval_video_filter and "eval_video" in df.columns:
    df = df[df["eval_video"].isin(eval_video_filter)]
if eval_overall_filter and "eval_overall" in df.columns:
    df = df[df["eval_overall"].isin(eval_overall_filter)]
if mj_body_filter and "grade_mj_body" in df.columns:
    df = df[df["grade_mj_body"].isin(mj_body_filter)]
if mj_dam_filter and "grade_mj_dam" in df.columns:
    df = df[df["grade_mj_dam"].isin(mj_dam_filter)]
if mj_trainer_filter and "grade_mj_trainer" in df.columns:
    df = df[df["grade_mj_trainer"].isin(mj_trainer_filter)]
df = df.sort_values(sort_col, ascending=(sort_col == "recruit_no")).reset_index(drop=True)

if "weight_kg_latest" in df.columns and "weight_kg" in df.columns:
    df["weight_diff"] = (df["weight_kg_latest"] - df["weight_kg"]).where(
        df["weight_kg_latest"].notna() & df["weight_kg"].notna()
    )
else:
    df["weight_diff"] = None

for _bc in ("applied", "won"):
    if _bc in df.columns:
        df[_bc] = df[_bc].fillna(0).astype(bool)

for col in EVAL_COLS:
    if col not in df.columns:
        df[col] = None

# セッション中に保存した評価値をオーバーレイ
# フィルタは scored_df の元値で動かし、表示だけ最新の保存値を使う。
# これにより「評価フィルタ中に評価を編集しても行が消えない」を実現する。
_BASELINE_KEY = f"candidates_eval_baseline_{year}"
_baseline_overlay: dict = st.session_state.get(_BASELINE_KEY, {})
if _baseline_overlay:
    for idx, row in df.iterrows():
        name = row["horse_name"]
        if name in _baseline_overlay:
            for col, val in _baseline_overlay[name].items():
                if col in df.columns:
                    df.at[idx, col] = val

col_count, col_export = st.columns([4, 1])
col_count.caption(f"{len(df)}頭表示中（{year}年）← 「→」で詳細ページへ、評価・フラグを直接編集して自動保存")
with col_export:
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 CSV", csv, "candidates.csv", "text/csv")

# --- インライン編集テーブル ---
display_df = df.copy()
display_df["detail_url"] = display_df["horse_name"].apply(
    lambda n: f"horse_detail?horse={urllib.parse.quote(str(n))}"
)

visible_cols = [c for c in COLUMN_ORDER if c in display_df.columns]
display_df = display_df[visible_cols].reset_index(drop=True)

col_config = {
    "detail_url":            st.column_config.LinkColumn("", display_text="→", width="small", pinned=True),
    "recruit_no":            st.column_config.NumberColumn("No.", format="%d", width="small", pinned=True),
    "horse_name":            st.column_config.TextColumn("馬名", width=150, pinned=True),
    "sex":                   st.column_config.TextColumn("性", width="small"),
    "sire_name":             st.column_config.TextColumn("父名", width=120),
    "broodmare_sire_name":   st.column_config.TextColumn("母父名", width=120),
    "stable":                st.column_config.TextColumn("所属", width=100),
    "trainer_name":          st.column_config.TextColumn("調教師名", width=120),
    "birth_date":            st.column_config.TextColumn("誕生日", width=100),
    "weight_kg":             st.column_config.NumberColumn("馬体重kg", format="%.1f"),
    "weight_kg_latest":      st.column_config.NumberColumn("直近体重kg", format="%.1f"),
    "weight_diff":           st.column_config.NumberColumn("増減kg", format="%+.1f"),
    "height_cm":             st.column_config.NumberColumn("高さcm", format="%.1f"),
    "chest_cm":              st.column_config.NumberColumn("胸囲cm", format="%.1f"),
    "cannon_cm":             st.column_config.NumberColumn("管周cm", format="%.1f"),
    "total_score":           st.column_config.ProgressColumn("総合スコア", min_value=0, max_value=100, format="%.1f"),
    "grade_mj_body":         st.column_config.TextColumn("馬体判定", width="small"),
    "grade_mj_dam":          st.column_config.TextColumn("母馬判定", width="small"),
    "grade_mj_trainer":      st.column_config.TextColumn("調教師判定", width="small"),
    "score_sire":            st.column_config.NumberColumn("父S", format="%.1f"),
    "score_trainer":         st.column_config.NumberColumn("調教師S", format="%.1f"),
    "score_farm":            st.column_config.NumberColumn("牧場S", format="%.1f"),
    "score_siblings":        st.column_config.NumberColumn("兄弟S", format="%.1f"),
    "score_physical":        st.column_config.NumberColumn("測尺S", format="%.1f"),
    "score_physical_latest": st.column_config.NumberColumn("直近体重S", format="%.1f"),
    "price_total":           st.column_config.NumberColumn("募集額(万)", format="%d"),
    "eval_video":            st.column_config.SelectboxColumn(
        "動画/現場", options=EVAL_VIDEO_OPTIONS, width="small"),
    "eval_overall":          st.column_config.SelectboxColumn(
        "総合評価", options=EVAL_OVERALL_OPTIONS, width="small",
        help="◎=出資候補 ◯=検討 ×=見送り ★=悩み中"),
    "applied":               st.column_config.CheckboxColumn("申込", width="small"),
    "won":                   st.column_config.CheckboxColumn("当選", width="small"),
    "notes":                 st.column_config.TextColumn("メモ", width=200),
}

_non_edit_cols = [c for c in visible_cols if c not in EVAL_COLS]

_before: dict | None = st.session_state.get(_BASELINE_KEY)

edited = st.data_editor(
    display_df,
    column_config=col_config,
    disabled=_non_edit_cols,
    use_container_width=True,
    hide_index=True,
    height=620,
    key="candidates_editor",
)

ud: UserDataWriter | None = st.session_state.get("userdata")
if ud and year:
    _eval_cols_present = [c for c in EVAL_COLS if c in edited.columns]
    _after = _eval_snapshot(edited, _eval_cols_present)

    if _before is None:
        st.session_state[_BASELINE_KEY] = _after
    else:
        changed = {name: vals for name, vals in _after.items() if _before.get(name) != vals}
        if changed:
            _change_df = pd.DataFrame([{"horse_name": k, **v} for k, v in changed.items()])
            ud.update_evals_bulk(year, _change_df)
            # scored_df は更新しない: フィルタを scored_df の元値で動かし続けることで
            # 「評価フィルタ中に編集しても行が消えない」を維持する。
            st.toast("保存しました ✓")

        new_baseline = {**_before}
        new_baseline.update(_after)
        st.session_state[_BASELINE_KEY] = new_baseline
