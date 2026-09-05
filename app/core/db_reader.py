"""SQLite参照専用クライアント。Mac側のStreamlitアプリから使用。"""
from __future__ import annotations
import re
import sqlite3
import pandas as pd


def _build_age_clause(age_filter) -> tuple[str, list]:
    """age_filter から WHERE 句フラグメントとバインドパラメータを返す。
    age_filter: None=全体 / int=単一年齢 / tuple[int,...]=複数年齢
    """
    if age_filter is None:
        return "", []
    if isinstance(age_filter, int):
        return "AND hrr.age = ?", [age_filter]
    placeholders = ",".join("?" * len(age_filter))
    return f"AND hrr.age IN ({placeholders})", list(age_filter)


def _build_sex_clause(sex_filter: str | None) -> tuple[str, list]:
    """sex_filter から WHERE 句フラグメントとバインドパラメータを返す。
    sex_filter: None=全体 / '牡馬'=code IN('1','3') / '牝馬'=code='2'
    騸馬(3)は募集時点では牡馬扱いなので牡馬グループに含める。
    """
    if sex_filter is None:
        return "", []
    if sex_filter == "牡馬":
        return "AND hrr.sex_code IN (?, ?)", ["1", "3"]
    return "AND hrr.sex_code = ?", ["2"]


def parse_recruitment_name(name: str) -> tuple[str, int] | None:
    """
    「{母名}の{年}」形式の募集名を (dam_name, birth_year) に解析する。
    年は2桁(20→2020)・4桁どちらも対応。パース失敗時は None を返す。

    例:
        「ネオフレグランスの2024」 → ('ネオフレグランス', 2024)
        「ネオフレグランスの20」   → ('ネオフレグランス', 2020)
        「ブルージェイ」           → None（正式名や別パターン）
    """
    m = re.match(r"^(.+)の(\d{2,4})$", str(name).strip())
    if not m:
        return None
    dam_name = m.group(1)
    year = int(m.group(2))
    if year < 100:
        year += 2000
    return dam_name, year


