# INCIDENT_RUNBOOK.md

## 障害記録テンプレート

- 発生日時:
- 検知日時:
- 記録者:
- 障害ID:
- 対象サービス:
- 影響範囲:
- 症状:
- 重大度:
- 発生契機:
- 初動対応:
- 原因:
- 暫定対処:
- 恒久対策:
- 復旧日時:
- 再発防止:
- 参考ログ/証跡:
- 備考:

## 禁止事項

- 根拠が取れる前に、破壊的操作を実行しない。

```bash
docker compose down -v
```

```bash
docker system prune -a
```

- 影響範囲を確認せずにコンテナ再作成、イメージ再ビルド、設定変更をしない。
- ログ、メトリクス、ディスク使用量を確認する前に推測だけで原因を断定しない。
- 障害中に複数の変更を同時投入しない。
- 一時対応と恒久対応を混同しない。
- 証跡を残さずに復旧作業を進めない。

## 目的

Docker コンテナ群で障害が発生した際に、影響範囲の確認、初動、切り分け、復旧、記録を一貫して実施する。

## 共通初動

1. 影響範囲を確認する。
2. コンテナ状態、リソース逼迫、ディスク残量を確認する。
3. 直近ログを採取する。
4. 復旧操作の前に障害記録を開始する。

### 確認コマンド

```bash
docker compose ps
```

```bash
docker ps -a
```

```bash
docker stats --no-stream
```

```bash
df -h
```

```bash
docker compose logs --tail=200
```

## 基本切り分け

### 1. コンテナ停止・再起動多発

確認コマンド

```bash
docker compose ps
```

```bash
docker ps -a
```

```bash
docker compose top
```

```bash
docker compose logs --tail=200
```

見るポイント

- `Exited` の終了コード
- `Restarting` の継続有無
- OOMKilled 相当の兆候
- 起動コマンド、環境変数、依存先接続失敗

### 2. アプリ応答なし

確認コマンド

```bash
docker compose ps
```

```bash
docker compose logs --tail=200
```

```bash
docker compose top
```

見るポイント

- ポート待受の有無
- ヘルスチェック失敗
- upstream / DB / API 接続失敗
- タイムアウト、例外、デッドロック兆候

### 3. ディスク逼迫

確認コマンド

```bash
df -h
```

```bash
docker system df
```

```bash
docker volume ls
```

```bash
docker images
```

見るポイント

- Docker データ領域の逼迫
- 巨大ログ、未使用イメージ、肥大化した volume
- 一時ファイルの残留

### 4. メモリ・CPU逼迫

確認コマンド

```bash
docker stats --no-stream
```

```bash
docker compose ps
```

```bash
docker compose logs --tail=200
```

見るポイント

- 特定コンテナの CPU / MEM スパイク
- OOMKill
- リトライループ
- ワーカープロセス暴走

### 5. ネットワーク・名前解決異常

確認コマンド

```bash
docker network ls
```

```bash
docker compose ps
```

```bash
docker compose exec clawdbot-gateway sh -lc "getent hosts redis postgres litellm ollama qdrant open_notebook"
```

```bash
docker compose exec clawdbot-gateway sh -lc "curl -I http://litellm:4000"
```

補足

- `ping` や `nslookup` が無い場合は `getent hosts` で名前解決を確認する。
- HTTP 系サービスは `curl -I` で疎通確認する。

見るポイント

- 同一ネットワーク参加有無
- サービス名解決可否
- 外部接続断
- プロキシ、DNS、FW の影響

## 復旧手順

### レベル1: 非侵襲の確認のみ

```bash
docker compose ps
```

```bash
docker compose logs --tail=200
```

```bash
docker stats --no-stream
```

### レベル2: 単一サービス再起動

```bash
docker compose restart <service_name>
```

確認コマンド

```bash
docker compose ps <service_name>
```

```bash
docker compose logs --tail=200 <service_name>
```

### レベル3: 単一サービス再作成

```bash
docker compose up -d --force-recreate <service_name>
```

確認コマンド

```bash
docker compose ps <service_name>
```

```bash
docker compose logs --tail=200 <service_name>
```

### レベル4: 全体復旧

```bash
docker compose up -d
```

確認コマンド

```bash
docker compose ps
```

