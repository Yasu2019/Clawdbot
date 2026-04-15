# Incident Log  Eトラブル記録・再発防止台帳

本ファイルは、シスチE��に発生した障害・不�E合とそ�E根本原因・修正冁E��・再発防止策を記録します、E修正を行った場合�E、忁E��こ�Eファイルにエントリを追加してください、E
---

## INC-019: Local self-growth and scout loops were incomplete and inconsistent
| Item | Details |
|---|---|
| **Date** | 2026-04-12 |
| **Detected By** | Follow-up audit of self-growth, scout freshness, and Qdrant hygiene |
| **Impact** | The system had partial self-improvement parts, but they were not fully aligned: local scout refresh depended on brittle n8n patching, approved RL skills were syncing to `universal_knowledge` instead of `agent_self_growth_memory`, and startup retrieval verification was not recorded. |
| **Root Cause (5 Why)** | **Why1**: The project had design intent for self-growth and memory hygiene, but not a complete local-only operational loop. **Why2**: AI Scout safe-source patching still depended on an n8n API path that could fail independently of the actual local collection logic. **Why3**: RLAnything skill sync used a generic knowledge collection instead of the dedicated self-growth collection named in governance. **Why4**: No pre-tool or start-of-session verification existed to prove that stored self-growth memory was being queried on future sessions. **Why5**: Memory hygiene thresholds were documented, but no active archive guard was enforcing them on the actual collection. |
| **Fix Summary** | Added a local no-API-cost scout runner and freshness watchdog, added a self-growth memory hygiene guard for `agent_self_growth_memory`, redirected RL skill sync to `agent_self_growth_memory`, and added a `PreToolUse` hook to record first-use retrieval attempts per session. |
| **Files Changed** | `data/workspace/run_ai_strategy_scout_local.py`, `data/workspace/ai_strategy_scout_watchdog.py`, `scripts/start_ai_strategy_scout_watchdog.ps1`, `data/workspace/agent_self_growth_memory_hygiene.py`, `scripts/start_agent_self_growth_memory_hygiene.ps1`, `data/workspace/rl_anything/hook_pre_tool_use.py`, `data/workspace/rl_anything/qdrant_sync.py`, `.claude/settings.json`, `docs/INCIDENT_LOG.md` |
| **Validation** | Local scout refresh can run without n8n API writes, self-growth Qdrant sync now targets `agent_self_growth_memory`, hygiene status can report thresholds without deleting healthy data, and startup retrieval verification writes per-session status with top hits or errors. |
| **Lessons Learned** | For self-improving systems, “memory exists Eis not enough. The store, retrieval path, and hygiene path must target the same collection, and there should be an explicit log proving that startup retrieval was attempted. |
| **Recurrence Prevention** | Keep AI Scout on local/no-cost collection paths where possible, enforce a dedicated hygiene script on the actual self-growth collection, and keep first-use retrieval verification enabled through repo-local hook config. |

---

## INC-001: C ドライブ容量枯渁E��Eost_gmail_incremental_* 一時フォルダ未削除�E�E
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-05 |
| **発見方況E* | Docker エンジンがフリーズし、�EコンチE��が停止、E ドライブ残容量がほぼ 0 バイト、E|
| **影響篁E��** | Docker Desktop 全体！EATF System, QA Dashboard, Gateway 等すべてのコンチE���E�|
| **根本原因** | `data/workspace/host_gmail_incremental_sync.py` の 110 行目で `tempfile.mkdtemp(prefix="host_gmail_incremental_")` により一時ディレクトリを作�Eするが、`finally` ブロチE��に `shutil.rmtree()` が無く、�E琁E��亁E��もフォルダが残存。毎�E紁E370MB ÁE1 個�Eペ�Eスで蓁E��し、数時間で数十〜数百 GB に到達、E|
| **修正冁E��** | `finally` ブロチE��に `shutil.rmtree(tempdir, ignore_errors=True)` を追加、E|
| **修正ファイル** | [host_gmail_incremental_sync.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/host_gmail_incremental_sync.py) L221-228 |
| **検証結果** | 修正征E4 刁E��監要EↁE新規ゴミフォルダ 0 個、E8.12 GB を即時解放、E|
| **追加対筁E* | (1) 手動渁E��スクリプト `scripts/clawstack_janitor.ps1` を�E備、E2) QA Dashboard に「Host Maintenance」カードを追加、E|
| **再発防止** | 本インシチE��トを契機に AGENTS.md に「修正後�E記録義務」ルールを追加、E|

### 教訓！Eessons Learned�E�E
1. **`tempfile.mkdtemp()` を使ぁE��合�E、忁E�� `try...finally` で `shutil.rmtree()` を�Eれること、E* Python の `tempfile.TemporaryDirectory()` コンチE��スト�Eネ�Eジャを使え�E自動削除される、E2. **定期実行！Eron / daemon�E�スクリプトは 1 回あたりのチE��スク使用量が小さくても、蓄積すると致命皁E��なる、E* 新しい定期実行スクリプトを書く際は、忁E��「後片付け」コード�E有無をレビューすること、E3. **チE��スク枯渁E�E連鎖障害を引き起こす、E* Docker エンジン、PostgreSQL、Redis、Rails すべてが巻き添えで停止する。早期検知の仕絁E���E�Eptime Kuma のチE��スク監視等）を検討する、E
---

## INC-002: IATF Rails アプリ 500 エラー�E�EB_PORT 不一致�E�E
| 頁E�� | 冁E�� |
| --- | --- |
| **発生日** | 2026-04-05 |
| **発見方況E* | `http://127.0.0.1:3003/users/sign_in` にアクセスすると HTTP 500 が返る。ユーザーからの報告、E|
| **影響篁E��** | IATF16949 品質管琁E��スチE���E�Eails アプリ�E��E機�Eが利用不可、E|
| **発生経緯** | INC-001�E�E ドライブ枯渁E��により Docker Desktop が停止。復旧のため Docker を�E起動し、`docker-compose.production.yml` で IATF スタチE��を�E構�E。コンチE��自体�E起動したが、Rails ぁEDB に接続できず 500 エラーとなった、E|
| **根本原因�E�EWhy�E�E* | **Why1**: Rails ぁEDB に接続できなぁEↁE**Why2**: `host.docker.internal:5432` に接続しようとしてぁE�� ↁE**Why3**: `database.yml` ぁE`DB_PORT` 環墁E��数�E�デフォルチE5432�E�を使用 ↁE**Why4**: `docker-compose.production.yml` の `web` サービスに `DB_PORT` が未定義 ↁE**Why5**: DB コンチE��のポ�Eト�EチE��ングぁE`5436:5432`�E��Eスト�E 5436�E�なのに、Rails はチE��ォルト�E 5432 で接続を試行、E*ポ�Eト�EチE��ングと環墁E��数の不整合、E* |
| **修正冁E��** | `docker-compose.production.yml` の `web` および `sidekiq` サービスの `environment` に `DB_PORT=5436` を追加、E|
| **修正ファイル** | [docker-compose.production.yml](file:///d:/Clawdbot_Docker_20260125/iatf_system/docker-compose.production.yml) L66, L99 |
| **検証結果** | 修正征E`curl` で HTTP 200 を確認。ブラウザでログインペ�Eジが正常表示�E�「接続テスチE 通知シスチE��が正常に動作してぁE��す」�E緑バナ�E表示�E�、E|
| **再発防止** | 下記「教訓」参照、E|

### 教訓！Eessons Learned�E�E
1. **`docker-compose.yml` でホスト経由�E�Ehost.docker.internal`�E��EDB接続を使ぁE��合、�Eート�EチE��ング�E�E5436:5432`�E��Eホスト�Eポ�Eトを `DB_PORT` 環墁E��数に明示すること、E* チE��ォルト値�E�E432�E��EコンチE��冁E��のポ�Eトであり、�Eスト経由では一致しなぁE��E2. **Docker 再起動後�E、コンチE��の起動頁E��に注意する、E* DB の「ready to accept connections」ログを確認してから Web を起動しなぁE��、Rails ぁEDB 起動中�E�Edatabase system is starting up"�E�に接続を試み、そのまま接続�Eールが壊れた状態で動き続ける、E3. **復旧作業時�E `docker compose logs --tail N <service>` でエラーの全斁E��確認すること、E* 今回は「port 5432」への接続失敗ログが�EてぁE��が、ターミナルの出力トランケーションで見落としが発生した、E
---

## INC-003: Gateway フリーズ、Obsidian 連携タイムアウチE
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-10 |
| **発見方況E* | Obsidian Claudian プラグインにて `Request timeout: initialize (120000ms)` エラー、E|
| **影響篁E��** | OpenClaw Gateway 全体！EI, API, MCP 連携不可�E�E|
| **発生経緯** | 前日�E�E4-09�E��Eログを最後に gateway の更新が停止。`curl` によるヘルスチェチE��も応答しなくなった、E|
| **根本原因�E�推測�E�E* | 子�Eロセス�E�Eummary cache builder�E�が defunct となり、メインの gateway プロセスのイベントループがチE��ドロチE��また�EブロチE��ング状態に陥った可能性。リソース�E�EPU/MEM/DISK�E��E逼迫は見られなぁE��E|
| **修正冁E��** | `docker restart clawstack-unified-clawdbot-gateway-1` による強制再起動、E|
| **修正ファイル** | N/A (運用操作による復旧) |
| **検証結果** | 再起動後、ログぁE`2026-04-10.log` に正常生�Eされ、`ws://0.0.0.0:18789` での征E��を確認、E|
| **再発防止** | (1) Gateway のヘルスチェチE���E�Eiveness Probe�E�を Docker Compose 側また�E監視スクリプトに検討、E2) defunct プロセスの発生を防ぐため、子�Eロセスのハンドリング処琁E��見直す、E|

### 教訓！Eessons Learned�E�E
1. **コンチE��ぁE`Up` でもアプリケーション層がフリーズしてぁE��場合がある、E* `docker ps` だけでは不十刁E��、ログの更新日時や API の応答確認が忁E��、E2. **defunct プロセス�E�ゾンビ）�E発生�E異常の允E��、E* 子�EロセスめEfork する設計�E場合、シグナルハンドリングめEwaitpid 等�E適刁E��後�E琁E��欠けるとゾンビが蓁E��し、親プロセスに影響を及ぼすことがある、E3. **「initialize」タイムアウト�E MCP/LSP ハンドシェイク失敗を示す、E* クライアント�E�E�Ebsidian�E��EエラーメチE��ージから、どのプロトコルのどの段階で止まってぁE��かを推測できる、E
---

## INC-004: ゾンビ�Eロセス蓁E��と Paperless 異常による Gateway 連続停止

| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-10 |
| **発見方況E* | Obsidian Claudian 再度の `Request timeout: initialize`。�E起動かめE時間後に再発、E|
| **影響篁E��** | Gateway, LiteLLM, Paperless 連携全佁E|
| **発生経緯** | INC-003 での単なめE`docker restart` では根本原因が解消されず、数時間後に再発、Eateway 側でのゾンビ�Eロセス蓁E��、およ�E外部 E: ドライブ上�E Paperless チE��レクトリ消失による Liveness Probe 失敗が重なり、シスチE��がハングした、E|
| **根本原因** | (1) `docker-compose.yml` で `init: true` が未設定�Eため、孤立した子�EロセスぁEPID 1 (OpenClaw) に回収されず滞留、E2) Paperless のマウント�E�E�E: ドライチEJunction�E�にチE��レクトリが存在せず、Paperless が起動エラー�E�EileExistsError�E�で停止、E3) `ingest_watchdog.py` が異常状態�E Paperless に対しリトライを繰り返し、リソースまた�Eプロセス制御に影響、E|
| **修正冁E��** | (1) `docker-compose.yml` に `init: true` を追加、E2) E: ドライブ上�E Paperless 構造を復旧、E3) `ingest_watchdog.py` に持E��バックオフ！Exponential Backoff�E�を実裁E��E|
| **修正ファイル** | [docker-compose.yml](file:///d:/Clawdbot_Docker_20260125/docker-compose.yml), [ingest_watchdog.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/ingest_watchdog.py) |
| **検証結果** | Gateway の PID 1 ぁE`docker-init` になってぁE��ことを確認。Paperless の Healthy 到達およ�E Watchdog の正常ポ�Eリングを確認、E|
| **再発防止** | (1) 全ての長期実行コンチE��で `init: true` また�E `tini` の使用を検討、E2) ホスト�Eの Junction 先（外付けドライブ）�E死活監視また�E起動前チェチE��を強化、E|

### 教訓！Eessons Learned�E�E
1. **PID 1 問題�E重要性**�E�Node.js 等�Eランタイムを直接 PID 1 で動かすと、ゾンビ�Eロセスの回収がエンジンの実裁E��依存し、意図しなぁE��ングを招く。`init: true` の利用が鉄剁E��E2. **外部ドライブ連携のリスク**�E�Junction を使用した外部マウント�E、ドライブ�E刁E��めE��造変更に弱ぁE��起動時にチE��レクトリの存在チェチE��を行う等、E��御皁E��裁E��忁E��、E3. **バックオフ�E欠如による二次被害**�E�依存サービスが死んでぁE��際に、�Eーリング側が�E力でリトライを続けると、正常なコンチE��まで負荷めE��グの増大で道連れになる可能性がある、E
---

*次のインシチE��ト�E INC-005 として追記してください、E

---

