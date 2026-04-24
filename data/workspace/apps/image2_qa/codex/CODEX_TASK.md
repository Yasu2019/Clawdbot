# Codex投入指示

D:\Clawdbot_Docker_20260125\clawstack_v2 に本ZIPを展開し、以下を自律実行してください。

1. 既存Portalカード、Gateway API、docker-compose.ymlを調査
2. `/apps/image2_qa/` と `/api/image2-qa/generate` の衝突有無を確認
3. 衝突なしなら導入。衝突ありなら別名ルートで提案
4. OpenAI APIキーは既存secret/.env運用に合わせ、絶対にログ出力しない
5. dry_runで疎通確認
6. 生成結果と変更ファイル一覧を報告

採用基準:
- 既存機能を壊さない
- loopback/ローカル運用を維持
- prompt/evidence/review checklistが保存される
