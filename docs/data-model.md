# データモデル

> **Shift-JIS パースの詳細・仕様変更の経緯は `CLAUDE.md` を参照。**
> **フィールド定義の 1 次ソース: `ref/JRA-VAN Data Lab. SDK Ver4.9.0.2/ドキュメント/JV-Data仕様書_4.9.0.1.xlsx`**

## DataSpec と対応レコード種別

| DataSpec | 説明 | 含まれるレコード種別 |
|---|---|---|
| **DIFN** | 蓄積情報（旧: DIFF） | UM / CH / BR / KS / BN / RC / RA / SE |
| **BLDN** | 血統情報（旧: BLOD） | HN / SK / BT |
| **HOSN** | 競走馬市場取引価格（旧: HOSE） | HS |

> **2023年8月仕様変更**: 旧 DataSpec（DIFF/BLOD/HOSE）は廃止扱い。
> 繁殖登録番号 8→**10byte**、生産者コード 6→**8byte**、生産者名 70→**72byte** に拡張。
> 必ず新 DataSpec（N付き）を使用すること。

## jravan.db — アプリ用 DB（5テーブル）

スコアリングと候補馬検索に特化した最小構成。

| テーブル | レコード種別 | 説明 | PK |
|---|---|---|---|
| `horses` | UM | 競走馬マスタ・3代血統・累計成績 | horse_code |
| `broodmares` | HN | 繁殖馬マスタ | mare_code |
| `sales` | HS | 競走馬市場取引価格（セリ） | (horse_code, market_code, sale_start_date) |
| `trainer_yearly_stats` | CH | 調教師年次成績（本年/前年/累計） | (trainer_code, period_year, period_type) |
| `farm_yearly_stats` | BR | 生産者年次成績（本年/累計） | (farm_code, period_year, period_type) |

## jravan_raw.db — 探索用 DB（16テーブル）

上記5テーブルに加え、全 DataSpec カバーの追加テーブル。

| テーブル | レコード種別 | 説明 | PK | 参考件数 |
|---|---|---|---|---|
| `races` | RA | レース詳細 | (kaisai_year, kaisai_date, venue_code, kai, nichi, race_no) | ~150 |
| `horse_race_results` | SE | 馬毎レース情報 | (...同上..., horse_no) | ~1,500 |
| `jockeys` | KS | 騎手マスタ | jockey_code | ~1,900 |
| `jockey_yearly_stats` | KS（繰返） | 騎手年次成績（本年/前年/累計） | (jockey_code, period_year, period_type) | ~5,700 |
| `owners` | BN | 馬主マスタ | owner_code | ~10,000 |
| `owner_yearly_stats` | BN（繰返） | 馬主年次成績（本年/累計） | (owner_code, period_year, period_type) | ~20,000 |
| `progeny` | SK | 産駒マスタ・3代血統 | horse_code | ~40,000 |
| `record_times` | RC | レコードマスタ | (record_type_code, kaisai_year, kaisai_date, venue_code, kai, nichi, race_no, tokubetsu_no) | ~2,100 |
| `pedigree_lines` | BT | 系統情報 | mare_code | ~90 |
| `unknown_records` | 未知種別 | 未対応種別の raw テキスト（先頭200文字） | — | 0 |
| `fetch_log` | — | 最終取得日・書き込み件数 | table_name | — |

> **races / horse_race_results が少ない理由**: DIFN DataSpec は主にマスタデータを提供する。
> フルのレース成績が必要な場合は RACE/RACN DataSpec の追加が必要（未実装）。

## レコード種別 ID と仕様書の対応（紛らわしいもの）

| 種別ID | 仕様書上の名称 | 備考 |
|---|---|---|
| RA | レース詳細（「２．」） | RC とよく混同される |
| RC | レコードマスタ（「２１．」） | Race ではなく Record |
| SK | 産駒マスタ（「１９．」） | Sire/Stallion の成績ではない（産駒一覧） |
| HS | 競走馬市場取引価格（「６．」） | CS（コース情報）と混同しないこと |

## 主な変換ルール

| フィールド種別 | 変換内容 |
|---|---|
| 賞金（UM / CH / BR / RA / SE 等） | 生値 ÷ 10 → 万円（REAL 型） |
| 賞金（HS） | 生値 ÷ 10,000 → 万円（REAL 型） |
| 日付 YYYYMMDD | "YYYY-MM-DD" 形式に変換、00000000 → NULL |
| CH / KS の繰返し成績（3期） | 本年 / 前年 / 累計 を別行展開（`period_type` カラム） |
| BR / BN の繰返し成績（2期） | 本年 / 累計 を別行展開（`period_type` カラム） |
| 生産者コード | 2023年8月以降は 8byte（旧 6byte） |
| 繁殖登録番号 | 2023年8月以降は 10byte（旧 8byte） |
| 空文字列フィールド | NULL として保存（`NullIfEmpty` ヘルパー） |

## パース方式

全パーサーは Shift-JIS バイトベースで動作する。
JVLink COM は UTF-16 string を返すが、フィールド位置は仕様書の 1 始まりバイト位置に従う。

```csharp
// RecordParser.F(b, pos, len): b[pos-1] から len バイト切り出して Trim
var bytes = Encoding.GetEncoding(932).GetBytes(rec);  // UTF-16 → cp932
var field = Encoding.GetEncoding(932).GetString(bytes, pos - 1, len).Trim();
```

繰返しセクションの絶対バイト位置:
```
absolute_1indexed = sectionStart + (relativePos - 1)
```