## INC-005: Claudian Codex 起動失敗と initialize ターゲチE��不一致
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | Obsidian Claudian で `Request timeout: initialize (120000ms)` の後、`Codex target mismatch` が連鎖、E|
| **影響篁E��** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 配下�E Codex 連携。Vault 冁E��めECodex ワークスペ�Eス初期化が失敗、E|
| **根本原因 (5 Why)** | **Why1**: Codex プロセスが起動せぁEinitialize ぁE120 秒でタイムアウトした、E**Why2**: Windows 自動解決ぁE`codex.cmd` / `codex.bat` を探索対象に含めてぁE��かった、E**Why3**: Vault プラグイン配下には `codex.cmd` ラチE��ーがあり、PATH には存在してぁE��が解決できなかった、E**Why4**: たとぁE`.cmd` を見つけても、Windows では `spawn(..., { shell: false })` のままでは起動互換性が弱ぁE��E**Why5**: 起動後も `codex_bridge.js` の initialize 応答に `platformOs` / `platformFamily` がなく、ターゲチE��検証で別エラーになってぁE��、E|
| **修正冁E��** | Windows の CLI 探索に `codex.cmd` / `codex.bat` を追加し、`.cmd` / `.bat` が解決された場合�E sibling の `codex_bridge.js` めE`node` で直接起動するよぁE��正。さらに bridge initialize 応答へ `platformOs=windows` と `platformFamily=windows` を追加し、ログチE��レクトリを�E動作�Eするよう修正、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60884`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60905`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61858`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:11`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:37` |
| **検証結果** | ソース確認で Windows 探索対象に `.cmd` / `.bat` が追加されたこと、`.cmd` 解決時に `node + codex_bridge.js` の直接起動へ刁E��替わること、bridge initialize 応答に target 惁E��が載ることを確認。加えて `codex_bridge.js` 単体�E initialize 応答テストで `platformOs` / `platformFamily` を返すことを確認、E|
| **再発防止筁E* | Windows 固有�E実行形弁E(`.cmd` / `.bat`) めECLI 自動解決から外さなぁE��initialize 応答�E忁E��フィールドを欠かさなぁE��ぁE��bridge 変更時�E起動前の JSON-RPC スモークチE��トを維持する、E|

### Lessons Learned
1. Windows 縺�E�縺�E�縲訓ATH 縺�E�縺めE��縲阪□縺代〒縺�E�荳榊香蛻・〒縲�E�spawn` 縺�E�螳溯�E�悟ｽ�E�蠑丞ｷ�E�縺�E�縺�E�隕九ｋ蠢・�E�√′縺めE��縲・2. `initialize` 縺�E�繧�E�繧�E�繝繧�E�繧�E�繝医□縺代〒縺�E�縺上∝ｿ懁E��斐せ繧�E�繝ｼ繝樔ｸ榊ｙ縺�E�繧めE��梧�E��E�逶�E�縺�E�髫懷�E��E�繧定ｵ�E�縺薙�E縺溘ａ縲∬�E��E�蜍輔�E蠢懁E��斐�E荳�E�譁E��繧貞�E譎ゅ↓讀懁E���E�縺吶�E�縲・3. 譌｢蟁E��Λ繝�Eヱ繝ｼ (`codex.cmd`) 繧呈ｴ�E�縺九�E諡�E�蠑ｵ縺�E�譁E��縺後∝挨邉ｻ邨�E�縺�E�襍ｷ蜍�E�E�瑚ｷ�E�繧貞｢励�E�E��吶�E�繧雁E��牙�E縺�E�蟁E��・縺�E�縺阪�E�縲・

## INC-017: `email_search.db` 破損時の自動修復経路を追加
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-12 |
| **発見方況E* | `email_continuous_watchdog_status.json` と `email_continuous_ingest_status.json` で `temp integrity_check failed` / `database disk image is malformed` を確誁E|
| **影響篁E��** | Gmail incremental ingest が失敗ループに入り、watchdog ぁEdaemon を�E起動しても回復しなぁE��慁E|
| **根本原因 (5 Why)** | **Why1**: `email_search.db` に freelist 不整合が入めE`PRAGMA integrity_check` が失敗した、E**Why2**: `host_gmail_incremental_sync.py` は temp DB の検査で異常を検知しても、daemon 側に修復刁E��がなかった、E**Why3**: `continuous_email_ingest_daemon.py` は失敗時に `error` を書ぁE��征E��するだけで、破損シグナルと一般エラーを区別してぁE��かった、E**Why4**: 既存�E `repair_email_search_db.py` はあったが、daemon 冁E��ら安�Eに呼ぶ配線がなかった、E**Why5**: watchdog めE`db repair` を通常エラーと区別しなぁE��提で、修復中の保護が不足してぁE��、E|
| **修正冁E��** | `data/workspace/continuous_email_ingest_daemon.py` に DB 破損シグナル検知、修復呼び出し、repair cooldown、repair 状態保存を追加、E`data/workspace/repair_email_search_db.py` に `--skip-stop-processes` を追加し、daemon から安�Eに inline 実行できるようにした、E`data/workspace/email_continuous_watchdog.py` で `stage == "db_repair"` を健全扱ぁE��して、修復中の無駁E��再起動を防止、Eそ�E征E`python data/workspace/repair_email_search_db.py --restart-watchdog` を実行して宁EDB を修復、E|
| **検証結果** | 修復結果 `email_search_db_repair_status.json` は `stage=completed`、E復旧後�E DB は `integrity_check=ok`, `quick_check=ok`, `emails=22688`, `tasks=9065` を確認、Ewatchdog は PID `10428`、daemon は PID `11748` で再起動済み、E|
| **Lessons Learned** | 修復スクリプトが存在してぁE��も、異常刁E��と呼び出し経路が無ければ現場では回復しなぁE��E破損系は一般失敗と刁E��、status JSON と watchdog の両方で専用状態を持つべき、E|
| **再発防止筁E* | daemon 側で DB 破損を検知したら�E動修復へ刁E��する、Ewatchdog は `db_repair` を�E起動対象から外す、E以後�E DB 破損�E backup と repair status を残しながら回復を試みる、E|

## INC-018: mini PC 常駐ハーネスの未接続と誤警報を整琁E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-12 |
| **発見方況E* | system hardening 点検で、`docker_desktop_ui_watchdog` ぁEobserve-only、`claudian_watchdog` が未常駐、`minipc_optimizer` に自動�E口が無ぁE��`n8n` API キーがスクリプトへ直書き、`continuous_system_improvement` が一部を誤って high risk 扱ぁE��てぁE��ことを確誁E|
| **影響篁E��** | Docker UI 不調時に自動回復しなぁE��Claudian/mini PC 軽量化の監視が刁E��ても気づきにくい、system summary が実際より危険に見える、秘寁E��報のローチE�Eションが難しい |
| **根本原因 (5 Why)** | **Why1**: watchdog めEoptimizer 自体�E存在しても、常駐起動や相互補完�E配線が不足してぁE��、E**Why2**: Docker UI watchdog は `allowUiReset=false` のまま長時間 failure を積んでぁE��、E**Why3**: Claudian watchdog は古ぁE��グを最近�E失敗として解釈し、E��止状態でめEerror になり得た、E**Why4**: mini PC optimizer は手動 CLI のみで、常駐�E監視役が存在しなかった、E**Why5**: n8n API キーがスクリプト冁E��埋め込まれ、設定変更めE�E利用時にコード編雁E��忁E��だった、E|
| **修正冁E��** | `data/workspace/docker_desktop_ui_watchdog.py` に長朁Efailure 時�E強制 reset 刁E��を追加し、`docker_desktop_ui_watchdog_config.json` めE`quietMode=true`, `allowUiReset=true`, `consecutiveFailuresForReset=12` へ更新、E`data/workspace/claudian_watchdog.py` を、recent activity が無ぁE��ぁEbridge/spawn ログでは error を�EさなぁE��ぁE��強、E`data/workspace/minipc_optimizer_watchdog.py` と `scripts/start_minipc_optimizer_watchdog.ps1` を追加し、低メモリ時だぁE`apply-lite` を実行する軽釁Ewatchdog を新設、E`data/workspace/continuous_system_improvement.py` と `data/workspace/auto_repair_allowed.py` を更新し、Docker UI / Claudian / mini PC watchdog の常駐確認と再起動を追加、E`data/workspace/add_ai_scout_safe_sources.py` と `scripts/setup_n8n_changedetection_flow.ps1` は `N8N_API_KEY` めE`.env` / 環墁E��数から読む方式へ変更、E|
| **検証結果** | `docker_desktop_ui_watchdog.py`, `claudian_watchdog.py`, `minipc_optimizer_watchdog.py` はすべて `py_compile` 成功、E実�Eロセスとして 3 本の watchdog 起動を確認、E`claudian_watchdog.py --once` は `stage=healthy`、E`minipc_optimizer_watchdog_status.json` では free memory `35.14GB`, `freePercent=73.6`, `stage=healthy` を確認、EDocker UI watchdog は `lastAction=reset_frontend_cache` まで進み、以後�E status で reset が有効化されたことを確認、E|
| **Lessons Learned** | 監視ロジチE��は「存在すること」より「常駐し続けること」と「古ぁE��敗を現在の障害として扱わなぁE��と」が重要、E低負荷端末では、常駐ツールを増やすよりも軽釁Ewatchdog で段階制御する方が安�E、E|
| **再発防止筁E* | system summary と auto repair に watchdog 常駐チェチE��を残す、EDocker UI は observe-only に戻さず段隁Ereset を継続する、E秘寁E��報は `.env` / 環墁E��数へ寁E��、スクリプト直書きを増やさなぁE��E|

---

## INC-013: Antigravity `Notify file events failed` 連打による IDE フリーズ
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | Mini PC が午後から断続的にフリーズし、Remote Desktop 上で Antigravity の `Notify file events failed.` が数秒ごとに出続けることを確認、E|
| **影響篁E��** | Antigravity 編雁E��面の操作性低下、CPU 使用玁E���E、ログ肥大化。Remote Desktop 自体�E接続維持されるが、IDE の応答性が悪化、E|
| **根本原因 (5 Why)** | **Why1**: Antigravity 拡張ホストで `Notify file events failed.` が連続発生してぁE��、E**Why2**: 同じログ直前に `Client is not running` が繰り返し出ており、言語サーバ�E再起動後もファイル監視通知だけが残留してぁE��、E**Why3**: こ�Eワークスペ�Eスは `data/workspace` 配下に `node_modules`、褁E��の `venv`、Obsidian Vault、生成物、ログ、tmp を大量に抱えており、監視対象が過大だった、E**Why4**: `.vscode/settings.json` に watcher 除外や検索除外がなく、IDE が巨大チE��レクトリ群をそのまま監視してぁE��、E**Why5**: 監視負荷の高い生�E物と実際に編雁E��るコード領域の刁E��ポリシーが未設定で、�E起動時に同じ監視負荷が�E現してぁE��、E|
| **修正冁E��** | `.vscode/settings.json` に `files.watcherExclude`、`search.exclude`、`python.analysis.exclude` を追加し、`node_modules`、仮想環墁E��Obsidian Vault、生成物、tmp、ログ系チE��レクトリを監視�E検索対象から除外した、E|
| **修正ファイル** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **検証結果** | Antigravity ログで `Notify file events failed.` ぁE`Client is not running` 直後から継続発生してぁE��こと、CPU 上位に Antigravity 本体と `remoting_host` が並んでぁE��こと、監視対象に巨大チE��レクトリが含まれてぁE��ことを確認した。設定反映後�E Antigravity の `Developer: Reload Window` また�Eアプリ再起動で新しい watcher 設定が有効化される状態にした、E|
| **Lessons Learned** | Remote Desktop を止められなぁE��況では、まぁEIDE の watcher 負荷を�Eり離す方が安�Eで効果が高い。巨大な生�E物めEVault を同一ワークスペ�Eスで開く場合、検索除外だけでなぁEwatcher 除外も最初から�Eれておく忁E��がある、E|
| **再発防止筁E* | 新しい大容量ディレクトリをこの repo 配下へ追加する際�E、`.vscode/settings.json` の watcher 除外に同時追加する、EDE フリーズ系の障害では、`logs/.../7-antigravity.log` の `Client is not running` と `Notify file events failed.` の絁E��合わせを初動確認頁E��にする、E|

## INC-014: Antigravity の R 拡張ぁE`cmd.exe` ポップアチE�Eを連続起勁E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-12 |
| **発見方況E* | Antigravity 復旧後も `CMD` ウィンドウが数秒ごとに開いて閉じることを確認。実行中プロセスの親子関係とコマンドラインを調査した、E|
| **影響篁E��** | Mini PC 操作性低下、画面のちらつき、Antigravity 利用中の雁E��阻害、E|
| **根本原因 (5 Why)** | **Why1**: `cmd.exe` が周期的に起動してぁE��、E**Why2**: コマンドラインは `cmd.exe /c ... Rterm.exe ... helpServer.R` と `languageServer.R` で、Antigravity の R 拡張が起点だった、E**Why3**: ワークスペ�Eス冁E�E R 関連ファイル検知で R 拡張ぁEactivation され、言語サーバと help server を�E動起動してぁE��、E**Why4**: こ�E repo では R を主要用途として使ってぁE��ぁE��方、`.vscode/settings.json` には `r.rpath.windows` のみがあり、�E動起動を抑える設定がなかった、E**Why5**: 非使用拡張の自動機�Eをワークスペ�Eス単位で絞る運用が未整備で、不要な補助プロセスが常時起動してぁE��、E|
| **修正冁E��** | `.vscode/settings.json` に `r.lsp.enabled=false`、`r.sessionWatcher=false`、`r.helpPanel.previewLocalPackages=[]`、`r.session.viewers.viewColumn.*=Disable`、`r.alwaysUseActiveTerminal=true` を追加し、R 拡張の自動言語サーバ�EHelp/Plot ビューア起動を停止した、E|
| **修正ファイル** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **検証結果** | 実行中 `cmd.exe` のコマンドラインぁEAntigravity 配下�E `reditorsupport.r-2.8.8-universal` を指してぁE��こと、最新ログに `R Language Server ... started` が�EてぁE��ことを確認した。設定反映後�E Antigravity のウィンドウ再読み込みまた�E再起動で新設定が有効になる、E|
| **Lessons Learned** | IDE フリーズ調査では、ファイル watcher だけでなく拡張が裏で立ち上げる補助プロセスまで見ると原因に早く届く。使ってぁE��ぁE��語拡張は、無効化できなぁE��合でもワークスペ�Eス設定で自動機�Eを止めるだけで安定性が上がる、E|
| **再発防止筁E* | 新しい IDE 拡張を常用する前に、�E動起動する言語サーバ、help server、watcher の有無を確認する。今回のような `cmd.exe` 点滁E��出た場合�E、まず親プロセスとコマンドラインから拡張名を特定してワークスペ�Eス設定で抑制する、E|

