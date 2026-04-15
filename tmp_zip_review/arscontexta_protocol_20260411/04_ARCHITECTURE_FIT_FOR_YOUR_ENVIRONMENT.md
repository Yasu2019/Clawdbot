# あなたの環境との適合整理

## 既存構成（要点）
- OpenClaw
- LiteLLM
- Gemini / Claude / ローカルLLM
- Qdrant
- Paperless-ngx
- Docling
- SearXNG
- Langfuse
- Obsidian 関心あり
- 継続蓄積型の知識管理ニーズあり

## 役割分担の推奨
### arscontexta
- 人間が読む / 編集する markdown knowledge base
- 思考導線、wiki links、MOC、要約の再編
- Claude Code の継続文脈基盤

### 既存 RAG
- 大量文書検索
- PDF / OCR / 技術資料 / 監査資料 / 手順書の横断検索
- Qdrant ベースの retrieval

### OpenClaw / Antigravity / Codex / Claude
- 実行エージェント
- 設計・開発・変換・要約・自動化
- arscontexta や RAG を必要に応じて参照

## 重複を避ける原則
1. **原本保管**は Paperless / file library / 文書置き場
2. **検索主役**は RAG
3. **思考の再利用**は arscontexta
4. **実行**は Claude / Codex / OpenClaw

## 一番危険な失敗
- 同じ情報を RAG と Obsidian の両方へ無秩序に複製すること
- 自動生成ノートを監査せず蓄積し、リンクだけ増えること
- 既存 Vault へいきなり本番導入すること
