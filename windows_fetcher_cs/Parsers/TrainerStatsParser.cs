namespace JVLinkFetcher.Parsers;

// JV-Data 15. 調教師マスタ (CH, 3862byte)
// pos 705 から「本年･前年･累計成績情報」が 3 回繰返 (各1052byte)
internal static class TrainerStatsParser
{
    private const int Stats_Start = 705;
    private const int Stats_Each  = 1052;
    private static readonly string[] PeriodTypes = ["current", "previous", "cumulative"];

    public static List<Dictionary<string, object?>> ParseAll(string rec)
    {
        var rows = new List<Dictionary<string, object?>>();
        if (rec.Length < 2 || rec[..2] != "CH") return rows;
        try
        {
            var b = RecordParser.ToBytes(rec);
            if (b.Length < 3862) return rows;

            var trainerCode    = RecordParser.F(b,   12,  5);
            var licenseDate    = RecordParser.F(b,   18,  8);
            var revokedDate    = RecordParser.F(b,   26,  8);
            var birthDate      = RecordParser.F(b,   34,  8);
            var trainerName    = RecordParser.F(b,   42, 34);
            var trainerKana    = RecordParser.F(b,   76, 30);
            var trainerShort   = RecordParser.F(b,  106,  8);
            var trainerEng     = RecordParser.F(b,  114, 80);
            var sex            = RecordParser.F(b,  194,  1);
            var eastWest       = RecordParser.F(b,  195,  1);

            if (string.IsNullOrEmpty(trainerCode) || string.IsNullOrEmpty(trainerName))
                return rows;

            for (int i = 0; i < 3; i++)
            {
                int basePos = Stats_Start + i * Stats_Each;
                var yearStr = RecordParser.F(b, basePos,       4);
                var flatPr  = RecordParser.F(b, basePos +   4, 10);
                var obsPr   = RecordParser.F(b, basePos +  14, 10);
                var flatEx  = RecordParser.F(b, basePos +  24, 10);
                var obsEx   = RecordParser.F(b, basePos +  34, 10);
                var (fRuns, fW, f2, f3, f4, fOut) = Read6x6Counts(b, basePos + 44);
                var (oRuns, oW, o2, o3, o4, oOut) = Read6x6Counts(b, basePos + 80);

                int? year = RecordParser.AsciiYear(yearStr);
                if (year == null && PeriodTypes[i] != "cumulative") continue;

                rows.Add(new Dictionary<string, object?>
                {
                    ["trainer_code"]              = trainerCode,
                    ["period_year"]               = year ?? 0,
                    ["period_type"]               = PeriodTypes[i],
                    ["trainer_name"]              = trainerName,
                    ["trainer_name_kana"]         = string.IsNullOrEmpty(trainerKana)  ? null : trainerKana,
                    ["trainer_name_short"]        = string.IsNullOrEmpty(trainerShort) ? null : trainerShort,
                    ["trainer_name_eng"]          = string.IsNullOrEmpty(trainerEng)   ? null : trainerEng,
                    ["sex"]                       = string.IsNullOrEmpty(sex)          ? null : sex,
                    ["east_west_code"]            = string.IsNullOrEmpty(eastWest)     ? null : eastWest,
                    ["license_date"]              = (object?)RecordParser.DateYMD(licenseDate),
                    ["license_revoked_date"]      = (object?)RecordParser.DateYMD(revokedDate),
                    ["birth_date"]                = (object?)RecordParser.DateYMD(birthDate),
                    ["flat_prize_total"]          = RecordParser.D(flatPr) / 10.0,
                    ["obstacle_prize_total"]      = RecordParser.D(obsPr)  / 10.0,
                    ["flat_extra_prize_total"]    = RecordParser.D(flatEx) / 10.0,
                    ["obstacle_extra_prize_total"]= RecordParser.D(obsEx)  / 10.0,
                    ["flat_runs"]      = fRuns, ["flat_wins"] = fW,
                    ["flat_2nd"]       = f2,    ["flat_3rd"]  = f3,
                    ["flat_outside"]   = f4 + fOut,
                    ["obstacle_runs"]      = oRuns, ["obstacle_wins"] = oW,
                    ["obstacle_2nd"]       = o2,    ["obstacle_3rd"]  = o3,
                    ["obstacle_outside"]   = o4 + oOut,
                });
            }
            return rows;
        }
        catch { return []; }
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
}
