# OpenClaw × Manus × Instagram 安全統合アーキテクチャ

## 基本思想

Manusは外部SNS操作・生成支援の役割。  
OpenClawは安全管理、承認、ログ、プロンプト管理、収益導線設計の役割。  
Claude/Codexは採用判断と実装前レビューの役割。

## 推奨構成

```text
[User]
  |
  v
[OpenClaw Portal]
  |-- Strategy Card
  |-- Manus Prompt Generator
  |-- Review Queue
  |-- KPI Dashboard
  |-- Weekly Report
  |
  v
[Manus Instagram Connector]
  |-- Ideate
  |-- Generate
  |-- Publish draft or post after approval
  |-- Pull insights
  |
  v
[Instagram Professional Account]
```

## データフロー

1. OpenClawで投稿テーマと制約を作る
2. Manusに競合分析や投稿案生成を依頼する
3. Manus結果をOpenClawに戻す
4. OpenClawで安全チェックする
5. 人間が承認する
6. ManusまたはInstagram公式予約機能で投稿する
7. インサイトを取得する
8. OpenClawで週次レポート化する

## OpenClaw側に保存するデータ

保存してよいもの:

- 投稿案
- 承認ステータス
- 投稿日
- 投稿URL
- リーチ、保存、シェア、コメント数などの集計値
- 週次レポート
- プロンプト履歴
- NG理由
- 改善案

保存しないもの:

- Instagramパスワード
- Manusログイン情報
- Metaアクセストークンの平文
- 個人のDM本文
- 非公開の個人情報
- 無断収集した競合データ

## DB設計案

初期はDB統合しない。CSV/JSON/Markdownで十分。  
DB化は、Claudeが安全性を確認してから検討する。

### 初期ファイル保存案

```text
data/
  sns/
    drafts/
    approved/
    posted/
    insights/
    weekly_reports/
```

## Portalカード案

`09_configs/portal_card.manus_instagram.json` を参照。

## 競合ポート確認

このZIPは新規コンテナを立ち上げる前提ではありません。  
Portal統合が必要な場合のみ、既存ポートと競合しないか確認してください。

代表的な既存ポート候補:

- 5432: PostgreSQL
- 6379: Redis
- 6333: Qdrant
- 9000/9001: Minio
- 11434: Ollama
- 8081: drawio
- 8083: Label Studio候補

