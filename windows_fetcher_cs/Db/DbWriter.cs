using Microsoft.Data.Sqlite;
using System.Reflection;

namespace JVLinkFetcher.Db;

internal static class DbWriter
{
    public static SqliteConnection GetConnection(string dbPath)
    {
        var conn = new SqliteConnection($"Data Source={dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "PRAGMA journal_mode=WAL;";
        cmd.ExecuteNonQuery();
        return conn;
    }

    public static void Initialize(string dbPath, string schemaResource = "JVLinkFetcher.Db.schema.sql")
    {
        var asm = Assembly.GetExecutingAssembly();
        using var stream = asm.GetManifestResourceStream(schemaResource)
            ?? throw new InvalidOperationException($"Embedded resource not found: {schemaResource}");
        using var reader = new StreamReader(stream);
        var sql = reader.ReadToEnd();

        using var conn = GetConnection(dbPath);
        using var cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    public static int Upsert(SqliteConnection conn, string tableName, List<Dictionary<string, object?>> rows)
    {
        if (rows.Count == 0) return 0;

        var now = DateTime.Now.ToString("o");
        foreach (var row in rows)
            row["fetched_at"] = now;

        var cols = rows[0].Keys.ToList();
        var colStr = string.Join(", ", cols);
        var placeholders = string.Join(", ", cols.Select(c => $"@{c}"));
        var sql = $"INSERT OR REPLACE INTO {tableName} ({colStr}) VALUES ({placeholders})";

        int count = 0;
        using var tx = conn.BeginTransaction();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        cmd.Transaction = tx;

        foreach (var row in rows)
        {
            cmd.Parameters.Clear();
            foreach (var (k, v) in row)
                cmd.Parameters.AddWithValue($"@{k}", v ?? DBNull.Value);
            count += cmd.ExecuteNonQuery();
        }

        tx.Commit();
        return count;
    }

    public static void UpdateFetchLog(SqliteConnection conn, string tableName, int count)
    {
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT OR REPLACE INTO fetch_log (table_name, last_fetched_at, record_count)
            VALUES (@table_name, @last_fetched_at, @record_count)
            """;
        cmd.Parameters.AddWithValue("@table_name", tableName);
        cmd.Parameters.AddWithValue("@last_fetched_at", DateTime.Now.ToString("o"));
        cmd.Parameters.AddWithValue("@record_count", count);
        cmd.ExecuteNonQuery();
    }
}
