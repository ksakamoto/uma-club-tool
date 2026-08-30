using System.Text;

namespace JVLinkFetcher.Parsers;

// JV-Data はShift-JIS固定長レコード。仕様書の位置は1始まりバイト。
// COM経由でUTF-16 string になった時点で日本語文字が圧縮されてズレるので、
// 必ず Shift-JIS バイト配列に戻してから位置で切り出す。
internal static class RecordParser
{
    private static Encoding? _sjis;
    private static Encoding Sjis => _sjis ??= Encoding.GetEncoding(932);

    public static byte[] ToBytes(string rec) => Sjis.GetBytes(rec);

    // 仕様書の1始まりバイト位置 (pos) から len バイト切り出して文字列化（trim付き）
    public static string F(byte[] b, int pos, int len)
    {
        int start = pos - 1;
        if (start < 0 || start + len > b.Length) return "";
        return Sjis.GetString(b, start, len).Trim();
    }

    public static int    I(string s) => int.TryParse(s, out var v) ? v : 0;
    public static double D(string s) => double.TryParse(s, out var v) ? v : 0.0;

    public static int?    NullableI(string s) => int.TryParse(s, out var v) ? v : null;
    public static double? NullableD(string s) => double.TryParse(s, out var v) ? v : null;

    public static double Rate(int wins, int runs) => runs > 0 ? (double)wins / runs : 0.0;

    // ASCII数字フィールドが全0なら null扱い（"00000000" 等の意味なしデータを除外）
    public static int? AsciiYear(string s) =>
        s.Length == 4 && int.TryParse(s, out var v) && v > 0 ? v : null;

    // YYYYMMDD → "YYYY-MM-DD"
    public static string? DateYMD(string s)
        => s.Length == 8 && s != "00000000" && int.TryParse(s, out _)
            ? $"{s[..4]}-{s[4..6]}-{s[6..]}"
            : null;

    // YYYYMMDD → year のみ
    public static int? YearFromYMD(string s)
        => s.Length >= 4 && int.TryParse(s[..4], out var y) && y > 0 ? y : null;

    public static int? MonthFromYMD(string s)
        => s.Length >= 6 && int.TryParse(s[4..6], out var m) && m > 0 ? m : null;
}
