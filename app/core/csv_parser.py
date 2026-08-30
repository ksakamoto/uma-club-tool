"""募集馬CSV/Excelの解析・バリデーション。"""
from __future__ import annotations
import pandas as pd
import io

# 必須列: これがないと採点も表示もできない
REQUIRED_COLUMNS = [
    "horse_name", "trainer_name", "price_total",
]

# 任意列: なくてもOK（該当ルールのスコアが「データなし」になるだけ）
OPTIONAL_COLUMNS = [
    "sex", "birth_date", "sire_name", "dam_name", "farm_name", "year",
    "weight_kg", "height_cm", "chest_cm", "cannon_cm",
]

# 警告を出す任意列（クラブ側のExcelフォーマットにあるはずなのに見つからない列）
EXPECTED_OPTIONAL_COLUMNS = [
    "sex", "birth_date", "sire_name", "dam_name", "broodmare_sire_name", "farm_name",
    "weight_kg", "height_cm", "chest_cm", "cannon_cm",
]

# 日本語ヘッダー → 内部キーのマッピング
COLUMN_ALIASES: dict[str, str] = {
    "No.":            "recruit_no",
    "No":             "recruit_no",
    "番号":           "recruit_no",
    "馬名":           "horse_name",
    "募集馬名":       "horse_name",
    "性別":           "sex",
    "生年月日":       "birth_date",
    "誕生日":         "birth_date",
    "父":             "sire_name",
    "父(母の父)":     "sire_name",
    "母":             "dam_name",
    "母父":           "broodmare_sire_name",
    "母の父":         "broodmare_sire_name",
    "母父名":         "broodmare_sire_name",
    "BMS":            "broodmare_sire_name",
    "生産牧場":       "farm_name",
    "生産者":         "farm_name",
    "調教師":         "trainer_name",
    "予定厩舎":       "trainer_name",
    "所属":           "stable",
    "募集総額":       "price_total",
    "総額":           "price_total",
    "1口価格":        "price_per_lot",
    "一口金額":       "price_per_lot",
    "口数":           "lot_count",
    "馬体重":             "weight_kg_base",
    "馬体重(kg)":         "weight_kg_base",
    "直近馬体重":         "weight_kg_latest",
    "直近馬体重(kg)":     "weight_kg_latest",
    "8月中旬馬体重":      "weight_kg_latest",
    "体高":           "height_cm",
    "体高(cm)":       "height_cm",
    "胸囲":           "chest_cm",
    "胸囲(cm)":       "chest_cm",
    "管囲":           "cannon_cm",
    "管囲(cm)":       "cannon_cm",
    "毛色":           "coat_color",
    "募集年":         "year",
    "クラブ名":       "club_name",
}

# Excelの「一覧」シートに含まれる余分な列（スキップ対象）
_EXCEL_SKIP_COLS_STARTSWITH = ("機械的判断", "母評価", "動画", "総合評価", "コメント", "発表状況", "倍率")


def parse_excel_sheet(
    uploaded_file, sheet_name: str = "一覧", fill_year: int | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """
    Excelファイルの指定シートを読み込む。
    fill_year: year 列がない場合に補完する年度（01_upload.py の upload_year を渡す）
    Returns (DataFrame, errors)
    """
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=0)
    except Exception as e:
        return pd.DataFrame(), [f"Excel読み込み失敗: {e}"]

    # 列名の正規化：改行・スペースを除去してからエイリアス変換
    df.columns = [c.replace("\n", "").strip() if isinstance(c, str) else c for c in df.columns]
    df = df.rename(columns=COLUMN_ALIASES)

    # 評価列など不要な列を除外（内部キーに変換されなかった日本語列）
    drop_cols = [c for c in df.columns if isinstance(c, str) and
                 any(c.startswith(p) for p in _EXCEL_SKIP_COLS_STARTSWITH)]
    df = df.drop(columns=drop_cols, errors="ignore")

    # 同名列が複数できた場合（馬体重 + 8月中旬馬体重 → 両方 weight_kg など）は最後の列を残す
    df = df.loc[:, ~df.columns.duplicated(keep="last")]

    # 馬名が空の行（集計行・空白行）を除去
    if "horse_name" in df.columns:
        df = df[df["horse_name"].notna() & (df["horse_name"].astype(str).str.strip() != "")]

    # year 列がなければ補完
    if "year" not in df.columns and fill_year is not None:
        df["year"] = fill_year

    errors = _validate(df)
    if errors:
        return df, errors

    df = _normalize(df)
    return df, []


def parse_file(uploaded_file, fill_year: int | None = None) -> tuple[pd.DataFrame, list[str]]:
    """csv / xlsx どちらにも対応したエントリーポイント。"""
    name = getattr(uploaded_file, "name", "")
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return parse_excel_sheet(uploaded_file, fill_year=fill_year)
    return parse_csv(uploaded_file)


def parse_csv(uploaded_file) -> tuple[pd.DataFrame, list[str]]:
    """
    Returns
    -------
    (DataFrame, errors)
        errors が空リストなら正常。
    """
    try:
        content = uploaded_file.read()
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("shift_jis", errors="replace")

        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        return pd.DataFrame(), [f"CSV読み込み失敗: {e}"]

    df = df.rename(columns=COLUMN_ALIASES)
    df.columns = [c.strip() for c in df.columns]

    errors = _validate(df)
    if errors:
        return df, errors

    df = _normalize(df)
    return df, []


def _validate(df: pd.DataFrame) -> list[str]:
    errors = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"必須カラムが不足しています: {missing}")
    return errors


def missing_optional(df: pd.DataFrame) -> list[str]:
    """クラブExcelに本来あるはずの任意列のうち存在しないものを返す（警告表示用）。"""
    return [c for c in EXPECTED_OPTIONAL_COLUMNS if c not in df.columns]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # Excelで日付型(datetime64/pd.Timestamp)になる列を文字列に変換
    if "birth_date" in df.columns:
        df["birth_date"] = df["birth_date"].apply(
            lambda v: v.strftime("%Y/%m/%d") if pd.notna(v) and hasattr(v, "strftime")
            else (str(v).strip() if pd.notna(v) and str(v).strip() not in ("", "nan", "NaT") else None)
        )

    for col in ["horse_name", "sire_name", "dam_name", "broodmare_sire_name",
                "farm_name", "trainer_name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace("　", " ", regex=False)

    for col in ["weight_kg", "weight_kg_base", "weight_kg_latest", "height_cm", "chest_cm", "cannon_cm",
                "price_total", "price_per_lot"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 馬体重（基準値）を weight_kg にリネーム
    if "weight_kg_base" in df.columns:
        df = df.rename(columns={"weight_kg_base": "weight_kg"})
    # 基準値なしで直近のみある場合のフォールバック（後方互換）
    if "weight_kg" not in df.columns and "weight_kg_latest" in df.columns:
        df["weight_kg"] = df["weight_kg_latest"]

    # 「父(母の父)」列: "キズナ （Henrythenavigator）" → sire_name="キズナ", broodmare_sire_name="Henrythenavigator"
    if "sire_name" in df.columns:
        extracted = df["sire_name"].astype(str).str.extract(
            r"^([^（(]+?)\s*[（(]([^）)]+)[）)]", expand=True
        )
        has_paren = extracted[0].notna()
        if has_paren.any():
            df.loc[has_paren, "sire_name"] = extracted.loc[has_paren, 0].str.strip()
            if "broodmare_sire_name" not in df.columns:
                df["broodmare_sire_name"] = None
            df.loc[has_paren, "broodmare_sire_name"] = extracted.loc[has_paren, 1].str.strip()

    return df
