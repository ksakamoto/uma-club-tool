-- ============================================================
-- jravan_raw.db  全レコード種別対応スキーマ
-- ============================================================
-- 既存5テーブル (jravan.db と同構造)
-- ============================================================

-- 競走馬マスタ (UM)
CREATE TABLE IF NOT EXISTS horses (
    horse_code              TEXT PRIMARY KEY,
    horse_name              TEXT NOT NULL,
    horse_name_kana         TEXT,
    horse_name_eng          TEXT,
    birth_year              INTEGER,
    birth_month             INTEGER,
    birth_day               INTEGER,
    sex_code                TEXT,
    breed_code              TEXT,
    color_code              TEXT,
    horse_symbol            TEXT,
    registered_date         TEXT,
    deregistered_date       TEXT,
    in_jra_facility         TEXT,
    sire_code               TEXT,
    sire_name               TEXT,
    dam_code                TEXT,
    dam_name                TEXT,
    broodmare_sire_code     TEXT,
    broodmare_sire_name     TEXT,
    east_west_code          TEXT,
    trainer_code            TEXT,
    trainer_name_short      TEXT,
    invited_area            TEXT,
    farm_code               TEXT,
    farm_name               TEXT,
    farm_area               TEXT,
    owner_code              TEXT,
    owner_name              TEXT,
    flat_prize_total        REAL,
    obstacle_prize_total    REAL,
    total_runs              INTEGER,
    total_wins              INTEGER,
    total_2nd               INTEGER,
    total_3rd               INTEGER,
    central_runs            INTEGER,
    central_wins            INTEGER,
    turf_runs               INTEGER,
    turf_wins               INTEGER,
    dirt_runs               INTEGER,
    dirt_wins               INTEGER,
    registered_race_count   INTEGER,
    fetched_at              TEXT
);

-- 繁殖馬マスタ (HN)
CREATE TABLE IF NOT EXISTS broodmares (
    mare_code               TEXT PRIMARY KEY,
    pedigree_code           TEXT,
    mare_name               TEXT NOT NULL,
    mare_name_kana          TEXT,
    mare_name_eng           TEXT,
    birth_year              INTEGER,
    sex_code                TEXT,
    breed_code              TEXT,
    color_code              TEXT,
    import_flag             TEXT,
    import_year             INTEGER,
    farm_area               TEXT,
    sire_mare_code          TEXT,
    dam_mare_code           TEXT,
    fetched_at              TEXT
);

-- 競走馬市場取引価格 (HS)
CREATE TABLE IF NOT EXISTS sales (
    horse_code              TEXT NOT NULL,
    market_code             TEXT NOT NULL,
    sale_start_date         TEXT NOT NULL,
    sale_end_date           TEXT,
    sire_mare_code          TEXT,
    dam_mare_code           TEXT,
    birth_year              INTEGER,
    age_at_sale             INTEGER,
    organizer_name          TEXT,
    market_name             TEXT,
    sale_price              REAL,
    fetched_at              TEXT,
    PRIMARY KEY (horse_code, market_code, sale_start_date)
);

-- 調教師マスタ + 年次成績 (CH)
CREATE TABLE IF NOT EXISTS trainer_yearly_stats (
    trainer_code            TEXT NOT NULL,
    period_year             INTEGER NOT NULL,
    period_type             TEXT NOT NULL,
    trainer_name            TEXT NOT NULL,
    trainer_name_kana       TEXT,
    trainer_name_short      TEXT,
    trainer_name_eng        TEXT,
    sex                     TEXT,
    east_west_code          TEXT,
    license_date            TEXT,
    license_revoked_date    TEXT,
    birth_date              TEXT,
    flat_prize_total        REAL,
    obstacle_prize_total    REAL,
    flat_extra_prize_total  REAL,
    obstacle_extra_prize_total REAL,
    flat_runs               INTEGER,
    flat_wins               INTEGER,
    flat_2nd                INTEGER,
    flat_3rd                INTEGER,
    flat_outside            INTEGER,
    obstacle_runs           INTEGER,
    obstacle_wins           INTEGER,
    obstacle_2nd            INTEGER,
    obstacle_3rd            INTEGER,
    obstacle_outside        INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (trainer_code, period_year, period_type)
);

