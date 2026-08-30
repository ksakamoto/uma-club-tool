# システムアーキテクチャ

> **Claude 向け詳細コンテキスト・ハマりポイントは `CLAUDE.md` を参照。**
> **API 仕様の 1 次ソースは `ref/JRA-VAN Data Lab. SDK Ver4.9.0.2/ドキュメント/` を参照。**

## 全体図

```
[Windows / Parallels]                              [macOS]
  JVLinkFetcher.exe
    │
    ├─ JVLink COM (JVDTLab.JVLink, 32bit)
    │    └─ JVOpen → JVStatus → JVRead ループ
    │
    ├─→ shared/jravan.db      ← アプリ用 DB（5種別・5テーブル）
    └─→ shared/jravan_raw.db  ← 探索用 DB（全種別・16テーブル）
                                 ※ --raw-db-path 指定時のみ
              ↑
    Parallels 共有フォルダ (Y:\Documents\Workspaces\uma-club-tool\)
              ↓
                                  Streamlit app (app/) ← 未実装
                                    └─ read-only で jravan.db 参照
```

## コンポーネント

| ファイル | 役割 |
|---|---|
| `Program.cs` | CLI エントリポイント・パーサー dispatch・DB 書き込みループ |
| `JVLinkClient.cs` | JVLink COM ラッパー（JVOpen / JVStatus / JVRead） |
| `Parsers/RecordParser.cs` | Shift-JIS バイトパース helper（全パーサーが依存） |
| `Parsers/*Parser.cs` | 各レコード種別パーサー（12 種別対応） |
| `Db/DbWriter.cs` | SQLite 書き込み（INSERT OR REPLACE バッチ） |
| `Db/schema.sql` | jravan.db スキーマ（5テーブル） |
| `Db/schema_raw.sql` | jravan_raw.db スキーマ（16テーブル） |

## 技術スタック

| 要素 | 詳細 |
|---|---|
| 言語・ランタイム | C# / .NET 8 / **x86 必須**（JVLink は 32bit COM） |
| COM コンポーネント | JVDTLab.JVLink（JRA-VAN Data Lab 提供） |
| 文字コード | Shift-JIS (cp932) バイトベースパース |
| DB | SQLite（Microsoft.Data.Sqlite）WAL モード |
| 実行環境 | Windows（Parallels VM 上でも可） |
| Mac 側（将来） | Python / Streamlit / rapidfuzz |

## ディレクトリ構成

```
uma-club-tool/
├── CLAUDE.md                    ← Claude 向け詳細コンテキスト
├── docs/                        ← このドキュメント群
├── windows_fetcher_cs/          ← C# フェッチャー（本体）
│   ├── JVLinkFetcher.csproj
│   ├── Program.cs
│   ├── JVLinkClient.cs
│   ├── Parsers/                 ← 12 レコード種別対応パーサー群
│   │   ├── RecordParser.cs      ← Shift-JIS helper
│   │   ├── HorseCareerParser.cs ← UM
│   │   ├── BroodmareParser.cs   ← HN
│   │   ├── SalesParser.cs       ← HS
│   │   ├── TrainerStatsParser.cs← CH
│   │   ├── FarmStatsParser.cs   ← BR
│   │   ├── RaceParser.cs        ← RA
│   │   ├── HorseRaceResultParser.cs ← SE
│   │   ├── JockeyParser.cs      ← KS
│   │   ├── OwnerParser.cs       ← BN
│   │   ├── ProgenyParser.cs     ← SK
│   │   ├── RecordTimeParser.cs  ← RC
│   │   └── PedigreeLineParser.cs← BT
│   └── Db/
│       ├── DbWriter.cs
│       ├── schema.sql           ← jravan.db（5テーブル）
│       └── schema_raw.sql       ← jravan_raw.db（16テーブル）
├── app/                         ← Mac 側 Streamlit（未実装）
├── shared/                      ← Parallels 共有フォルダ配置先
│   ├── jravan.db                ← アプリ用 DB
│   └── jravan_raw.db            ← 探索用 DB
├── ref/                         ← JRA-VAN SDK ドキュメント（仕様書）
└── data/samples/
```
