# OpenClaw 視覚AI品質検査ライン 完全統合版

作成日: 2026-04-28

## 目的

このZIPは、OpenClaw / Clawstack 環境に「視覚AI × 品質検査 × 現場IoTデータ」を追加するための本番導入テンプレートです。

対象例:

- プレス品のキズ、バリ、打痕、シミムラ、変形、付着、めくれ
- 樹脂成形品の欠け、ヒケ、変形、汚れ
- レベラー後の外観異常
- 洗浄後の油残り、シミ
- SPM、ショット数、チョコ停止回数などの設備データとの相関

## 設計方針

- 既存OpenClawを壊さない追加配置型
- ローカル優先、API消費最小
- 人間承認前提
- AIの誤判定を前提に二重チェック
- 監査ログ、根拠、画像、センサーデータを保存
- Portalカードからアクセス可能
- Node-RED / MQTT / Dropbox CSV運用と疎結合

## ディレクトリ構成

```text
openclaw_vision_quality_inspection_full/
  README.md
  docker-compose.vision.yml
  .env.example
  portal/
  backend/
  frontend/
  nodered/
  mqtt/
  rag/
  docs/
  prompts/
  scripts/
  sample_data/
  audit/
```

## 最短導入

```bash
cd /opt/clawstack
unzip openclaw_vision_quality_inspection_full.zip -d ./modules/vision_quality

cd ./modules/vision_quality
cp .env.example .env

docker compose -f docker-compose.vision.yml up -d
```

## Portal追加

`portal/cards/vision_quality_card.json` を既存Portalのカード定義に追加してください。

推奨URL:

```text
http://localhost:8088/apps/vision_quality/index.html
```

API:

```text
http://localhost:18789/api/vision-quality
```

## 注意

このテンプレートは「現場投入の骨格」です。実運用前に以下を必ず実施してください。

1. 良品画像、不良画像を自社データで登録
2. 不良分類名を社内用語に合わせる
3. 誤判定時の人間レビュー手順を確認
4. 保存先、個人情報、顧客図面の扱いを確認
5. AI判定を最終判定にしない