## INC-015: R 拡張設定だけでは `cmd.exe` 点滁E��止めきれず、拡張本体を無効匁E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-12 |
| **発見方況E* | INC-014 の設定変更後に Antigravity を�E起動してめE`cmd.exe` ポップアチE�Eが継続。最新ログ `20260412T000423` と `cmd.exe` のコマンドラインを�E確認した、E|
| **影響篁E��** | ワークスペ�Eス設定変更だけでは R 拡張の自動起動が残り、画面点滁E��操作阻害が継続した、E|
| **根本原因 (5 Why)** | **Why1**: `r.lsp.enabled=false` と `r.sessionWatcher=false` を�EれてめE`cmd.exe /c ... Rterm.exe ... helpServer.R` が�E発した、E**Why2**: R 拡張は `workspaceContains` により activation され、設定無効化後も Help server 側の起動経路が残ってぁE��、E**Why3**: こ�Eワークスペ�Eスには R 関連ファイル検知条件があり、拡張自体�E読み込みを避けられなかった、E**Why4**: Antigravity 側でこ�E拡張をワークスペ�Eス単位に簡単に disable できず、設定だけでは完�E停止に届かなかった、E**Why5**: 非使用言語拡張に対する最終手段として「可送E��拡張退避」を運用手頁E��持ってぁE��かった、E|
| **修正冁E��** | Antigravity を停止した上で `C:\\Users\\yasu\\.antigravity\\extensions\\reditorsupport.r-2.8.8-universal` めE`...universal.disabled` へリネ�Eムし、R 拡張本体を可送E��無効化した、E|
| **修正ファイル** | `docs/INCIDENT_LOG.md` |
| **検証結果** | 無効化後、拡張一覧上�E `reditorsupport.r-2.8.8-universal.disabled` として退避され、Antigravity 再起動時に当該拡張がロード対象から外れる状態にした、E|
| **Lessons Learned** | IDE 拡張の自動起動�E、設定値よりめEactivation event が�Eに効く場合がある。不要拡張が安定性を崩すとき�E、可送E��フォルダ退避が最も速く安�Eな止血策になる、E|
| **再発防止筁E* | 非使用拡張が補助プロセスめEwatcher を勝手に起動する場合、E) 設定で抑制、E) だめなら拡張本体を退避、�E頁E��対処する。復帰が忁E��になった場合�E `.disabled` を�E名に戻して再起動する、E|

## INC-016: `continuous_email_ingest_daemon.py` が孁EPython をコンソール付きで起勁E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-12 |
| **発見方況E* | R 拡張を無効化した後も新しい `CMD` が�E発。最新 `conhost.exe` の親子関係を追ったところ、`python.exe -> host_gmail_incremental_sync.py` に到達した、E|
| **影響篁E��** | 数刁E��とに `CMD` ウィンドウぁE1 つ開き、ユーザー操作を妨げた、E|
| **根本原因 (5 Why)** | **Why1**: 新しい `conhost.exe` が生成されてぁE��、E**Why2**: 親は `python.exe` で、`host_gmail_incremental_sync.py` を実行してぁE��、E**Why3**: そ�E親は `continuous_email_ingest_daemon.py` で、`subprocess.Popen()` により孁EPython を起動してぁE��、E**Why4**: Windows 向けの `CREATE_NO_WINDOW` 持E��がなく、既定でコンソール付き起動になってぁE��、E**Why5**: 常駐ハーネスから子�Eロセスを起動する際の「非表示起動」ルールがコードに絁E��込まれてぁE��かった、E|
| **修正冁E��** | `data/workspace/continuous_email_ingest_daemon.py` の `subprocess.Popen()` に Windows では `creationflags=subprocess.CREATE_NO_WINDOW` を渡すよぁE��正した、E|
| **修正ファイル** | `data/workspace/continuous_email_ingest_daemon.py`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `conhost.exe PID 13652` の親ぁE`python.exe PID 6160`、その親ぁE`continuous_email_ingest_daemon.py` であることを確認。既存�E `python.exe` / `conhost.exe` は停止済みで、次回起動から�E非表示フラグ付きで子�Eロセスが起動する構�Eにした、E|
| **Lessons Learned** | Windows 常駐スクリプトが別の Python を起動する場合、表示有無は明示しなぁE��既定挙動に引きずられる。UI を持たなぁE��助プロセスは、常に非表示起動をチE��ォルトにする方が安�E、E|
| **再発防止筁E* | Windows で `subprocess.Popen()` / `run()` を使ぁE��駐系スクリプトは、コンソール不要なめE`CREATE_NO_WINDOW` を標準化する。新しい `conhost.exe` が�Eた場合�E親子関係をたどり、まぁEdaemon からの子起動かを確認する、E|

---

## INC-010: Claudian 同種障害の自動検知欠妁E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | ユーザーから「同種障害を�E動検知するチェチE��頁E��まで追加」と要望。既存�E復旧後も、`claudian-spawn.log` と `claudian-bridge.log` を手動で読む運用に依存してぁE��、E|
| **影響篁E��** | Claudian の Windows 起動、bridge response shape、Ollama 直結設定、返答征E��遁E��の再発を即時に検知できず、�Eび「無反応」に見えるリスクが残ってぁE��、E|
| **根本原因 (5 Why)** | **Why1**: 復旧コード�E入ってぁE��が、�E発允E��を継続監視すめEwatchdog がなかった、E**Why2**: `spawn EINVAL`、`undefined.id`、`model not found`、空返答、pending turn が別ログに散在してぁE��、E**Why3**: 古ぁE��敗ログが残るため、単紁Egrep では誤検知しやすく「最後�E成功が最後�E失敗を上回ったか」�E判定が忁E��だった、E**Why4**: 一次復旧を優先した結果、E��用 observability の実裁E��後回しになってぁE��、E**Why5**: Claudian 専用の `status.json` / `harness_status.json` を�Eす外付けハ�Eネスが未整備だった、E|
| **修正冁E��** | `data/workspace/claudian_watchdog.py` を追加し、E1) `.claudian/claudian-settings.json` と plugin `data.json` の設定整合性、E2) spawn log の `spawn EINVAL` 再発有無と configured path 回復、E3) bridge log の `undefined.id` / `model 'openai/qwen3:8b' not found` / 空返筁E/ pending turn / 高遅延、E4) Ollama `/api/tags` による `qwen3:8b` 存在確認を自動判定するよぁE��した。あわせて `scripts/start_claudian_watchdog.ps1` を追加し、外付け常駐起動を可能にした、E|
| **修正ファイル** | `data/workspace/claudian_watchdog.py`, `scripts/start_claudian_watchdog.ps1`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `python data/workspace/claudian_watchdog.py --once` で status JSON を生成し、EつのチェチE��が�E力されることを確認する。`spawn EINVAL` は「履歴ありだが回復済み」、bridge は recent completed turn と latency、Ollama は `qwen3:8b` の存在を判定できる構�E、E|
| **Lessons Learned** | 復旧だけで終えると、�E発時�E初動がまた手動ログ調査に戻る。Windows wrapper めEbridge contract のような墁E��障害は、修正と同時に watchdog / status JSON まで入れて初めて運用品質になる、E|
| **再発防止筁E* | `claudian_watchdog.py` を定期実行また�E常駐させ、`data/workspace/claudian_watchdog_status.json` の `stage` / `findings` を監視対象にする。今征EClaudian 関連修正を�Eれるた�Eに、この watchdog へ新しい failure signature を追加する、E|

---

## INC-012: Claudian Codex モチE��選択肢が少なく軽量モチE��へ刁E��替えにくい
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | ユーザー報告、Elaudian の Codex モチE��ドロチE�Eダウンに `GPT-5.4` と `qwen3:8b` など一部しか出ず、より軽ぁE��チE��へ刁E��替えにくかった、E|
| **影響篁E��** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 配下�E Codex UI。選択肢不足により、E��度重視�E刁E��替えや追加モチE��の露出が運用依存になってぁE��、E|
| **根本原因 (5 Why)** | **Why1**: Codex モチE��一覧ぁE`main.js` 冁E�E静的配�Eにほぼ固定されてぁE��、E**Why2**: 既存実裁E�E `OPENAI_MODEL` 1件だけを特別扱ぁE��、褁E��モチE��の列挙を受け取れなかった、E**Why3**: ローカル/追加モチE��を�EしたぁE��合でも、UI に渡せる環墁E��数が単一モチE��前提だった、E**Why4**: そ�Eため軽量モチE��めE��E��追加モチE��を�Eすたびにコード変更が忁E��だった、E**Why5**: 「既定モチE��」と「環墁E��来の追加モチE��」をマ�Eジする共通�E琁E�� Codex 側に未実裁E��った、E|
| **修正冁E��** | `main.js` の Codex モチE��定義に `gpt-5.3-codex` と `gpt-5.2` を追加し、さらに `OPENAI_AVAILABLE_MODELS` / `CODEX_AVAILABLE_MODELS` から褁E��モチE��を読み込んでドロチE�Eダウンへ統合するよぁE��正した。あわせて `.claudian/claudian-settings.json` と plugin `data.json` に `OPENAI_AVAILABLE_MODELS` を追加し、軽量寁E��の候補を即時選択可能にした、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `node --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` で構文エラーなしを確認。`OPENAI_AVAILABLE_MODELS` に列挙したモチE��が設定ファイル上で保持され、既定モチE��と重褁E��去しつつ UI に渡る構�Eになった、E|
| **Lessons Learned** | モチE��選抁EUI は固定�E挙に寁E��すぎると運用速度が落ちる。追加頻度が高い値は、既定値を持ちつつ環墁E��数から拡張できる形にしておくと保守しめE��ぁE��E|
| **再発防止筁E* | Claudian の Codex モチE��追加時�E `OPENAI_AVAILABLE_MODELS` を優先的に更新し、コード変更は既定候補やマ�EジロジチE��の改喁E��に限定する。今後新モチE��を足す際も単一 `OPENAI_MODEL` だけに依存しなぁE��とをレビュー頁E��に加える、E|

---

## INC-011: Claudian 初回応答�E体感遁E��
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | ユーザーぁE`Hello` 後�E返答征E��が長すぎると報告。bridge log では 2026-04-11 13:10:40 JST の送信から 13:13:37 JST の返答完亁E��で紁E77秒かかってぁE��、E|
| **影響篁E��** | Claudian の軽ぁE��話でも「無反応」に見えめE��く、利用継続性を下げてぁE��、E|
| **根本原因 (5 Why)** | **Why1**: `Hello` のような軽ぁE�E力でもローカル `qwen3:8b` の応答完亁E��で征E��てから UI に全斁E��返してぁE��、E**Why2**: bridge は `stream:false` で completion 完亁E��に 1 回だぁE`delta` を送ってぁE��、E**Why3**: 初回メチE��ージ送信時には別スレチE��で会話タイトル生�Eも同時に走ってぁE��、E**Why4**: タイトル生�Eも本体と同じローカルモチE��を使ぁE��め、GPU/CPU 賁E��と征E��時間を余計に消費してぁE��、E**Why5**: 体感速度改喁E�Eための「�Eに斁E��を出す」「補助処琁E��ローカル即時化する」とぁE��最適化が bridge に未実裁E��った、E|
| **修正冁E��** | `codex_bridge.js` を更新し、E1) 通常応答�E Ollama OpenAI 互換 API めE`stream:true` で呼び出して `item/agentMessage/delta` を逐次送る、E2) `max_tokens: 160` と `temperature: 0.2` で短め�E安定寁E��にする、E3) タイトル生�Eリクエスト�EモチE��を呼ばぁEbridge 冁E��即時生成する、よぁE��した、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `node --check` で構文確認済み。ローカル再現でタイトル生�Eリクエスト�E即座に `Greet the assistant` を返すことを確認。通常会話は `item/agentMessage/start` が即時に出ることを確認した、E|
| **Lessons Learned** | ローカルモチE��では「最終完亁E��間」だけでなく「最初�E可視文字までの時間」を最適化しなぁE��、ユーザー体感は大きく悪化する。補助タスクぁEdeterministic に処琁E��きるならモチE��に投げなぁE��が安定する、E|
| **再発防止筁E* | Claudian の latency 改喁E��は、モチE��変更前に `streaming`、`token cap`、`title-generation bypass` のような transport 側対策を先に検討する。watchdog の latency チェチE��を継続し、�E度 2 刁E��E�E履歴が増える場合�E軽量モチE��追加を検討する、E|

---

