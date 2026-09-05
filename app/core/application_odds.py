"""申込倍率の推計計算。

計算ロジックは暫定的であり、見直しが発生しうる。
参考: 2026出資馬検討Excel「票読み第1回/第2回」シートの数式に準拠。

【推計の考え方】
前年の同回公表時点での申込数と最終申込数の比率（prev_year_ratio）を使い、
現在の公表値から最終的な申込数を外挿する。
さらに毎年の会員増加率（member_growth_rate）で補正する。

【倍率の考え方（キャロットクラブ 400口/馬 の場合）】
- 優先枠 priority_quota (200口): 母馬優先+最優先 が先取り
- 一般枠 total_quota - priority_quota (200口): 残りを一般に開放
- 最優先が優先枠を使い切れない場合、余剰分は一般枠に上乗せされる
"""
from __future__ import annotations
import math


def calc_odds(
    total: int,
    priority_tickets: int,
    mother_general: int,
    top_priority: int,
    prev_year_ratio: float,
    member_growth_rate: float = 0.01,
    priority_quota: int = 200,
    total_quota: int = 400,
) -> dict:
    """申込倍率を推計する。

    Parameters
    ----------
    total:
        発表された総申込数
    priority_tickets:
        発表された母馬優先＋最優先票数
    mother_general:
        発表された母馬優先（一般）数
    top_priority:
        発表された最優先数
    prev_year_ratio:
        前年比申込状況。前年の同回公表時点申込数 / 前年最終申込数。
        例: 第1回公表が前年最終の14.8%のタイミングなら 0.148
    member_growth_rate:
        会員増加率（デフォルト 0.01 = 1%）
    priority_quota:
        優先枠口数（キャロット: 200口）
    total_quota:
        総募集口数（キャロット: 400口）

    Returns
    -------
    dict:
        est_total         推計最終総申込数
        est_priority      推計最終 母馬優先+最優先票数
        est_mother        推計最終 母馬優先（一般）数
        est_top           推計最終 最優先数
        lottery_top       最優先抽選対象（倍率計算の分子）
        odds_top          最優先倍率（1.0未満 = 全員当確）
        lottery_general   一般抽選対象数（odds_top > 1 なら None = 一般枠なし）
        odds_general      一般倍率（lottery_general が None なら None）
    """
    if prev_year_ratio <= 0:
        raise ValueError(f"prev_year_ratio must be > 0, got {prev_year_ratio}")

    # --- 推計値（発表値 → 最終推計） ---
    # 総申込・最優先は会員増加率で補正。母馬優先は頭数依存で増えないため補正なし。
    est_total    = math.ceil((total / prev_year_ratio) * (1 + member_growth_rate))
    est_priority = math.ceil(priority_tickets / prev_year_ratio)
    est_mother   = math.ceil(mother_general / prev_year_ratio)
    est_top      = math.ceil((top_priority / prev_year_ratio) * (1 + member_growth_rate))

    # --- 最優先抽選対象 ---
    # 優先枠（priority_quota）を母馬優先+最優先が超えた場合:
    #   超過分 + 最優先 が優先枠内で抽選にかかる
    # 超えない場合:
    #   最優先のみが抽選対象（余剰枠は一般に回る）
    overflow = est_priority + est_mother - priority_quota
    if overflow > 0:
        lottery_top = overflow + est_top
    else:
        lottery_top = est_top

    # --- 最優先倍率 ---
    # 優先枠が超過している場合は priority_quota 口に対して lottery_top 人が競合
    # 超過していない場合は余剰分も最優先が使えるため、実質の枠が広がる
    if overflow > 0:
        odds_top = lottery_top / priority_quota
    else:
        effective_top_slots = 2 * priority_quota - est_priority - est_mother
        odds_top = lottery_top / max(effective_top_slots, 1)

    # --- 一般倍率 ---
    # 最優先でも落選する（odds_top > 1）なら一般枠は実質なし
    if odds_top > 1:
        lottery_general = None
        odds_general = None
    else:
        lottery_general = est_total - lottery_top
        remaining_slots = total_quota - lottery_top
        odds_general = lottery_general / max(remaining_slots, 1) if remaining_slots > 0 else None

    return {
        "est_total":       est_total,
        "est_priority":    est_priority,
        "est_mother":      est_mother,
        "est_top":         est_top,
        "lottery_top":     lottery_top,
        "odds_top":        odds_top,
        "lottery_general": lottery_general,
        "odds_general":    odds_general,
    }


def format_odds(odds: float | None, *, show_kakujitsu: bool = True) -> str:
    """倍率を表示用文字列に変換。"""
    if odds is None:
        return "-"
    if show_kakujitsu and odds < 1.0:
        return "当確"
    return f"{odds:.1f}倍"
