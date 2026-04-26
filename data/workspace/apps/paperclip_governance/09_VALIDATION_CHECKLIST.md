# 検証チェックリスト

## 起動前
- [ ] 3100 / 3110 のポート使用状況確認
- [ ] Node.js 20+ 確認
- [ ] pnpm 9.15+ 確認
- [ ] 既存 compose のバックアップ取得

## 起動後
- [ ] `http://127.0.0.1:3110` にアクセスできる
- [ ] Paperclip health が正常
- [ ] company 作成ができる
- [ ] agent 追加ができる
- [ ] heartbeat が動く
- [ ] budget 上限で自動停止する
- [ ] approval gate が有効

## 既存統合確認
- [ ] OpenClaw 通常動作に影響なし
- [ ] LiteLLM 経由モデル呼び出しに影響なし
- [ ] Langfuse 観測に異常なし
- [ ] n8n 通知に異常なし

## Go / No-Go 判定
- [ ] 1週間は小規模運用
- [ ] 予算逸脱なし
- [ ] heartbeat miss の挙動確認済み
- [ ] 人間承認フローが現場負荷として許容範囲
