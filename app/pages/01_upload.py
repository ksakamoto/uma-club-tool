"""データ準備ページ：DB接続確認 + 募集馬CSV/Excelアップロード + マッチング + 自動採点 + userdata.db保存。"""
import streamlit as st
from datetime import datetime

from app.core.db_reader import DBReader
from app.core.csv_parser import parse_file, missing_optional
from app.core.data_merger import merge
from app.core.userdata_writer import UserDataWriter
from app.core.session_init import ensure_session
from app.scoring.context import ScoringContext
from app.scoring.engine import ScoringEngine
from app.scoring.registry import discover_rules

ensure_session()

st.title("📂 データ準備")

# --- DB接続 ---
st.header("1. JRA-VAN DBの接続確認")

if st.session_state.get("DATA_LOADED_FROM_DB"):
    year  = st.session_state.get("scoring_year", "?")
    count = len(st.session_state.get("scored_df", []))
    st.info(f"💾 {year}年の採点データ（{count}頭）を userdata.db から自動読み込みしました。再アップロードで上書きできます。")
db_path = st.text_input(
    "jravan.db のパス",
    value=st.session_state.get("db_path", "shared/jravan.db"),
    help="Parallels共有フォルダのマウントパスを入力してください",
)
userdata_path = st.text_input(
    "userdata.db のパス",
    value=st.session_state.get("userdata_path", "shared/userdata.db"),
    help="ユーザー評価・出資記録を保存するDBのパス",
)

if st.button("接続テスト"):
    try:
        db = DBReader(db_path)
        db.connect()
        log = db.fetch_log()

        ud = UserDataWriter(userdata_path)
        ud.connect()

        st.session_state["db_path"] = db_path
        st.session_state["db"] = db
        st.session_state["userdata_path"] = userdata_path
        st.session_state["userdata"] = ud

        if log:
            st.success("JRA-VAN DB + userdata.db に接続しました")
            cols = st.columns(len(log))
            for col, (table, info) in zip(cols, log.items()):
                col.metric(
                    table,
                    f"{info.get('record_count', '?'):,}件",
                    info.get("last_fetched_at", "")[:10],
                )
        else:
            st.warning("DB接続成功ですが fetch_log が空です。Windows側でデータ取得を実行してください。")
    except Exception as e:
        st.error(f"接続失敗: {e}")

# --- CSV / Excel アップロード ---
st.header("2. 募集馬データアップロード")
st.markdown("""
**対応形式:** CSV / Excel（.xlsx）

**必須列:** horse_name（馬名）, sex（性別）, birth_date, sire_name（父）, dam_name（母）,
farm_name（生産牧場）, trainer_name（調教師）, price_total（募集総額）, year（募集年）

日本語ヘッダー（父・母・調教師・総額 等）も自動変換対応。Excelは「一覧」シートを読み込みます。
""")

col_year, col_upload = st.columns([1, 3])
with col_year:
    default_year = st.session_state.get("upload_year", datetime.now().year)
    upload_year = st.number_input("募集年度", min_value=2020, max_value=2035, value=default_year, step=1)
    st.session_state["upload_year"] = upload_year

with col_upload:
    uploaded = st.file_uploader("ファイルを選択", type=["csv", "xlsx"])