## INC-007: Claudian `spawn EINVAL` 再、E���E�Eonfigured `cliPath` ぁEPATH 自動解決に負ける�E�E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | ユーザー報呁E`Error: spawn EINVAL`。`C:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` を確認すると、`data.json` では plugin 同梱 `codex.cmd` を指定してぁE��のに、実行時は `C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` が選ばれてぁE��、E|
| **影響篁E��** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 配下�E Codex 連携。Windows 環墁E�� Codex provider 初期化が失敗し、Obsidian から Codex セチE��ョンを開始できなぁE��E|
| **根本原因 (5 Why)** | **Why1**: Claudian ぁEglobal npm 配下�E `codex.cmd` を直接 spawn し、`spawn EINVAL` になった、E**Why2**: `codex_bridge.js` へ刁E��替える前段の CLI 解決で、設定済み `cliPath` より PATH 自動探索結果が優先されてぁE��、E**Why3**: `data.json` には plugin 同梱 `codex.cmd` が保存されてぁE��が、`resolveCodexCliPath` ぁEWindows で `findCodexBinaryPath(customEnv.PATH)` を�Eに返してぁE��、E**Why4**: そ�E結果、sibling bridge 探索めEglobal npm 配下を基準にし、存在しなぁE`codex_bridge.js` を見た後に危険な `.cmd` 直 spawn へ残留した、E**Why5**: 「ユーザーが�E示設定しぁECLI path を最優先する」とぁE��基本ルールぁEresolver に反映されてぁE��かった、E|
| **修正冁E��** | `resolveCodexCliPath` の優先頁E��を修正し、`cliPathsByHost` / `cliPath` の実在ファイルめEPATH 自動解決より先に採用するよう変更。設宁Epath を使った場合も spawn ログへ残すようにした、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `data.json` の `cliPath` ぁEplugin 同梱 `codex.cmd` を指してぁE��ことを確認。修正後ソースでは configured path を�Eに返すことを確認。`node --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` を実行し、構文エラーなしを確認、E|
| **Lessons Learned** | Windows の wrapper 回避だけでなく、「どの wrapper を選ぶか」�E優先頁E��も同じくらぁE��要。�E動探索は便利でも、�E示設定を上書きすると再発要因になりやすい。ログには「何を見つけたか」だけでなく「何を採用したか」を残す方が追跡しやすい、E|
| **再発防止筁E* | Windows resolver の回帰確認では、`configured path exists` / `PATH has different codex.cmd` の競合ケースを忁E��含める。spawn ログは採用 CLI path を残し、`.cmd` 直 spawn が起きたら即座に異常判定できるようにする、E|

---

## INC-008: Claudian `Cannot read properties of undefined (reading 'id')`
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | `spawn EINVAL` 解消後、Claudian 側で `Cannot read properties of undefined (reading 'id')` が発生。bridge log では `thread/start` が届いてぁE��が、対応する構造化応答が不足してぁE��、E|
| **影響篁E��** | Obsidian Vault の Claudian プラグイン、Eodex provider 初期化後に thread 作�EめEturn 開始で UI が継続不�Eになる、E|
| **根本原因 (5 Why)** | **Why1**: Claudian ぁE`result.thread.id` また�E `result.turn.id` を読み取ろぁE��して `undefined.id` になった、E**Why2**: `codex_bridge.js` は `initialize` 以外�E大半�EメソチE��に対して `{}` を返すだけで、Codex app-server 互換の応答形を返してぁE��かった、E**Why3**: `thread/start` の戻り値に `thread.id` / `thread.path` がなく、`turn/start` にめE`turn.id` がなかった、E**Why4**: 通知系も未実裁E��、turn 完亁E��征E��側が期征E��めE`turn/completed` めEagent message イベントが来なかった、E**Why5**: 起動確認を `initialize` 成功までで止めており、実際の turn 開始フローまでの互換性検証が不足してぁE��、E|
| **修正冁E��** | `codex_bridge.js` を最小限の Codex app-server 互換 bridge に拡張。`thread/start` / `thread/resume` / `turn/start` / `turn/interrupt` / `thread/compact/start` の応答を追加し、`thread.id` / `thread.path` / `turn.id` を返すよう修正。さらに `item/agentMessage/*` と `turn/completed` 通知を送るようにした、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **検証結果** | `node --check` で bridge の構文確認を実施。ローカル再現では `initialize` 後�E `thread/start` ぁE`thread.id` と `path` を返し、`turn/start` ぁE`turn.id` と `turn/completed` 通知を返すことを確認、E|
| **Lessons Learned** | transport 接続�E功と app-server 互換は別問題、ECP/JSON-RPC の「つながる」だけでは不十刁E��、UI が読む具体的なレスポンス shape まで合わせる忁E��がある、E|
| **再発防止筁E* | Claudian bridge の回帰確認に `initialize -> thread/start -> turn/start` の一連のスモークチE��トを追加し、`thread.id` / `turn.id` / `turn/completed` の存在を忁E��チェチE��にする、E|

---

## INC-009: Claudian 送信無反応！EiteLLM alias 不整合と Ollama 直結化�E�E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | ユーザーぁE`Hello` を送信してめEUI が無反応。`claudian-bridge.log` では `turn/start` まで進んでぁE��が、返答本斁E��空だった、E|
| **影響篁E��** | Obsidian Vault の Claudian プラグイン。送信自体�E通るが、返答が表示されず会話利用が実質不�E、E|
| **根本原因 (5 Why)** | **Why1**: Claudian では `turn/start` が完亁E��てぁE��のに応答本斁E��返らなかった、E**Why2**: bridge ぁELiteLLM の 404 エラーを空返答として扱ってぁE��、E**Why3**: LiteLLM proxy の alias `claude` / `codex` は冁E��で `openai/qwen3:8b` を参照し続け、Ollama 側で `model not found` になってぁE��、E**Why4**: config 修正だけでは proxy 冁E��の provider 解釈差を完�Eに潰せず、Claudian の対話経路が不安定なままだった、E**Why5**: Claudian が本当に忁E��としてぁE��のは LiteLLM 固有機�Eではなく、ローカル Ollama への安定しぁEchat completion 経路だった、E|
| **修正冁E��** | `codex_bridge.js` を環墁E��数ベ�Eスにし、`OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` から直接接続�Eを解決するよう変更、Elaudiian 設定を `http://127.0.0.1:11434/v1` + `qwen3:8b` に更新し、LiteLLM を経由せず Ollama へ直結する経路へ刁E��替えた。併せて `data/state/litellm_config.yaml` のローカルモチE��定義めELiteLLM 互換形式へ是正した、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/litellm_config.yaml`, `docs/INCIDENT_LOG.md` |
| **検証結果** | bridge 単体�E現で `initialize -> thread/start -> turn/start` を実行し、`Hello! How can I assist you today?` ぁE`item/agentMessage/delta` と `completed` で返ることを確認、E|
| **Lessons Learned** | proxy を間に挟�E設計�E柔軟だが、原因刁E��刁E��中は依存点が増える。ローカル単一路線で十�Eな機�Eは、まず最短経路で安定稼働させてから抽象化を足す方が安�E、E|
| **再発防止筁E* | Claudian の疎通確認では、UI 表示だけでなぁEbridge 単体�E `Hello` スモークチE��トを維持する、EiteLLM alias を使ぁE��合も、ローカル Ollama 直結�E代替経路を残しておく、E|

---

## INC-006: Claudian `spawn EINVAL` 再発�E�Elobal `codex.cmd` と bundled bridge の刁E���E�E| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-11 |
| **発見方況E* | Claudian 起動時に `spawn EINVAL`。`C:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` を確認すると、`C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` を直接 spawn して失敗してぁE��、E|
| **影響篁E��** | Obsidian Vault の Claudian プラグインから Codex app-server を起動できず、�E期化に失敗、E|
| **根本原因 (5 Why)** | **Why1**: Windows で `codex.cmd` めE`spawn(..., { shell: false })` し、`spawn EINVAL` が�E発した、E**Why2**: `.cmd` を直接起動しなぁE��め�E回避は入ってぁE��が、`codex_bridge.js` の探索ぁEglobal npm 配下�E sibling を前提にしてぁE��、E**Why3**: 実際の環墁E��は `codex.cmd` は `C:\\Users\\yasu\\AppData\\Roaming\\npm` にあり、`codex_bridge.js` は `data/state/Obsidian Vault/.obsidian/plugins/claudian/` に同梱されてぁE��同じ場所に無かった、E**Why4**: bridge が見つからなぁE��めE`node + codex_bridge.js` の直起動へ刁E��替わらず、既存�E危険な `.cmd` spawn 経路に残留した、E**Why5**: global CLI と plugin bundled asset が�E離された�E置を想定した最後�Eフォールバックが未実裁E��った、E|
| **修正冁E��** | Windows wrapper 検�E時�E bridge 解決頁E�� `preferred PATH bridge` -> `codex.cmd sibling bridge` -> `plugin bundled codex_bridge.js` に変更。spawn 失敗時の retry 経路も同じ頁E��に統一し、global npm 配下に bridge が無くてめEbundled bridge めE`node.exe` で起動できるようにした、E|
| **修正ファイル** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60983`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61007` |
| **検証結果** | ソース確認で bridge 解決頁E�� bundled fallback が追加されたことを確認。`main.js` は `node` で構文チェチE��済み。`codex_bridge.js` 側の initialize 応答�E `platformOs=windows`, `platformFamily=windows` を返すことを�E確認。ログ上�E失敗経路 (`codex.cmd` 直 spawn) は今回の刁E��で回避される、E|
| **Lessons Learned** | Windows の `.cmd` 回避は「bridge が見つかる前提」だけでは不十刁E��ELI と bridge が別配置になめEnpm/plugin 混在環墁E��前提に、最後に bundled asset へ戻れる設計が忁E��、E|
| **再発防止筁E* | Windows 起動コードでは wrapper 実体と bridge 実体�E配置刁E��を常に想定する。bridge 解決頁E��ログへ残し、`.cmd` を直接 spawn する経路を回帰確認対象にする、E|
1. Windows では「PATH にある」だけでは不十刁E��、`spawn` の実行形式差まで見る忁E��がある、E2. `initialize` はタイムアウトだけでなく、応答スキーマ不備でも二段目の障害を起こすため、起動と応答�E両方を同時に検証する、E3. 既存ラチE��ー (`codex.cmd`) を活かす拡張の方が、別系統の起動経路を増やすより安�Eに導�Eできる、E## INC-020: Gmail priority backfill container path was unstable on the mini PC
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | A manual priority backfill run for `2026-01-01` onward failed first with `returncode 137` even after reducing the month scope, while host-side Gmail incremental sync for the same query completed successfully. |
| **Impact** | Historical Gmail ingestion was not progressing beyond recent incremental sync, so older mail from January 2026 onward was not being backfilled continuously. |
| **Root Cause (5 Why)** | **Why1**: `run_priority_gmail_backfill.py` executed Gmail indexing inside the gateway container via `docker exec`. **Why2**: On this mini PC, that container backfill path was unstable and the process was killed with exit `137` before completing a month-sized chunk. **Why3**: The daemon had been restarted with `--skip-full-backfill`, so the unstable full-backfill path stayed bypassed and historical ingestion never resumed. **Why4**: The original backfill implementation used a heavier execution path than the already-stable host-side temp-DB promotion flow used by `host_gmail_incremental_sync.py`. **Why5**: The system lacked a bounded, host-side historical backfill path that reused the proven safe SQLite promotion pattern. |
| **Fix** | Switched `data/workspace/run_priority_gmail_backfill.py` from container execution to the host-side temp-DB promotion pattern, added bounded CLI args (`--start-date`, `--end-date`, `--max-messages-per-chunk`), reduced the default monthly backfill chunk to `500`, and removed `--skip-full-backfill` from `data/workspace/email_continuous_watchdog.py` so restarted daemons can resume historical backfill. |
| **Files** | `data/workspace/run_priority_gmail_backfill.py`, `data/workspace/email_continuous_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python data/workspace/run_priority_gmail_backfill.py --start-date 2026-01-01 --end-date 2026-01-31 --max-messages-per-chunk 500` completed with `returncode 0`; January chunk result was `candidates=500`, `indexed=160`, `skipped=340`, `errors=0`. Direct host sync for the same query also succeeded earlier with `indexed=411`, `skipped=89`, `errors=0`. |
| **Lessons Learned** | For long-running Gmail backfills on this mini PC, reuse the host-side temp SQLite promotion path that already proved stable. Prefer bounded month or date windows before re-enabling unattended historical catch-up. |
| **Prevention** | Keep full backfill chunk sizes bounded, preserve lock-based serialization with `EmailDbLock`, and validate backfill changes with a single-month run before allowing unattended daemon recovery to trigger them. |
## INC-021: Blacklisted Gmail messages were still stored in `emails`
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | Review of the Gmail ingest flow showed that blacklist and newsletter filters only affected task extraction and did not prevent blacklisted messages from being written into `emails` and SQLite FTS. |
| **Impact** | Newsletter and blocked notification mail still consumed SQLite rows, FTS space, and downstream processing time even when they were excluded from `tasks`. |
| **Root Cause (5 Why)** | **Why1**: `index_gmail()` fetched and parsed Gmail messages, then always called `upsert_record()`. **Why2**: The sender filter file was only consulted inside `looks_like_task()`. **Why3**: `looks_like_task()` runs after the email row is already inserted, during task extraction. **Why4**: The system optimized task quality but not storage hygiene. **Why5**: There was no pre-storage Gmail filter step that reused the existing blacklist, newsletter, and whitelist logic. |
| **Fix** | Added a Gmail pre-storage filter in `data/workspace/email_search_index.py` so blacklisted and newsletter messages are skipped before insertion into `emails`, and exposed `skipped_by_filter` in the Gmail ingest summary. Added `email ingest watchdog restart` to `data/workspace/email_rag_sender_filters.json` so watchdog restart notifications are dropped before DB insertion. |
| **Files** | `data/workspace/email_search_index.py`, `data/workspace/email_rag_sender_filters.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Static validation via `python -m py_compile data/workspace/email_search_index.py`. Runtime Gmail summaries now include `skipped_by_filter`, enabling direct observation of pre-storage blacklist filtering in future sync cycles. |
| **Lessons Learned** | On this mini PC, blacklist and newsletter rules should be applied as early as possible to reduce DB growth and FTS churn, not only at task extraction time. |
| **Prevention** | Keep sender and content filters shared between task classification and pre-storage gating, and include skip counters in operational status so filter effectiveness is visible without inspecting the DB manually. |
## INC-022: Continuous patrol missed local API outages and user-intent drift
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that local APIs such as `email_blacklist_hub` often fell unnoticed, and earlier Gmail ingest drift had shown that patrols were checking heartbeat files without fully validating whether user-requested behavior was still being achieved. |
| **Impact** | Local tools could be down while dashboards still looked broadly healthy, and user-requested behaviors such as January 2026 onward Gmail backfill or blacklist effectiveness observability could drift without prompt correction. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` focused on watchdog freshness and status JSONs, but not on direct local API reachability. **Why2**: `email_blacklist_hub` had a start script, yet neither `continuous_system_improvement.py` nor `auto_repair_allowed.py` monitored or restarted it. **Why3**: Patrol logic did not audit contract-level expectations such as “Gmail daemon must not run with `--skip-full-backfill` Eor “filter telemetry must remain visible. E**Why4**: `data/workspace` resolves through the `E:` workspace path on this machine, so repo-root discovery based only on `__file__.resolve()` could point start actions at non-existent `E:\scripts\...` paths. **Why5**: The patrol layer had grown around component heartbeat checks, but not around user-intent contracts and mixed-drive path reality on this mini PC. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` to probe `email_blacklist_hub` API endpoints directly, verify Gmail backfill drift and filter telemetry, and expose those checks in summary/status output. Extended `data/workspace/auto_repair_allowed.py` to restart `email_blacklist_hub` when stale or missing. Added repo-root fallback resolution in both scripts so start actions use the actual repo `scripts/` directory even when `data/workspace` resolves through `E:`. Restarted `email_blacklist_hub` and re-ran the patrol until summary showed the API reachable and `skipped_by_filter` visible. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py` passed. `http://127.0.0.1:8791/api/email-blacklist/config` returned live JSON again. `python data/workspace/host_gmail_incremental_sync.py --gmail-max-messages 5 --gmail-fallback-days 1` completed with `skipped_by_filter=2`. `data/workspace/continuous_system_improvement_status.json` at `2026-04-12 07:12:58 JST` showed `Email blacklist hub API is reachable`, `Historical Gmail backfill still targets January 2026 onward`, and `Gmail filter telemetry is visible in ingest summaries`. |
| **Lessons Learned** | Heartbeat files are necessary but not sufficient. On this environment, patrols must verify API endpoints and a small set of explicit user-intent contracts, not just whether a process exists. |
| **Prevention** | Keep critical local APIs in the patrol catalog, keep at least one observable metric for each user-facing optimization (such as `skipped_by_filter`), and resolve repo-root paths defensively whenever workspace files may be mirrored onto another drive. |
## INC-023: Email Search API was not supervised and degraded the portal experience
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that `http://localhost:8088/apps/email_search/` looked down during a broader mini PC slowdown check. Investigation showed the portal page itself was reachable, but its backend API on `127.0.0.1:8792` was not running. |
| **Impact** | The Email Search UI loaded from the portal but could not return stats or search results, so it appeared broken. The system also lacked automatic restart for that API, making the failure recur silently after process loss. |
| **Root Cause (5 Why)** | **Why1**: `apps/email_search/index.html` depends on `email_search_api.py` at `127.0.0.1:8792`. **Why2**: The API had no dedicated Windows start script or watchdog integration. **Why3**: `continuous_system_improvement.py` and `auto_repair_allowed.py` originally monitored other local APIs but not Email Search. **Why4**: The mini PC slowdown symptoms prompted a check of background activity, revealing that watchdog cadence was moderate while the heavier pressure came from `Memory Compression`, `vmmemWSL`, Docker/WSL workloads, and VS Code processes. **Why5**: Service supervision coverage had focused on Gmail, Docker UI, and Blacklist Hub first, leaving Email Search outside the local API patrol catalog. |
| **Fix** | Added `scripts/start_email_search_api.ps1` to start and health-check `data/workspace/email_search_api.py`. Extended `data/workspace/continuous_system_improvement.py` to probe `http://127.0.0.1:8792/api/stats` and surface Email Search health in patrol summaries. Extended `data/workspace/auto_repair_allowed.py` to restart Email Search API when the process is missing or the API probe fails. Started the API and confirmed the portal backend was serving again. |
| **Files** | `scripts/start_email_search_api.ps1`, `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/email_search_api.py` passed. `http://127.0.0.1:8792/api/stats` returned JSON with `total_emails=23212` and `total_tasks=9172`. `data/workspace/continuous_system_improvement_status.json` showed `Email search API is reachable`. |
| **Lessons Learned** | For portal apps backed by local host APIs, supervising only the static UI path is not enough. The host API must be in the patrol catalog with a concrete health probe. |
| **Prevention** | Keep each portal app’s host API paired with a start script and patrol probe, and treat UI reachability and backend reachability as separate checks. |

