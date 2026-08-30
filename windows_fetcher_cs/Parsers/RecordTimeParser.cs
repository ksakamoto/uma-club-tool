namespace JVLinkFetcher.Parsers;

// JV-Data 21. レコードマスタ (RC, 501byte)
// レコード保持馬情報 ×3 at pos 110 (各130byte)
internal static class RecordTimeParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "RC") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);

            var recordTypeCode = RecordParser.F(b, 12, 1);
            var kaisaiYear     = RecordParser.F(b, 13, 4);
            var kaisaiDate     = RecordParser.F(b, 17, 4);
            var venueCode      = RecordParser.F(b, 21, 2);
            var kai            = RecordParser.F(b, 23, 2);
            var nichi          = RecordParser.F(b, 25, 2);
            var raceNo         = RecordParser.F(b, 27, 2);
            var tokubetsuNo    = RecordParser.F(b, 29, 4);

            if (string.IsNullOrEmpty(kaisaiYear) || string.IsNullOrEmpty(raceNo)) return null;

            // レコード保持馬情報[0]: pos 110, 130byte (血統登録番号10, 馬名36, ..., 騎手コード pos=92 5byte, 騎手名 pos=97 34byte)
            var horse1Code    = RecordParser.F(b, 110,  10);
            var horse1Name    = RecordParser.F(b, 120,  36);
            var jockey1Code   = RecordParser.F(b, 201,   5); // 110 + (92-1) = 201
            // jockey name at 110 + (97-1) = 206
            // trainer code at 110 + (50-1) = 159

            return new Dictionary<string, object?>
            {
                ["record_type_code"]  = recordTypeCode,
                ["kaisai_year"]       = kaisaiYear,
                ["kaisai_date"]       = kaisaiDate,
                ["venue_code"]        = venueCode,
                ["kai"]               = kai,
                ["nichi"]             = nichi,
                ["race_no"]           = raceNo,
                ["tokubetsu_no"]      = tokubetsuNo,
                ["race_name"]         = NullIfEmpty(RecordParser.F(b,  33, 60)),
                ["grade_code"]        = NullIfEmpty(RecordParser.F(b,  93,  1)),
                ["race_type_code"]    = NullIfEmpty(RecordParser.F(b,  94,  2)),
                ["distance"]          = RecordParser.NullableI(RecordParser.F(b, 96, 4)),
                ["track_code"]        = NullIfEmpty(RecordParser.F(b, 100,  2)),
                ["record_class"]      = NullIfEmpty(RecordParser.F(b, 102,  1)),
                ["record_time_raw"]   = NullIfEmpty(RecordParser.F(b, 103,  4)),
                ["weather_code"]      = NullIfEmpty(RecordParser.F(b, 107,  1)),
                ["turf_condition"]    = NullIfEmpty(RecordParser.F(b, 108,  1)),
                ["dirt_condition"]    = NullIfEmpty(RecordParser.F(b, 109,  1)),
                ["record_horse_code"] = NullIfEmpty(horse1Code),
                ["record_horse_name"] = NullIfEmpty(horse1Name),
                ["record_jockey_code"]= NullIfEmpty(jockey1Code),
            };
        }
        catch { return null; }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
