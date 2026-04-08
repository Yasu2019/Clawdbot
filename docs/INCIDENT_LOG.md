# Incident Log — トラブル記録・再発防止台帳

本ファイルは、システムに発生した障害・不具合とその根本原因・修正内容・再発防止策を記録します。
修正を行った場合は、必ずこのファイルにエントリを追加してください。

---

## INC-001: C ドライブ容量枯渇（host_gmail_incremental_* 一時フォルダ未削除）

| 項目 | 内容 |
|---|---|
| **発生日** | 2026-04-05 |
| **発見方法** | Docker エンジンがフリーズし、全コンテナが停止。C ドライブ残容量がほぼ 0 バイト。 |
| **影響範囲** | Docker Desktop 全体（IATF System, QA Dashboard, Gateway 等すべてのコンテナ）|
| **根本原因** | `data/workspace/host_gmail_incremental_sync.py` の 110 行目で `tempfile.mkdtemp(prefix="host_gmail_incremental_")` により一時ディレクトリを作成するが、`finally` ブロックに `shutil.rmtree()` が無く、処理完了後もフォルダが残存。毎分約 370MB × 1 個のペースで蓄積し、数時間で数十〜数百 GB に到達。 |
| **修正内容** | `finally` ブロックに `shutil.rmtree(tempdir, ignore_errors=True)` を追加。 |
| **修正ファイル** | [host_gmail_incremental_sync.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/host_gmail_incremental_sync.py) L221-228 |
| **検証結果** | 修正後 4 分間監視 → 新規ゴミフォルダ 0 個。78.12 GB を即時解放。 |
| **追加対策** | (1) 手動清掃スクリプト `scripts/clawstack_janitor.ps1` を配備。(2) QA Dashboard に「Host Maintenance」カードを追加。 |
| **再発防止** | 本インシデントを契機に AGENTS.md に「修正後の記録義務」ルールを追加。 |

### 教訓（Lessons Learned）

1. **`tempfile.mkdtemp()` を使う場合は、必ず `try...finally` で `shutil.rmtree()` を入れること。** Python の `tempfile.TemporaryDirectory()` コンテキストマネージャを使えば自動削除される。
2. **定期実行（cron / daemon）スクリプトは 1 回あたりのディスク使用量が小さくても、蓄積すると致命的になる。** 新しい定期実行スクリプトを書く際は、必ず「後片付け」コードの有無をレビューすること。
3. **ディスク枯渇は連鎖障害を引き起こす。** Docker エンジン、PostgreSQL、Redis、Rails すべてが巻き添えで停止する。早期検知の仕組み（Uptime Kuma のディスク監視等）を検討する。

---

## INC-002: IATF Rails アプリ 500 エラー（DB_PORT 不一致）

| 項目 | 内容 |
| --- | --- |
| **発生日** | 2026-04-05 |
| **発見方法** | `http://127.0.0.1:3003/users/sign_in` にアクセスすると HTTP 500 が返る。ユーザーからの報告。 |
| **影響範囲** | IATF16949 品質管理システム（Rails アプリ）全機能が利用不可。 |
| **発生経緯** | INC-001（C ドライブ枯渇）により Docker Desktop が停止。復旧のため Docker を再起動し、`docker-compose.production.yml` で IATF スタックを再構成。コンテナ自体は起動したが、Rails が DB に接続できず 500 エラーとなった。 |
| **根本原因（5Why）** | **Why1**: Rails が DB に接続できない → **Why2**: `host.docker.internal:5432` に接続しようとしている → **Why3**: `database.yml` が `DB_PORT` 環境変数（デフォルト 5432）を使用 → **Why4**: `docker-compose.production.yml` の `web` サービスに `DB_PORT` が未定義 → **Why5**: DB コンテナのポートマッピングが `5436:5432`（ホスト側 5436）なのに、Rails はデフォルトの 5432 で接続を試行。**ポートマッピングと環境変数の不整合。** |
| **修正内容** | `docker-compose.production.yml` の `web` および `sidekiq` サービスの `environment` に `DB_PORT=5436` を追加。 |
| **修正ファイル** | [docker-compose.production.yml](file:///d:/Clawdbot_Docker_20260125/iatf_system/docker-compose.production.yml) L66, L99 |
| **検証結果** | 修正後 `curl` で HTTP 200 を確認。ブラウザでログインページが正常表示（「接続テスト: 通知システムが正常に動作しています」の緑バナー表示）。 |
| **再発防止** | 下記「教訓」参照。 |

### 教訓（Lessons Learned）

1. **`docker-compose.yml` でホスト経由（`host.docker.internal`）のDB接続を使う場合、ポートマッピング（`5436:5432`）のホスト側ポートを `DB_PORT` 環境変数に明示すること。** デフォルト値（5432）はコンテナ内部のポートであり、ホスト経由では一致しない。
2. **Docker 再起動後は、コンテナの起動順序に注意する。** DB の「ready to accept connections」ログを確認してから Web を起動しないと、Rails が DB 起動中（"database system is starting up"）に接続を試み、そのまま接続プールが壊れた状態で動き続ける。
3. **復旧作業時は `docker compose logs --tail N <service>` でエラーの全文を確認すること。** 今回は「port 5432」への接続失敗ログが出ていたが、ターミナルの出力トランケーションで見落としが発生した。

---

*次のインシデントは INC-003 として追記してください。*