## INC-024: `minipc_optimizer` ぁEmini PC の実環墁E�� Lite 停止に失敗してぁE��

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 07:32 JST |
| **Detection** | User approved stopping safe background services to lighten the mini PC. `python data/workspace/minipc_optimizer.py apply-lite` first failed with `open E:\\clawstack_v2\\docker-compose.yml` and then `no such service: infinity`, even though candidate containers were visibly running. |
| **Impact** | The lightweight-mode harness could report heavy candidates but could not actually stop them on this machine, so memory-heavy optional services stayed online and the user-facing slowdown would persist longer than necessary. |
| **Root Cause (5 Why)** | **Why1**: `minipc_optimizer.py` derived `ROOT` from `Path(__file__).resolve()`, which can resolve through the `E:` workspace mirror on this mini PC. **Why2**: That made the compose path point to a non-existent `E:\\clawstack_v2\\docker-compose.yml` instead of the real repo on `D:`. **Why3**: After fixing the root, the harness still used `docker compose stop <service>`, assuming guessed service names exactly matched compose service ids. **Why4**: At least one running container (`clawstack-unified-infinity-1`) did not map cleanly enough for compose-stop by guessed service name, causing `no such service`. **Why5**: The optimizer had been designed around compose topology, but this mini PC now has mixed-drive path reality and practical container-name truth that are more reliable for emergency lightweight actions. |
| **Fix** | Updated `data/workspace/minipc_optimizer.py` to resolve the repo root by searching for the actual repo containing `clawstack_v2/docker-compose.yml` and `data/workspace`, falling back only if needed. Reworked Lite stopping to target currently running container names via `docker stop` instead of `docker compose stop`, so optional services can be stopped even when compose service ids drift from guessed names. |
| **Files** | `data/workspace/minipc_optimizer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. `python data/workspace/minipc_optimizer.py apply-lite` returned `changed=true` and stopped 21 optional containers including `infinity`, `clickhouse`, `paperless`, `docling`, `metabase`, `stirling_pdf`, `portainer`, and `uptime-kuma`. A follow-up `python data/workspace/minipc_optimizer.py status` reported `heavyRunningCandidates=[]`, and `docker ps` no longer listed those optional services as running. |
| **Lessons Learned** | On this machine, host-side harnesses should prefer runtime-truth checks over inferred compose metadata when doing safe operational reductions. Mixed-drive path resolution and partial compose drift are normal enough that emergency controls should degrade gracefully. |
| **Prevention** | Reuse repo-root fallback logic in every host harness that launches or stops services, and prefer container-name based safe-stop flows for Lite mode unless a strong reason exists to require compose service ids. |

## INC-025: Gateway memory bloat was caused by duplicate `ingest_watchdog.py` processes and the harness lacked a full live inventory

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 21:12 JST |
| **Detection** | During mini PC slowdown analysis, `docker stats` showed `clawstack-unified-clawdbot-gateway-1` consuming about `4.8 GiB` RSS. Inspecting processes inside the container revealed hundreds of duplicate `python3 /home/node/clawd/ingest_watchdog.py` instances. At the same time, the AI Engineering Harness page did not yet expose a complete host API and major Docker service inventory, which made the drift harder to see quickly. |
| **Impact** | The gateway container consumed several GiB of memory, increasing overall pressure on `vmmemWSL` and host memory compression, and the existing dashboard did not clearly show which APIs or services were up, down, or intentionally stopped. |
| **Root Cause (5 Why)** | **Why1**: `paperless_rag_watchdog.py` only treated “no ingest process Eas unhealthy and did not detect duplicate `ingest_watchdog.py` processes. **Why2**: Its restart flow mainly relied on a single pidfile-oriented path, so stale or multiplied watchdog processes could survive while new ones were launched. **Why3**: Repeated repair attempts over time allowed duplicate `ingest_watchdog.py` processes to accumulate inside the gateway container. **Why4**: `continuous_system_improvement.py` summarized many patrol signals but did not yet collect a single inventory of host APIs, key Docker services, and gateway ingest watchdog counts. **Why5**: Operational observability had evolved around individual status files rather than a compact live inventory tied to the user-facing Harness card. |
| **Fix** | Updated `data/workspace/paperless_rag_watchdog.py` to count running `ingest_watchdog.py` processes, mark duplicate counts as unhealthy, and restart by killing all matching ingest watchdog processes before relaunching a single one. Updated `data/workspace/continuous_system_improvement.py` to collect `hostApiInventory`, `serviceInventory`, and `gatewayIngestWatchdogCount`, and to schedule `run_paperless_rag_watchdog` when duplicate gateway ingest processes are detected. Expanded `data/workspace/apps/ai_engineering_harness_status/index.html` to show the gateway ingest watchdog count, a full Host APIs panel, and a Major Docker Services panel. Restarted both the Windows `paperless_rag_watchdog.py` and `continuous_system_improvement.py` background patrols so the new logic is active. Manually collapsed duplicate gateway ingest watchdog processes back to a single running process. |
| **Files** | `data/workspace/paperless_rag_watchdog.py`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/paperless_rag_watchdog.py data/workspace/continuous_system_improvement.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'ps -ef | grep ingest_watchdog.py | grep -v grep | wc -l'` returned `1` after cleanup. `docker stats` dropped gateway memory from about `4.8 GiB` to about `580 MiB`. `python data/workspace/continuous_system_improvement.py --once` produced `continuous_system_improvement_status.json` with `context.hostApiInventory`, `context.serviceInventory`, and `context.gatewayIngestWatchdogCount`, and the status summary now reports `Gateway ingest watchdog process count is healthy` with `processes=1`. |
| **Lessons Learned** | For long-running gateway sidecars, “process exists Eis not a sufficient health test. The harness must detect multiplicity, not just absence. Operational cards are much more useful when they display both health summaries and the current live inventory that explains those summaries. |
| **Prevention** | Keep duplicate-process counts as first-class patrol signals, restart Windows patrol daemons after harness code changes, and expose the up/down state of major APIs and services on the Harness page so silent drift is visible before memory bloat becomes user-visible. |

## INC-026: Paperless ingest stopped because Paperless was offline and the gateway used a stale direct token path

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:02 JST |
| **Detection** | User requested Paperless ingest recovery after investigation showed repeated `401 Unauthorized` in `/home/node/clawd/ingest_watchdog.log`, stale `paperless_rag_watchdog` warnings, and `clawstack-unified-paperless-1` stopped with `Exited (137)`. |
| **Impact** | Paperless document ingestion into `universal_knowledge` was no longer progressing, watchdogs kept trying to revive the ingest loop, and the mini PC carried extra background churn without actually indexing new Paperless documents. |
| **Root Cause (5 Why)** | **Why1**: The Paperless container itself was not running, so the ingest path was intermittently unreachable. **Why2**: Even when Paperless was available again, `data/workspace/ingest_watchdog.py` still used a hard-coded legacy API token and direct `http://paperless:8000` target. **Why3**: That legacy token was no longer valid for the current Paperless API, causing repeated `401 Unauthorized`. **Why4**: On this mini PC, the gateway could successfully authenticate through `http://host.docker.internal:8000`, while the direct container alias path returned `Invalid token`, so the old fixed endpoint was no longer the reliable route. **Why5**: Paperless ingest credentials and route selection had been embedded in scripts instead of being kept in one host-editable operational config. |
| **Fix** | Restarted `clawstack-unified-paperless-1`, verified the Paperless API on `127.0.0.1:8000`, generated a fresh API token via `/api/token/`, and moved Paperless ingest settings into `data/workspace/paperless_ingest_config.json`. Updated `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, and `data/workspace/audit_paperless_ingest_alignment.py` to consume that config instead of a hard-coded token. Switched the gateway ingest route to `http://host.docker.internal:8000`, updated `paperless_rag_watchdog.py` to count only real Python ingest processes, and reran the Paperless audit using host-side fallbacks. |
| **Files** | `data/workspace/paperless_ingest_config.json`, `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, `data/workspace/audit_paperless_ingest_alignment.py`, `data/workspace/paperless_rag_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `docker start clawstack-unified-paperless-1` brought Paperless back to `Up ... (healthy)`. `POST http://127.0.0.1:8000/api/token/` with `admin/admin` returned a fresh token. From inside the gateway, `requests.get('http://host.docker.internal:8000/api/documents/?page_size=1', headers={'Authorization': 'Token ...'})` returned `200`, and importing `ingest_watchdog.py` inside the gateway showed `PAPERLESS_URL=http://host.docker.internal:8000`. `paperless_rag_watchdog_status.json` then reported `stage=healthy`, `ingestAlive=true`, `ingestProcessCount=1`. `python data/workspace/audit_paperless_ingest_alignment.py --recent-limit 10` completed with `status=healthy` and no missing recent documents. |
| **Lessons Learned** | For Paperless on this mini PC, the stable path is not just “container-to-container by service name E Authentication and reachability can diverge between the direct container alias and the host-exposed route, so the operational config needs an explicit chosen endpoint. |
| **Prevention** | Keep Paperless ingest token and base URL in a dedicated workspace config file, avoid hard-coded long-lived tokens in scripts, and validate both “API auth works Eand “audit sees recent docs Eafter any Paperless restart or Lite-mode service reduction. |

