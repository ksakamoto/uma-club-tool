# 運用手順

> **詳細な注意点・JVLink の挙動は `CLAUDE.md` を参照。**

## ビルド

```powershell
cd Y:\Documents\Workspaces\uma-club-tool\windows_fetcher_cs

# self-contained で publish（x86 ランタイム別途インストール不要）
dotnet publish -r win-x86 --self-contained true -c Release
```

実行ファイルの出力先:
```
windows_fetcher_cs\bin\Release\net8.0-windows\win-x86\publish\JVLinkFetcher.exe
```

以降のコマンド例では `.\JVLinkFetcher.exe` と省略する。

---

## 初回セットアップ

初回または新 DataSpec の初使用時は **`--setup` が必須**（option=4）。
`--setup` なしで新 DB に対して実行すると JVOpen が `-1` を返して失敗する。

### jravan.db（アプリ用）のみ

```powershell
# DB ファイルを事前に削除（既存の場合）
Remove-Item "Y:\...\shared\jravan.db" -Force

.\JVLinkFetcher.exe `
    --sid YOUR_SID_HERE `
    --db-path "Y:\Documents\Workspaces\uma-club-tool\shared\jravan.db" `
    --setup
```

### jravan.db + jravan_raw.db（探索用も同時作成）

```powershell
Remove-Item "Y:\...\shared\jravan.db"     -Force
Remove-Item "Y:\...\shared\jravan_raw.db" -Force

.\JVLinkFetcher.exe `
    --sid YOUR_SID_HERE `
    --db-path     "Y:\Documents\Workspaces\uma-club-tool\shared\jravan.db" `
    --raw-db-path "Y:\Documents\Workspaces\uma-club-tool\shared\jravan_raw.db" `
    --setup
```

> **PowerShell の注意**: `<SID>` の `<` はリダイレクト演算子と解釈される。
> SID を直接記述するか、クォートで囲むこと（例: `--sid 'JG123456789'`）。

---

## 差分更新（通常運用）

セットアップ完了後の定期実行。`--setup` を付けずに実行すると差分のみ取得する（option=1）。

```powershell
# jravan.db のみ更新
.\JVLinkFetcher.exe `
    --sid YOUR_SID_HERE `
    --db-path "Y:\...\shared\jravan.db"

# jravan.db + jravan_raw.db 両方更新
.\JVLinkFetcher.exe `
    --sid YOUR_SID_HERE `
    --db-path     "Y:\...\shared\jravan.db" `
    --raw-db-path "Y:\...\shared\jravan_raw.db"
```

オプション:

| オプション | デフォルト | 説明 |
|---|---|---|
| `--sid` | 必須 | JRA-VAN SID |
| `--db-path` | 必須 | jravan.db のパス |
| `--raw-db-path` | なし | 指定時のみ jravan_raw.db に全種別書き込み |
| `--years N` | 5 | 取得対象期間（現在から N 年前まで） |
| `--setup` | なし | 全件取得モード（初回のみ） |

---

## スキーマ変更時

現状マイグレーション機能なし。スキーマ変更時は DB を削除して `--setup` で再構築する。

```powershell
Remove-Item "Y:\...\shared\jravan.db"     -Force -ErrorAction SilentlyContinue
Remove-Item "Y:\...\shared\jravan_raw.db" -Force -ErrorAction SilentlyContinue

# → 上記「初回セットアップ」の手順を再実行
```

---

## データ確認

### SQLite CLI（PowerShell / macOS Terminal）

```bash
# テーブル一覧
sqlite3 shared/jravan_raw.db "SELECT name FROM sqlite_master WHERE type='table';"

# 各テーブルの件数
sqlite3 shared/jravan_raw.db "
  SELECT 'horses',             COUNT(*) FROM horses
  UNION ALL SELECT 'jockeys',  COUNT(*) FROM jockeys
  UNION ALL SELECT 'owners',   COUNT(*) FROM owners
  UNION ALL SELECT 'progeny',  COUNT(*) FROM progeny
  UNION ALL SELECT 'races',    COUNT(*) FROM races;
"

# 最終取得日の確認
sqlite3 shared/jravan.db "SELECT * FROM fetch_log;"

# unknown_records の確認（0 件であること）
sqlite3 shared/jravan_raw.db "
  SELECT record_type, COUNT(*) FROM unknown_records GROUP BY record_type;
"

# unknown_records の内容確認（0 件でない場合）
sqlite3 shared/jravan_raw.db "
  SELECT record_type, raw_text FROM unknown_records LIMIT 5;
"
```

### DB Browser for SQLite（GUI）

macOS で `shared/jravan.db` または `shared/jravan_raw.db` をファイルとして開くと、
テーブル・カラム・データを GUI でブラウズできる。

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| JVOpen が `-1` を返す | 新 DataSpec の初回使用 / DB が未セットアップ | `--setup` オプションを付けて再実行 |
| ダウンロードが進まない | `readCount` と `downloadCount` の取り違え | `CLAUDE.md` の「JVOpen の out引数順序」を参照 |
| Shift-JIS エラー | `CodePagesEncodingProvider` 未登録 | `Program.cs` の `Encoding.RegisterProvider` 呼び出し確認 |
| SQLite ロックエラー | 同時書き込みの競合 | Mac 側は read-only で参照する（WAL モードで基本競合なし） |
| COM エラー `CLASS_NOT_REGISTERED` | JVLink が未インストールまたは x64 ビルド | JVLink インストール確認 + `PlatformTarget=x86` を確認 |
| パーサが null を返す | レコード長が spec より短い | `RecordParser.F()` は範囲外を `""` で返す設計。主キーのみ存在チェック |
| unknown_records に件数がある | 未実装の種別が DataSpec に含まれていた | `raw_text` を確認して新パーサー追加を検討 |
