# Codex CLI投入用：OpenClaw × Workspace Agents 本番完全版

あなたはOpenClaw/Clawstack統合担当AIです。以下のZIPをD:\Clawdbot_Docker_20260125\clawstack_v2\extensions\workspace_agents に配置した前提で作業してください。

## 最優先ゴール
既存OpenClaw環境を壊さず、QA/IATF/CSV監視/資料生成のWorkspace Agents Hubを追加してください。

## 必須調査
1. docker-compose.yml と override群を確認し、既存サービス・ポート・ネットワークを一覧化。
2. PORTAL_APPS.md / SOUL.md / TOOLS.md の有無と内容を確認。
3. 既存Portalカードと重複がないか確認。
4. 127.0.0.1バインド方針を維持。

## 実装ルール
- 既存ファイルは直接上書き禁止。必ずバックアップまたはappend patch。
- DBはREAD ONLYのみ。SQL Guardを必ず有効化。
- 外部送信はALLOW_EXTERNAL_SEND=falseを初期値にする。
- HITL承認なしにSlack/メール/外部API送信しない。
- ポート18080が使用済みなら別ポートに変更し、READMEに記録。

## 完了条件
- docker compose config が通る。
- workspace-agents-api が /health で ok を返す。
- sample CSVで /qa/analyze-csv が動く。
- 禁止SQLが /guard/sql-check で拒否される。
- PortalカードからHub入口が見える。
- 変更差分とリスクを REPORT_WORKSPACE_AGENTS.md にまとめる。