```bash
docker compose logs --tail=200
```

## ログ採取

```bash
docker compose logs --tail=500 > incident_logs.txt
```

```bash
docker stats --no-stream > incident_stats.txt
```

```bash
df -h > incident_disk.txt
```

```bash
docker compose ps > incident_ps.txt
```

## 復旧判定

以下をすべて満たしたら復旧とみなす。

- 対象サービスが `Up` で安定している
- エラーログが連続発生していない
- ヘルスチェックが正常
- ユーザー影響機能が疎通している
- リソース使用率が異常値に戻っていない

確認コマンド

```bash
docker compose ps
```

```bash
docker compose logs --tail=200
```

```bash
docker stats --no-stream
```

## 事後対応

- 障害記録テンプレートを埋める
- 原因、暫定対処、恒久対策を分離して整理する
- 再発防止のために監視項目、閾値、手順不足を更新する
- 必要なら runbook を改訂する

## 追記ルール

- 事実、時刻、実行コマンド、結果を時系列で残す
- 推測は推測と明記する
- 復旧後に「なぜ検知が遅れたか」も記録する
- 同種障害へ再利用できる粒度で残す

---

## サービス別手順

## clawdbot-gateway

### 先に確認する依存先

- redis
- postgres
- litellm
- ollama
- qdrant
- open_notebook

### 症状

- API 応答なし
- 5xx 多発
- downstream 接続失敗
- 起動後すぐ再起動する
- 18789 または 18791 に疎通できない

### 影響範囲

- 外部入口全体
- UI / API / MCP 経由の呼び出し
- LLM 連携の上流全体

### 確認コマンド

```bash
docker compose ps clawdbot-gateway
```

```bash
docker compose logs --tail=300 clawdbot-gateway
```

```bash
docker compose top clawdbot-gateway
```

```bash
curl -I http://localhost:18789
```

```bash
curl -I http://localhost:18791
```

```bash
docker compose exec clawdbot-gateway sh -lc "getent hosts redis postgres litellm ollama qdrant open_notebook"
```

### ログ確認箇所

- アプリケーション起動ログ
- 依存先接続失敗ログ
- 認証エラー
- タイムアウト、例外スタックトレース

### 復旧手順

```bash
docker compose logs --tail=300 clawdbot-gateway
```

```bash
docker compose ps redis postgres litellm ollama qdrant open_notebook
```

```bash
docker compose restart clawdbot-gateway
```

```bash
docker compose ps clawdbot-gateway
```

```bash
curl -I http://localhost:18789
```

```bash
curl -I http://localhost:18791
```

必要時のみ:

```bash
docker compose up -d --force-recreate clawdbot-gateway
```

### 復旧完了条件

- `Up` で安定
- 18789 または 18791 が正常応答
- 依存先接続エラーが収束
- 5xx が止まる

### 再起動を慎重にすべき条件

- 大量のリクエスト処理中
- 長時間ジョブの中継中
- downstream 障害が主因で gateway 自体は健全
- セッションやストリームを保持している

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream clawdbot-gateway
```

```bash
df -h
```

### 再発防止の確認項目

- readiness / liveness の妥当性
- upstream タイムアウト設定
- 再試行回数と circuit breaker 設定
- 依存先障害時の degrade 動作

## redis

### 先に確認する依存先

- ホストディスク
- 永続化先 volume
- clawdbot-gateway
- n8n
- paperless

### 症状

- セッション消失
- キュー詰まり
- 接続拒否
- レイテンシ増大

### 影響範囲

- キャッシュ
- ジョブキュー
- セッション管理
- 一部 API の性能劣化

### 確認コマンド

```bash
docker compose ps redis
```

```bash
docker compose logs --tail=300 redis
```

```bash
docker compose exec redis redis-cli ping
```

```bash
docker compose exec redis redis-cli info
```

```bash
docker compose exec redis redis-cli info memory
```

### ログ確認箇所

- RDB / AOF 書き込み失敗
- メモリ不足
- 接続数超過
- 永続化失敗

### 復旧手順

```bash
docker compose exec redis redis-cli ping
```

```bash
docker compose restart redis
```

```bash
docker compose exec redis redis-cli ping
```

```bash
docker compose exec redis redis-cli info memory
```

### 復旧完了条件

- `PONG` 応答
- 接続数とメモリ使用量が安定
- キュー処理再開
- アプリ側の Redis エラー収束

### 再起動を慎重にすべき条件

- メモリ上データが重要
- AOF / RDB 破損が疑われる
- バックグラウンド保存中
- queue backlog が大きい

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream redis
```

