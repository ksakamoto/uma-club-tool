namespace JVLinkFetcher.Parsers;

// JV-Data 18. 繁殖馬マスタ (HN, 251byte)
// DataSpec=BLDN(新仕様)を前提に、繁殖登録番号系は仕様書通り10byte。
internal static class BroodmareParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "HN") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);
            if (b.Length < 50) return null;

            var mareCode    = RecordParser.F(b,  12, 10); // 繁殖登録番号
            var pedigreeCd  = RecordParser.F(b,  30, 10); // 血統登録番号
            var mareName    = RecordParser.F(b,  41, 36); // 馬名
            var mareKana    = RecordParser.F(b,  77, 40); // 馬名半角ｶﾅ
            var mareEng     = RecordParser.F(b, 117, 80); // 馬名欧字
            var birthYear   = RecordParser.F(b, 197,  4); // 生年
            var sexCode     = RecordParser.F(b, 201,  1);
            var breedCode   = RecordParser.F(b, 202,  1);
            var colorCode   = RecordParser.F(b, 203,  2);
            var importFlag  = RecordParser.F(b, 205,  1);
            var importYear  = RecordParser.F(b, 206,  4);
            var farmArea    = RecordParser.F(b, 210, 20);
            var sireMareCd  = RecordParser.F(b, 230, 10); // 父馬繁殖登録番号
            var damMareCd   = RecordParser.F(b, 240, 10); // 母馬繁殖登録番号

            if (string.IsNullOrEmpty(mareCode) || string.IsNullOrEmpty(mareName))
                return null;

            return new Dictionary<string, object?>
            {
                ["mare_code"]      = mareCode,
                ["pedigree_code"]  = string.IsNullOrEmpty(pedigreeCd) ? null : pedigreeCd,
                ["mare_name"]      = mareName,
                ["mare_name_kana"] = string.IsNullOrEmpty(mareKana) ? null : mareKana,
                ["mare_name_eng"]  = string.IsNullOrEmpty(mareEng)  ? null : mareEng,
                ["birth_year"]     = (object?)RecordParser.AsciiYear(birthYear),
                ["sex_code"]       = string.IsNullOrEmpty(sexCode)   ? null : sexCode,
                ["breed_code"]     = string.IsNullOrEmpty(breedCode) ? null : breedCode,
                ["color_code"]     = string.IsNullOrEmpty(colorCode) ? null : colorCode,
                ["import_flag"]    = string.IsNullOrEmpty(importFlag) ? null : importFlag,
                ["import_year"]    = (object?)RecordParser.AsciiYear(importYear),
                ["farm_area"]      = string.IsNullOrEmpty(farmArea) ? null : farmArea,
                ["sire_mare_code"] = string.IsNullOrEmpty(sireMareCd) ? null : sireMareCd,
                ["dam_mare_code"]  = string.IsNullOrEmpty(damMareCd)  ? null : damMareCd,
            };
        }
        catch { return null; }
    }
}
