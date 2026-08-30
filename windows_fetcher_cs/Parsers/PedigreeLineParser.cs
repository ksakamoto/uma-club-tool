namespace JVLinkFetcher.Parsers;

// JV-Data 26. 系統情報 (BT, 6889byte)
internal static class PedigreeLineParser
{
    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "BT") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);

            var mareCode = RecordParser.F(b, 12, 10);
            if (string.IsNullOrEmpty(mareCode)) return null;

            return new Dictionary<string, object?>
            {
                ["mare_code"]     = mareCode,
                ["lineage_id"]    = NullIfEmpty(RecordParser.F(b, 22,   30)),
                ["lineage_name"]  = NullIfEmpty(RecordParser.F(b, 52,   36)),
                ["lineage_desc"]  = NullIfEmpty(RecordParser.F(b, 88, 6800)),
            };
        }
        catch { return null; }
    }

    private static object? NullIfEmpty(string s) => string.IsNullOrEmpty(s) ? null : (object)s;
}