## INC-027: Patrols needed to treat `401/403` as outage-equivalent and semi-automate Paperless token renewal

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:14 JST |
| **Detection** | User requested that `401/403` responses be treated as patrol failures rather than mere “API responded Esignals, and asked for Paperless-style token reissue to be semi-automated. Existing API inventory cards could show up/down, but auth drift still required manual digging. |
| **Impact** | An API could be effectively unusable while still appearing reachable, and token-backed integrations like Paperless ingest could silently degrade until a human manually reissued credentials and updated config. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` treated successful TCP/HTTP response handling and authentication validity as the same concept. **Why2**: `401/403` were not being elevated into explicit auth-failure patrol weaknesses. **Why3**: Paperless ingest token refresh existed only as a manual recovery pattern from the previous incident, not as a reusable harness action. **Why4**: `auto_repair_allowed.py` did not have a direct rule for “auth is stale but service is otherwise reachable E **Why5**: Operational hardening had focused first on process recovery and freshness, leaving auth-contract drift as a separate manual concern. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` so HTTP probes classify `401/403` as `authFailure`, expose that on `hostApiInventory`, and raise explicit weaknesses such as `paperless_ingest_auth`. Added `refresh_paperless_ingest_token.py` to mint a fresh Paperless API token from the running Paperless container credentials and update `paperless_ingest_config.json`. Integrated that refresh action into both `continuous_system_improvement.py` and `auto_repair_allowed.py`. Updated `data/workspace/apps/ai_engineering_harness_status/index.html` so host API rows show `AUTH 401/403` instead of looking like generic connectivity failures. Also aligned gateway ingest-process counting in `continuous_system_improvement.py` with `pgrep` so the dashboard does not overcount wrapper shells. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `data/workspace/refresh_paperless_ingest_token.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/refresh_paperless_ingest_token.py` passed. `python data/workspace/refresh_paperless_ingest_token.py` completed and wrote `paperless_token_refresh_status.json`. A fresh `continuous_system_improvement.py --once` run showed `Paperless ingest API authentication is valid` and included `paperless_ingest_auth` in `hostApiInventory`. `auto_repair_allowed.py` completed with `paperless_token` rule evaluating `healthy`, confirming the new semi-automatic path is wired in. |
| **Lessons Learned** | For operations patrols, `reachable` is not enough. Authentication validity is part of availability when a user-facing workflow depends on it. |
| **Prevention** | Keep auth-backed probes separate from plain liveness checks, surface them on the portal card, and maintain one dedicated token-refresh harness per long-lived local integration that depends on renewable credentials. |

## INC-028: Auto-repair had stale target assumptions for scheduled reports and missed dead Paperless watchdogs

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:49 JST |
| **Detection** | A weakness review of the current mini PC patrol stack showed two avoidable blind spots: `auto_repair_allowed.py` still tried to run scheduled report sync through a non-existent `clawstack-unified-learning_engine-1` container, and it could mark `paperless_rag` healthy even when `paperless_rag_watchdog.py` itself was no longer running. |
| **Impact** | Scheduled-report repair attempts produced misleading `No such container` failures instead of the real underlying cause, and Paperless ingest supervision could silently degrade if the Windows watchdog died while the ingest heartbeat remained fresh for a while. |
| **Root Cause (5 Why)** | **Why1**: `auto_repair_allowed.py` had an old hard-coded `docker exec clawstack-unified-learning_engine-1 ...` command. **Why2**: The environment had moved to `wsl_native` and no longer guaranteed that container name or a container-based execution path for this task. **Why3**: The same script evaluated `paperless_rag` only from JSON freshness, not from the Windows watchdog process itself. **Why4**: That allowed a dead watchdog to be masked by still-fresh ingest heartbeat files. **Why5**: Repair logic had evolved around status files first, and some operational assumptions were not updated when the runtime topology changed. |
| **Fix** | Updated `data/workspace/auto_repair_allowed.py` so scheduled-report repair now executes the host-side `scheduled_report_search.py` directly instead of targeting the removed container name. Added an explicit process-presence check for `paperless_rag_watchdog.py` before declaring Paperless RAG healthy, so auto-repair can restart the watchdog when the Windows process is missing. |
| **Files** | `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/auto_repair_allowed.py` passed. A fresh `python data/workspace/auto_repair_allowed.py` run restarted `paperless_rag_watchdog.py` successfully and showed `scheduled_reports_sync` invoking the host-side script path instead of the removed container. The scheduled report sync still failed, but now with the true cause: upstream `n8n` API timeout, not a fake container-name mismatch. |
| **Lessons Learned** | Repair harnesses should point at the smallest stable execution surface available on the host, and liveness of a watchdog process must be checked separately from freshness of the child service it supervises. |
| **Prevention** | Prefer host-side script entry points over fragile container-name assumptions for maintenance jobs, and always combine `status freshness` with `process existence` when supervising watchdog-style services. |

## INC-029: Scheduled-report sync used the wrong n8n auth path and gateway ingest had multiple owners

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 23:25 JST |
| **Detection** | User requested root-cause investigation for `n8n timeout` and `gateway duplicate ingest`. The scheduled report repair path had stopped failing with a fake container-name error, but still timed out while probing `host.docker.internal:5679`. Separately, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "ps -o pid,ppid,lstart,cmd -C python3 | grep ingest_watchdog.py"` showed a new `ingest_watchdog.py` process every ~5 minutes with `PPID 1`, confirming duplicate ownership. |
| **Impact** | Scheduled report sync could not read workflow executions reliably, so `scheduled_reports` stayed stale. Gateway memory and CPU were wasted by many duplicate `ingest_watchdog.py` processes, worsening mini PC responsiveness and risking repeated Paperless ingest churn. |
| **Root Cause (5 Why)** | **Why1**: `scheduled_report_search.py` only tried n8n public API-key routes and kept `host.docker.internal` in the host-side candidate set. **Why2**: On this machine, host access to `127.0.0.1:5679/rest/login` succeeds, but API-key access to `/api/v1` and `/rest` returns `401`, and `host.docker.internal:5679` can time out from the Windows host. **Why3**: The script had no login-cookie fallback even though other repo utilities already used `n8n-auth` cookies successfully. **Why4**: Gateway ingest was started by more than one control plane: container boot plus the active n8n workflow `Ingest Watchdog Supervisor`. **Why5**: Lifecycle ownership for `ingest_watchdog.py` was never reduced to one authoritative watchdog, so overlapping restart paths kept multiplying the process. |
| **Fix** | Updated `data/workspace/scheduled_report_search.py` to load `N8N_API_KEY` from env/`.env`, prefer localhost routes, and fall back to `POST /rest/login` with cached `n8n-auth` cookies when API-key auth returns `401/403`. Applied the same login fallback pattern to `data/workspace/create_scheduled_report_sync_workflow.py`. Updated `data/workspace/recreate_workflows.py` so the `Ingest Watchdog Supervisor` workflow is preserved but explicitly deactivated, with future re-runs keeping it inactive instead of re-enabling duplicate restarts. Clarified `data/state/entrypoint.sh` so host-side `paperless_rag_watchdog` is the intended restart owner. Then deactivated n8n workflow `VBQMPFGWSVtwy2Vy`, killed all real `ingest_watchdog.py` processes in the live gateway container, and relaunched a single instance. |
| **Files** | `data/workspace/scheduled_report_search.py`, `data/workspace/create_scheduled_report_sync_workflow.py`, `data/workspace/recreate_workflows.py`, `data/state/entrypoint.sh`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/scheduled_report_search.py data/workspace/create_scheduled_report_sync_workflow.py data/workspace/recreate_workflows.py` passed. Direct host login to `http://127.0.0.1:5679/rest/login` returned `200` and an `n8n-auth` cookie. `python data/workspace/scheduled_report_search.py sync --limit-executions 20` now completes successfully instead of timing out. `python data/workspace/recreate_workflows.py` reported `Ingest Watchdog Supervisor ... active=False`. After cleanup, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "sleep 330; pgrep -fc '^python3 /home/node/clawd/ingest_watchdog.py$'"` returned `1`, proving the 5-minute duplicate loop stopped. |
| **Lessons Learned** | For n8n on this mini PC, host-maintenance scripts must prefer the same login-cookie path that already works for other local admin tools; API-key-only assumptions are brittle. For long-running sidecars, one process owner is a design rule, not just an implementation detail. |
| **Prevention** | Keep host-side n8n maintenance utilities on localhost-first login fallback, and keep only one authoritative restart path for gateway sidecars. When a workflow is retained only for historical reference, explicitly keep it deactivated in the workflow recreation script so future maintenance runs do not resurrect duplicate process loops. |

## INC-030: Outbound notifications relied on policy text more than code-level allowlist enforcement

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 06:12 JST |
| **Detection** | User requested a hard-force guard so no information could ever be sent outside their own Telegram and `y.suzuki.hk@gmail.com`. Review found that policy files already restricted outbound delivery, but multiple runtime send paths still relied on local constants or environment values instead of one fail-closed allowlist check. |
| **Impact** | A drifted environment variable, reused helper, or future sender script could have delivered notifications to an unintended Telegram chat or Gmail recipient even though the written policy prohibited it. |
| **Root Cause (5 Why)** | **Why1**: Outbound safety was documented in `data/workspace/AGENTS.md` and `email_ops_policy.json`, but not centralized in a shared runtime guard. **Why2**: Several scripts (`email_continuous_watchdog.py`, `run_email_rag_ingest_report.py`, `risk_notification.py`, `workflow_healer.py`, `inbox_watcher.py`, `scheduled_notify.py`, and Telegram bridge code) each constructed their own send calls. **Why3**: Most of those senders trusted embedded constants or env-derived values rather than validating the destination at send time. **Why4**: The AI Engineering Harness had no dedicated visibility card for outbound-delivery policy enforcement. **Why5**: Safety hardening had focused first on `draft_only` policy and specific Gmail helper scripts, but not on one shared fail-closed outbound guard across all active notification paths. |
| **Fix** | Added `data/workspace/outbound_delivery_guard.py` as a shared fail-closed allowlist module that only permits Gmail delivery to `y.suzuki.hk@gmail.com` and Telegram delivery to chat `8173025084`, while recording policy status in `outbound_delivery_guard_status.json`. Wired the guard into `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, and `data/workspace/scripts/scheduled_notify.py`. Hardened `scripts/telegram_fast_bridge.js` to block non-allowlisted Telegram chat IDs at send/edit time. Extended `data/workspace/continuous_system_improvement.py` and `data/workspace/apps/ai_engineering_harness_status/index.html` so the Harness now shows an `Outbound Guard` card and raises a weakness if the enforced Gmail or Telegram targets drift. |
| **Files** | `data/workspace/outbound_delivery_guard.py`, `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, `data/workspace/scripts/scheduled_notify.py`, `scripts/telegram_fast_bridge.js`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for all changed Python files, and `node --check scripts/telegram_fast_bridge.js` passed. `outbound_delivery_guard_status.json` now shows `policyActive=true`, `allowedGmailRecipient=y.suzuki.hk@gmail.com`, and `allowedTelegramChatId=8173025084`. A fresh `continuous_system_improvement_status.json` run now includes the strength `Outbound delivery allowlist guard is enforced`, and the Harness page can render the new `Outbound Guard` card. |
| **Lessons Learned** | Written safety policy is not enough for outbound channels. Telegram and Gmail delivery must both be guarded by one runtime allowlist that fails closed. |
| **Prevention** | Require every future outbound sender to import the shared guard before network delivery, keep the Harness card visible so drift is obvious, and treat any non-allowlisted destination as a hard error instead of a warning. |

## INC-031: Telegram bridge stopped replying because runtime ownership drifted away from the supervised implementation

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 |
| **Detection** | User reported that Telegram messages no longer received replies after a mini PC freeze/slowdown period. Investigation found the last successful Telegram reply recorded at `2026-04-13 08:10:26 JST`, while runtime status later pointed to a live `powershell.exe -File scripts\\telegram_fast_bridge_v3.ps1` process instead of the monitored `node scripts\\telegram_fast_bridge.js` bridge. |
| **Impact** | Telegram could silently stop behaving as expected while the repo still contained a newer hardened bridge implementation. Recovery was unreliable because the watchdog, startup task, and active runtime were not aligned on one canonical process owner. |
| **Root Cause (5 Why)** | **Why1**: Multiple Telegram bridge implementations (`telegram_fast_bridge.js`, `telegram_fast_bridge.ps1`, `telegram_fast_bridge_v2.ps1`, `telegram_fast_bridge_v3.ps1`) coexisted. **Why2**: The active runtime had drifted to `telegram_fast_bridge_v3.ps1`, while the startup script and recent hardening targeted `telegram_fast_bridge.js`. **Why3**: The watchdog only checked pid/status freshness and did not verify that the running process actually matched the canonical implementation. **Why4**: The Windows Startup folder and scheduled-task setup did not enforce one authoritative owner end to end, so an older/manual PowerShell bridge could survive outside the intended recovery path. **Why5**: Operational supervision focused on liveness files first, but not on implementation drift between legacy and canonical Telegram bridge entrypoints. |
| **Fix** | Updated `scripts/start_telegram_fast_bridge.ps1` to stop all repo-local Telegram bridge variants before starting the canonical `node scripts/telegram_fast_bridge.js` process, and to log startup actions in `data/state/telegram_fast/startup.log`. Updated `scripts/watchdog_telegram_bridge.ps1` to detect legacy PowerShell bridge variants, duplicate bridge processes, and status-pid mismatch, then restart only the canonical JS bridge. Updated `scripts/check_telegram_fast_bridge.ps1` so diagnostics now show the actual bridge command line and implementation type. Updated `scripts/install_telegram_fast_bridge_startup.ps1` so watchdog installation and login-time startup are handled together, with Windows Startup-folder fallback if scheduled-task creation is denied. |
| **Files** | `scripts/start_telegram_fast_bridge.ps1`, `scripts/watchdog_telegram_bridge.ps1`, `scripts/check_telegram_fast_bridge.ps1`, `scripts/install_telegram_fast_bridge_startup.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `powershell -ExecutionPolicy Bypass -File scripts/install_telegram_fast_bridge_startup.ps1` ensured watchdog installation and login-start fallback. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` stopped the drifted PowerShell bridge and launched the canonical Node bridge. `powershell -ExecutionPolicy Bypass -File scripts/check_telegram_fast_bridge.ps1` now reports the live `telegram_fast_bridge.js` command line. `node --check scripts/telegram_fast_bridge.js` passed, and `watchdog_telegram_bridge.ps1` now restarts when a legacy PowerShell implementation is detected. |
| **Lessons Learned** | For long-poll bots, "a process exists" is not enough. The harness must verify that the supervised implementation is the one actually consuming updates. |
| **Prevention** | Keep one canonical Telegram bridge owner, make watchdogs validate command-line identity in addition to pid freshness, and reinstall startup/watchdog tasks together whenever the Telegram runtime path changes. |

## INC-032: Workflow Healer crashed after n8n execution-list API shape drift and always returned a failure exit code

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:04 JST |
| **Detection** | User reported that `Workflow Healer` had crashed. Investigation of `/home/node/clawd/workflow_healer.log` showed repeated `FATAL: 0` every 15 minutes from `2026-04-13 21:15 JST` onward. A traced manual run inside `clawstack-unified-clawdbot-gateway-1` reproduced `KeyError: 0` at `latest_status = execs[0].get("status", "")`. |
| **Impact** | The `P017 Workflow Self-Healer` n8n job was running on schedule but failing before it could inspect or repair any workflow. Because the script also unconditionally ended with `sys.exit(1)`, even healthy runs would still be marked as failed by n8n. |
| **Root Cause (5 Why)** | **Why1**: `workflow_healer.py` assumed `/rest/executions` returned a plain list under `data`, and indexed `execs[0]`. **Why2**: The current n8n API shape returns execution rows under `data.results`, so `get_recent_executions()` handed back a dict instead of a list. **Why3**: The script had no response-normalization helper for API shape drift across n8n versions. **Why4**: Runtime logging only recorded `FATAL: 0`, because the raised `KeyError(0)` was stringified without a traceback. **Why5**: The CLI epilogue had also been left with an unconditional `sys.exit(1)`, so successful runs were not clearly distinguishable from real crashes in scheduler results. |
| **Fix** | Updated `data/workspace/workflow_healer.py` to normalize n8n list payloads via `extract_n8n_items()`, covering both legacy `data: [...]` and current `data.results: [...]` execution responses. Wired that normalization into `get_active_workflows()`, `get_recent_executions()`, and `get_execution_error()`. Also added traceback logging on fatal errors and corrected the CLI exit path so `--dry-run` and healthy runtime executions return exit code `0`, while true exceptions return `1`. |
| **Files** | `data/workspace/workflow_healer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/workflow_healer.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py --dry-run'` reported `Active workflows: 5` with all monitored workflows healthy. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py; code=$?; echo EXIT=$code'` completed with `=== Workflow Healer done ===` and `EXIT=0`. The live log no longer ends in `FATAL: 0` after the fix. |
| **Lessons Learned** | n8n maintenance scripts need one local normalization layer for REST payloads instead of baking in a single response shape. Exit codes matter as much as business logic in scheduled jobs, because a scheduler can only distinguish healthy from broken through process termination status. |
| **Prevention** | Reuse response-normalization helpers for other n8n maintenance scripts, log tracebacks for unexpected exceptions instead of only exception strings, and treat `exit 0 on healthy / exit 1 on fault` as a required check whenever a script is run under n8n `Execute Command`. |

## INC-033: Telegram bridge treated DB-search requests as generic email chat instead of explicit local DB lookup

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:32 JST |
| **Detection** | User reported that a Telegram request to search the mini PC's DB did not work. Review of `data/state/telegram_fast/harness_status.json` showed the latest request had been routed as `email`, and the bridge replied with a generic Gmail capability explanation instead of returning local DB search results. |
| **Impact** | Telegram users could ask for a DB search and receive a misleading explanatory reply rather than actual results from the local indexed stores, making the mini PC appear unable to search its own data even though the underlying SQLite search backend was healthy. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` had no dedicated `db` route. **Why2**: Messages containing words like `gmail` or `mail` were classified directly as `email`, even when the user's intent was "search the DB". **Why3**: The `email` path used a general prompt-building flow that can answer conversationally, not a fail-closed structured DB response. **Why4**: Telegram routing relied mainly on broad intent regexes rather than an explicit "local DB lookup" override. **Why5**: The bridge design had evolved around email/task/report assistants, but not around a user-facing "DB検索して" command family. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` to recognize explicit DB-search wording via `isDatabaseIntent()`, prioritize a new `db` route in `classifyRoute()`, and answer through `generateDatabaseReply()` that queries local task, report, and email contexts directly and returns structured DB-hit summaries. Restarted the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1` so the new routing logic is live. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db context 'gmail 読み取る できますか' --limit 3` returned valid JSON results from the live SQLite DB inside `clawstack-unified-clawdbot-gateway-1`, confirming the backend was healthy. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical Node bridge at `2026-04-14 07:31:57 JST`. End-to-end Telegram confirmation still requires one fresh user message after this routing fix. |
| **Lessons Learned** | For chat-driven ops tools, "search-capable backend exists" is not enough. The conversational router needs an explicit intent for "search the local DB now" so capability explanations do not mask successful search backends. |
| **Prevention** | Keep explicit operational intents such as `DB検索`, `履歴検索`, and `メールDB検索` ahead of softer conversational email intents, and prefer structured fail-closed summaries for search requests instead of letting them fall through to open-ended model prompting. |

