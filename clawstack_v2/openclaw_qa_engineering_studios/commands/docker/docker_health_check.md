# /docker_health_check

## 目的
Clawstack の Docker Compose サービス状態、ポート、ログ、ヘルスチェックを確認する。

## 推奨コマンド
```powershell
docker compose ps
docker compose logs --tail=100 openclaw-gateway
docker compose logs --tail=100 litellm
docker compose logs --tail=100 qdrant
```
