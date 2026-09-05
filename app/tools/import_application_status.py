"""申込状況データをuserdata.dbに書き込むCLIツール。

Claudeが公表テキストをパースした結果をJSONで受け取り、DBに登録する。

使い方:
    python -m app.tools.import_application_status \\
        --db shared/userdata.db \\
        --year 2026 \\
        --announcement-no 1 \\
        --prev-year-ratio 0.148 \\
        --announced-date 2026-08-05 \\
        --data '[{"horse_name":"テスト馬A","total_applications":120,"priority_tickets":30,"mother_general_count":8,"top_priority_count":3}]'

--dataのJSONフィールド:
    horse_name            馬名（必須）
    total_applications    総申込数
    priority_tickets      母馬優先＋最優先票数
    mother_general_count  母馬優先（一般）数
    top_priority_count    最優先数
    priority_quota        優先枠口数（省略時: config.yaml の clubs.carrot.priority_quota, デフォルト200）
    total_quota           総募集口数（省略時: config.yaml の clubs.carrot.total_quota, デフォルト400）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # type: ignore

from app.core.userdata_writer import UserDataWriter


def _load_club_config(config_path: Path, club: str = "carrot") -> dict:
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("clubs", {}).get(club, {})
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="申込状況をuserdata.dbに登録する")
    parser.add_argument("--db", required=True, help="userdata.db のパス")
    parser.add_argument("--year", type=int, required=True, help="募集年 (例: 2026)")
    parser.add_argument("--announcement-no", type=int, required=True, help="公表回 (例: 1)")
    parser.add_argument("--prev-year-ratio", type=float, required=True,
                        help="前年比申込状況 (例: 0.148)")
    parser.add_argument("--member-growth-rate", type=float, default=None,
                        help="会員増加率 (省略時: config.yaml の値, デフォルト 0.01)")
    parser.add_argument("--announced-date", default=None, help="公表日 (例: 2026-08-05)")
    parser.add_argument("--club", default="carrot", help="クラブ名 (デフォルト: carrot)")
    parser.add_argument("--data", required=True,
                        help="馬ごとのデータJSON文字列 (リスト形式)")
    parser.add_argument("--config", default="config.yaml",
                        help="config.yaml のパス (デフォルト: config.yaml)")
    args = parser.parse_args()

    club_cfg = _load_club_config(Path(args.config), args.club)
    default_pq = club_cfg.get("priority_quota", 200)
    default_tq = club_cfg.get("total_quota", 400)
    default_growth = club_cfg.get("member_growth_rate", 0.01)

    member_growth_rate = args.member_growth_rate if args.member_growth_rate is not None else default_growth

    try:
        rows = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"[ERROR] --data のJSONパースに失敗: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(rows, list):
        print("[ERROR] --data はリスト形式のJSONにしてください", file=sys.stderr)
        sys.exit(1)

    # デフォルトのquotaを各rowに適用
    for row in rows:
        row.setdefault("priority_quota", default_pq)
        row.setdefault("total_quota", default_tq)

    ud = UserDataWriter(args.db)
    ud.connect()
    try:
        ud.upsert_application_announcement(
            year=args.year,
            announcement_no=args.announcement_no,
            prev_year_ratio=args.prev_year_ratio,
            member_growth_rate=member_growth_rate,
            announced_date=args.announced_date,
        )
        count = ud.upsert_application_status_bulk(
            year=args.year,
            announcement_no=args.announcement_no,
            rows=rows,
            priority_quota=default_pq,
            total_quota=default_tq,
        )
        print(f"[OK] 第{args.announcement_no}回公表データを登録しました ({count}頭)")

        # 倍率プレビュー
        odds_map = ud.get_application_odds_by_year(args.year)
        if odds_map:
            print("\n--- 倍率プレビュー ---")
            for name, o in odds_map.items():
                top_str = f"{o['odds_top']:.2f}倍" if o["odds_top"] >= 1.0 else "当確"
                gen_str = f"{o['odds_general']:.2f}倍" if o["odds_general"] is not None else "-"
                print(f"  {name}: 最優先={top_str}  一般={gen_str}")
    finally:
        ud.disconnect()


if __name__ == "__main__":
    main()
