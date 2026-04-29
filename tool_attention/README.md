# Tool Attention × Clawstack 完全自律版

目的: MCP税を削減し、OpenClaw/Clawstackのツール選択を「検索・状態判定・遅延ロード・実行結果学習・異常検知」で自律最適化する後付けパッケージです。

## 追加される機能
- Qdrant tool_registry によるツール要約検索
- State-Aware Gating による実行不能ツール除外
- Lazy Schema Loader による必要時だけスキーマ注入
- Tool Outcome Learning による成功/失敗スコア学習
- Anomaly Guard による異常ツール呼び出し検知
- Auto Rollback Hint による危険操作前の停止指示
- Langfuse観測項目テンプレ
- Portalカード監視UI

## 導入方針
既存composeを直接書き換えず、docker-compose.tool-attention.yml を追加して起動します。

```bash
cd <clawstack-unified>
cp -r tool_attention_autonomous_clawstack ./tool_attention
cp tool_attention/docker-compose.tool-attention.yml ./docker-compose.tool-attention.yml
docker compose -f docker-compose.yml -f docker-compose.tool-attention.yml up -d --build
```

## ポート
- tool-router: 8090
- lazy-loader: 8091
- learning-store: 8092
- anomaly-guard: 8093
- portal-card: 8088/apps/tool_attention/index.html に配置想定

## 安全原則
- SQLはread-onlyのみ
- GitHubバックアップ前の大規模変更は禁止
- state gatingで未接続サービスのツールを除外
- anomaly guardで高リスクツール連続実行をブロック
