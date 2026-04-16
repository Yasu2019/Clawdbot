ZELOD IN AI Scanner 導入プロトコル一式
====================================

このZIPは、Mozilla系のAI脆弱性スキャン思想を、既存のローカルAI基盤
（OpenClaw / n8n / RAG / Local LLM）へ安全に取り込むための、
文字化けし難い handoff 用プロトコルです。

想定用途
--------
1. Codex CLI / Claude Code / 他のAIエージェントへそのまま渡す
2. 採用・部分採用・保留の判断をさせる
3. 既存の Portal / Docker Compose / OpenClaw 構成との衝突確認をさせる
4. AI特有の脆弱性テスト（Prompt Injection, Jailbreak, Data Exfiltration）を
   実務導入するための叩き台にする

使い方（推奨）
--------------
1. まず「02_AGENT_PROMPT_CODEX.txt」または「03_AGENT_PROMPT_CLAUDE.txt」を
   受け取り側AIへ貼り付ける
2. ZIP内の残りファイルを参照させる
3. 受け取り側AIに、以下を必ず実施させる
   - 既存構成の衝突確認
   - 完全採用 / 部分採用 / 保留 の三択判断
   - 判断理由の明文化
   - 差分設計
   - セキュリティテストの最小実装案提示

文字コード
----------
主要テキストは UTF-8 with BOM です。
CSV も UTF-8 with BOM です。

同梱ファイル
------------
00_README_FIRST.txt
01_PROTOCOL_MASTER.md
02_AGENT_PROMPT_CODEX.txt
03_AGENT_PROMPT_CLAUDE.txt
04_IMPLEMENTATION_CHECKLIST.md
05_SECURITY_TEST_MATRIX.csv
06_ADOPTION_DECISION_TEMPLATE.md
07_MINIMAL_GUARD_ARCHITECTURE.md
08_DOCKER_COMPOSE_SNIPPET.yml
09_RUNBOOK_JP.txt

注意
----
このZIPは、動画要約ベースの導入プロトコルであり、
実在リポジトリや実際のCLI仕様を保証するものではありません。
実装前に、受け取り側AIまたは人が必ず一次情報を確認してください。
