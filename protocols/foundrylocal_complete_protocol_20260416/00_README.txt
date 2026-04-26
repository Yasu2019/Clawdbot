Foundry Local × Ollama 併用評価・実装 完全版プロトコル
====================================================

このZIPは、Microsoft Foundry Local を既存の Ollama / LiteLLM / OpenClaw / n8n 環境に
「全面移行ではなく、比較用に横付けする」ための完全版プロトコルです。

目的
----
1. 既存 Ollama 主系を壊さない
2. Foundry Local を比較系として追加する
3. 評価結果に応じて 採用 / 保留 / 中止 を判断する
4. ロールバックを容易にする
5. Codex / Claude / 他AIエージェントへ、そのまま引き継げる

同梱ファイル
------------
00_README.txt
01_完全版_実装方針.md
02_環境前提チェックリスト.csv
03_導入手順_段階導入.md
04_LiteLLM_設定例.yaml
05_OpenClaw_接続方針.md
06_n8n_連携方針.md
07_比較試験プロンプト集.md
08_評価記録シート.csv
09_ロールバック手順.md
10_採用保留中止_判断基準.md
11_Codex_Claude_引継ぎプロンプト.txt
12_実装タスク分解表.csv
13_トラブルシュート.md
14_推奨ディレクトリ構成.txt
15_短時間サマリ.md
99_metadata.json

文字コード
----------
すべて UTF-8 BOM です。
Windows メモ帳 / Excel / VS Code での文字化け低減を狙っています。

推奨運用
--------
- まずは併用
- 主系は Ollama のまま
- Foundry Local は比較・将来の組み込み候補
- 明確な優位が無ければ保留

注意
----
本ZIPは「いきなり全面移行」を推奨しません。
既存資産（Ollama / Qwen / OpenClaw / LiteLLM / n8n）を守りながら、
比較評価し、導入価値がある時だけ前に進む方針です。