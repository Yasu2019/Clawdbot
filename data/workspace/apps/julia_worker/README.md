# Clawstack Julia Numerical Worker 完全統合版

## 1. これは何か

Clawstack / OpenClaw / Portal に、Julia製の高速数値計算Workerを追加するためのパッケージです。

Juliaは以下の用途に限定して使います。

- DOE / 実験計画
- 最適化
- レベラー条件探索
- CAE前処理・後処理
- 微分方程式・簡易物理モデル
- Pythonでは遅い数値ループの高速化
- OpenFOAM / Elmer / CalculiX / PrePoMax の周辺計算

OpenClaw本体、RAG、帳票処理、IATF文書処理、Node-RED運用は基本的にPython側を維持します。

## 2. 推奨アーキテクチャ

```text
Portal / OpenClaw / Node-RED
        |
        v
Python Bridge / FastAPI
        |
        v
Julia Numerical Worker
        |
        +-- DOE
        +-- Optimization
        +-- Leveler Model
        +-- CAE Parameter Search
        +-- Differential Equation Solver
```

## 3. ポート

既定ポート:

- Julia Worker: `8096`
- Python Bridge: `8097`

既存Clawstackと衝突しにくい番号にしています。

## 4. 単独起動

```bash
docker compose -f docker-compose.julia-worker.standalone.yml up --build
```

確認:

```bash
curl http://localhost:8096/health
curl http://localhost:8097/health
```

## 5. レベラー簡易計算API

```bash
curl -X POST http://localhost:8096/leveler/estimate \
  -H "Content-Type: application/json" \
  -d "{\"thickness_mm\":0.8,\"yield_mpa\":85,\"roller_diameter_mm\":12,\"pitch_mm\":16,\"entry_gap_mm\":0.7,\"exit_gap_mm\":1.1,\"stages\":11}"
```

## 6. DOE生成API

```bash
curl -X POST http://localhost:8096/doe/latin_hypercube \
  -H "Content-Type: application/json" \
  -d "{\"n\":12,\"variables\":{\"entry_gap_mm\":[0.5,1.5],\"exit_gap_mm\":[0.5,1.5],\"friction\":[0.02,0.15]}}"
```

## 7. 最適化API

```bash
curl -X POST http://localhost:8096/optimize/leveler_grid \
  -H "Content-Type: application/json" \
  -d "{\"thickness_mm\":0.8,\"yield_mpa\":85,\"roller_diameter_mm\":12,\"pitch_mm\":16,\"entry_gap_range\":[0.5,1.5,0.1],\"exit_gap_range\":[0.5,1.5,0.1],\"stages\":11}"
```

## 8. 既存Clawstackへの統合方針

- 既存 `docker-compose.yml` は直接編集しない。
- `docker-compose.julia-worker.override.example.yml` を参考に、overrideとして追加する。
- 既存Portalは壊さず、カードを追加するだけ。
- 既存OpenClaw Gatewayへは、HTTPツールとして登録する。
- まず単独テスト、次に統合テスト。

## 9. Codex / Claude / Gemini / OpenCode GO に渡す時

`prompts/` 内の指示書をそのまま渡してください。

特に重要:

- 既存ファイルを勝手に大規模リファクタしない
- 変更前にGitバックアップ
- docker-composeはoverride方式
- Portalカードは追加のみ
- Node-REDフローはインポート用サンプルとして扱う
- API消費を最小化し、まずローカルテスト

## 10. 注意

このZIPのレベラー計算は「現場検討用の簡易推定モデル」です。
正式な応力・ひずみ・残留応力評価は、PrePoMax / CalculiX / Elmer / OpenFOAM 等のCAE結果と照合してください。
