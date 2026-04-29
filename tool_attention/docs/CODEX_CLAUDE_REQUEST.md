# Codex / Claude への依頼文

以下の方針で、既存ClawstackにTool Attention完全自律版を差分統合してください。

- 既存docker-compose.ymlを直接破壊しない
- docker-compose.tool-attention.ymlを追加合成する
- OpenClaw本体の「LLMへ全ツール定義を注入する処理」を、Tool Router経由へ置換する
- 大規模変更前にGitHubへバックアップブランチを作成する
- Portalへ tool_attention/index.html をカード追加する
- Langfuseへ以下を記録する
  - selected_tools
  - blocked_tools
  - tool_token_estimate_before/after
  - tool_success
  - learning_multiplier
- SQLツールはSELECT専用ガードを入れる
- MQTT/Node-RED/GitHub/Paperlessは接続状態がFalseなら選択候補から除外する
- 既存カード、Observability Hub、Tolerance Center、Kinematics Hubとは競合させない
