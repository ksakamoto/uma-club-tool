namespace JVLinkFetcher.Parsers;

// JV-Data 3. 馬毎レース情報 (SE, 555byte)
internal static class HorseRaceResultParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "SE") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);

            var kaisaiYear = RecordParser.F(b, 12, 4);
            var kaisaiDate = RecordParser.F(b, 16, 4);
            var venueCode  = RecordParser.F(b, 20, 2);
            var kai        = RecordParser.F(b, 22, 2);
            var nichi      = RecordParser.F(b, 24, 2);
            var raceNo     = RecordParser.F(b, 26, 2);
            var horseNo    = RecordParser.F(b, 29, 2);

            if (string.IsNullOrEmpty(kaisaiYear) || string.IsNullOrEmpty(horseNo)) return null;

            var prizeWon   = RecordParser.F(b, 366, 8);
            var extraPrize = RecordParser.F(b, 374, 8);

            return new Dictionary<string, object?>
            {
                ["kaisai_year"]        = kaisaiYear,
                ["kaisai_date"]        = kaisaiDate,
                ["venue_code"]         = venueCode,
                ["kai"]                = kai,
                ["nichi"]              = nichi,
                ["race_no"]            = raceNo,
                ["horse_no"]           = horseNo,
                ["horse_code"]         = NullIfEmpty(RecordParser.F(b,  31, 10)),
                ["horse_name"]         = NullIfEmpty(RecordParser.F(b,  41, 36)),
                ["sex_code"]           = NullIfEmpty(RecordParser.F(b,  79,  1)),
                ["age"]                = RecordParser.NullableI(RecordParser.F(b, 83, 2)),
                ["east_west_code"]     = NullIfEmpty(RecordParser.F(b,  85,  1)),
                ["trainer_code"]       = NullIfEmpty(RecordParser.F(b,  86,  5)),
                ["trainer_name_short"] = NullIfEmpty(RecordParser.F(b,  91,  8)),
                ["owner_code"]         = NullIfEmpty(RecordParser.F(b,  99,  6)),
                ["owner_name"]         = NullIfEmpty(RecordParser.F(b, 105, 64)),
                ["weight_carried"]     = RecordParser.NullableI(RecordParser.F(b, 289, 3)),
                ["jockey_code"]        = NullIfEmpty(RecordParser.F(b, 297,  5)),
                ["jockey_name_short"]  = NullIfEmpty(RecordParser.F(b, 307,  8)),
                ["horse_weight"]       = RecordParser.NullableI(RecordParser.F(b, 325, 3)),
                ["weight_diff_sign"]   = NullIfEmpty(RecordParser.F(b, 328,  1)),
                ["weight_diff"]        = RecordParser.NullableI(RecordParser.F(b, 329, 3)),
                ["abnormal_code"]      = NullIfEmpty(RecordParser.F(b, 332,  1)),
                ["finish_pos"]         = RecordParser.NullableI(RecordParser.F(b, 335, 2)),
                ["finish_time_raw"]    = NullIfEmpty(RecordParser.F(b, 339,  4)),
                ["win_odds"]           = NullIfEmpty(RecordParser.F(b, 360,  4)),
                ["popularity"]         = RecordParser.NullableI(RecordParser.F(b, 364, 2)),
                ["prize_won"]          = RecordParser.D(prizeWon)   / 10.0,
                ["extra_prize_won"]    = RecordParser.D(extraPrize) / 10.0,
                ["last_3f"]            = NullIfEmpty(RecordParser.F(b, 391,  3)),
                ["corner1_pos"]        = RecordParser.NullableI(RecordParser.F(b, 352, 2)),
                ["corner2_pos"]        = RecordParser.NullableI(RecordParser.F(b, 354, 2)),
                ["corner3_pos"]        = RecordParser.NullableI(RecordParser.F(b, 356, 2)),
                ["corner4_pos"]        = RecordParser.NullableI(RecordParser.F(b, 358, 2)),
            };
        }
        catch { return null; }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
