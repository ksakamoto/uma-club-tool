"""ユーザーデータ（評価・出資記録）の読み書きクライアント。userdata.db を管理する。"""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path
import pandas as pd

from app.core.application_odds import calc_odds

_SCHEMA = """
CREATE TABLE IF NOT EXISTS annual_horses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    year            INTEGER NOT NULL,
    horse_name      TEXT NOT NULL,
    recruit_no      INTEGER,
    sire_name       TEXT,
    dam_name        TEXT,
    broodmare_sire_name TEXT,
    trainer_name    TEXT,
    farm_name       TEXT,
    stable          TEXT,
    birth_date      TEXT,
    sex             TEXT,
    price_total     REAL,

    body_weight     REAL,
    body_weight_latest REAL,
    height          REAL,
    chest_girth     REAL,
    cannon_bone     REAL,

    mj_body         TEXT,
    mj_dam          TEXT,
    mj_trainer      TEXT,

    score_total     REAL,
    score_sire      REAL,
    score_trainer   REAL,
    score_farm      REAL,
    score_siblings  REAL,
    score_physical  REAL,
    score_physical_latest REAL,
    score_mj_body   REAL,
    score_mj_dam    REAL,
    score_mj_trainer REAL,

    eval_video      TEXT,
    eval_overall    TEXT,

    applied         INTEGER DEFAULT 0,
    won             INTEGER DEFAULT 0,
    notes           TEXT,

    UNIQUE(year, horse_name)
);

CREATE TABLE IF NOT EXISTS application_announcement (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    year                INTEGER NOT NULL,
    announcement_no     INTEGER NOT NULL,
    prev_year_ratio     REAL NOT NULL,
    member_growth_rate  REAL DEFAULT 0.01,
    announced_date      TEXT,
    UNIQUE(year, announcement_no)
);

CREATE TABLE IF NOT EXISTS application_status (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    year                  INTEGER NOT NULL,
    horse_name            TEXT NOT NULL,
    announcement_no       INTEGER NOT NULL,
    total_applications    INTEGER,
    priority_tickets      INTEGER,
    mother_general_count  INTEGER,
    top_priority_count    INTEGER,
    priority_quota        INTEGER DEFAULT 200,
    total_quota           INTEGER DEFAULT 400,
    UNIQUE(year, horse_name, announcement_no)
);
"""


