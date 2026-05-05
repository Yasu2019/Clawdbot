# existing_system_audit.md

## 目的
新規QMS監査アプリ実装前に、既存Dockerコンテナ・既存コード・既存文書解析基盤との重複や衝突を洗い出す。

## 監査対象
- docker-compose.yml / compose.*.yml
- Dockerfile 群
- 稼働中コンテナ
- 使用中ポート
- 既存 FastAPI / Streamlit / OCR / RAG / 文書比較系アプリ
- Paperless / Docling / ingest_watchdog / Qdrant / embedding サービス
- 既存 LLM gateway / proxy / UI

## チェック項目
### 1. 類似機能の有無
- 文書取込アプリが既にあるか
- OCRアプリが既にあるか
- 帳票解析機能が既にあるか
- 比較/差分検出機能が既にあるか
- 監査/内部監査アプリが既にあるか

### 2. 衝突確認
- ポート衝突
- DB名 / schema 名衝突
- volume 名衝突
- collection 名衝突
- queue / worker 名衝突
- 同一フォルダ監視重複

### 3. 再利用候補
- 既存 parser
- 既存 OCR
- 既存 embedding
- 既存 UI コンポーネント
- 既存認証/設定基盤

### 4. 実装方針結論
- 再利用
- 拡張
- ラッパー化
- 新規実装

## 成果物
- 類似機能一覧
- 衝突一覧
- 再利用案
- 統合案
- 新規実装必要箇所
