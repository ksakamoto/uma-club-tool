# uma-club-tool

一口馬主の投資候補馬を効率よく探すための分析ツール。

募集馬一覧CSV（キャロット等）をアップロードし、JRA-VANデータを元にスコアリングして候補馬を提示するStreamlitアプリです。

---

## アーキテクチャ

```
[Windows / Parallels]
  C# console app (windows_fetcher_cs/)
    └─ JVLink COM でデータ取得
    └─ UM/HN/HS/CH/BR/RA/SE レコードをパース
    └─ SQLite (shared/jravan.db) に書き込み

[macOS]
  Streamlit app (app/)
    └─ shared/jravan.db を参照（read-only）
    └─ 募集馬CSV（キャロット等）をアップロード
    └─ rapidfuzz で馬名マッチング
    └─ スコアリングエンジン（プラグイン方式）
    └─ 候補馬ランキング表示
```

Parallels共有フォルダ経由でSQLiteファイルを共有する。

---

## 必要なもの

- **JRA-VAN サービスID**（有料契約が必要）
- **Windows環境**（Parallels可）— C#フェッチャーはJVLink COM依存のためWindows必須
- .NET 8 SDK（x86）
- Python 3.10+（Mac側）

---

## セットアップ

### 1. リポジトリをクローン

```bash
git clone <repo-url>
cd uma-club-tool
```

### 2. shared/ ディレクトリを準備

`shared/` にSQLiteファイルが配置される。初回は空でOK（フェッチャーが自動作成）。

```bash
mkdir -p shared
```

### 3. Windows側: C#フェッチャーのビルドと初回実行

```powershell
cd windows_fetcher_cs

# self-contained でビルド（x86ランタイム別途不要）
dotnet publish -r win-x86 --self-contained true -c Release

# 初回: マスターデータ全件取得（DIFN/BLDN/HOSN）
.\bin\Release\net8.0-windows\win-x86\publish\JVLinkFetcher.exe `
    --sid <YOUR_SID> `
    --db-path "..\shared\jravan.db" `
    --setup

# 初回: レースデータ全件取得（RACE）
.\bin\Release\net8.0-windows\win-x86\publish\JVLinkFetcher.exe `
    --sid <YOUR_SID> `
    --db-path "..\shared\jravan.db" `
    --race-setup `
    --race-from-year 2024
```

### 4. Mac側: Streamlitアプリの起動

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

ブラウザで `http://localhost:8501` にアクセスする。

---

## フェッチャー CLIオプション

| オプション | 説明 |
|---|---|
| `--sid` | JRA-VAN サービスID（必須） |
| `--db-path` | SQLiteパス（必須） |
| `--setup` | DIFN/BLDN/HOSN を全件取得（初回のみ） |
| `--with-racn` | RACE を差分取得（通常運用） |
| `--race-setup` | RACE を全件取得（初回のみ） |
| `--race-from-year YYYY` | RA/SE のフィルタ年（例: 2024） |
| `--years N` | マスターデータの fromDate を N年前に設定（デフォルト5） |

### 通常運用（差分更新）

```powershell
# マスター差分 + レース差分を同時取得
.\JVLinkFetcher.exe --sid <YOUR_SID> --db-path "..\shared\jravan.db" --with-racn
```

---

## SQLiteスキーマ

8テーブル。詳細は `windows_fetcher_cs/Db/schema.sql` を参照。

| テーブル | JVレコード | 用途 |
|---|---|---|
| horses | UM | 競走馬マスタ・3代血統・累計成績 |
| broodmares | HN | 繁殖馬マスタ |
| sales | HS | 競走馬市場取引価格 |
| trainer_yearly_stats | CH | 調教師マスタ（本年/前年/累計） |
| farm_yearly_stats | BR | 生産者マスタ（本年/累計） |
| races | RA | レース情報・グレードコード |
| horse_race_results | SE | 着順・調教師コード・獲得賞金 |
| fetch_log | — | 最終取得日・件数ログ |

---

## スコアリングプラグイン

新しいルールを追加するには `app/scoring/rules/` に `BaseRule` を継承したファイルを置くだけ。

```python
class BaseRule(ABC):
    name: str
    label: str

    @abstractmethod
    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        ...
```

重み設定は `config.yaml` で管理。

---

## ツール

```bash
# 調教師評価Excel生成（2025年分）
python3 -m app.tools.generate_trainer_eval \
    --db shared/jravan.db \
    --year 2025 \
    --output trainer_eval_2025.xlsx
```

---

## 注意事項

- JVLinkはWindows上でのみ動作（32bit COM）
- SQLiteファイルはParallels共有フォルダ経由で共有する
- `shared/` 以下のDBファイルはリポジトリに含まれていない（各自生成が必要）
- JRA-VAN SDKドキュメントは `ref/` ディレクトリに配置（別途取得）
