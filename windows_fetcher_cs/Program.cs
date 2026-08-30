using System.Text;
using JVLinkFetcher.Db;
using JVLinkFetcher.Parsers;
using Microsoft.Data.Sqlite;

namespace JVLinkFetcher;

internal class Program
{
    private const string DataSpec  = "DIFNBLDNHOSN";
    private const int    BatchSize = 5000;

    // app DB (jravan.db) の書き込み先テーブルマップ
    private static readonly Dictionary<string, string> TableMap = new()
    {
        ["CH"] = "trainer_yearly_stats",
        ["BR"] = "farm_yearly_stats",
        ["UM"] = "horses",
        ["HN"] = "broodmares",
        ["HS"] = "sales",
        ["RA"] = "races",
        ["SE"] = "horse_race_results",
    };

    // raw DB (jravan_raw.db) の書き込み先テーブルマップ
    // KS/BN は master + stats の2テーブルなので特殊処理
    private static readonly Dictionary<string, string> RawTableMap = new()
    {
        ["CH"] = "trainer_yearly_stats",
        ["BR"] = "farm_yearly_stats",
        ["UM"] = "horses",
        ["HN"] = "broodmares",
        ["HS"] = "sales",
        ["RA"] = "races",
        ["SE"] = "horse_race_results",
        ["SK"] = "progeny",
        ["RC"] = "record_times",
        ["BT"] = "pedigree_lines",
    };

