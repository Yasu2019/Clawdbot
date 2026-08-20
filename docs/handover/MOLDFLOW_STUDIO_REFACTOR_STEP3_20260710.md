# Moldflow CAE Studio リファクタ STEP3: 成熟度+ゴールデン誤差推移パネル (2026-07-10)

> 作成: Fable5。3ステップ計画の最終弾。前段: `MOLDFLOW_STUDIO_REFACTOR_STEP2_20260710.md`

## 追加機能

### API (`scripts/moldflow_cae_studio_api.py`)

| エンドポイント | 内容 |
|---|---|
| `GET /api/maturity` | `apps/growth_dashboard/commercial_benchmark_maturity_latest.json` からMOLDFLOW行を抽出して返す(読み取り専用・再計算しない=決定論)。`age_hours`と**26h超stale判定**付き(死活再チェックプロトコルと同じ閾値) |
| `GET /api/golden-error-trend?limit=N` | `data/workspace/moldflow_golden_error_log.jsonl` の直近N件(既定50・上限500)。壊れ行スキップ。**未生成時はavailable:false+説明note**(ゴールデン未実行=発効条件はFABLE5_FINAL_SESSION_HANDOVER §0) |

補助: `_rel_or_str()`(ROOT外パス耐性) / assessed_atはtz付きISO対応(`+09:00`実データで検証済み)

### UI (`data/workspace/apps/moldflow_cae_studio/app.js`)

- `Maturity & Golden Trend` パネルを既存の ensure*Panel パターン(ChatGPT方式踏襲)でExportセクション前に注入
- 成熟度: カテゴリ別プログレスバー(L0-L10・current_stage・progress_pct)+ 鮮度バッジ(STALE>26h)
- ゴールデン誤差推移: SVGスパークライン(`max_err_pct`/`per_variant`両形式対応)
- API停止時はローカル `../growth_dashboard/commercial_benchmark_maturity_latest.json` へフォールバック(`LOCAL_MATURITY`)
- **バックアップ**: `app.js.bak_step3`

## 検証

- `python -m unittest tests.test_moldflow_studio_api_multipart` — **10件全PASS**(STEP2の7件+STEP3の3件: maturity形状/log未生成安全応答/壊れ行+limit)
- 実データ検証: MOLDFLOW行6カテゴリ抽出・age_hours=49.7h(assessed 7/8 05:30)→STALE正検知
- `node --check`(ESM) PASS / py_compile PASS

## 発効条件

STEP2と同じ=**APIプロセス再起動が必要**(手順はSTEP2文書§発効条件)。UIはブラウザリロードのみ。

## 気づき(次AIへ)

- `commercial_benchmark_maturity_latest.json` が**7/8 05:31から更新停止**(26h超stale)。日次実行が止まっている可能性 → 死活再チェック(`heartbeat_manifest.json`)への登録有無を確認し、未登録なら登録すること(bd起票要)
- golden_error_log未生成=ゴールデンケース自動投入(25サイクル毎)がまだ発火していない。K10オーケストレータ再起動(§0-2)は完了済みのはずなので、次の25サイクル境界で生成されるか監視

## STEP1-3全体の未解決事項

1. `.git/index.lock` 削除待ち(ユーザー) → STEP1〜3のcommit実行
2. `scripts/moldflow_golden_case_SYNC_TMP.py` 手動削除(ユーザー)
3. APIプロセス再起動(ユーザー)
4. bd起票(次のbd可能セッション): STEP1-3実施記録+maturity更新停止調査
