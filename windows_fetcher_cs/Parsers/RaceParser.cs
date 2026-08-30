namespace JVLinkFetcher.Parsers;

// JV-Data 2. レース詳細 (RA, 1272byte)
internal static class RaceParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "RA") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);

            var kaisaiYear = RecordParser.F(b,  12, 4);
            var kaisaiDate = RecordParser.F(b,  16, 4);
            var venueCode  = RecordParser.F(b,  20, 2);
            var kai        = RecordParser.F(b,  22, 2);
            var nichi      = RecordParser.F(b,  24, 2);
            var raceNo     = RecordParser.F(b,  26, 2);

            if (string.IsNullOrEmpty(kaisaiYear) || string.IsNullOrEmpty(raceNo)) return null;

            return new Dictionary<string, object?>
            {
                ["kaisai_year"]       = kaisaiYear,
                ["kaisai_date"]       = kaisaiDate,
                ["venue_code"]        = venueCode,
                ["kai"]               = kai,
                ["nichi"]             = nichi,
                ["race_no"]           = raceNo,
                ["data_created_date"] = RecordParser.DateYMD(RecordParser.F(b, 4, 8)),
                ["race_name"]         = NullIfEmpty(RecordParser.F(b,  33, 60)),
                ["race_name_abbr10"]  = NullIfEmpty(RecordParser.F(b, 573, 20)),
                ["race_name_abbr6"]   = NullIfEmpty(RecordParser.F(b, 593, 12)),
                ["race_name_abbr3"]   = NullIfEmpty(RecordParser.F(b, 605,  6)),
                ["grade_code"]        = NullIfEmpty(RecordParser.F(b, 615,  1)),
                ["race_type_code"]    = NullIfEmpty(RecordParser.F(b, 617,  2)),
                ["condition_code_2y"] = NullIfEmpty(RecordParser.F(b, 623,  3)),
                ["condition_code_3y"] = NullIfEmpty(RecordParser.F(b, 626,  3)),
                ["condition_name"]    = NullIfEmpty(RecordParser.F(b, 638, 60)),
                ["distance"]          = RecordParser.NullableI(RecordParser.F(b, 698, 4)),
                ["track_code"]        = NullIfEmpty(RecordParser.F(b, 706,  2)),
                ["prize_1st"]         = RecordParser.D(RecordParser.F(b, 714, 8)) / 10.0,
                ["start_time"]        = NullIfEmpty(RecordParser.F(b, 874,  4)),
                ["registered_count"]  = RecordParser.NullableI(RecordParser.F(b, 882, 2)),
                ["runner_count"]      = RecordParser.NullableI(RecordParser.F(b, 884, 2)),
                ["finisher_count"]    = RecordParser.NullableI(RecordParser.F(b, 886, 2)),
                ["weather_code"]      = NullIfEmpty(RecordParser.F(b, 888,  1)),
                ["turf_condition"]    = NullIfEmpty(RecordParser.F(b, 889,  1)),
                ["dirt_condition"]    = NullIfEmpty(RecordParser.F(b, 890,  1)),
            };
        }
        catch { return null; }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