if uploaded:
    # Excel の生の列名を先に取得（列名マッピングのデバッグ用）
    raw_excel_cols: list[str] | None = None
    if uploaded.name.endswith((".xlsx", ".xls")):
        try:
            import pandas as _pd
            raw_excel_cols = _pd.read_excel(uploaded, sheet_name="一覧", nrows=0).columns.tolist()
        except Exception:
            pass
        uploaded.seek(0)

    df, errors = parse_file(uploaded, fill_year=upload_year)

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    st.success(f"{len(df)}頭のデータを読み込みました")

    # 欠損列の警告（エラーではない）
    from app.core.csv_parser import COLUMN_ALIASES as _ALIASES
    _ALIAS_REVERSE: dict[str, list[str]] = {}
    for jp, en in _ALIASES.items():
        _ALIAS_REVERSE.setdefault(en, []).append(jp)

    missing = missing_optional(df)
    if missing:
        with st.expander(f"⚠️ 以下の列が見つかりません（{len(missing)}件）", expanded=True):
            for m in missing:
                jp_names = "/".join(_ALIAS_REVERSE.get(m, [m]))
                st.write(f"- **{m}** （Excel列名の候補: `{jp_names}`）")
            if raw_excel_cols:
                st.divider()
                st.write("**Excelで実際に見つかった列名:**")
                st.code(", ".join(str(c) for c in raw_excel_cols))

    st.dataframe(df.head(10), use_container_width=True)

    # --- 名前マッチング ---
    st.header("3. 名前マッチング確認")
    if "db" not in st.session_state:
        st.warning("先にDB接続を完了してください")
        st.stop()

    with st.spinner("JRA-VANデータと照合中..."):
        merged_df, report_df = merge(df, st.session_state["db"])

    match_ok = report_df[report_df["matched"].notna() & (report_df["matched"] != report_df["original"])]
    no_match = report_df[report_df["matched"].isna()]

    c1, c2, c3 = st.columns(3)
    c1.metric("総頭数", f"{len(df)}頭")
    c2.metric("補正マッチ", f"{len(match_ok)}件", "表記揺れを修正")
    c3.metric("未マッチ", f"{len(no_match)}件", delta_color="inverse")

    if not match_ok.empty:
        with st.expander("補正マッチの詳細（確認してください）"):
            st.dataframe(match_ok[["field", "original", "matched", "score"]], use_container_width=True)

    if not no_match.empty:
        with st.expander("⚠️ 未マッチ（DBにデータなし）"):
            st.dataframe(no_match[["field", "original", "score"]], use_container_width=True)

    st.session_state["df_horses"] = merged_df
    st.session_state["match_report"] = report_df

    # --- 自動採点（全ルール・等重み） ---
    st.header("4. 自動採点")
    with st.spinner("全観点でスコアリング中..."):
        all_rules = discover_rules()
        equal_weights = {cls.name: 1.0 for cls in all_rules}
        context = ScoringContext(st.session_state["db"], years=3)
        engine = ScoringEngine(weights=equal_weights, context=context)
        horses = merged_df.to_dict(orient="records")
        scored_df = engine.score_all(horses)

    st.session_state["scored_df"] = scored_df
    st.session_state["scoring_weights"] = equal_weights
    st.session_state["scoring_year"] = upload_year

    score_cols = [c for c in scored_df.columns if c.startswith("score_")]
    mj_grade_cols = [c for c in scored_df.columns if c.startswith("grade_mj_")]
    display_cols = (
        ["recruit_no", "horse_name", "total_score"]
        + mj_grade_cols
        + score_cols
        + ["sire_name", "trainer_name", "farm_name", "price_total"]
    )
    display_cols = [c for c in display_cols if c in scored_df.columns]

    st.success(f"採点完了！{len(scored_df)}頭を全観点で評価しました")
    st.dataframe(
        scored_df[display_cols].rename(columns={"total_score": "総合点（等重み）"}),
        use_container_width=True,
    )

    # --- userdata.db へ保存 ---
    st.header("5. userdata.db へ保存")
    if "userdata" not in st.session_state:
        st.warning("userdata.db に接続されていません。接続テストを先に実行してください。")
    else:
        if st.button(f"💾 {upload_year}年分の採点結果を保存", type="primary"):
            ud: UserDataWriter = st.session_state["userdata"]
            count = ud.upsert_horses_bulk(upload_year, scored_df)
            st.session_state.pop("DATA_LOADED_FROM_DB", None)
            st.success(f"{count}頭を userdata.db（{upload_year}年）に保存しました。候補一覧ページで評価を入力できます。")

    st.info("👉 **候補一覧**ページでカード表示・主観評価入力ができます。重みを変えたい場合は**スコアリング設定**ページへ。")
