namespace JVLinkFetcher.Parsers;

// JV-Data 16. 生産者マスタ (BR, 545byte)
// pos 424 から「本年･累計成績情報」が 2 回繰返 (各60byte)
internal static class FarmStatsParser
{
    private const int Stats_Start = 424;
    private const int Stats_Each  = 60;
    private static readonly string[] PeriodTypes = ["current", "cumulative"];

    public static List<Dictionary<string, object?>> ParseAll(string rec)
    {
        var rows = new List<Dictionary<string, object?>>();
        if (rec.Length < 2 || rec[..2] != "BR") return rows;
        try
        {
            var b = RecordParser.ToBytes(rec);
            if (b.Length < 50) return rows;

            var farmCode      = RecordParser.F(b,  12,   8);
            var farmNameOrg   = RecordParser.F(b,  20,  72);
            var farmNameNoOrg = RecordParser.F(b,  92,  72);
            var farmNameKana  = RecordParser.F(b, 164,  72);
            var farmNameEng   = RecordParser.F(b, 236, 168);
            var farmAddress   = RecordParser.F(b, 404,  20);

            if (string.IsNullOrEmpty(farmCode) || string.IsNullOrEmpty(farmNameNoOrg))
                return rows;

            for (int i = 0; i < 2; i++)
            {
                int basePos = Stats_Start + i * Stats_Each;
                var yearStr = RecordParser.F(b, basePos,      4);
                var prize   = RecordParser.F(b, basePos +  4, 10);
                var extra   = RecordParser.F(b, basePos + 14, 10);
                // 着回数 (6 × 6byte): 1着,2着,3着,4着,5着,着外
                int p1 = RecordParser.I(RecordParser.F(b, basePos + 24, 6));
                int p2 = RecordParser.I(RecordParser.F(b, basePos + 30, 6));
                int p3 = RecordParser.I(RecordParser.F(b, basePos + 36, 6));
                int p4 = RecordParser.I(RecordParser.F(b, basePos + 42, 6));
                int p5 = RecordParser.I(RecordParser.F(b, basePos + 48, 6));
                int po = RecordParser.I(RecordParser.F(b, basePos + 54, 6));

                int? year = RecordParser.AsciiYear(yearStr);
                if (year == null && PeriodTypes[i] != "cumulative") continue;

                rows.Add(new Dictionary<string, object?>
                {
                    ["farm_code"]          = farmCode,
                    ["period_year"]        = year ?? 0,
                    ["period_type"]        = PeriodTypes[i],
                    ["farm_name"]          = farmNameNoOrg,
                    ["farm_name_with_org"] = string.IsNullOrEmpty(farmNameOrg)  ? null : farmNameOrg,
                    ["farm_name_kana"]     = string.IsNullOrEmpty(farmNameKana) ? null : farmNameKana,
                    ["farm_name_eng"]      = string.IsNullOrEmpty(farmNameEng)  ? null : farmNameEng,
                    ["farm_address"]       = string.IsNullOrEmpty(farmAddress)  ? null : farmAddress,
                    ["prize_total"]        = RecordParser.D(prize) / 10.0,
                    ["extra_prize_total"]  = RecordParser.D(extra) / 10.0,
                    ["runs"]               = p1 + p2 + p3 + p4 + p5 + po,
                    ["wins"]               = p1,
                    ["second"]             = p2,
                    ["third"]              = p3,
                    ["outside"]            = p4 + p5 + po,
                });
            }
            return rows;
        }
        catch { return []; }
    }
}
