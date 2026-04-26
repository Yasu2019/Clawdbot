# Codex / Antigravity / Claude向け 実装プロトコル

## 目的

既存の `D:\Clawdbot_Docker_20260125` / Clawstackに、OpenClaw SPICE Labを安全に統合する。

## 最重要ルール

1. 既存ファイルを無確認で大規模リファクタリングしない。
2. 変更前にGit状態を確認する。
3. 既存compose、Nginx、Portalカード、OpenClaw Gateway tool定義と競合確認する。
4. 既存ポートと衝突しないことを確認する。
5. まず `integrations/spice_lab` として独立追加し、既存中核に直接混ぜない。
6. LTspice本体やインストーラーをリポジトリへ入れない。
7. 外部公開ポートにしない。既定は `127.0.0.1` バインド。
8. 失敗時にロールバックできるよう、変更ファイル一覧を最後に報告する。

## 実施タスク

### Phase 0: 事前確認

```powershell
cd D:\Clawdbot_Docker_20260125
git status
git branch --show-current
docker compose ps
```

未コミット差分がある場合は、変更前にユーザーへ報告する。許可がある場合のみバックアップブランチを作成する。

```powershell
git checkout -b backup/before-spice-lab-YYYYMMDD-HHMM
```

### Phase 1: 独立配置

以下に配置する。

```text
D:\Clawdbot_Docker_20260125\integrations\spice_lab\
```

配置対象:

```text
01_docker_ngspice_service/*
02_openclaw_portal_integration/apps/circuit_sim_hub/index.html
```

### Phase 2: compose統合

既存composeに直接貼り付ける前に、単体composeで起動確認する。

```powershell
cd D:\Clawdbot_Docker_20260125\integrations\spice_lab\01_docker_ngspice_service
docker compose -f docker-compose.ngspice.yml up -d --build
Invoke-RestMethod http://127.0.0.1:8765/health
```

問題なければ、既存のcompose include方式、または別compose運用のどちらがよいか判定する。

### Phase 3: Portal統合

既存Portalの静的ファイル構造を調査し、同名アプリがないか確認する。

候補:

```text
portal/apps/circuit_sim_hub/index.html
```

既存カード登録方式に従い `Circuit Simulation Hub` を追加する。

### Phase 4: OpenClaw Gateway tool化

GatewayにHTTP clientツールを追加できる場合のみ、以下の最小toolを追加する。

- `spice_health_check()`
- `spice_get_example(name)`
- `spice_run_netlist(name, netlist)`

### Phase 5: 検証

- healthがOK
- RC low-passが実行できる
- run.logが保存される
- measurementsがJSONに出る
- Portalから実行できる
- 既存サービスが落ちていない

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8765/health
```

### Phase 6: 報告

最後に以下を報告する。

- 追加ファイル一覧
- 変更ファイル一覧
- 起動コマンド
- 動作確認結果
- 未解決リスク
- 次に推奨する改善

## 採用/部分採用/保留の判断基準

- 完全採用: 単体起動、Portal、Gateway tool、ログ保存がすべてOK
- 部分採用: ngspice APIのみOK、PortalまたはGateway統合は後回し
- 保留: compose競合、ポート競合、既存Portal構造不明、LTspice連携が不安定

## 禁止事項

- 既存Portal全体の作り直し
- 既存OpenClaw Gatewayの大規模再設計
- 不要なLLMモデル変更
- LTspiceインストーラーのリポジトリ追加
- `0.0.0.0` への不用意な公開
