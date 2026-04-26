# 実装プロトコル: Image2 × OpenClaw QA資料自動生成

## 1. 追加する構成

- Portalカード: `/apps/image2_qa/index.html`
- Gateway API: `/api/image2-qa/generate`
- Prompt生成: RAG検索結果 + ユーザー入力 + テンプレート
- Image生成: OpenAI `gpt-image-2` adapter
- Evidence保存: prompt.json / source_summary.md / review_checklist.md / generated image

## 2. 導入順序

1. `openclaw_portal/apps/image2_qa/` を Portal の apps 配下へコピー
2. `openclaw_gateway/app/image2_qa_router.py` を Gateway API に追加
3. `config/image2_qa_config.yaml` を OpenClaw の config 配下へコピー
4. Gateway の FastAPI app に router を include
5. Portal のカード一覧に Image2 QA Auto を追加
6. `.env` に `OPENAI_API_KEY` を設定
7. Docker Compose 再起動
8. サンプルJSONで疎通確認

## 3. 運用ルール

- 初回生成は必ず `draft` 扱い
- 画像内テキストは人間が確認
- 顧客提出資料は承認者を記録
- RAG根拠が不足した場合は「根拠不足」と明記

## 4. 採用/保留判定

Codex/Antigravityは以下を確認してから導入:
- 既存Portalカードとパス衝突しないか
- Gateway routeが既存APIと衝突しないか
- 画像保存先が永続volumeにあるか
- OpenAI APIキーがログに出ないか