## INC-034: Relative due-date parsing missed `来週` / `来週末` and fell back to free-text task search

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:43 JST |
| **Detection** | User reported that asking Telegram for tasks due by next week returned obviously stale items from 2019-2020. Log review showed the Telegram bridge correctly routed `来週末までが納期の業務教えてください` to `task`, but `email_search_query.py` returned `due_on=null`, `due_from=null`, and `due_to=null`, causing a plain text-match search instead of a due-date range filter. |
| **Impact** | Relative-date task queries such as `来週まで`, `来週末まで`, and similar deadline requests could return unrelated historical tasks, making Telegram task-search answers unreliable for near-term planning. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` successfully routed the user message to task search. **Why2**: `data/workspace/email_search_query.py` only recognized `今日`, `明日`, `今週`, and `今月` for due-date resolution. **Why3**: `来週` and `来週末` were not mapped into a date window in `resolve_due_range()`. **Why4**: When no date window was found, task search fell back to term-based SQL matching. **Why5**: Relative-date coverage had grown incrementally around current-day and current-week use cases, but the next-week planning phrases used from Telegram had not been added to the parser. |
| **Fix** | Updated `data/workspace/email_search_query.py` so `RELATIVE_TERMS` includes `来週`, `今週末`, and `来週末`, and `resolve_due_range()` now maps `今週末` to the current week window and `来週` / `来週末` to the next week window. Synced the updated script into `clawstack-unified-clawdbot-gateway-1` at `/home/node/clawd/email_search_query.py`. |
| **Files** | `data/workspace/email_search_query.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "cd /home/node/clawd && python3 email_search_query.py --db /home/node/clawd/email_search.db tasks-context '来週末までが納期の業務教えてください' --limit 5"` now returns `due_from=2026-04-20` and `due_to=2026-04-26`, with current 2026-dated items instead of 2019-2020 records. |
| **Lessons Learned** | Chat routing and DB health are only half the path. Relative-date parsers need explicit coverage for the phrases users actually use in operations, especially planning ranges like next week and next weekend. |
| **Prevention** | Extend relative-date parsing with a maintained set of operational Japanese phrases and add smoke checks for `今日`, `今週`, `今週末`, `来週`, and `来週末` whenever task-search date logic changes. |

## INC-035: Telegram DB count requests fell through to generic RAG advice instead of returning a numeric count

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:49 JST |
| **Detection** | User reported another disappointing Telegram reply after sending `DBからIATF関連の賁E��数を数えて`. The latest bridge log showed `route=general`, `tier=rag`, and the reply was generic guidance about searching for `IATF`, rather than a counted result from the local DB. |
| **Impact** | Telegram could answer count-style DB requests with advice text instead of an actual number, making DB-backed operational questions feel unreliable even though the underlying SQLite store was healthy and queryable. |
| **Root Cause (5 Why)** | **Why1**: The bridge recognized some DB-search wording, but not the specific combination of `DBから ... 賁E��数を数えて`. **Why2**: That message therefore fell through to general classification, where `IATF` triggered the RAG path. **Why3**: The RAG path can summarize retrieved snippets, but it has no notion of total matching-document count. **Why4**: `email_search_query.py` had context and search commands, but no dedicated count command for Telegram to call. **Why5**: DB-search support had been expanded around retrieval and due-date queries first, while aggregate/count requests were still unimplemented. |
| **Fix** | Added `search-count` to `data/workspace/email_search_query.py`, backed by `count_search_rows()` using FTS count with LIKE fallback. Added `fetchEmailCount()` to `data/state/email_context_helper.js`. Updated `scripts/telegram_fast_bridge.js` so DB + IATF/material/count wording is forced onto the `db` route, and `generateDatabaseReply()` now returns a numeric count for count-style requests. Restarted the canonical Telegram bridge and synced the updated Python script into `clawstack-unified-clawdbot-gateway-1`. |
| **Files** | `data/workspace/email_search_query.py`, `data/state/email_context_helper.js`, `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `node --check scripts/telegram_fast_bridge.js` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 関連 賁E��'"` returned `result_count=1117`. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical bridge so the new route is live. |
| **Lessons Learned** | For chat ops, retrieval and aggregation are different capabilities. If users can ask "how many?", the bridge needs a dedicated count path instead of hoping a retrieval-oriented model route will infer aggregation correctly. |
| **Prevention** | Keep explicit patterns for `件数`, `何件`, `数を数えて`, and similar aggregate queries ahead of generic RAG routing, and maintain one script-level count command so Telegram, CLI, and future dashboards can all reuse the same DB-count implementation. |

## INC-036: Telegram answered IATF document counts from model inference instead of DB truth and lost follow-up title context

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 08:12 JST |
| **Detection** | User reported that Telegram answered `IATF関連の賁E��は何件ありますか�E�` with `12件`, and then answered `賁E��名�E何ですか�E�` with only one fabricated-looking title. Log review showed the first message routed to `general` and `tier=rag`, not `db`, and the follow-up also routed to `general/simple`. |
| **Impact** | Telegram gave materially wrong inventory information for IATF-related materials, undercounting a large local corpus and failing to list representative titles from the real DB. This undermined trust in Telegram-based retrieval for local knowledge counts. |
| **Root Cause (5 Why)** | **Why1**: The bridge only forced `db` routing when the message explicitly contained DB-like wording. **Why2**: `IATF関連の賁E��は何件ありますか�E�` lacked `DB` but still semantically asked for a local count, so it fell through to general classification. **Why3**: General classification sent `IATF` questions into the RAG path, which is retrieval-oriented rather than count-oriented. **Why4**: The count response path did not persist the returned title list for the next follow-up turn. **Why5**: Telegram DB support had been implemented as one-shot answers first, without a lightweight local context memory for follow-up questions like `賁E��名�E�E�`. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` so `IATF/ISO/QMS + 件数/賁E��/数` questions route directly to `db` even without the literal `DB` keyword. Extended `generateDatabaseReply()` to call the real `search-count` backend, include representative titles from `fetchEmailContext()`, and save those titles into `data/state/telegram_fast/last_db_context.json` for immediate follow-up questions such as `賁E��名�E何ですか�E�`. Restarted the canonical Telegram bridge after the change. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. The live DB backend reports `result_count=1118` for `IATF 関連 賁E��` via `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 関連 賁E��'`. Representative titles returned from the same DB search include `Re: 購買プロセス KPIにつぁE��`, `グループアカウンチE IATF冁E��監査員 "更新のお知らせ`, and `Re: VDAにつぁE��`, confirming that the local store contains far more than 12 items and multiple distinct titles. |
| **Lessons Learned** | For local-knowledge chat tools, "domain question" and "DB truth query" are not the same. Count and listing requests need to bypass generative shortcuts, and follow-up questions need lightweight state so users can ask naturally without repeating the full query every turn. |
| **Prevention** | Route `何件` / `件数` / `賁E��名` follow-ups to the DB layer by default when a recent DB context exists, and keep a short-lived local result cache for follow-up listing questions in Telegram. |

