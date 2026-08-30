"""セッション初期化 — userdata.db から最新年度データを自動ロードする。"""
from __future__ import annotations
import streamlit as st
import pandas as pd

from app.core.db_reader import DBReader
from app.core.userdata_writer import UserDataWriter

_DEFAULT_DB_PATH       = "shared/jravan.db"
_DEFAULT_USERDATA_PATH = "shared/userdata.db"

# DB列名 → scored_df列名 のリネームマップ
_DB_TO_DF_RENAME = {
    "body_weight":        "weight_kg",
    "body_weight_latest": "weight_kg_latest",
    "height":             "height_cm",
    "chest_girth":        "chest_cm",
    "cannon_bone":        "cannon_cm",
    "mj_body":            "grade_mj_body",
    "mj_dam":             "grade_mj_dam",
    "mj_trainer":         "grade_mj_trainer",
    "score_total":        "total_score",
}


def ensure_session() -> None:
    """各ページ冒頭で呼ぶ冪等な初期化。

    - DB接続が未設定なら接続を試みる
    - scored_df が session state になければ userdata.db の最新年度データを自動ロードする
    """
    _ensure_connections()
    _maybe_load_scored_df()


def _ensure_connections() -> None:
    if "db" not in st.session_state:
        db_path = st.session_state.get("db_path", _DEFAULT_DB_PATH)
        try:
            db = DBReader(db_path)
            db.connect()
            st.session_state["db_path"] = db_path
            st.session_state["db"] = db
        except Exception:
            pass  # jravan.db は pages 02-04 では必須ではない

    if "userdata" not in st.session_state:
        userdata_path = st.session_state.get("userdata_path", _DEFAULT_USERDATA_PATH)
        try:
            ud = UserDataWriter(userdata_path)
            ud.connect()
            st.session_state["userdata_path"] = userdata_path
            st.session_state["userdata"] = ud
        except Exception:
            pass  # DB が存在しない場合はサイレントに失敗


def _maybe_load_scored_df() -> None:
    if "scored_df" in st.session_state:
        return  # アップロード済みデータを上書きしない

    ud: UserDataWriter | None = st.session_state.get("userdata")
    if ud is None:
        return

    try:
        years = ud.get_all_years()
    except Exception:
        return

    if not years:
        return

    latest_year = max(years)
    try:
        raw_df = ud.get_horses_by_year(latest_year)
    except Exception:
        return

    if raw_df.empty:
        return

    df = raw_df.rename(columns=_DB_TO_DF_RENAME)

    if "stable" not in df.columns:
        df["stable"] = ""

    # 直近体重スコアのデータ有無フラグは weight_kg_latest の有無から正確に再現
    if "weight_kg_latest" in df.columns:
        df["avail_physical_latest"] = df["weight_kg_latest"].notna()

    # score_* 列ごとに avail_* を補完（DB には保存されていない）
    for col in [c for c in df.columns if c.startswith("score_")]:
        rule = col[len("score_"):]
        avail_col = f"avail_{rule}"
        if avail_col not in df.columns:
            df[avail_col] = True

    st.session_state["scored_df"]           = df
    st.session_state["scoring_year"]        = latest_year
    st.session_state["upload_year"]         = latest_year
    st.session_state["scoring_weights"]     = {
        col[len("score_"):]: 1.0
        for col in df.columns if col.startswith("score_")
    }
    st.session_state["DATA_LOADED_FROM_DB"] = True
