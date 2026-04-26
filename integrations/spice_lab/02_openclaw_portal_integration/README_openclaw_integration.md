# OpenClaw / Clawstack 統合方針

## 推奨統合手順

1. このZIPを任意フォルダで展開
2. `01_docker_ngspice_service` 単体で起動確認
3. Gitで既存Clawstackをバックアップ
4. Codex / Antigravityに `03_protocols/01_codex_antigravity_implementation_protocol.md` を渡す
5. 既存compose / Portalカード / Nginx / OpenClaw Gatewayとの競合確認
6. 問題なければ `integrations/spice_lab` として追加

## Portalカード案

`apps/circuit_sim_hub/index.html` を既存Portalの静的アプリとして配置します。

候補:

```text
D:\Clawdbot_Docker_20260125\clawstack_v2\portal\apps\circuit_sim_hub\index.html
```

既存のPortal実装構造が異なる場合は、既存カード一覧・Nginx設定・PORTAL_APPS.mdを確認してから統合してください。

## API

既定:

```text
http://127.0.0.1:8765
```

Dockerコンテナ間で呼ぶ場合は、composeネットワーク名に応じて次のように変更します。

```text
http://openclaw-spice-lab:8765
```

## OpenClaw Gateway tool化案

Gatewayに以下のようなツールを追加します。

```python
async def run_spice_simulation(name: str, netlist: str) -> dict:
    # POST http://openclaw-spice-lab:8765/simulate
    # return measurements/log/files
```

## RAG化の対象

- netlist
- run.log
- metadata.json
- markdown report
- 実験条件・部品表・測定値

## 品質保証観点

- 回路シミュレーションは「設計検討補助」であり、実機確認の代替ではない
- 顧客提出資料にする場合は、部品モデル、温度条件、許容差、実測結果との対応を明記
- 自動生成結果には「シミュレーション条件」「モデル限界」「検証者」を残す
