# SECRETS MANAGEMENT

## 禁止
- .env に秘密情報を平文保存
- Git 管理下に秘密鍵を置く
- AI に secrets 一覧を見せる

## 必須
- Docker secrets または OS の secure store を使う
- runtime injection を優先する
- テスト用ダミー鍵と本番鍵を分離する

## 例
```bash
docker secret create openai_key ./openai_key.txt
```
