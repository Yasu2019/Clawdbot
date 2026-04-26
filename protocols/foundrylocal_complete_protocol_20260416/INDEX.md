# Foundry Local × Ollama 併用評価・実装（完全版プロトコル / 2026-04-16）

このフォルダは、`FoundryLocal_完全版プロトコル_UTF8BOM_20260416.zip` を **そのまま展開** した内容です。
主系は Ollama を維持し、Foundry Local は比較系として横付けする方針（全面移行しない）を前提にしています。

## 入口（まず読む）
- `15_短時間サマリ.md`
- `01_完全版_実装方針.md`
- `03_導入手順_段階導入.md`
- `09_ロールバック手順.md`
- `10_採用保留中止_判断基準.md`

## テンプレ・設定例
- `02_環境前提チェックリスト.csv`
- `04_LiteLLM_設定例.yaml`（※サンプル。既存 `docker-compose.yml` 等は変更しない）
- `07_比較試験プロンプト集.md`
- `08_評価記録シート.csv`
- `12_実装タスク分解表.csv`
- `13_トラブルシュート.md`
- `14_推奨ディレクトリ構成.txt`
- `11_Codex_Claude_引継ぎプロンプト.txt`

## 本リポジトリ側の最小ハーネス（read-only）
- `scripts/hybrid_eval/hybrid_eval.py`（Ollama 主系 + Foundry 比較系の任意コマンド）