-- 生産者マスタ + 年次成績 (BR)
CREATE TABLE IF NOT EXISTS farm_yearly_stats (
    farm_code               TEXT NOT NULL,
    period_year             INTEGER NOT NULL,
    period_type             TEXT NOT NULL,
    farm_name               TEXT NOT NULL,
    farm_name_with_org      TEXT,
    farm_name_kana          TEXT,
    farm_name_eng           TEXT,
    farm_address            TEXT,
    prize_total             REAL,
    extra_prize_total       REAL,
    runs                    INTEGER,
    wins                    INTEGER,
    second                  INTEGER,
    third                   INTEGER,
    outside                 INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (farm_code, period_year, period_type)
);

-- ============================================================
-- 新規テーブル
-- ============================================================

-- レース詳細 (RA)
CREATE TABLE IF NOT EXISTS races (
    kaisai_year             TEXT NOT NULL,  -- 開催年 (4byte)
    kaisai_date             TEXT NOT NULL,  -- 開催月日 MMDD (4byte)
    venue_code              TEXT NOT NULL,  -- 競馬場コード (2byte)
    kai                     TEXT NOT NULL,  -- 開催回 (2byte)
    nichi                   TEXT NOT NULL,  -- 開催日目 (2byte)
    race_no                 TEXT NOT NULL,  -- レース番号 (2byte)
    data_created_date       TEXT,           -- データ作成年月日
    race_name               TEXT,           -- 競走名本題
    race_name_abbr10        TEXT,           -- 競走名略称10文字
    race_name_abbr6         TEXT,           -- 競走名略称6文字
    race_name_abbr3         TEXT,           -- 競走名略称3文字
    grade_code              TEXT,           -- グレードコード
    race_type_code          TEXT,           -- 競走種別コード
    condition_code_2y       TEXT,           -- 競走条件コード 2歳条件
    condition_code_3y       TEXT,           -- 競走条件コード 3歳条件
    condition_name          TEXT,           -- 競走条件名称
    distance                INTEGER,        -- 距離 (m)
    track_code              TEXT,           -- トラックコード
    prize_1st               REAL,           -- 本賞金1位 (万円)
    start_time              TEXT,           -- 発走時刻 (HHMM)
    registered_count        INTEGER,        -- 登録頭数
    runner_count            INTEGER,        -- 出走頭数
    finisher_count          INTEGER,        -- 入線頭数
    weather_code            TEXT,           -- 天候コード
    turf_condition          TEXT,           -- 芝馬場状態コード
    dirt_condition          TEXT,           -- ダート馬場状態コード
    fetched_at              TEXT,
    PRIMARY KEY (kaisai_year, kaisai_date, venue_code, kai, nichi, race_no)
);

-- 馬毎レース情報 (SE)
CREATE TABLE IF NOT EXISTS horse_race_results (
    kaisai_year             TEXT NOT NULL,
    kaisai_date             TEXT NOT NULL,
    venue_code              TEXT NOT NULL,
    kai                     TEXT NOT NULL,
    nichi                   TEXT NOT NULL,
    race_no                 TEXT NOT NULL,
    horse_no                TEXT NOT NULL,  -- 馬番 (2byte)
    horse_code              TEXT,           -- 血統登録番号
    horse_name              TEXT,           -- 馬名
    sex_code                TEXT,
    age                     INTEGER,        -- 馬齢
    east_west_code          TEXT,
    trainer_code            TEXT,
    trainer_name_short      TEXT,
    owner_code              TEXT,
    owner_name              TEXT,
    weight_carried          INTEGER,        -- 負担重量 (0.1kg単位)
    jockey_code             TEXT,           -- 騎手コード
    jockey_name_short       TEXT,           -- 騎手名略称
    horse_weight            INTEGER,        -- 馬体重 (kg)
    weight_diff_sign        TEXT,           -- 増減符号
    weight_diff             INTEGER,        -- 増減差
    abnormal_code           TEXT,           -- 異常区分コード
    finish_pos              INTEGER,        -- 確定着順
    finish_time_raw         TEXT,           -- 走破タイム (生値 HMMSS)
    win_odds                TEXT,           -- 単勝オッズ (raw)
    popularity              INTEGER,        -- 単勝人気順
    prize_won               REAL,           -- 獲得本賞金 (万円)
    extra_prize_won         REAL,           -- 獲得付加賞金 (万円)
    last_3f                 TEXT,           -- 後3ハロンタイム
    corner1_pos             INTEGER,        -- 1コーナー通過順位
    corner2_pos             INTEGER,        -- 2コーナー
    corner3_pos             INTEGER,
    corner4_pos             INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (kaisai_year, kaisai_date, venue_code, kai, nichi, race_no, horse_no)
);