```bash
docker compose exec redis redis-cli info stats
```

```bash
df -h
```

### 再発防止の確認項目

- maxmemory と eviction policy
- AOF / RDB 永続化設定
- 接続プール設定
- キー肥大化監視

## postgres

### 先に確認する依存先

- ホストディスク
- 永続化先 volume
- clawdbot-gateway
- n8n
- paperless

### 症状

- DB 接続失敗
- クエリ遅延
- 起動失敗
- WAL 関連エラー

### 影響範囲

- 永続データ全般
- 認証、設定、履歴、ワークフロー
- 複数サービスの同時障害

### 確認コマンド

```bash
docker compose ps postgres
```

```bash
docker compose logs --tail=300 postgres
```

```bash
docker compose exec postgres pg_isready
```

```bash
docker compose exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select now();"'
```

```bash
docker compose exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from pg_stat_activity;"'
```

### ログ確認箇所

- recovery / crash recovery
- checkpoint 遅延
- disk full
- too many connections
- relation / WAL / fsync エラー

### 復旧手順

```bash
docker compose exec postgres pg_isready
```

```bash
docker compose restart postgres
```

```bash
docker compose exec postgres pg_isready
```

```bash
docker compose exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select now();"'
```

### 復旧完了条件

- `pg_isready` 正常
- 主要クエリ成功
- 接続数安定
- 依存サービスの DB エラー解消

### 再起動を慎重にすべき条件

- 長時間トランザクション実行中
- VACUUM / migration / restore 中
- crash recovery 中
- ディスク逼迫が未解消

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream postgres
```

```bash
df -h
```

```bash
docker compose exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select * from pg_stat_bgwriter;"'
```

### 再発防止の確認項目

- connection pool 上限
- backup / restore 手順
- WAL とディスク容量監視
- slow query 監視

## ollama

### 先に確認する依存先

- モデル保存先 volume
- ホストディスク
- litellm
- clawdbot-gateway

### 症状

- モデル応答なし
- モデルロード失敗
- 推論が極端に遅い
- pull 中断またはハング
- 11434 に疎通できない

### 影響範囲

- ローカル LLM 利用機能
- 埋め込み / 推論依存機能
- AI ワークフロー全般

### 確認コマンド

```bash
docker compose ps ollama
```

```bash
docker compose logs --tail=300 ollama
```

```bash
curl http://localhost:11434/api/tags
```

```bash
curl http://localhost:11434/api/version
```

```bash
docker compose exec ollama ollama list
```

### ログ確認箇所

- モデルロード失敗
- GPU / CPU / メモリ不足
- pull 停滞
- ファイル破損

### 復旧手順

```bash
curl http://localhost:11434/api/tags
```

```bash
docker compose restart ollama
```

```bash
curl http://localhost:11434/api/version
```

```bash
docker compose exec ollama ollama list
```

### 復旧完了条件

- 11434 が正常応答
- 必要モデルが一覧に存在
- 推論リクエストが成功
- モデルロード失敗が止まる

### 再起動を慎重にすべき条件

- 大きなモデルのロード中
- pull 実行中
- 他サービスが高頻度で依存中
- モデルキャッシュ破損が疑われる

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream ollama
```

```bash
df -h
```

```bash
docker compose exec ollama ollama list
```

### 再発防止の確認項目

- モデル保存先容量
- pull 監視手順
- モデル事前配置
- タイムアウトとフォールバック先

## litellm

### 先に確認する依存先

- ollama
- 外部 LLM API
- clawdbot-gateway

### 症状

- モデルプロキシ応答なし
- 認証失敗
- upstream API エラー
- レート制限多発
- 4000 に疎通できない

### 影響範囲

- すべての LLM API 中継
- モデル切替機能
- アプリの推論依頼全般

### 確認コマンド

```bash
docker compose ps litellm
```

