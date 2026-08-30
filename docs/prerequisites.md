# 前提条件・セットアップ

> **詳細な注意点・ハマりポイントは `CLAUDE.md` を参照。**

## JRA-VAN Data Lab 加入

1. https://jra-van.jp/dlb/ で加入手続き（有料サービス）
2. 加入後に **SID（ユーザーID）** が発行される
3. SID は `--sid` 引数で JVLinkFetcher に渡す

## JVLink のインストール（Windows のみ）

1. JRA-VAN Data Lab のサイトから **JVLink** をダウンロード・インストール
2. インストール後に SID を登録
3. 32bit COM コンポーネントとしてシステムに登録される

> JVLink は Windows 専用。Mac 上では動作しない。

## Windows 開発環境

| ツール | 用途 | 備考 |
|---|---|---|
| .NET 8 SDK (x86) | ビルド | **x86 必須**（JVLink が 32bit COM のため） |
| Visual Studio 2022 または dotnet CLI | ビルド・デバッグ | CLI だけでも可 |
| PowerShell | ビルド・実行スクリプト | `<SID>` は `<` がリダイレクトと解釈されるため注意 |

### .NET 8 SDK の確認

```powershell
dotnet --list-sdks
# 8.0.x が存在すること

# self-contained ビルドは win-x86 ランタイムを内包するため
# x86 ランタイムの別途インストールは不要
```

## macOS 環境

| ツール | 用途 |
|---|---|
| DB Browser for SQLite | jravan.db / jravan_raw.db を GUI でブラウズ |
| sqlite3 (CLI) | データ確認クエリ |
| Python 3.11+（将来） | Streamlit アプリ（app/ ディレクトリ、未実装） |

## Parallels 共有フォルダ設定

Parallels の「共有フォルダ」でリポジトリを共有することで、
Windows フェッチャーと Mac の SQLite 参照を同一ファイルで実現する。

1. Parallels 設定 → 共有フォルダ → macOS のリポジトリフォルダを追加
2. Windows 側では `Y:\Documents\Workspaces\uma-club-tool\` などでアクセス可能になる
3. `shared/` ディレクトリに DB ファイルを配置する
4. Mac 側は SQLite を **read-only** で参照（WAL モードのため競合なし）

> `Y:\` のドライブレターは Parallels の設定によって異なる場合がある。