-- 騎手マスタ (KS)
CREATE TABLE IF NOT EXISTS jockeys (
    jockey_code             TEXT PRIMARY KEY,  -- 騎手コード (5byte)
    jockey_name             TEXT NOT NULL,
    jockey_name_kana        TEXT,
    jockey_name_short       TEXT,
    jockey_name_eng         TEXT,
    sex                     TEXT,
    license_date            TEXT,           -- 騎手免許交付年月日
    license_revoked_date    TEXT,           -- 騎手免許抹消年月日
    birth_date              TEXT,
    apprentice_code         TEXT,           -- 騎手見習コード
    east_west_code          TEXT,           -- 騎手東西所属コード
    trainer_code            TEXT,           -- 所属調教師コード
    trainer_name_short      TEXT,
    fetched_at              TEXT
);

-- 騎手マスタ 年次成績 (KS繰返部)
CREATE TABLE IF NOT EXISTS jockey_yearly_stats (
    jockey_code             TEXT NOT NULL,
    period_year             INTEGER NOT NULL,
    period_type             TEXT NOT NULL,  -- 'current' / 'previous' / 'cumulative'
    flat_prize_total        REAL,
    obstacle_prize_total    REAL,
    flat_extra_prize_total  REAL,
    obstacle_extra_prize_total REAL,
    flat_runs               INTEGER,
    flat_wins               INTEGER,
    flat_2nd                INTEGER,
    flat_3rd                INTEGER,
    flat_outside            INTEGER,
    obstacle_runs           INTEGER,
    obstacle_wins           INTEGER,
    obstacle_2nd            INTEGER,
    obstacle_3rd            INTEGER,
    obstacle_outside        INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (jockey_code, period_year, period_type)
);

-- 馬主マスタ (BN)
CREATE TABLE IF NOT EXISTS owners (
    owner_code              TEXT PRIMARY KEY,  -- 馬主コード (6byte)
    owner_name              TEXT,           -- 馬主名(法人格有)
    owner_name_no_corp      TEXT NOT NULL,  -- 馬主名(法人格無)
    owner_name_kana         TEXT,
    owner_name_eng          TEXT,
    silks_color             TEXT,           -- 服色標示
    fetched_at              TEXT
);

-- 馬主マスタ 年次成績 (BN繰返部)
CREATE TABLE IF NOT EXISTS owner_yearly_stats (
    owner_code              TEXT NOT NULL,
    period_year             INTEGER NOT NULL,
    period_type             TEXT NOT NULL,  -- 'current' / 'cumulative'
    prize_total             REAL,
    extra_prize_total       REAL,
    runs                    INTEGER,
    wins                    INTEGER,
    second                  INTEGER,
    third                   INTEGER,
    outside                 INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (owner_code, period_year, period_type)
);

-- 産駒マスタ (SK)
CREATE TABLE IF NOT EXISTS progeny (
    horse_code              TEXT PRIMARY KEY,  -- 血統登録番号 (10byte)
    birth_date              TEXT,           -- 生年月日
    sex_code                TEXT,
    breed_code              TEXT,
    color_code              TEXT,
    import_flag             TEXT,           -- 産駒持込区分
    import_year             INTEGER,
    farm_code               TEXT,           -- 生産者コード (8byte)
    farm_area               TEXT,           -- 産地名
    sire_code               TEXT,           -- 父 繁殖登録番号 (3代血統[0])
    dam_code                TEXT,           -- 母 繁殖登録番号 (3代血統[1])
    broodmare_sire_code     TEXT,           -- 母父 繁殖登録番号 (3代血統[3])
    fetched_at              TEXT
);