```bash
docker compose logs --tail=300 litellm
```

```bash
curl -I http://localhost:4000
```

```bash
docker compose exec clawdbot-gateway sh -lc "curl -I http://litellm:4000"
```

### ログ確認箇所

- upstream 4xx / 5xx
- API キー読み込み失敗
- ルーティング設定ミス
- request timeout

### 復旧手順

```bash
docker compose logs --tail=300 litellm
```

```bash
docker compose ps ollama
```

```bash
docker compose restart litellm
```

```bash
curl -I http://localhost:4000
```

### 復旧完了条件

- 4000 が正常応答
- upstream への到達確認
- 主要モデル呼び出し成功
- 4xx / 5xx が収束

### 再起動を慎重にすべき条件

- 多数の推論リクエスト中継中
- upstream 側障害が主因
- 一時トークンや設定再読込の影響が不明

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream litellm
```

```bash
df -h
```

### 再発防止の確認項目

- API キー管理
- upstream 別のレート制限監視
- フォールバック設定
- 失敗時リトライ方針

## qdrant

### 先に確認する依存先

- 永続化先 volume
- ホストディスク
- clawdbot-gateway

### 症状

- ベクタ検索失敗
- collection 読み込み失敗
- 書き込みエラー
- 応答遅延
- 6333 に疎通できない

### 影響範囲

- RAG 検索
- 類似検索
- 埋め込み依存ワークフロー

### 確認コマンド

```bash
docker compose ps qdrant
```

```bash
docker compose logs --tail=300 qdrant
```

```bash
curl http://localhost:6333/collections
```

```bash
curl http://localhost:6333/healthz
```

### ログ確認箇所

- collection open error
- storage error
- WAL / segment error
- out of memory

### 復旧手順

```bash
curl http://localhost:6333/healthz
```

```bash
docker compose restart qdrant
```

```bash
curl http://localhost:6333/collections
```

### 復旧完了条件

- 6333 の health 正常
- 必要 collection 参照可能
- 検索 API 成功
- 書き込みエラーが止まる

### 再起動を慎重にすべき条件

- インデックス構築中
- 大量 ingest 実行中
- ストレージ破損が疑われる

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream qdrant
```

```bash
df -h
```

### 再発防止の確認項目

- collection バックアップ
- storage 容量監視
- ingest レート制御
- メモリ上限見直し

## n8n

### 先に確認する依存先

- postgres
- redis
- clawdbot-gateway

### 症状

- ワークフロー停止
- UI 応答なし
- ジョブ失敗増加
- webhook 不達
- 5679 に疎通できない

### 影響範囲

- 自動化処理全般
- webhook 起点処理
- 定期ジョブ

### 確認コマンド

```bash
docker compose ps n8n
```

```bash
docker compose logs --tail=300 n8n
```

```bash
curl -I http://localhost:5679
```

```bash
docker compose exec clawdbot-gateway sh -lc "curl -I http://n8n:5679"
```

### ログ確認箇所

- workflow execution failed
- DB 接続失敗
- queue / webhook 関連エラー
- credential 読み込み失敗

### 復旧手順

```bash
docker compose logs --tail=300 n8n
```

```bash
docker compose ps postgres redis
```

```bash
docker compose restart n8n
```

```bash
curl -I http://localhost:5679
```

### 復旧完了条件

- 5679 が正常応答
- UI 正常表示
- webhook 受信正常
- 主要 workflow 実行成功

### 再起動を慎重にすべき条件