class DBReader:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def conn(self) -> sqlite3.Connection:
        if not self._conn:
            raise RuntimeError("DB not connected.")
        return self._conn

    def fetch_df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.conn, params=params)

    def fetch_log(self) -> dict[str, dict]:
        try:
            df = self.fetch_df("SELECT * FROM fetch_log")
            return {row["table_name"]: dict(row) for _, row in df.iterrows()}
        except Exception:
            return {}

    # --- 種牡馬（horsesテーブルからの集計） ---

    def get_sire_stats_avg(self, years: int = 3) -> pd.DataFrame:
        """産駒の累計成績を種牡馬ごとに集計（全産駒対象）。"""
        return self.fetch_df(
            """
            SELECT sire_code, sire_name,
                COUNT(*)                                                     AS offspring_count,
                SUM(COALESCE(total_runs, 0))                                 AS runs_total,
                SUM(COALESCE(total_wins, 0))                                 AS wins_total,
                CAST(SUM(COALESCE(total_wins, 0)) AS REAL)
                    / NULLIF(SUM(COALESCE(total_runs, 0)), 0)                AS win_rate,
                CAST(
                    SUM(COALESCE(total_wins,0)) + SUM(COALESCE(total_2nd,0)) + SUM(COALESCE(total_3rd,0))
                    AS REAL) / NULLIF(SUM(COALESCE(total_runs, 0)), 0)       AS top3_rate,
                CAST(
                    SUM(COALESCE(flat_prize_total,0) + COALESCE(obstacle_prize_total,0))
                    AS REAL) / NULLIF(COUNT(*), 0)                           AS avg_prize
            FROM horses
            WHERE sire_name IS NOT NULL AND sire_name != ''
              AND COALESCE(total_runs, 0) > 0
            GROUP BY sire_code, sire_name
            HAVING COUNT(*) >= 3
            """
        )

    # --- 調教師 ---

    def get_trainer_stats_avg(self, years: int = 3) -> pd.DataFrame:
        return self.fetch_df(
            """
            SELECT trainer_code, trainer_name,
                SUM(COALESCE(flat_runs, 0))  AS runs_total,
                SUM(COALESCE(flat_wins, 0))  AS wins_total,
                CAST(SUM(COALESCE(flat_wins, 0)) AS REAL)
                    / NULLIF(SUM(COALESCE(flat_runs, 0)), 0)                 AS win_rate,
                CAST(
                    SUM(COALESCE(flat_wins,0)) + SUM(COALESCE(flat_2nd,0)) + SUM(COALESCE(flat_3rd,0))
                    AS REAL) / NULLIF(SUM(COALESCE(flat_runs, 0)), 0)        AS top3_rate,
                CAST(SUM(COALESCE(flat_prize_total, 0)) AS REAL)
                    / NULLIF(SUM(COALESCE(flat_runs, 0)), 0)                 AS avg_prize
            FROM trainer_yearly_stats
            WHERE period_type != 'cumulative'
              AND period_year >= (
                  SELECT MAX(period_year) FROM trainer_yearly_stats WHERE period_type != 'cumulative'
              ) - ? + 1
              AND COALESCE(flat_runs, 0) > 0
            GROUP BY trainer_code, trainer_name
            HAVING SUM(flat_runs) >= 20
            """,
            (years,),
        )

    # --- 牧場 ---

    def get_farm_stats_avg(self, years: int = 3) -> pd.DataFrame:
        return self.fetch_df(
            """
            SELECT farm_code, farm_name,
                SUM(COALESCE(runs, 0))  AS runs_total,
                SUM(COALESCE(wins, 0))  AS wins_total,
                CAST(SUM(COALESCE(wins, 0)) AS REAL)
                    / NULLIF(SUM(COALESCE(runs, 0)), 0)                      AS win_rate,
                CAST(
                    SUM(COALESCE(wins,0)) + SUM(COALESCE(second,0)) + SUM(COALESCE(third,0))
                    AS REAL) / NULLIF(SUM(COALESCE(runs, 0)), 0)             AS top3_rate,
                CAST(SUM(COALESCE(prize_total, 0)) AS REAL)
                    / NULLIF(SUM(COALESCE(runs, 0)), 0)                      AS avg_prize
            FROM farm_yearly_stats
            WHERE period_type != 'cumulative'
              AND period_year >= (
                  SELECT MAX(period_year) FROM farm_yearly_stats WHERE period_type != 'cumulative'
              ) - ? + 1
              AND COALESCE(runs, 0) > 0
            GROUP BY farm_code, farm_name
            HAVING SUM(runs) >= 20
            """,
            (years,),
        )

    # --- 兄弟馬 ---

    def get_siblings(self, dam_name: str) -> pd.DataFrame:
        return self.fetch_df(
            """
            SELECT horse_name, sire_name, birth_year, sex_code AS sex,
                COALESCE(total_runs, 0) AS total_runs,
                COALESCE(total_wins, 0) AS total_wins,
                CAST(COALESCE(total_wins, 0) AS REAL)
                    / NULLIF(COALESCE(total_runs, 0), 0)             AS win_rate,
                COALESCE(flat_prize_total, 0) + COALESCE(obstacle_prize_total, 0) AS total_prize,
                deregistered_date
            FROM horses
            WHERE dam_name = ?
            ORDER BY birth_year DESC
            """,
            (dam_name,),
        )

    # --- 繁殖牝馬 ---

    def get_dam_birth_year(self, dam_name: str) -> int | None:
        # 繁殖馬マスタを先に検索
        df = self.fetch_df(
            "SELECT birth_year FROM broodmares WHERE mare_name = ? LIMIT 1",
            (dam_name,),
        )
        if not df.empty and not pd.isna(df.iloc[0]["birth_year"]):
            return int(df.iloc[0]["birth_year"])
        # 未登録の場合は競走馬マスタでフォールバック（引退直後の母馬など）
        # birth_year < 2010 は同名別馬（繁殖牝馬でない古い馬）のヒットを避けるため除外
        df2 = self.fetch_df(
            "SELECT birth_year FROM horses WHERE horse_name = ? AND birth_year >= 2010 LIMIT 1",
            (dam_name,),
        )
        if not df2.empty and not pd.isna(df2.iloc[0]["birth_year"]):
            return int(df2.iloc[0]["birth_year"])
        return None

    # --- マッチング用名前リスト ---

    # --- 種牡馬レース成績（RACE DataSpec ベース） ---

    def get_sire_available_years(self) -> list[int]:
        """horse_race_results に存在する開催年の一覧（降順）。"""
        df = self.fetch_df(
            "SELECT DISTINCT CAST(kaisai_year AS INTEGER) AS yr FROM horse_race_results ORDER BY yr DESC"
        )
        return df["yr"].tolist() if not df.empty else []

    def get_sire_ranking(self, year: int, age_filter=None, sex_filter: str | None = None) -> pd.DataFrame:
        """選択年・年齢条件・性別条件での種牡馬別成績ランキング（総賞金降順）。"""
        age_clause, age_params = _build_age_clause(age_filter)
        sex_clause, sex_params = _build_sex_clause(sex_filter)
        return self.fetch_df(
            f"""
            SELECT
                h.sire_code,
                h.sire_name,
                COUNT(DISTINCT hrr.horse_code)                                         AS offspring_count,
                COUNT(*)                                                                AS total_runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)                  AS wins,
                SUM(CASE WHEN hrr.finish_pos <= 2 THEN 1 ELSE 0 END)                 AS places,
                SUM(CASE WHEN hrr.finish_pos <= 3 THEN 1 ELSE 0 END)                 AS shows,
                CAST(SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END) AS REAL)
                    / NULLIF(COUNT(*), 0)                                              AS win_rate,
                CAST(SUM(CASE WHEN hrr.finish_pos <= 2 THEN 1 ELSE 0 END) AS REAL)
                    / NULLIF(COUNT(*), 0)                                              AS place_rate,
                CAST(SUM(CASE WHEN hrr.finish_pos <= 3 THEN 1 ELSE 0 END) AS REAL)
                    / NULLIF(COUNT(*), 0)                                              AS show_rate,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))                AS total_prize,
                SUM(CASE WHEN r.grade_code IN ('A','B','C') AND hrr.finish_pos = 1
                         THEN 1 ELSE 0 END)                                           AS graded_wins,
                COUNT(DISTINCT CASE WHEN hrr.finish_pos = 1
                         THEN hrr.horse_code END)                                     AS winners_count,
                CAST(COUNT(DISTINCT CASE WHEN hrr.finish_pos = 1
                         THEN hrr.horse_code END) AS REAL)
                    / NULLIF(COUNT(DISTINCT hrr.horse_code), 0)                       AS win_up_rate,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))
                    / NULLIF(COUNT(DISTINCT hrr.horse_code), 0)                       AS prize_per_offspring
            FROM horse_race_results hrr
            JOIN horses h ON h.horse_code = hrr.horse_code
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code = hrr.venue_code AND r.kai = hrr.kai
              AND r.nichi = hrr.nichi AND r.race_no = hrr.race_no
            WHERE hrr.kaisai_year = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
              AND h.sire_name IS NOT NULL AND h.sire_name != ''
              {age_clause}
              {sex_clause}
            GROUP BY h.sire_code, h.sire_name
            ORDER BY total_prize DESC
            """,
            tuple([str(year)] + age_params + sex_params),
        )

    def get_sire_by_condition(self, sire_code: str, year: int, age_filter=None) -> pd.DataFrame:
        """指定種牡馬の条件別（芝/ダ × 距離帯）成績。"""
        age_clause, age_params = _build_age_clause(age_filter)
        return self.fetch_df(
            f"""
            SELECT
                CASE
                    WHEN r.track_code IN ('10','11','12','13','15','17','18','19') THEN '芝'
                    WHEN r.track_code IN ('20','21','22','23','24','25') THEN 'ダート'
                    ELSE 'その他'
                END AS track_type,
                CASE
                    WHEN r.distance <= 1400 THEN '～1400m'
                    WHEN r.distance <= 1800 THEN '1401～1800m'
                    WHEN r.distance <= 2200 THEN '1801～2200m'
                    ELSE '2201m～'
                END AS distance_bucket,
                COUNT(*)                                                               AS runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)                  AS wins,
                SUM(CASE WHEN hrr.finish_pos <= 2 THEN 1 ELSE 0 END)                 AS places,
                SUM(CASE WHEN hrr.finish_pos <= 3 THEN 1 ELSE 0 END)                 AS shows,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))                AS total_prize
            FROM horse_race_results hrr
            JOIN horses h ON h.horse_code = hrr.horse_code
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code = hrr.venue_code AND r.kai = hrr.kai
              AND r.nichi = hrr.nichi AND r.race_no = hrr.race_no
            WHERE h.sire_code = ?
              AND hrr.kaisai_year = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
              {age_clause}
            GROUP BY track_type, distance_bucket
            ORDER BY total_prize DESC
            """,
            tuple([sire_code, str(year)] + age_params),
        )

    def get_sire_sex_condition_breakdown(self, sire_code: str, year: int, age_filter=None) -> pd.DataFrame:
        """指定種牡馬の性別×条件別（芝/ダ × 距離帯）成績。騸馬は牡馬に含める。"""
        age_clause, age_params = _build_age_clause(age_filter)
        return self.fetch_df(
            f"""
            SELECT
                CASE WHEN hrr.sex_code IN ('1', '3') THEN '牡馬' ELSE '牝馬' END AS sex_label,
                CASE
                    WHEN r.track_code IN ('10','11','12','13','15','17','18','19') THEN '芝'
                    WHEN r.track_code IN ('20','21','22','23','24','25') THEN 'ダート'
                    ELSE 'その他'
                END AS track_type,
                CASE
                    WHEN r.distance <= 1400 THEN '～1400m'
                    WHEN r.distance <= 1800 THEN '1401～1800m'
                    WHEN r.distance <= 2200 THEN '1801～2200m'
                    ELSE '2201m～'
                END AS distance_bucket,
                COUNT(*)                                                               AS runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)                  AS wins,
                SUM(CASE WHEN hrr.finish_pos <= 2 THEN 1 ELSE 0 END)                 AS places,
                SUM(CASE WHEN hrr.finish_pos <= 3 THEN 1 ELSE 0 END)                 AS shows,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))                AS total_prize
            FROM horse_race_results hrr
            JOIN horses h ON h.horse_code = hrr.horse_code
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code = hrr.venue_code AND r.kai = hrr.kai
              AND r.nichi = hrr.nichi AND r.race_no = hrr.race_no
            WHERE h.sire_code = ?
              AND hrr.kaisai_year = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
              {age_clause}
            GROUP BY sex_label, track_type, distance_bucket
            ORDER BY sex_label, track_type, distance_bucket
            """,
            tuple([sire_code, str(year)] + age_params),
        )

    def get_sire_top_broodmare_sires(
        self, sire_code: str, year: int, age_filter=None, limit: int = 10
    ) -> pd.DataFrame:
        """指定種牡馬の主要母父（獲得賞金上位N）。"""
        age_clause, age_params = _build_age_clause(age_filter)
        return self.fetch_df(
            f"""
            SELECT
                h.broodmare_sire_name,
                COUNT(DISTINCT hrr.horse_code)                                         AS offspring_count,
                COUNT(*)                                                                AS runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)                  AS wins,
                CAST(SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END) AS REAL)
                    / NULLIF(COUNT(*), 0)                                              AS win_rate,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))                AS total_prize
            FROM horse_race_results hrr
            JOIN horses h ON h.horse_code = hrr.horse_code
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code = hrr.venue_code AND r.kai = hrr.kai
              AND r.nichi = hrr.nichi AND r.race_no = hrr.race_no
            WHERE h.sire_code = ?
              AND hrr.kaisai_year = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
              AND h.broodmare_sire_name IS NOT NULL AND h.broodmare_sire_name != ''
              {age_clause}
            GROUP BY h.broodmare_sire_code, h.broodmare_sire_name
            ORDER BY total_prize DESC
            LIMIT ?
            """,
            tuple([sire_code, str(year)] + age_params + [limit]),
        )

    def get_sire_top_offspring(
        self, sire_code: str, year: int, age_filter=None, limit: int = 10
    ) -> pd.DataFrame:
        """指定種牡馬の主要産駒（獲得賞金上位N）。"""
        age_clause, age_params = _build_age_clause(age_filter)
        return self.fetch_df(
            f"""
            SELECT
                hrr.horse_name,
                COUNT(*)                                                                AS runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)                  AS wins,
                SUM(CASE WHEN r.grade_code IN ('A','B','C') AND hrr.finish_pos = 1
                         THEN 1 ELSE 0 END)                                           AS graded_wins,
                SUM(hrr.prize_won + COALESCE(hrr.extra_prize_won, 0))                AS total_prize
            FROM horse_race_results hrr
            JOIN horses h ON h.horse_code = hrr.horse_code
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code = hrr.venue_code AND r.kai = hrr.kai
              AND r.nichi = hrr.nichi AND r.race_no = hrr.race_no
            WHERE h.sire_code = ?
              AND hrr.kaisai_year = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
              {age_clause}
            GROUP BY hrr.horse_code, hrr.horse_name
            ORDER BY total_prize DESC
            LIMIT ?
            """,
            tuple([sire_code, str(year)] + age_params + [limit]),
        )

    # --- マッチング用名前リスト ---

    def get_all_sire_names(self) -> list[str]:
        df = self.fetch_df(
            "SELECT DISTINCT sire_name FROM horses WHERE sire_name IS NOT NULL AND sire_name != ''"
        )
        return df["sire_name"].tolist()

    def get_all_trainer_names(self) -> list[str]:
        df = self.fetch_df(
            "SELECT DISTINCT trainer_name FROM trainer_yearly_stats WHERE trainer_name IS NOT NULL AND trainer_name != ''"
        )
        return df["trainer_name"].tolist()

    def get_all_farm_names(self) -> list[str]:
        df = self.fetch_df(
            "SELECT DISTINCT farm_name FROM farm_yearly_stats WHERE farm_name IS NOT NULL AND farm_name != ''"
        )
        return df["farm_name"].tolist()

    def get_all_dam_names(self) -> list[str]:
        df = self.fetch_df(
            "SELECT DISTINCT dam_name FROM horses WHERE dam_name IS NOT NULL AND dam_name != ''"
        )
        return df["dam_name"].tolist()

    # --- 機械的判断（MJルール）用 ---

    def get_trainer_mj_stats(self, years: int = 5) -> pd.DataFrame:
        """調教師ごとのN年平均勝利数・重賞勝利数・直近3年top10回数。mj_trainer ルール用。"""
        return self.fetch_df(
            """
            WITH max_year AS (
                -- 最新の完全な暦年（period_year < 現在年、かつ previous として確定している年）
                SELECT MAX(period_year) AS yr
                FROM trainer_yearly_stats
                WHERE period_type != 'cumulative'
                  AND period_year < CAST(strftime('%Y', 'now') AS INTEGER)
            ),
            deduped AS (
                -- 同一 (trainer_code, period_year) に current/previous 両方ある場合は1行に集約
                SELECT
                    trainer_code,
                    MAX(trainer_name)                  AS trainer_name,
                    MAX(license_date)                  AS license_date,
                    period_year,
                    MAX(COALESCE(flat_wins, 0))        AS flat_wins
                FROM trainer_yearly_stats, max_year
                WHERE period_type != 'cumulative'
                  AND period_year >= max_year.yr - ? + 1
                  AND period_year <= max_year.yr
                GROUP BY trainer_code, period_year
            ),
            ranked AS (
                SELECT
                    trainer_code,
                    trainer_name,
                    license_date,
                    period_year,
                    flat_wins,
                    RANK() OVER (
                        PARTITION BY period_year
                        ORDER BY flat_wins DESC
                    ) AS year_rank
                FROM deduped
            ),
            base AS (
                SELECT
                    trainer_code,
                    trainer_name,
                    license_date,
                    COUNT(DISTINCT period_year)                  AS years_count,
                    ROUND(AVG(flat_wins), 1)                     AS avg_wins,
                    SUM(flat_wins)                               AS total_wins,
                    SUM(CASE WHEN year_rank <= 10 THEN 1 ELSE 0 END) AS top10_count_all,
                    SUM(CASE WHEN year_rank <= 10 AND period_year >= (
                            SELECT yr FROM max_year) - 2
                        THEN 1 ELSE 0 END)                       AS top10_count_3y
                FROM ranked
                GROUP BY trainer_code, trainer_name, license_date
            ),
            graded AS (
                SELECT
                    hrr.trainer_code,
                    COUNT(*)                                     AS graded_wins
                FROM horse_race_results hrr
                JOIN races r
                  ON r.kaisai_year = hrr.kaisai_year
                  AND r.kaisai_date = hrr.kaisai_date
                  AND r.venue_code  = hrr.venue_code
                  AND r.kai         = hrr.kai
                  AND r.nichi       = hrr.nichi
                  AND r.race_no     = hrr.race_no
                WHERE r.grade_code IN ('A','B','C','D')
                  AND hrr.finish_pos = 1
                  AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
                GROUP BY hrr.trainer_code
            )
            SELECT
                b.*,
                COALESCE(g.graded_wins, 0) AS graded_wins
            FROM base b
            LEFT JOIN graded g ON b.trainer_code = g.trainer_code
            """,
            (years,),
        )

    def get_dam_offspring_grade_info(self, dam_name: str) -> dict:
        """
        母馬の直仔（兄弟馬）の重賞成績を返す。
        Returns: {has_graded_win, has_graded_placed, has_open_win, sibling_count}
        """
        df = self.fetch_df(
            """
            SELECT
                h.horse_name,
                h.total_runs,
                h.total_wins,
                h.flat_prize_total,
                h.obstacle_prize_total,
                EXISTS (
                    SELECT 1
                    FROM horse_race_results hrr
                    JOIN races r
                      ON r.kaisai_year = hrr.kaisai_year
                      AND r.kaisai_date = hrr.kaisai_date
                      AND r.venue_code  = hrr.venue_code
                      AND r.kai         = hrr.kai
                      AND r.nichi       = hrr.nichi
                      AND r.race_no     = hrr.race_no
                    WHERE hrr.horse_code = h.horse_code
                      AND r.grade_code IN ('A','B','C')
                      AND hrr.finish_pos = 1
                      AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
                ) AS has_g123_win,
                EXISTS (
                    SELECT 1
                    FROM horse_race_results hrr
                    JOIN races r
                      ON r.kaisai_year = hrr.kaisai_year
                      AND r.kaisai_date = hrr.kaisai_date
                      AND r.venue_code  = hrr.venue_code
                      AND r.kai         = hrr.kai
                      AND r.nichi       = hrr.nichi
                      AND r.race_no     = hrr.race_no
                    WHERE hrr.horse_code = h.horse_code
                      AND r.grade_code IN ('A','B','C')
                      AND hrr.finish_pos <= 2
                      AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
                ) AS has_g123_placed,
                EXISTS (
                    SELECT 1
                    FROM horse_race_results hrr
                    JOIN races r
                      ON r.kaisai_year = hrr.kaisai_year
                      AND r.kaisai_date = hrr.kaisai_date
                      AND r.venue_code  = hrr.venue_code
                      AND r.kai         = hrr.kai
                      AND r.nichi       = hrr.nichi
                      AND r.race_no     = hrr.race_no
                    WHERE hrr.horse_code = h.horse_code
                      AND (r.grade_code IN ('A','B','C','D') OR r.condition_name LIKE '%オープン%')
                      AND hrr.finish_pos = 1
                      AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
                ) AS has_open_win
            FROM horses h
            WHERE h.dam_name = ?
            """,
            (dam_name,),
        )
        if df.empty:
            return {"has_graded_win": False, "has_graded_placed": False, "has_open_win": False, "sibling_count": 0}
        return {
            "has_graded_win":    bool(df["has_g123_win"].any()),
            "has_graded_placed": bool(df["has_g123_placed"].any()),
            "has_open_win":      bool(df["has_open_win"].any()),
            "sibling_count":     len(df),
        }

    def get_horse_career_results(self, horse_name: str) -> pd.DataFrame:
        """馬名で馬毎レース成績を取得（活躍状況追跡用）。"""
        return self.fetch_df(
            """
            SELECT
                hrr.kaisai_year,
                hrr.kaisai_date,
                hrr.finish_pos,
                hrr.prize_won,
                hrr.extra_prize_won,
                r.race_name,
                r.grade_code,
                r.distance,
                hrr.abnormal_code
            FROM horse_race_results hrr
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year
              AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code  = hrr.venue_code
              AND r.kai         = hrr.kai
              AND r.nichi       = hrr.nichi
              AND r.race_no     = hrr.race_no
            WHERE hrr.horse_name = ?
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
            ORDER BY hrr.kaisai_year, hrr.kaisai_date
            """,
            (horse_name,),
        )

    def resolve_recruitment_names(self, recruitment_names: list[str]) -> pd.DataFrame:
        """
        募集名リストを正式馬名に解決する。

        「母名の年」形式 → horses テーブルを (dam_name, birth_year) で引いて正式馬名を取得。
        パース失敗または未マッチの場合は recruitment_name をそのまま official_name に使う。

        Returns
        -------
        DataFrame with columns:
            recruitment_name, official_name, resolved (bool)
        """
        parsed: list[tuple[str, str | None, int | None]] = []
        for name in recruitment_names:
            result = parse_recruitment_name(name)
            if result:
                parsed.append((name, result[0], result[1]))
            else:
                parsed.append((name, None, None))

        resolvable_dams = list({dam for _, dam, _ in parsed if dam is not None})
        horses_df = pd.DataFrame()
        if resolvable_dams:
            placeholders = ",".join("?" * len(resolvable_dams))
            horses_df = self.fetch_df(
                f"SELECT horse_code, horse_name, dam_name, birth_year FROM horses "
                f"WHERE dam_name IN ({placeholders})",
                tuple(resolvable_dams),
            )

        rows = []
        for rec_name, dam, yr in parsed:
            if dam is None or horses_df.empty:
                rows.append({"recruitment_name": rec_name, "official_name": rec_name, "resolved": False})
                continue
            match = horses_df[(horses_df["dam_name"] == dam) & (horses_df["birth_year"] == yr)]
            if match.empty:
                rows.append({"recruitment_name": rec_name, "official_name": rec_name, "resolved": False})
            else:
                rows.append({
                    "recruitment_name": rec_name,
                    "official_name": match.iloc[0]["horse_name"],
                    "resolved": True,
                })
        return pd.DataFrame(rows)

    def get_performance_summary(self, horse_names: list[str]) -> pd.DataFrame:
        """複数の馬名から一括で成績サマリーを取得（活躍状況一覧用）。"""
        if not horse_names:
            return pd.DataFrame()
        placeholders = ",".join("?" * len(horse_names))
        return self.fetch_df(
            f"""
            SELECT
                hrr.horse_name,
                COUNT(*)                                                        AS total_runs,
                SUM(CASE WHEN hrr.finish_pos = 1 THEN 1 ELSE 0 END)           AS wins,
                SUM(CASE WHEN hrr.finish_pos <= 3 THEN 1 ELSE 0 END)          AS top3,
                ROUND((MAX(COALESCE(h.flat_prize_total, 0)) + MAX(COALESCE(h.obstacle_prize_total, 0))) / 10.0, 1) AS total_prize,
                SUM(CASE WHEN r.grade_code IN ('A','B','C') AND hrr.finish_pos = 1
                          THEN 1 ELSE 0 END)                                    AS graded_wins,
                SUM(CASE WHEN r.grade_code IN ('A','B','C','D') AND hrr.finish_pos <= 2
                          THEN 1 ELSE 0 END)                                    AS graded_placed
            FROM horse_race_results hrr
            JOIN races r
              ON r.kaisai_year = hrr.kaisai_year
              AND r.kaisai_date = hrr.kaisai_date
              AND r.venue_code  = hrr.venue_code
              AND r.kai         = hrr.kai
              AND r.nichi       = hrr.nichi
              AND r.race_no     = hrr.race_no
            JOIN horses h ON h.horse_code = hrr.horse_code
            WHERE hrr.horse_name IN ({placeholders})
              AND (hrr.abnormal_code IS NULL OR hrr.abnormal_code = '0')
            GROUP BY hrr.horse_name
            """,
            tuple(horse_names),
        )
