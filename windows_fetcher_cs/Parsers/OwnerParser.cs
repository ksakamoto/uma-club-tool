namespace JVLinkFetcher.Parsers;

// JV-Data 17. 馬主マスタ (BN, 477byte)
// pos 356 から「本年･累計成績情報」が 2 回繰返 (各60byte)
// BR と同じ構造なので FarmStatsParser に準拠
internal static class OwnerParser
{
    private const int Stats_Start = 356;
    private const int Stats_Each  = 60;
    private static readonly string[] PeriodTypes = ["current", "cumulative"];

    public static (Dictionary<string, object?>? master, List<Dictionary<string, object?>> stats) ParseAll(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "BN")
            return (null, []);
        try
        {
            var b = RecordParser.ToBytes(rec);

            var ownerCode    = RecordParser.F(b,  12,  6);
            var ownerNameOrg = RecordParser.F(b,  18, 64);
            var ownerNameNoOrg = RecordParser.F(b, 82, 64);
            var ownerKana    = RecordParser.F(b, 146, 50);
            var ownerEng     = RecordParser.F(b, 196, 100);
            var silks        = RecordParser.F(b, 296, 60);

            if (string.IsNullOrEmpty(ownerCode)) return (null, []);
            // 馬主名(法人格無) が空でも(法人格有)があれば主キーは成立
            var displayName = string.IsNullOrEmpty(ownerNameNoOrg) ? ownerNameOrg : ownerNameNoOrg;
            if (string.IsNullOrEmpty(displayName)) return (null, []);

            var master = new Dictionary<string, object?>
            {
                ["owner_code"]         = ownerCode,
                ["owner_name"]         = NullIfEmpty(ownerNameOrg),
                ["owner_name_no_corp"] = NullIfEmpty(ownerNameNoOrg) ?? ownerNameOrg,
                ["owner_name_kana"]    = NullIfEmpty(ownerKana),
                ["owner_name_eng"]     = NullIfEmpty(ownerEng),
                ["silks_color"]        = NullIfEmpty(silks),
            };

            var statRows = new List<Dictionary<string, object?>>();
            for (int i = 0; i < 2; i++)
            {
                int basePos = Stats_Start + i * Stats_Each;
                var yearStr = RecordParser.F(b, basePos,      4);
                var prize   = RecordParser.F(b, basePos +  4, 10);
                var extra   = RecordParser.F(b, basePos + 14, 10);
                int p1 = RecordParser.I(RecordParser.F(b, basePos + 24, 6));
                int p2 = RecordParser.I(RecordParser.F(b, basePos + 30, 6));
                int p3 = RecordParser.I(RecordParser.F(b, basePos + 36, 6));
                int p4 = RecordParser.I(RecordParser.F(b, basePos + 42, 6));
                int p5 = RecordParser.I(RecordParser.F(b, basePos + 48, 6));
                int po = RecordParser.I(RecordParser.F(b, basePos + 54, 6));

                int? year = RecordParser.AsciiYear(yearStr);
                if (year == null && PeriodTypes[i] != "cumulative") continue;

                statRows.Add(new Dictionary<string, object?>
                {
                    ["owner_code"]       = ownerCode,
                    ["period_year"]      = year ?? 0,
                    ["period_type"]      = PeriodTypes[i],
                    ["prize_total"]      = RecordParser.D(prize) / 10.0,
                    ["extra_prize_total"]= RecordParser.D(extra) / 10.0,
                    ["runs"]             = p1 + p2 + p3 + p4 + p5 + po,
                    ["wins"]             = p1,
                    ["second"]           = p2,
                    ["third"]            = p3,
                    ["outside"]          = p4 + p5 + po,
                });
            }
            return (master, statRows);
        }
        catch { return (null, []); }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