## INC-037: Telegram intent handling needed canonical normalization for varied Japanese expressions
| 頁E�� | 冁E�� |
|---|---|
| **発生日** | 2026-04-14 |
| **発見方況E* | User reported that Telegram replies still missed intent when the same request was phrased as `IATF関連の賁E��は何件ありますか�E�`, `賁E��名�E何ですか�E�`, `来週までが納期の業務教えて`, or `メールDBで受信したIATFの賁E��を探して`. |
| **影響篁E��** | Telegram routing for local DB search, task search, and follow-up questions. Users could receive model-style replies or ambiguous fallbacks instead of the intended local search behavior. |
| **Root Cause (5 Why)** | **Why1**: Route selection depended on ad hoc regex branches added case by case. **Why2**: The same user intent could appear as count, list, follow-up, or search wording, but those variants were not normalized into a canonical intent bucket. **Why3**: Follow-up questions relied on a single cached title list, but the cache was only useful after some branches and not consistently preserved across all DB responses. **Why4**: The search layer was already capable, but the bridge did not enforce a stable `db_count` / `db_list` / `db_followup` / `task_due` style classification. **Why5**: The system had been optimized for individual fixes first, rather than a reusable intent normalization layer. |
| **Fix** | Reworked `scripts/telegram_fast_bridge.js` so user text is normalized with NFKC and compacted before routing. Added canonical intent helpers for DB count/list/follow-up, task due-date phrasing, report, email, and complaint intents. Updated `generateDatabaseReply()` to store and reuse recent titles for follow-up questions, and to keep DB count replies grounded in the local search backend. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed after the change. The updated bridge now classifies the representative inputs above into the intended intent buckets in code review, and the previous `12件` style inference path is no longer the DB count path for IATF material questions. |
| **Lessons Learned** | User phrasing must be treated as noisy input, not as a specification. The bridge needs a small number of canonical intents and short-lived context, rather than one-off regexes for each new wording. |
| **Prevention** | Keep expanding canonical intent buckets and shared normalization instead of adding isolated phrasing rules. When a new wording appears more than once, map it to an existing intent bucket first and only add a new bucket when the behavior is genuinely new. |

## INC-038: 2025 process monitoring measurement refresh failed because PDF directory check blocked Excel-only regeneration

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:34 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` showed too many blank cells and did not reflect the Excel content. Investigation found `year_2025` in `db/process_monitoring_measurement.json` was still an array with only five monthly PDF items, even though `db/documents/プロセスの監視�E測定記録_2025年.xls` already existed. |
| **Impact** | The 2025 process-monitoring page displayed incomplete or mostly empty content, so users could not rely on it as a faithful view of the registered Excel source. |
| **Root Cause (5 Why)** | **Why1**: `ProcessMonitoringMeasurementRefreshService.call` returned `PDF source directory was not found.` before doing any work if `/paperless_consume` was absent. **Why2**: That guard lived at the top of `call`, even though `refresh_year` could already rebuild 2025 from the local Excel file alone. **Why3**: As a result, Excel-only regeneration was impossible unless a PDF source directory happened to exist. **Why4**: The current JSON had never been switched from the older `year_2025` array format into the Excel-backed grid format. **Why5**: The refresh flow had been optimized around PDF fallback first, and the Excel-primary case was not allowed to complete without an unrelated PDF directory. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so the top-level `call` no longer fails early when the PDF source directory is missing. The PDF directory check now happens only inside the PDF fallback branch of `refresh_year`, after Excel has been checked first. Then regenerated 2025 from `db/documents/プロセスの監視�E測定記録_2025年.xls`, which rewrote `db/process_monitoring_measurement.json` with the full grid data. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` now returns `success=>true` and `updated_years=>[2025]`. The refreshed JSON now stores `year_2025` as a hash with `rows=96`, `nonblank_cells=1365`, and `source_file=プロセスの監視�E測定記録_2025年.xls`. `http://localhost:3004/products/process_monitoring_measurement?year=2025` returns `200` after the refresh. |
| **Lessons Learned** | A fallback path should not block the primary path. If a year can be rebuilt from local Excel, the refresh flow must not require an unrelated PDF source directory first. |
| **Prevention** | Keep Excel regeneration independent from PDF availability, and prefer source-specific checks inside each branch instead of at the top of the whole refresh flow. Add a smoke check for 2025 refresh whenever this service changes. |

## INC-039: 2025 process monitoring measurement header layout broke because the refresh path lacked template widths and header rows

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:57 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` still had a broken header after the 2025 data regeneration. A visual browser check with Playwright confirmed that the page was rendering, but the 2025 table header was compressed and misaligned compared with 2024. |
| **Impact** | The 2025 process-monitoring page was readable in the body but the top header region looked malformed, which made the page feel unreliable even though the data rows were present. |
| **Root Cause (5 Why)** | **Why1**: The 2025 refresh path wrote Excel-derived rows into `db/process_monitoring_measurement.json` without `column_widths`. **Why2**: The view uses `active_year[:column_widths]` to size the table, so a missing array falls back to browser auto-sizing. **Why3**: The Excel-only regeneration path also preserved the workbook's raw top rows, which did not visually match the stable 2024 template header. **Why4**: The earlier fix focused on getting the 2025 data and counts back, but not on preserving the 2024 visual baseline. **Why5**: The refresh service did not have a template-normalization step for the header region, so structurally valid data could still render with a broken-looking table top. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel-backed refreshes now copy `column_widths` from the 2024 template and replace the first eight rows with the 2024 header rows before saving the 2025 payload. Re-ran `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` and verified the rendered page with Playwright screenshot after the fix. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true` and rewrote the JSON with the normalized 2025 payload. Playwright screenshot review of the authenticated `2025` page showed the header aligned to the 2024 visual baseline and the table no longer compressed at the top. `http://localhost:3004/products/process_monitoring_measurement?year=2025` continued to return `200`. |
| **Lessons Learned** | A structurally correct table can still look broken if the visual template is not preserved. Header rows and column widths are part of the contract, not just the data cells. |
| **Prevention** | Keep a template-normalization step for year-specific refreshes, and compare the rendered 2025 page against the 2024 visual baseline whenever the refresh pipeline changes. |

## INC-040: 2025 process monitoring measurement body rows were over-wrapped by long decimal values

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:05 JST |
| **Detection** | After visually comparing authenticated `2024` and `2025` screenshots, the 2025 body still looked denser than 2024 even though the header was aligned. The first metric block and some score cells were wrapping long floating-point strings such as `0.8571428571428571`, making the body feel compressed. |
| **Impact** | The 2025 page was technically correct but harder to read than 2024 because long numeric strings expanded several rows and reduced the visual similarity between the two years. |
| **Root Cause (5 Why)** | **Why1**: Excel-derived floats were serialized with full precision via `Float#to_s`. **Why2**: Some cells contained formula results with many decimal places. **Why3**: Those long strings wrapped inside fixed-width table cells. **Why4**: The 2025 rendering path did not apply the same compact numeric presentation as the 2024 template. **Why5**: The refresh pipeline focused on data completeness first and visual normalization second, so the body row density drifted from the 2024 baseline. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so float values are formatted with `%.4f` and trimmed before being written to `db/process_monitoring_measurement.json`. Re-ran the 2025 refresh and rechecked both `2024` and `2025` screenshots in Playwright. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | The refreshed `year_2025` payload now renders compact values such as `0.8571` instead of long full-precision decimals, and the authenticated 2025 screenshot no longer shows the same degree of body-row over-wrapping. Both `2024` and `2025` pages still return `200`. |
| **Lessons Learned** | Visual parity is not just about structure; numeric formatting materially affects row height and readability. |
| **Prevention** | Keep a compact formatting rule for all Excel-derived floats in this report, and compare rendered screenshots after refreshes that introduce or regenerate formula-driven numbers. |
## INC-041: 2025 process monitoring measurement body rows misrendered because refresh stored a raw grid instead of template-backed year items

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:19 JST |
| **Detection** | User pointed out that the `2025` page still had a misaligned `�ݐ� / ���� / �v��` region even after the header was fixed. Visual comparison showed the page was rendering a different structure than `2024`, especially in the effectiveness section. |
| **Impact** | The 2025 process-monitoring table looked structurally different from 2024, making the cumulative rows appear shifted and reducing trust in the report. |
| **Root Cause (5 Why)** | **Why1**: The refresh service was saving 2025 as an Excel-derived grid hash. **Why2**: The view expected 2025 data to be replayed through the 2024 template so row spans and block structure would remain stable. **Why3**: Excel layout and template layout diverged in the effectiveness section, especially around cumulative/actual/plan rows. **Why4**: A raw grid preserves workbook layout details instead of the canonical contract used by the page. **Why5**: The refresh flow had drifted from the `template + year items` design that the renderer already supports. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel refreshes now save 2025 as month-based year items instead of a raw grid. Added `extract_excel_year_entries` to read the workbook into `{process, metric, target, actual}` items, and updated `ProcessMonitoringMeasurementService#split_actual_values` to accept `���� / �݌v` as well as the legacy labels. The view now rebuilds 2025 through the 2024 template path again. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/app/services/process_monitoring_measurement_service.rb`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true`. `bundle exec ruby -c` passed for both modified service files. Playwright screenshots of authenticated `2024` and `2025` pages showed the 2025 table returning to the 2024 template shape, with the cumulative region no longer visibly shifted. |
| **Lessons Learned** | The page contract is the template, not the source workbook. Even when raw Excel looks valid, saving it as a final render format can break the visual invariants users rely on. |
| **Prevention** | Keep 2025 and later stored as normalized year items, not workbook-shaped grids. Compare the rendered result against the 2024 template whenever the refresh path changes. |
## INC-042: Mini PC slowdown required a split between always-on core services and on-demand heavy services
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 23:17 JST |
| **Detection** | User reported that the PC still felt slow while wanting `clawstack-unified` to remain basically always on, and specifically asked for a setup where Telegram stays usable without bringing the whole heavy stack up all the time. |
| **Impact** | The previous all-or-nothing mental model encouraged keeping many heavy services resident together, which made the mini PC feel sluggish even when only Telegram and the core gateway path were needed. |
| **Root Cause (5 Why)** | **Why1**: The unified Docker stack had been treated as one monolith. **Why2**: Heavy services such as Open WebUI, n8n, monitoring, and media tools tended to ride along with the always-on path. **Why3**: Telegram only needs the gateway and a small local model/runtime surface, not the full optional stack. **Why4**: There was no explicit host-side `core` startup entrypoint to separate �galways-on but light�h from �gstart only when needed.�h **Why5**: Operational convenience had been prioritized over load separation, so the slow mini PC had no first-class lightweight startup mode. |
| **Fix** | Added `scripts/start_clawstack_core.ps1` to start a lightweight always-on set of Docker services (`clawdbot-gateway`, `postgres`, `redis`, `ollama`, `qdrant`, `litellm`, `searxng`, `minio`, `portal_server`) and then launch the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1`. This keeps Telegram usable while leaving the heavy stack on demand through `scripts/start_docker_addons.ps1`. |
| **Files** | `scripts/start_clawstack_core.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. The new core-start script was added without touching `docker-compose.yml`, and the operational plan now separates the always-on Telegram/core path from the heavy addon path. |
| **Lessons Learned** | �gAlways on�h should mean �galways on at the lightest viable layer,�h not �gall services at once.�h A small host-side launcher is enough to make the split explicit and safe. |
| **Prevention** | Use the new core launcher for normal work, reserve `start_docker_addons.ps1` for heavy workloads, and keep Telegram bridge startup tied to the lightweight core path so user messages remain responsive. |
## INC-043: Mini PC load needed a staged startup plan instead of simultaneous service activation
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-15 |
| **Detection** | User requested a plan that keeps all apps available but reduces slowdown as much as possible. Current runtime showed a mix of always-on Docker services, email watchdogs, learning memory, and portal tooling, which can create a startup spike if launched together. |
| **Impact** | Simultaneous startup of Docker services and host-side watchdogs increases CPU, memory, and disk pressure during boot or recovery, especially on the mini PC. That makes the system feel slower even if each app is useful on its own. |
| **Root Cause (5 Why)** | **Why1**: Startup paths were spread across several scripts without a single coordinated sequence. **Why2**: Some services were safe individually but still expensive when launched at the same time. **Why3**: Dependency-aware waiting was only partially present in a few scripts. **Why4**: There was no host-side balanced launcher to serialize startup and gate the next step on readiness. **Why5**: The runtime had evolved toward feature coverage first, while load-shedding and startup pacing had not been formalized. |
| **Fix** | Added `scripts/start_minipc_balanced_stack.ps1` as a host-side launcher that starts services in a controlled sequence with per-step health probes and cooldowns. It writes status to `data/state/minipc_balanced_stack/startup_status.json` and supports `-DryRun` plus `-Mode balanced|full`. Also added readiness waits to `scripts/start_email_blacklist_hub_api.ps1` and `scripts/start_email_continuous_watchdog.ps1` so dependent services do not pile up immediately. |
| **Files** | `scripts/start_minipc_balanced_stack.ps1`, `scripts/start_email_blacklist_hub_api.ps1`, `scripts/start_email_continuous_watchdog.ps1`, `data/state/minipc_balanced_stack/startup_status.json`, `data/state/minipc_balanced_stack/startup.log`, `docs/INCIDENT_LOG.md` |
| **Verification** | PowerShell syntax check passed for all edited scripts. `scripts/start_minipc_balanced_stack.ps1 -DryRun` completed successfully and wrote the planned balanced startup sequence: postgres, redis, qdrant, ollama, gateway, portal_server, litellm, n8n, learning_engine, email_search_api, email_blacklist_hub, email_continuous_watchdog, telegram_fast_bridge. |
| **Lessons Learned** | Keeping all apps available does not require starting all of them at once. A staged launcher with health gates gives most of the responsiveness benefit without turning off useful services. |
| **Prevention** | Use the balanced launcher for normal boot and recovery scenarios. Keep heavy extras in `full` mode only, and continue adding readiness checks instead of adding more simultaneous startup paths. |
