"""CSV × JRA-VANデータのfuzzy名前マッチング。"""
from __future__ import annotations
import pandas as pd
from rapidfuzz import process, fuzz

from app.core.db_reader import DBReader

_THRESHOLD = 85.0
_MATCH_FIELDS = [
    ("sire_name",    "get_all_sire_names"),
    ("trainer_name", "get_all_trainer_names"),
    ("farm_name",    "get_all_farm_names"),
    # dam_name は採点ルール内で個別にJRA-VANルックアップするため、ここでは補正しない
    # （短い名前でのfuzzy誤マッチが多いため）
]

# DBの調教師名は「姓　名」（全角スペース区切り）で格納されており、
# CSVは「姓名」（スペースなし）の場合がある。
# fuzzy match 前に両側からスペースを除去して比較する。
_NORMALIZE_FIELDS = {"trainer_name"}


def _normalize(s: str) -> str:
    return s.replace("　", "").replace(" ", "")


def _best_match(name: str, candidates: list[str], normalize: bool = False) -> tuple[str | None, float]:
    if not name or not candidates:
        return None, 0.0
    if normalize:
        norm_name = _normalize(name)
        # 正規化後の名前→元の名前の逆引き辞書（同一正規化形が複数ある場合は最初を採用）
        norm_to_orig: dict[str, str] = {}
        for c in candidates:
            nc = _normalize(c)
            norm_to_orig.setdefault(nc, c)
        norm_candidates = list(norm_to_orig.keys())
        result = process.extractOne(norm_name, norm_candidates, scorer=fuzz.token_sort_ratio)
        if result is None:
            return None, 0.0
        norm_match, score, _ = result
        orig_match = norm_to_orig[norm_match]
        return (orig_match, score) if score >= _THRESHOLD else (None, score)
    else:
        result = process.extractOne(name, candidates, scorer=fuzz.token_sort_ratio)
        if result is None:
            return None, 0.0
        match, score, _ = result
        return (match, score) if score >= _THRESHOLD else (None, score)


def merge(df: pd.DataFrame, db: DBReader) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns
    -------
    (merged_df, match_report_df)
        match_report_df はUIのマッチング確認画面に使う。
    """
    name_lists = {field: getattr(db, getter)() for field, getter in _MATCH_FIELDS}
    report_rows = []

    for field, candidates in name_lists.items():
        if field not in df.columns:
            continue
        matched_col = f"{field}_matched"
        score_col   = f"{field}_match_score"
        df[matched_col] = df[field]
        df[score_col]   = 100.0

        for i, val in df[field].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            val_str = str(val).strip()
            if val_str in candidates:
                continue

            matched, score = _best_match(val_str, candidates, normalize=field in _NORMALIZE_FIELDS)
            df.at[i, matched_col] = matched if matched else val_str
            df.at[i, score_col]   = score

            if matched and matched != val_str:
                report_rows.append({
                    "field":    field,
                    "original": val_str,
                    "matched":  matched,
                    "score":    round(score, 1),
                    "row":      i,
                })
            elif not matched:
                report_rows.append({
                    "field":    field,
                    "original": val_str,
                    "matched":  None,
                    "score":    round(score, 1),
                    "row":      i,
                })

    report_df = pd.DataFrame(report_rows) if report_rows else pd.DataFrame(
        columns=["field", "original", "matched", "score", "row"]
    )
    return df, report_df
