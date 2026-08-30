namespace JVLinkFetcher.Parsers;

// JV-Data 23. 競走馬市場取引価格 (HS, 200byte)
internal static class SalesParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "HS") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);
            if (b.Length < 50) return null;

            var horseCode = RecordParser.F(b,  12, 10); // 血統登録番号
            var sireMare  = RecordParser.F(b,  22, 10); // 父馬繁殖登録番号
            var damMare   = RecordParser.F(b,  32, 10); // 母馬繁殖登録番号
            var birthYr   = RecordParser.F(b,  42,  4); // 生年
            var marketCd  = RecordParser.F(b,  46,  6); // 主催者・市場コード
            var orgName   = RecordParser.F(b,  52, 40); // 主催者名称
            var marketNm  = RecordParser.F(b,  92, 80); // 市場の名称
            var startD    = RecordParser.F(b, 172,  8); // 開催開始日
            var endD      = RecordParser.F(b, 180,  8); // 開催終了日
            var ageS      = RecordParser.F(b, 188,  1); // 取引時年齢
            var priceS    = RecordParser.F(b, 189, 10); // 取引価格

            var startDate = RecordParser.DateYMD(startD);
            if (string.IsNullOrEmpty(horseCode) || string.IsNullOrEmpty(marketCd) || startDate == null)
                return null;

            double? salePrice = !string.IsNullOrEmpty(priceS) && double.TryParse(priceS, out var pr)
                ? pr / 10000.0  // 円 → 万円
                : null;

            return new Dictionary<string, object?>
            {
                ["horse_code"]      = horseCode,
                ["market_code"]     = marketCd,
                ["sale_start_date"] = startDate,
                ["sale_end_date"]   = RecordParser.DateYMD(endD),
                ["sire_mare_code"]  = string.IsNullOrEmpty(sireMare) ? null : sireMare,
                ["dam_mare_code"]   = string.IsNullOrEmpty(damMare)  ? null : damMare,
                ["birth_year"]      = (object?)RecordParser.AsciiYear(birthYr),
                ["age_at_sale"]     = (object?)RecordParser.NullableI(ageS),
                ["organizer_name"]  = orgName,
                ["market_name"]     = marketNm,
                ["sale_price"]      = (object?)salePrice,
            };
        }
        catch { return null; }
    }
}
