-- 競走馬マスタ (JRA-VAN UM)
CREATE TABLE IF NOT EXISTS horses (
    horse_code              TEXT PRIMARY KEY,    -- 血統登録番号 (10)
    horse_name              TEXT NOT NULL,       -- 馬名
    horse_name_kana         TEXT,                -- 馬名半角ｶﾅ
    horse_name_eng          TEXT,                -- 馬名欧字
    birth_year              INTEGER,
    birth_month             INTEGER,
    birth_day               INTEGER,
    sex_code                TEXT,                -- 性別コード
    breed_code              TEXT,                -- 品種コード
    color_code              TEXT,                -- 毛色コード
    horse_symbol            TEXT,                -- 馬記号コード
    registered_date         TEXT,                -- 競走馬登録年月日
    deregistered_date       TEXT,                -- 競走馬抹消年月日
    in_jra_facility         TEXT,                -- JRA施設在きゅうフラグ
    sire_code               TEXT,                -- 父 繁殖登録番号 (3代血統[0])
    sire_name               TEXT,
    dam_code                TEXT,                -- 母
    dam_name                TEXT,
    broodmare_sire_code     TEXT,                -- 母父 (3代血統[3])
    broodmare_sire_name     TEXT,
    east_west_code          TEXT,                -- 東西所属コード
    trainer_code            TEXT,                -- 調教師コード (5)
    trainer_name_short      TEXT,                -- 調教師名略称
    invited_area            TEXT,                -- 招待地域名
    farm_code               TEXT,                -- 生産者コード (8)
    farm_name               TEXT,                -- 生産者名(法人格無)
    farm_area               TEXT,                -- 産地名
    owner_code              TEXT,                -- 馬主コード
    owner_name              TEXT,                -- 馬主名(法人格無)
    flat_prize_total        REAL,                -- 平地本賞金累計
    obstacle_prize_total    REAL,                -- 障害本賞金累計
    total_runs              INTEGER,             -- 総合 出走数
    total_wins              INTEGER,             -- 総合 1着
    total_2nd               INTEGER,
    total_3rd               INTEGER,
    central_runs            INTEGER,             -- 中央合計 出走数
    central_wins            INTEGER,
    turf_runs               INTEGER,
    turf_wins               INTEGER,
    dirt_runs               INTEGER,
    dirt_wins               INTEGER,
    registered_race_count   INTEGER,             -- 登録レース数
    fetched_at              TEXT
);

-- 繁殖馬マスタ (JRA-VAN HN)
CREATE TABLE IF NOT EXISTS broodmares (
    mare_code               TEXT PRIMARY KEY,    -- 繁殖登録番号 (10)
    pedigree_code           TEXT,                -- 血統登録番号 (10) - UM.horse_code と紐付け
    mare_name               TEXT NOT NULL,
    mare_name_kana          TEXT,
    mare_name_eng           TEXT,
    birth_year              INTEGER,             -- 生年 (4桁のみ)
    sex_code                TEXT,
    breed_code              TEXT,
    color_code              TEXT,
    import_flag             TEXT,                -- 繁殖馬持込区分
    import_year             INTEGER,
    farm_area               TEXT,                -- 産地名
    sire_mare_code          TEXT,                -- 父馬繁殖登録番号
    dam_mare_code           TEXT,                -- 母馬繁殖登録番号
    fetched_at              TEXT
);

-- 競走馬市場取引価格 (JRA-VAN HS / HOSE DataSpec)
CREATE TABLE IF NOT EXISTS sales (
    horse_code              TEXT NOT NULL,       -- 血統登録番号
    market_code             TEXT NOT NULL,       -- 主催者・市場コード
    sale_start_date         TEXT NOT NULL,       -- 開催開始日 yyyy-mm-dd
    sale_end_date           TEXT,
    sire_mare_code          TEXT,                -- 父馬繁殖登録番号
    dam_mare_code           TEXT,                -- 母馬繁殖登録番号
    birth_year              INTEGER,
    age_at_sale             INTEGER,             -- 取引時年齢
    organizer_name          TEXT,                -- 主催者名称
    market_name             TEXT,                -- 市場の名称
    sale_price              REAL,                -- 取引価格 (万円)
    fetched_at              TEXT,
    PRIMARY KEY (horse_code, market_code, sale_start_date)
);

-- 調教師マスタ + 年次成績 (JRA-VAN CH)
-- 本年/前年/累計 の3レコードに展開して格納
CREATE TABLE IF NOT EXISTS trainer_yearly_stats (
    trainer_code            TEXT NOT NULL,       -- 調教師コード (5)
    period_year             INTEGER NOT NULL,    -- 設定年 (0なら累計)
    period_type             TEXT NOT NULL,       -- 'current' / 'previous' / 'cumulative'
    trainer_name            TEXT NOT NULL,
    trainer_name_kana       TEXT,
    trainer_name_short      TEXT,
    trainer_name_eng        TEXT,
    sex                     TEXT,
    east_west_code          TEXT,                -- 東西所属
    license_date            TEXT,                -- 調教師免許交付年月日
    license_revoked_date    TEXT,                -- 抹消年月日
    birth_date              TEXT,                -- 生年月日
    flat_prize_total        REAL,                -- 平地本賞金合計
    obstacle_prize_total    REAL,                -- 障害本賞金合計
    flat_extra_prize_total  REAL,                -- 平地付加賞金合計
    obstacle_extra_prize_total REAL,
    flat_runs               INTEGER,             -- 平地着回数: 出走数
    flat_wins               INTEGER,
    flat_2nd                INTEGER,
    flat_3rd                INTEGER,
    flat_outside            INTEGER,
    obstacle_runs           INTEGER,             -- 障害着回数
    obstacle_wins           INTEGER,
    obstacle_2nd            INTEGER,
    obstacle_3rd            INTEGER,
    obstacle_outside        INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (trainer_code, period_year, period_type)
);

