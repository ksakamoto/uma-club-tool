namespace JVLinkFetcher.Parsers;

// JV-Data 14. 騎手マスタ (KS, 4173byte)
// pos 1016 から「本年･前年･累計成績情報」が 3 回繰返 (各1052byte)
// CH と同じ構造なので TrainerStatsParser に準拠
internal static class JockeyParser
{
    private const int Stats_Start = 1016;
    private const int Stats_Each  = 1052;
    private static readonly string[] PeriodTypes = ["current", "previous", "cumulative"];

    public static (Dictionary<string, object?>? master, List<Dictionary<string, object?>> stats) ParseAll(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "KS")
            return (null, []);
        try
        {
            var b = RecordParser.ToBytes(rec);

            var jockeyCode  = RecordParser.F(b,  12,  5);
            var licenseDate = RecordParser.F(b,  18,  8);
            var revokedDate = RecordParser.F(b,  26,  8);
            var birthDate   = RecordParser.F(b,  34,  8);
            var jockeyName  = RecordParser.F(b,  42, 34);
            var jockeyKana  = RecordParser.F(b, 110, 30);
            var jockeyShort = RecordParser.F(b, 140,  8);
            var jockeyEng   = RecordParser.F(b, 148, 80);
            var sex         = RecordParser.F(b, 228,  1);
            var apprentice  = RecordParser.F(b, 230,  1);
            var eastWest    = RecordParser.F(b, 231,  1);
            var trainerCode = RecordParser.F(b, 252,  5);
            var trainerShort= RecordParser.F(b, 257,  8);

            if (string.IsNullOrEmpty(jockeyCode) || string.IsNullOrEmpty(jockeyName))
                return (null, []);

            var master = new Dictionary<string, object?>
            {
                ["jockey_code"]          = jockeyCode,
                ["jockey_name"]          = jockeyName,
                ["jockey_name_kana"]     = NullIfEmpty(jockeyKana),
                ["jockey_name_short"]    = NullIfEmpty(jockeyShort),
                ["jockey_name_eng"]      = NullIfEmpty(jockeyEng),
                ["sex"]                  = NullIfEmpty(sex),
                ["license_date"]         = RecordParser.DateYMD(licenseDate),
                ["license_revoked_date"] = RecordParser.DateYMD(revokedDate),
                ["birth_date"]           = RecordParser.DateYMD(birthDate),
                ["apprentice_code"]      = NullIfEmpty(apprentice),
                ["east_west_code"]       = NullIfEmpty(eastWest),
                ["trainer_code"]         = NullIfEmpty(trainerCode),
                ["trainer_name_short"]   = NullIfEmpty(trainerShort),
            };

            var statRows = new List<Dictionary<string, object?>>();
            for (int i = 0; i < 3; i++)
            {
                int basePos = Stats_Start + i * Stats_Each;
                var yearStr = RecordParser.F(b, basePos,      4);
                var flatPr  = RecordParser.F(b, basePos +  4, 10);
                var obsPr   = RecordParser.F(b, basePos + 14, 10);
                var flatEx  = RecordParser.F(b, basePos + 24, 10);
                var obsEx   = RecordParser.F(b, basePos + 34, 10);
                var (fRuns, fW, f2, f3, f4, fOut) = Read6x6Counts(b, basePos + 44);
                var (oRuns, oW, o2, o3, o4, oOut) = Read6x6Counts(b, basePos + 80);

                int? year = RecordParser.AsciiYear(yearStr);
                if (year == null && PeriodTypes[i] != "cumulative") continue;

                statRows.Add(new Dictionary<string, object?>
                {
                    ["jockey_code"]                 = jockeyCode,
                    ["period_year"]                 = year ?? 0,
                    ["period_type"]                 = PeriodTypes[i],
                    ["flat_prize_total"]            = RecordParser.D(flatPr) / 10.0,
                    ["obstacle_prize_total"]        = RecordParser.D(obsPr)  / 10.0,
                    ["flat_extra_prize_total"]      = RecordParser.D(flatEx) / 10.0,
                    ["obstacle_extra_prize_total"]  = RecordParser.D(obsEx)  / 10.0,
                    ["flat_runs"]      = fRuns, ["flat_wins"] = fW,
                    ["flat_2nd"]       = f2,    ["flat_3rd"]  = f3,
                    ["flat_outside"]   = f4 + fOut,
                    ["obstacle_runs"]  = oRuns, ["obstacle_wins"] = oW,
                    ["obstacle_2nd"]   = o2,    ["obstacle_3rd"]  = o3,
                    ["obstacle_outside"] = o4 + oOut,
                });
            }
            return (master, statRows);
        }
        catch { return (null, []); }
    }

    private static (int runs, int p1, int p2, int p3, int p4, int pOut) Read6x6Counts(byte[] b, int pos)
    {
        int p1 = RecordParser.I(RecordParser.F(b, pos,      6));
        int p2 = RecordParser.I(RecordParser.F(b, pos +  6, 6));
        int p3 = RecordParser.I(RecordParser.F(b, pos + 12, 6));
        int p4 = RecordParser.I(RecordParser.F(b, pos + 18, 6));
        int p5 = RecordParser.I(RecordParser.F(b, pos + 24, 6));
        int po = RecordParser.I(RecordParser.F(b, pos + 30, 6));
        return (p1 + p2 + p3 + p4 + p5 + po, p1, p2, p3, p5, po);
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
