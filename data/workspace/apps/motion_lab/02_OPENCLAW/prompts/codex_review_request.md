# Codexレビュー依頼書

このZIPを、既存の OpenClaw / Clawstack / Portal 環境へ統合すべきか評価してください。

重点確認：
1. 既存Portalカードや既存3Dアプリと競合しないか
2. docker-compose.yml へ追加する必要があるか
3. 既存OpenClaw Gateway / MCP / n8n / Node-RED / Blender連携と衝突しないか
4. セキュリティ上、ブラウザ自動ログインや有料API使用が危険でないか
5. ファイル上書き事故を防げているか
6. Windows + WSL2 + Docker Desktop + GMKtec K10 環境で現実的に動くか
7. ローカルLLM優先、クラウドAPI最小の設計になっているか
8. 既存のIATF教育動画、3Dモデル/GD&Tビューア、Blender自動生成資産と融合すべきか、別アプリとして分離すべきか

出力形式：
- 採用可否: 採用 / 条件付き採用 / 不採用
- 統合方針: 既存アプリ融合 / 新規Portalカード / 実験フォルダ隔離
- 危険箇所
- 修正パッチ案
- 実行前チェックリスト
