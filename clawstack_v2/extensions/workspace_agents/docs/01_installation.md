# 導入手順

1. ZIPを `D:\Clawdbot_Docker_20260125\clawstack_v2\extensions\workspace_agents` に展開。
2. `config/.env.example` を `.env` にコピーし、必要値を設定。
3. 既存composeを調査。
4. 追加composeで起動。

```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2
docker compose -f docker-compose.yml -f extensions/workspace_agents/docker-compose.workspace-agents.yml config
docker compose -f docker-compose.yml -f extensions/workspace_agents/docker-compose.workspace-agents.yml up -d workspace-agents-api
curl http://127.0.0.1:18080/health
```