- 長時間 workflow 実行中
- 待ち状態ジョブが多い
- DB 障害が未解決

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream n8n
```

```bash
df -h
```

### 再発防止の確認項目

- workflow の再実行性
- queue backend 健全性
- credential 管理
- 失敗通知設定

## paperless

### 先に確認する依存先

- postgres
- redis
- 文書保存 volume
- consume ディレクトリ

### 症状

- 文書 UI にアクセスできない
- OCR / 消費処理が止まる
- 文書取り込み遅延
- 検索不能
- 8000 に疎通できない

### 影響範囲

- 文書管理
- OCR
- 検索、保管、参照
- 取り込みパイプライン

### 確認コマンド

```bash
docker compose ps paperless
```

```bash
docker compose logs --tail=300 paperless
```

```bash
curl -I http://localhost:8000
```

```bash
docker compose config
```

### ログ確認箇所

- consume ディレクトリ処理失敗
- OCR エラー
- DB / Redis 接続失敗
- ストレージ権限エラー
- consume の実コンテナ内パスは `docker compose config` と実コンテナ確認結果を合わせて判断する

### 復旧手順

```bash
docker compose logs --tail=300 paperless
```

```bash
docker compose ps postgres redis
```

```bash
docker compose restart paperless
```

```bash
curl -I http://localhost:8000
```

### 復旧完了条件

- 8000 が正常応答
- UI 表示正常
- 文書取り込み再開
- OCR 処理成功

### 再起動を慎重にすべき条件

- 大量 OCR 実行中
- 文書インポート中
- DB / Redis が不安定

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream paperless
```

```bash
df -h
```

### 再発防止の確認項目

- consume 監視
- OCR 失敗通知
- 保存先容量
- 権限とマウント設定

## open_notebook

### 先に確認する依存先

- open_notebook_db
- ollama
- 保存先 volume

### 症状

- ノート UI 応答なし
- 保存失敗
- open_notebook_db 接続失敗
- ollama 接続失敗
- コンテンツ参照不能
- 8502 または 5055 に疎通できない

### 影響範囲

- ナレッジ参照
- 編集機能
- 個人ワークスペース利用

### 確認コマンド

```bash
docker compose ps open_notebook
```

```bash
docker compose logs --tail=300 open_notebook
```

```bash
curl -I http://localhost:8502
```

```bash
curl -I http://localhost:5055
```

```bash
docker compose ps open_notebook_db ollama
```

### ログ確認箇所

- サーバ起動失敗
- ストレージ権限エラー
- open_notebook_db 接続失敗
- ollama 接続失敗
- ファイル I/O エラー

### 復旧手順

```bash
docker compose logs --tail=300 open_notebook
```

```bash
docker compose ps open_notebook_db ollama
```

```bash
docker compose restart open_notebook
```

```bash
curl -I http://localhost:8502
```

```bash
curl -I http://localhost:5055
```

### 復旧完了条件

- 8502 または 5055 が正常応答
- UI 応答正常
- 保存成功
- 対象ノート参照可能

### 再起動を慎重にすべき条件

- 大量同期中
- ファイル書き込み処理中
- マウント先異常が未解消

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream open_notebook
```

```bash
df -h
```

### 再発防止の確認項目

- ボリュームマウント整合性
- 保存先権限
- 定期バックアップ
- 同期競合対策

## minio

### 先に確認する依存先

- ストレージ volume
- ホストディスク
- paperless
- バックアップジョブ

### 症状

- オブジェクト保存失敗
- バケット参照失敗
- 署名 URL エラー
- 起動失敗
- 9000 または 9001 に疎通できない

### 影響範囲

- オブジェクトストレージ依存機能
- 添付ファイル、成果物保存
- バックアップ置き場

### 確認コマンド

```bash
docker compose ps minio
```

```bash
docker compose logs --tail=300 minio
```

```bash
curl -I http://localhost:9000
```

```bash
curl -I http://localhost:9001
```

使える場合のみ:

```bash
docker compose exec minio sh -lc "mc admin info local"
```

### ログ確認箇所

- disk not found
- write failure
- access denied
- erasure set / storage 初期化失敗

### 復旧手順

```bash
docker compose logs --tail=300 minio
```

```bash
docker compose restart minio
```

```bash
curl -I http://localhost:9000
```

```bash
curl -I http://localhost:9001
```

使える場合のみ:

```bash
docker compose exec minio sh -lc "mc admin info local"
```

### 復旧完了条件

- 9000 または 9001 が正常応答
- 主要バケット参照可能
- オブジェクト read / write 成功
- ストレージエラー停止

### 再起動を慎重にすべき条件

- 大量アップロード中
- バックアップ実行中
- ストレージマウント異常が継続
- データ整合性未確認

### 追加で見るべきリソース確認項目

```bash
docker stats --no-stream minio
```

```bash
df -h
```

### 再発防止の確認項目

- 保存先容量監視
- バケットポリシー確認
- バックアップ整備
- マウント先の健全性確認