-- 生産者マスタ + 年次成績 (JRA-VAN BR)
-- 本年/累計 の2レコードに展開して格納
CREATE TABLE IF NOT EXISTS farm_yearly_stats (
    farm_code               TEXT NOT NULL,       -- 生産者コード (8)
    period_year             INTEGER NOT NULL,    -- 設定年 (0なら累計)
    period_type             TEXT NOT NULL,       -- 'current' / 'cumulative'
    farm_name               TEXT NOT NULL,       -- 生産者名(法人格無)
    farm_name_with_org      TEXT,                -- 生産者名(法人格有)
    farm_name_kana          TEXT,
    farm_name_eng           TEXT,
    farm_address            TEXT,                -- 生産者住所自治省名
    prize_total             REAL,                -- 本賞金合計
    extra_prize_total       REAL,                -- 付加賞金合計
    runs                    INTEGER,             -- 着回数: 出走数
    wins                    INTEGER,
    second                  INTEGER,
    third                   INTEGER,
    outside                 INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (farm_code, period_year, period_type)
);

-- 取得ログ
CREATE TABLE IF NOT EXISTS fetch_log (
    table_name              TEXT PRIMARY KEY,
    last_fetched_at         TEXT,
    record_count            INTEGER
);

CREATE INDEX IF NOT EXISTS idx_horses_sire_code     ON horses(sire_code);
CREATE INDEX IF NOT EXISTS idx_horses_dam_code      ON horses(dam_code);
CREATE INDEX IF NOT EXISTS idx_horses_farm_code     ON horses(farm_code);
CREATE INDEX IF NOT EXISTS idx_horses_trainer       ON horses(trainer_code);
CREATE INDEX IF NOT EXISTS idx_horses_horse_name    ON horses(horse_name);
CREATE INDEX IF NOT EXISTS idx_horses_dam_name      ON horses(dam_name);
CREATE INDEX IF NOT EXISTS idx_broodmares_pedigree  ON broodmares(pedigree_code);
CREATE INDEX IF NOT EXISTS idx_broodmares_name      ON broodmares(mare_name);
CREATE INDEX IF NOT EXISTS idx_sales_horse_code     ON sales(horse_code);
CREATE INDEX IF NOT EXISTS idx_sales_market_date    ON sales(market_code, sale_start_date);
CREATE INDEX IF NOT EXISTS idx_trainer_yearly_name  ON trainer_yearly_stats(trainer_name);
CREATE INDEX IF NOT EXISTS idx_farm_yearly_name     ON farm_yearly_stats(farm_name);

-- レース詳細 (JRA-VAN RA) — 重賞判定用
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
    grade_code              TEXT,           -- グレードコード: A=G1,B=G2,C=G3,D=重賞(グレードなし),F=J-G1,G=J-G2,H=J-G3
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

-- 馬毎レース情報 (JRA-VAN SE) — 勝利数・重賞勝利数集計用
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
    east_west_code          TEXT,           -- 1=美浦,2=栗東
    trainer_code            TEXT,           -- 調教師コード
    trainer_name_short      TEXT,           -- 調教師名略称
    owner_code              TEXT,
    owner_name              TEXT,
    weight_carried          INTEGER,        -- 負担重量 (0.1kg単位)
    jockey_code             TEXT,
    jockey_name_short       TEXT,
    horse_weight            INTEGER,        -- 馬体重 (kg)
    weight_diff_sign        TEXT,
    weight_diff             INTEGER,
    abnormal_code           TEXT,           -- 異常区分コード (取消・失格等)
    finish_pos              INTEGER,        -- 確定着順
    finish_time_raw         TEXT,           -- 走破タイム
    win_odds                TEXT,           -- 単勝オッズ
    popularity              INTEGER,        -- 単勝人気順
    prize_won               REAL,           -- 獲得本賞金 (千円)
    extra_prize_won         REAL,           -- 獲得付加賞金 (千円)
    last_3f                 TEXT,           -- 後3ハロンタイム
    corner1_pos             INTEGER,
    corner2_pos             INTEGER,
    corner3_pos             INTEGER,
    corner4_pos             INTEGER,
    fetched_at              TEXT,
    PRIMARY KEY (kaisai_year, kaisai_date, venue_code, kai, nichi, race_no, horse_no)
);

CREATE INDEX IF NOT EXISTS idx_races_year_grade     ON races(kaisai_year, grade_code);
CREATE INDEX IF NOT EXISTS idx_results_year_trainer ON horse_race_results(kaisai_year, trainer_code);