-- レコードマスタ (RC)
CREATE TABLE IF NOT EXISTS record_times (
    record_type_code        TEXT NOT NULL,  -- レコード識別区分 (1byte)
    kaisai_year             TEXT NOT NULL,
    kaisai_date             TEXT NOT NULL,
    venue_code              TEXT NOT NULL,
    kai                     TEXT NOT NULL,
    nichi                   TEXT NOT NULL,
    race_no                 TEXT NOT NULL,
    tokubetsu_no            TEXT NOT NULL,  -- 特別競走番号 (4byte)
    race_name               TEXT,           -- 競走名本題
    grade_code              TEXT,
    race_type_code          TEXT,           -- 競走種別コード
    distance                INTEGER,        -- 距離
    track_code              TEXT,
    record_class            TEXT,           -- レコード区分
    record_time_raw         TEXT,           -- レコードタイム (生値)
    weather_code            TEXT,
    turf_condition          TEXT,
    dirt_condition          TEXT,
    record_horse_code       TEXT,           -- レコード保持馬情報[0] 血統登録番号
    record_horse_name       TEXT,           -- レコード保持馬情報[0] 馬名
    record_jockey_code      TEXT,           -- レコード保持馬情報[0] 騎手コード
    fetched_at              TEXT,
    PRIMARY KEY (record_type_code, kaisai_year, kaisai_date, venue_code, kai, nichi, race_no, tokubetsu_no)
);

-- 系統情報 (BT)
CREATE TABLE IF NOT EXISTS pedigree_lines (
    mare_code               TEXT PRIMARY KEY,  -- 繁殖登録番号 (10byte)
    lineage_id              TEXT,           -- 系統ID (30byte)
    lineage_name            TEXT,           -- 系統名 (36byte)
    lineage_desc            TEXT,           -- 系統説明 (6800byte テキスト)
    fetched_at              TEXT
);

-- 未知レコード種別 fallback
CREATE TABLE IF NOT EXISTS unknown_records (
    record_type             TEXT NOT NULL,
    raw_text                TEXT NOT NULL,
    fetched_at              TEXT NOT NULL
);

-- ============================================================
-- 取得ログ
-- ============================================================
CREATE TABLE IF NOT EXISTS fetch_log (
    table_name              TEXT PRIMARY KEY,
    last_fetched_at         TEXT,
    record_count            INTEGER
);

-- ============================================================
-- インデックス
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_horses_sire_code         ON horses(sire_code);
CREATE INDEX IF NOT EXISTS idx_horses_dam_code          ON horses(dam_code);
CREATE INDEX IF NOT EXISTS idx_horses_farm_code         ON horses(farm_code);
CREATE INDEX IF NOT EXISTS idx_horses_trainer           ON horses(trainer_code);
CREATE INDEX IF NOT EXISTS idx_horses_horse_name        ON horses(horse_name);
CREATE INDEX IF NOT EXISTS idx_horses_dam_name          ON horses(dam_name);
CREATE INDEX IF NOT EXISTS idx_broodmares_pedigree      ON broodmares(pedigree_code);
CREATE INDEX IF NOT EXISTS idx_broodmares_name          ON broodmares(mare_name);
CREATE INDEX IF NOT EXISTS idx_sales_horse_code         ON sales(horse_code);
CREATE INDEX IF NOT EXISTS idx_races_venue_date         ON races(venue_code, kaisai_year, kaisai_date);
CREATE INDEX IF NOT EXISTS idx_races_grade              ON races(grade_code);
CREATE INDEX IF NOT EXISTS idx_horse_results_horse      ON horse_race_results(horse_code);
CREATE INDEX IF NOT EXISTS idx_horse_results_race       ON horse_race_results(kaisai_year, kaisai_date, venue_code, race_no);
CREATE INDEX IF NOT EXISTS idx_jockeys_name             ON jockeys(jockey_name);
CREATE INDEX IF NOT EXISTS idx_jockey_stats_code        ON jockey_yearly_stats(jockey_code);
CREATE INDEX IF NOT EXISTS idx_owners_name              ON owners(owner_name_no_corp);
CREATE INDEX IF NOT EXISTS idx_owner_stats_code         ON owner_yearly_stats(owner_code);
CREATE INDEX IF NOT EXISTS idx_progeny_horse            ON progeny(horse_code);
CREATE INDEX IF NOT EXISTS idx_progeny_sire             ON progeny(sire_code);
CREATE INDEX IF NOT EXISTS idx_unknown_record_type      ON unknown_records(record_type);
