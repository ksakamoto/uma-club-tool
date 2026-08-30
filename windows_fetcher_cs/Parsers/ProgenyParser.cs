namespace JVLinkFetcher.Parsers;

// JV-Data 19. 産駒マスタ (SK, 208byte)
// 3代血統 繁殖登録番号 ×14 at pos 67 (各10byte)
internal static class ProgenyParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "SK") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);

            var horseCode = RecordParser.F(b, 12, 10);
            if (string.IsNullOrEmpty(horseCode)) return null;

            // 3代血統 繁殖登録番号 ×14 (pos 67, 各10byte): [0]=父, [1]=母, [3]=母父
            var sireCode          = RecordParser.F(b, 67,  10);
            var damCode           = RecordParser.F(b, 77,  10);
            var broodmareSireCode = RecordParser.F(b, 97,  10); // index 3 = 67 + 3*10

            var importYear = RecordParser.F(b, 35, 4);

            return new Dictionary<string, object?>
            {
                ["horse_code"]           = horseCode,
                ["birth_date"]           = RecordParser.DateYMD(RecordParser.F(b, 22, 8)),
                ["sex_code"]             = NullIfEmpty(RecordParser.F(b, 30, 1)),
                ["breed_code"]           = NullIfEmpty(RecordParser.F(b, 31, 1)),
                ["color_code"]           = NullIfEmpty(RecordParser.F(b, 32, 2)),
                ["import_flag"]          = NullIfEmpty(RecordParser.F(b, 34, 1)),
                ["import_year"]          = RecordParser.AsciiYear(importYear),
                ["farm_code"]            = NullIfEmpty(RecordParser.F(b, 39, 8)),
                ["farm_area"]            = NullIfEmpty(RecordParser.F(b, 47, 20)),
                ["sire_code"]            = NullIfEmpty(sireCode),
                ["dam_code"]             = NullIfEmpty(damCode),
                ["broodmare_sire_code"]  = NullIfEmpty(broodmareSireCode),
            };
        }
        catch { return null; }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