class UserDataWriter:
    """userdata.db の読み書きを担当する。jravan.db とは分離。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN recruit_no INTEGER")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # 列が既に存在する場合は無視
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN broodmare_sire_name TEXT")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # 列が既に存在する場合は無視
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN stable TEXT")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # 列が既に存在する場合は無視
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN birth_date TEXT")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN body_weight_latest REAL")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self._conn.execute("ALTER TABLE annual_horses ADD COLUMN score_physical_latest REAL")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def conn(self) -> sqlite3.Connection:
        if not self._conn:
            raise RuntimeError("UserDataWriter not connected.")
        return self._conn

    def upsert_horse(self, year: int, horse: dict) -> None:
        """scored_df の1行から annual_horses にupsert。"""
        self.conn.execute(
            """
            INSERT INTO annual_horses (
                year, horse_name, recruit_no, sire_name, dam_name, broodmare_sire_name,
                trainer_name, farm_name, stable, birth_date, sex, price_total,
                body_weight, body_weight_latest, height, chest_girth, cannon_bone,
                mj_body, mj_dam, mj_trainer,
                score_total, score_sire, score_trainer, score_farm,
                score_siblings, score_physical, score_physical_latest,
                score_mj_body, score_mj_dam, score_mj_trainer
            ) VALUES (
                :year, :horse_name, :recruit_no, :sire_name, :dam_name, :broodmare_sire_name,
                :trainer_name, :farm_name, :stable, :birth_date, :sex, :price_total,
                :weight_kg, :weight_kg_latest, :height_cm, :chest_cm, :cannon_cm,
                :grade_mj_body, :grade_mj_dam, :grade_mj_trainer,
                :total_score, :score_sire, :score_trainer, :score_farm,
                :score_siblings, :score_physical, :score_physical_latest,
                :score_mj_body, :score_mj_dam, :score_mj_trainer
            )
            ON CONFLICT(year, horse_name) DO UPDATE SET
                recruit_no            = excluded.recruit_no,
                sire_name             = excluded.sire_name,
                dam_name              = excluded.dam_name,
                broodmare_sire_name   = excluded.broodmare_sire_name,
                trainer_name          = excluded.trainer_name,
                farm_name             = excluded.farm_name,
                stable                = excluded.stable,
                birth_date            = excluded.birth_date,
                sex                   = excluded.sex,
                price_total           = excluded.price_total,
                body_weight           = excluded.body_weight,
                body_weight_latest    = COALESCE(excluded.body_weight_latest, annual_horses.body_weight_latest),
                height                = excluded.height,
                chest_girth           = excluded.chest_girth,
                cannon_bone           = excluded.cannon_bone,
                mj_body               = excluded.mj_body,
                mj_dam                = excluded.mj_dam,
                mj_trainer            = excluded.mj_trainer,
                score_total           = excluded.score_total,
                score_sire            = excluded.score_sire,
                score_trainer         = excluded.score_trainer,
                score_farm            = excluded.score_farm,
                score_siblings        = excluded.score_siblings,
                score_physical        = excluded.score_physical,
                score_physical_latest = COALESCE(excluded.score_physical_latest, annual_horses.score_physical_latest),
                score_mj_body         = excluded.score_mj_body,
                score_mj_dam          = excluded.score_mj_dam,
                score_mj_trainer      = excluded.score_mj_trainer
            """,
            {
                "broodmare_sire_name": None, "stable": None,
                "birth_date": None, "weight_kg_latest": None, "score_physical_latest": None,
                **horse, "year": year,
            },
        )
        self.conn.commit()

    def upsert_horses_bulk(self, year: int, scored_df: pd.DataFrame) -> int:
        """scored_df の全行を一括upsert。保存した件数を返す。"""
        count = 0
        for _, row in scored_df.iterrows():
            self.upsert_horse(year, row.to_dict())
            count += 1
        return count

    @staticmethod
    def _canonical_horse_year(name: str) -> str:
        """馬名末尾の年サフィックスを4桁年に統一する（比較専用）。
        'スルーセブンシーズの25' → 'スルーセブンシーズの2025'
        'スルーセブンシーズの2025' → そのまま
        """
        return re.sub(r'の(\d{2})$', lambda m: f'の20{m.group(1)}', name)

    def _resolve_horse_name(self, year: int, input_name: str, known_names: set[str] | None = None) -> str:
        """annual_horses の正規名と突き合わせ、の25/の2025 の揺らぎを吸収して返す。
        マッチしない場合は入力値をそのまま返す。
        """
        if known_names is None:
            rows = self.conn.execute(
                'SELECT horse_name FROM annual_horses WHERE year = ?', (year,)
            ).fetchall()
            known_names = {r[0] for r in rows}

        if input_name in known_names:
            return input_name

        norm_input = self._canonical_horse_year(input_name)
        for canonical in known_names:
            if self._canonical_horse_year(canonical) == norm_input:
                return canonical

        return input_name

    @staticmethod
    def _normalize_eval(v):
        """評価記号の表記揺れを正規化。"""
        _EVAL_NORMALIZE = {
            "○": "◯",   # U+25CB → U+25EF
            "▴": "▲",   # U+25B4 → U+25B2
            "▵": "▲",   # U+25B5 → U+25B2
            "✕": "×",   # U+2715 → U+00D7
            "✖": "×",   # U+2716 → U+00D7
            "×": "×",   # U+FF38 全角 → U+00D7 (念のため)
        }
        return _EVAL_NORMALIZE.get(v, v)

    def update_eval(self, year: int, horse_name: str, eval_dict: dict) -> None:
        """主観評価・申込フラグ・メモを更新。"""
        allowed_keys = {"eval_video", "eval_overall", "applied", "won", "notes"}
        updates = {k: v for k, v in eval_dict.items() if k in allowed_keys}
        for k in ("eval_video", "eval_overall"):
            if k in updates:
                updates[k] = self._normalize_eval(updates[k])
        if not updates:
            return
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        self.conn.execute(
            f"UPDATE annual_horses SET {set_clause} WHERE year = :year AND horse_name = :horse_name",
            {**updates, "year": year, "horse_name": horse_name},
        )
        self.conn.commit()

    def update_evals_bulk(self, year: int, df: pd.DataFrame) -> None:
        """st.data_editor 等で変更された評価列を一括更新。df は horse_name 列を持つこと。"""
        eval_cols = {"eval_video", "eval_overall", "applied", "won", "notes"}
        for _, row in df.iterrows():
            updates = {k: row[k] for k in eval_cols if k in df.columns}
            self.update_eval(year, row["horse_name"], updates)

    def get_horses_by_year(self, year: int) -> pd.DataFrame:
        return pd.read_sql_query(
            "SELECT * FROM annual_horses WHERE year = ? ORDER BY COALESCE(score_total, 0) DESC",
            self.conn,
            params=(year,),
        )

    def get_all_years(self) -> list[int]:
        df = pd.read_sql_query(
            "SELECT DISTINCT year FROM annual_horses ORDER BY year DESC", self.conn
        )
        return df["year"].tolist() if not df.empty else []

    def get_all_horses(self) -> pd.DataFrame:
        return pd.read_sql_query(
            "SELECT * FROM annual_horses ORDER BY year DESC, COALESCE(score_total, 0) DESC",
            self.conn,
        )

    def upsert_application_announcement(
        self,
        year: int,
        announcement_no: int,
        prev_year_ratio: float,
        member_growth_rate: float = 0.01,
        announced_date: str | None = None,
    ) -> None:
        """公表回ごとのグローバルパラメータを登録・更新する。"""
        self.conn.execute(
            """
            INSERT INTO application_announcement
                (year, announcement_no, prev_year_ratio, member_growth_rate, announced_date)
            VALUES (:year, :no, :ratio, :growth, :date)
            ON CONFLICT(year, announcement_no) DO UPDATE SET
                prev_year_ratio    = excluded.prev_year_ratio,
                member_growth_rate = excluded.member_growth_rate,
                announced_date     = excluded.announced_date
            """,
            {"year": year, "no": announcement_no, "ratio": prev_year_ratio,
             "growth": member_growth_rate, "date": announced_date},
        )
        self.conn.commit()

    def upsert_application_status_bulk(
        self,
        year: int,
        announcement_no: int,
        rows: list[dict],
        priority_quota: int = 200,
        total_quota: int = 400,
    ) -> int:
        """馬ごとの申込状況を一括登録・更新する。rows は horse_name + 各数値を持つ dict のリスト。
        horse_name は annual_horses の正規名と突き合わせ、の25/の2025 の揺らぎを吸収する。
        Returns: 処理した件数
        """
        # annual_horses の正規名を一度だけ取得してキャッシュ
        known_rows = self.conn.execute(
            'SELECT horse_name FROM annual_horses WHERE year = ?', (year,)
        ).fetchall()
        known_names: set[str] = {r[0] for r in known_rows}

        count = 0
        for row in rows:
            resolved_name = self._resolve_horse_name(year, row["horse_name"], known_names)
            self.conn.execute(
                """
                INSERT INTO application_status
                    (year, horse_name, announcement_no,
                     total_applications, priority_tickets, mother_general_count, top_priority_count,
                     priority_quota, total_quota)
                VALUES (:year, :name, :no, :total, :priority, :mother, :top, :pq, :tq)
                ON CONFLICT(year, horse_name, announcement_no) DO UPDATE SET
                    total_applications   = excluded.total_applications,
                    priority_tickets     = excluded.priority_tickets,
                    mother_general_count = excluded.mother_general_count,
                    top_priority_count   = excluded.top_priority_count,
                    priority_quota       = excluded.priority_quota,
                    total_quota          = excluded.total_quota
                """,
                {
                    "year": year, "name": resolved_name, "no": announcement_no,
                    "total": row.get("total_applications"),
                    "priority": row.get("priority_tickets"),
                    "mother": row.get("mother_general_count"),
                    "top": row.get("top_priority_count"),
                    "pq": row.get("priority_quota", priority_quota),
                    "tq": row.get("total_quota", total_quota),
                },
            )
            count += 1
        self.conn.commit()
        return count

    def get_application_odds_by_year(self, year: int) -> dict[str, dict]:
        """指定年の最新公表回の申込倍率を馬名をキーとして返す。

        Returns
        -------
        dict[horse_name, dict]:
            keys: odds_top, odds_general, announcement_no, announced_date
        """
        # 最新公表回の announcement を取得
        ann_df = pd.read_sql_query(
            "SELECT * FROM application_announcement WHERE year = ? ORDER BY announcement_no DESC LIMIT 1",
            self.conn, params=(year,),
        )
        if ann_df.empty:
            return {}

        ann = ann_df.iloc[0]
        latest_no = int(ann["announcement_no"])

        status_df = pd.read_sql_query(
            "SELECT * FROM application_status WHERE year = ? AND announcement_no = ?",
            self.conn, params=(year, latest_no),
        )
        if status_df.empty:
            return {}

        result = {}
        for _, row in status_df.iterrows():
            try:
                odds = calc_odds(
                    total=int(row["total_applications"] or 0),
                    priority_tickets=int(row["priority_tickets"] or 0),
                    mother_general=int(row["mother_general_count"] or 0),
                    top_priority=int(row["top_priority_count"] or 0),
                    prev_year_ratio=float(ann["prev_year_ratio"]),
                    member_growth_rate=float(ann["member_growth_rate"]),
                    priority_quota=int(row["priority_quota"] or 200),
                    total_quota=int(row["total_quota"] or 400),
                )
                result[row["horse_name"]] = {
                    "odds_top":        odds["odds_top"],
                    "odds_general":    odds["odds_general"],
                    "announcement_no": latest_no,
                    "announced_date":  ann.get("announced_date"),
                }
            except Exception:
                pass
        return result

    def import_from_excel_rows(self, year: int, rows: list[dict]) -> tuple[int, list[str]]:
        """
        過去Excel「一覧」シートの行リストをインポート。
        rows は {'horse_name': ..., 'applied': 0/1, 'won': 0/1, ...} の形式。
        Returns (imported_count, skipped_names)
        """
        count = 0
        skipped = []
        for row in rows:
            name = row.get("horse_name", "").strip()
            if not name:
                continue
            try:
                self.conn.execute(
                    """
                    INSERT INTO annual_horses (year, horse_name, sire_name, dam_name, trainer_name,
                        farm_name, sex, price_total, recruit_no, eval_video, eval_overall, applied, won)
                    VALUES (:year, :horse_name, :sire_name, :dam_name, :trainer_name,
                        :farm_name, :sex, :price_total, :recruit_no, :eval_video, :eval_overall, :applied, :won)
                    ON CONFLICT(year, horse_name) DO UPDATE SET
                        sire_name    = COALESCE(excluded.sire_name, annual_horses.sire_name),
                        dam_name     = COALESCE(excluded.dam_name, annual_horses.dam_name),
                        trainer_name = COALESCE(excluded.trainer_name, annual_horses.trainer_name),
                        farm_name    = COALESCE(excluded.farm_name, annual_horses.farm_name),
                        sex          = COALESCE(excluded.sex, annual_horses.sex),
                        price_total  = COALESCE(excluded.price_total, annual_horses.price_total),
                        recruit_no   = COALESCE(excluded.recruit_no, annual_horses.recruit_no),
                        eval_video   = COALESCE(excluded.eval_video, annual_horses.eval_video),
                        eval_overall = COALESCE(excluded.eval_overall, annual_horses.eval_overall),
                        applied      = CASE WHEN excluded.applied IS NOT NULL THEN excluded.applied
                                            ELSE annual_horses.applied END,
                        won          = CASE WHEN excluded.won IS NOT NULL THEN excluded.won
                                            ELSE annual_horses.won END
                    """,
                    {
                        "year": year,
                        "horse_name": name,
                        "sire_name": row.get("sire_name"),
                        "dam_name": row.get("dam_name"),
                        "trainer_name": row.get("trainer_name"),
                        "farm_name": row.get("farm_name"),
                        "sex": row.get("sex"),
                        "price_total": row.get("price_total"),
                        "recruit_no": row.get("recruit_no"),
                        "eval_video": row.get("eval_video"),
                        "eval_overall": row.get("eval_overall"),
                        "applied": row.get("applied", 0),
                        "won": row.get("won", 0),
                    },
                )
                count += 1
            except Exception:
                skipped.append(name)
        self.conn.commit()
        return count, skipped
