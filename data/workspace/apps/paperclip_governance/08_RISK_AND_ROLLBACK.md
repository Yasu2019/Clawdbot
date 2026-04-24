# リスクとロールバック

## 主なリスク
1. 役割重複
   - Paperclip と OpenClaw の責務が曖昧になる
2. 予算管理の二重化
   - Langfuse / LiteLLM / Paperclip の数値が一致しないことがある
3. heartbeat 過多
   - 監視間隔を短くしすぎると無駄な起床が増える
4. ポート競合
   - 3100 を他用途が使っている可能性
5. 既存 compose 破壊
   - 直編集すると復旧が面倒

## 回避策
- overlay compose を使う
- 3110 で外部公開
- まず 1 company / 3 agents で始める
- 承認ゲートを最初から有効化する
- 予算は最小値から増やす

## ロールバック手順
```powershell
# overlay 停止
docker compose -f docker-compose.yml -f 04_DOCKER_COMPOSE.paperclip-overlay.yml down

# or container 単体停止
docker stop paperclip-local
docker rm paperclip-local
```

## ロールバック判定条件
- OpenClaw の通常業務が阻害される
- Langfuse の観測が乱れる
- Paperclip 上の task / approval 運用が現場に重すぎる