    [STAThread]
    static void Main(string[] args)
    {
        string? sid = null, dbPath = null, rawDbPath = null;
        int years = 5;
        bool setup = false;
        int? raceFromYear = null;
        bool withRacn = false;
        bool raceSetup = false;

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--sid"             when i + 1 < args.Length: sid           = args[++i]; break;
                case "--db-path"         when i + 1 < args.Length: dbPath        = args[++i]; break;
                case "--raw-db-path"     when i + 1 < args.Length: rawDbPath     = args[++i]; break;
                case "--years"           when i + 1 < args.Length: years         = int.Parse(args[++i]); break;
                case "--race-from-year"  when i + 1 < args.Length: raceFromYear  = int.Parse(args[++i]); break;
                case "--setup":     setup     = true; break;
                case "--with-racn":  withRacn  = true; break;
                case "--race-setup": raceSetup = true; withRacn = true; break;
            }
        }

        if (sid == null || dbPath == null)
        {
            Console.Error.WriteLine("Usage: JVLinkFetcher --sid <SID> --db-path <PATH> [--raw-db-path <PATH>] [--years N] [--setup] [--race-from-year YYYY] [--with-racn] [--race-setup]");
            Environment.Exit(1);
        }

        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        try
        {
            var test = Encoding.GetEncoding(932);
            Log($"Shift-JIS ready: {test.WebName} ({test.EncodingName})");
        }
        catch (Exception ex)
        {
            Log($"FATAL: cp932 encoding unavailable: {ex.Message}");
            Environment.Exit(1);
        }

        var fromDate = DateTime.Now.AddDays(-365 * years).ToString("yyyyMMddHHmmss");
        int option   = setup ? 4 : 1;

        Log($"fromDate={fromDate}, option={option}, db={dbPath}");
        if (rawDbPath != null) Log($"raw-db={rawDbPath}");

        // app DB 初期化
        DbWriter.Initialize(dbPath);
        using var conn = DbWriter.GetConnection(dbPath);

        // raw DB 初期化（指定時のみ）
        SqliteConnection? rawConn = null;
        if (rawDbPath != null)
        {
            DbWriter.Initialize(rawDbPath, "JVLinkFetcher.Db.schema_raw.sql");
            rawConn = DbWriter.GetConnection(rawDbPath);
        }

        // app DB バッファ
        var buckets = new Dictionary<string, List<Dictionary<string, object?>>>();
        var counts  = new Dictionary<string, int>();
        foreach (var key in TableMap.Keys) { buckets[key] = []; counts[key] = 0; }

        // raw DB バッファ (KS/BN は master + stats で2種、unknown_records を追加)
        var rawBuckets = new Dictionary<string, List<Dictionary<string, object?>>>();
        var rawCounts  = new Dictionary<string, int>();
        if (rawConn != null)
        {
            foreach (var key in RawTableMap.Keys) { rawBuckets[key] = []; rawCounts[key] = 0; }
            rawBuckets["KS_master"] = []; rawCounts["KS_master"] = 0;
            rawBuckets["KS_stats"]  = []; rawCounts["KS_stats"]  = 0;
            rawBuckets["BN_master"] = []; rawCounts["BN_master"] = 0;
            rawBuckets["BN_stats"]  = []; rawCounts["BN_stats"]  = 0;
            rawBuckets["unknown"]   = []; rawCounts["unknown"]   = 0;
        }

        using var client = new JVLinkClient(sid);
        client.Connect();

        var unknownKeys   = new Dictionary<string, int>();
        var seenKeys      = new Dictionary<string, int>();
        var parseFailures = new Dictionary<string, (int count, string sample)>();

        Action<string> processRecord = raw =>
        {
            if (raw.Length < 2) return;
            var key = raw[..2];

            // === app DB 書き込み ===
            if (buckets.ContainsKey(key))
            {
                // RA/SE は --race-from-year 指定時に古い年をスキップ（setup時の大容量対策）
                // kaisai_year は pos=12, len=4 → 0-indexed: [11..15]
                if ((key == "RA" || key == "SE") && raceFromYear.HasValue
                    && raw.Length >= 15 && int.TryParse(raw[11..15], out var recYear)
                    && recYear < raceFromYear.Value)
                    return;

                seenKeys[key] = seenKeys.GetValueOrDefault(key) + 1;
                List<Dictionary<string, object?>>? parsedRows;
                try
                {
                    parsedRows = key switch
                    {
                        "CH" => TrainerStatsParser.ParseAll(raw),
                        "BR" => FarmStatsParser.ParseAll(raw),
                        "UM" => SingleAsList(HorseCareerParser.Parse(raw)),
                        "HN" => SingleAsList(BroodmareParser.Parse(raw)),
                        "HS" => SingleAsList(SalesParser.Parse(raw)),
                        "RA" => SingleAsList(RaceParser.Parse(raw)),
                        "SE" => SingleAsList(HorseRaceResultParser.Parse(raw)),
                        _    => null,
                    };
                }
                catch (Exception ex)
                {
                    RecordFailure(parseFailures, key, ex.GetType().Name + ": " + ex.Message);
                    parsedRows = null;
                }

                if (parsedRows == null || parsedRows.Count == 0)
                    RecordFailure(parseFailures, key, "parser returned null/empty");
                else
                {
                    buckets[key].AddRange(parsedRows);
                    if (buckets[key].Count >= BatchSize)
                        FlushBucket(conn, key, TableMap, buckets, counts);
                }
            }

            // === raw DB 書き込み (全種別、--raw-db-path ありの時のみ) ===
            if (rawConn == null) return;

            if (RawTableMap.ContainsKey(key))
            {
                List<Dictionary<string, object?>>? parsedRows = null;
                try
                {
                    parsedRows = key switch
                    {
                        "CH" => TrainerStatsParser.ParseAll(raw),
                        "BR" => FarmStatsParser.ParseAll(raw),
                        "UM" => SingleAsList(HorseCareerParser.Parse(raw)),
                        "HN" => SingleAsList(BroodmareParser.Parse(raw)),
                        "HS" => SingleAsList(SalesParser.Parse(raw)),
                        "RA" => SingleAsList(RaceParser.Parse(raw)),
                        "SE" => SingleAsList(HorseRaceResultParser.Parse(raw)),
                        "SK" => SingleAsList(ProgenyParser.Parse(raw)),
                        "RC" => SingleAsList(RecordTimeParser.Parse(raw)),
                        "BT" => SingleAsList(PedigreeLineParser.Parse(raw)),
                        _    => null,
                    };
                }
                catch { }

                if (parsedRows != null && parsedRows.Count > 0)
                {
                    rawBuckets[key].AddRange(parsedRows);
                    if (rawBuckets[key].Count >= BatchSize)
                        FlushBucket(rawConn, key, RawTableMap, rawBuckets, rawCounts);
                }
            }
            else if (key == "KS")
            {
                try
                {
                    var (master, stats) = JockeyParser.ParseAll(raw);
                    if (master != null) rawBuckets["KS_master"].Add(master);
                    if (stats.Count > 0) rawBuckets["KS_stats"].AddRange(stats);
                    if (rawBuckets["KS_master"].Count >= BatchSize)
                        FlushRawSpecial(rawConn, "KS_master", "jockeys", rawBuckets, rawCounts);
                    if (rawBuckets["KS_stats"].Count >= BatchSize)
                        FlushRawSpecial(rawConn, "KS_stats", "jockey_yearly_stats", rawBuckets, rawCounts);
                }
                catch { }
            }
            else if (key == "BN")
            {
                try
                {
                    var (master, stats) = OwnerParser.ParseAll(raw);
                    if (master != null) rawBuckets["BN_master"].Add(master);
                    if (stats.Count > 0) rawBuckets["BN_stats"].AddRange(stats);
                    if (rawBuckets["BN_master"].Count >= BatchSize)
                        FlushRawSpecial(rawConn, "BN_master", "owners", rawBuckets, rawCounts);
                    if (rawBuckets["BN_stats"].Count >= BatchSize)
                        FlushRawSpecial(rawConn, "BN_stats", "owner_yearly_stats", rawBuckets, rawCounts);
                }
                catch { }
            }
            else
            {
                // 未知種別 → unknown_records
                unknownKeys[key] = unknownKeys.GetValueOrDefault(key) + 1;
                rawBuckets["unknown"].Add(new Dictionary<string, object?>
                {
                    ["record_type"] = key,
                    ["raw_text"]    = raw.Length > 200 ? raw[..200] : raw,
                });
                if (rawBuckets["unknown"].Count >= BatchSize)
                    FlushRawSpecial(rawConn, "unknown", "unknown_records", rawBuckets, rawCounts);
            }
        };

        Log("Fetching DIFN/BLDN/HOSN data...");
        client.ReadStored(DataSpec, fromDate, option, processRecord);

        if (withRacn)
        {
            int raceOption = raceSetup ? 4 : option;
            Log($"Fetching RACE race data (option={raceOption})...");
            client.ReadStored("RACE", fromDate, raceOption, processRecord);
        }

        // 残余フラッシュ (app DB)
        foreach (var key in TableMap.Keys)
            if (buckets[key].Count > 0) FlushBucket(conn, key, TableMap, buckets, counts);

        // 残余フラッシュ (raw DB)
        if (rawConn != null)
        {
            foreach (var key in RawTableMap.Keys)
                if (rawBuckets[key].Count > 0)
                    FlushBucket(rawConn, key, RawTableMap, rawBuckets, rawCounts);
            FlushRawSpecial(rawConn, "KS_master", "jockeys",              rawBuckets, rawCounts);
            FlushRawSpecial(rawConn, "KS_stats",  "jockey_yearly_stats",  rawBuckets, rawCounts);
            FlushRawSpecial(rawConn, "BN_master", "owners",               rawBuckets, rawCounts);
            FlushRawSpecial(rawConn, "BN_stats",  "owner_yearly_stats",   rawBuckets, rawCounts);
            FlushRawSpecial(rawConn, "unknown",   "unknown_records",      rawBuckets, rawCounts);
        }

        // unknown_records サマリー
        if (unknownKeys.Count > 0 && rawConn != null)
        {
            Log($"[RAW] unknown_records に {rawCounts.GetValueOrDefault("unknown")} 件保存:");
            foreach (var (k, cnt) in unknownKeys.OrderByDescending(x => x.Value))
                Log($"  種別={k}: {cnt} 件 → sqlite3 jravan_raw.db \"SELECT raw_text FROM unknown_records WHERE record_type='{k}' LIMIT 3;\"");
        }
        else if (unknownKeys.Count > 0)
        {
            Log("Unknown record types (not captured; specify --raw-db-path to save):");
            foreach (var (k, cnt) in unknownKeys.OrderByDescending(x => x.Value))
                Log($"  {k}: {cnt} records");
        }

        // パーサ通過率
        Log("Parser pass rate:");
        foreach (var key in TableMap.Keys)
        {
            int seen = seenKeys.GetValueOrDefault(key);
            int failCount = parseFailures.TryGetValue(key, out var f) ? f.count : 0;
            string sample = parseFailures.TryGetValue(key, out var f2) ? f2.sample : "";
            Log($"  {key}: seen={seen}, failed={failCount} (sample: {sample})");
        }

        // fetch_log 更新 (app DB)
        foreach (var (key, tableName) in TableMap)
        {
            DbWriter.UpdateFetchLog(conn, tableName, counts[key]);
            Log($"{tableName}: {counts[key]} rows written");
        }

        // fetch_log 更新 (raw DB)
        if (rawConn != null)
        {
            var rawLogMap = new Dictionary<string, string>(RawTableMap)
            {
                ["KS_master"] = "jockeys",
                ["KS_stats"]  = "jockey_yearly_stats",
                ["BN_master"] = "owners",
                ["BN_stats"]  = "owner_yearly_stats",
                ["unknown"]   = "unknown_records",
            };
            foreach (var (key, tableName) in rawLogMap)
            {
                if (!rawCounts.TryGetValue(key, out var cnt)) continue;
                DbWriter.UpdateFetchLog(rawConn, tableName, cnt);
                Log($"[RAW] {tableName}: {cnt} rows written");
            }
            rawConn.Dispose();
        }

        Log("Done!");
    }

    private static List<Dictionary<string, object?>>? SingleAsList(Dictionary<string, object?>? d)
        => d == null ? null : [d];

    private static void FlushBucket(
        SqliteConnection conn,
        string key,
        Dictionary<string, string> tableMap,
        Dictionary<string, List<Dictionary<string, object?>>> buckets,
        Dictionary<string, int> counts)
    {
        var rows = buckets[key];
        if (rows.Count == 0) return;
        int written = DbWriter.Upsert(conn, tableMap[key], rows);
        counts[key] += written;
        rows.Clear();
    }

    private static void FlushRawSpecial(
        SqliteConnection conn,
        string bucketKey,
        string tableName,
        Dictionary<string, List<Dictionary<string, object?>>> buckets,
        Dictionary<string, int> counts)
    {
        var rows = buckets[bucketKey];
        if (rows.Count == 0) return;
        int written = DbWriter.Upsert(conn, tableName, rows);
        counts[bucketKey] = counts.GetValueOrDefault(bucketKey) + written;
        rows.Clear();
    }

    private static void RecordFailure(Dictionary<string, (int count, string sample)> failures, string key, string msg)
    {
        if (!failures.ContainsKey(key)) failures[key] = (1, msg);
        else failures[key] = (failures[key].count + 1, failures[key].sample);
    }

    private static void Log(string msg) =>
        Console.Error.WriteLine($"[{DateTime.Now:HH:mm:ss}] [INFO] {msg}");
}
