# INCIDENT RESPONSE

## 初動
1. 当該コンテナ停止
2. 外部通信遮断
3. ログ退避
4. 変更差分確認
5. 認証情報ローテーション

## 推奨手順
```bash
docker compose down
```

```bash
git diff
```

## 確認事項
- 外部送信痕跡はないか
- 不審な package install はないか
- forbidden command が呼ばれていないか
- ログ欠損はないか
