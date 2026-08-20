# Fable5 最終セッション引継ぎ (2026-07-07)

> 作成: Fable5 (最終日)。次の読者: ChatGPT 5.5 / Opus 4.8 / Codex / ローカルLLM / ユーザー
> 入口は `HANDOVER_MASTER_INDEX.md`(単一の入口)。本書は**2026-07-07セッションの差分**と
> **未完アクション**に限定する。全体像・恒久ルールはマスターインデックスから辿ること。

## 0. 最優先の未完アクション (この順で処理)

| # | アクション | 担当 | 手順 | 状態 |
|---|---|---|---|---|
| 1 | **LAVIEへengineペア配布** — G1物理ゲート(cae_te_engine.py変更)は配布まで実機未発効。**21:30追記: 質量収支KPI(L5素材)も同ファイルに追加済み=この配布に相乗り** | 人間+AI | T051方式: orchestrator停止→`cae_te_engine.py`+`cae_self_growth_gates.py`をSHA256照合付き配布→py_compile→`.bak_g1`→orchestrator再起動。罠3つは `T051_GATES_VERSION_MISMATCH_20260706.md` §残作業1 | **✅ 完了** |
| 2 | **K10オーケストレータ再起動** — 学習サンプラ+ゴールデン自動投入の発効 | 人間 | `powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\start_k10_tri_track_cae_watchdog.ps1` | **✅ 完了** (task-535起動完了) |
| 3 | **タスクスケジューラ登録2本** (未確認/未実施) | 人間 | `scripts\register_dead_project_recheck_task.bat` と `scripts\register_growth_loop_audit_task.bat` をダブルクリック。ログは同名.logに残る(AIが読める) | **✅ 完了** |
| 4 | **G3ミニPC復旧** — 電源/WiFi/Tailscale確認。復旧でP016納期レポート(21:00)自動再開 | 人間 | `docs/G3_K10_N8N_MIGRATION.md` / 死活: `100.121.241.128:5679/healthz` | **要人間介入** |
| 5 | **bd起票** (本環境からbd実行不可だった) | 次AI | §4のリストを`bd create`。完了後このファイルの該当行に済マーク | **✅ 完了** (bd iy63/7c62/9tgj/ip4 起票済) |
| 6 | red_lavie DOE誘導 — punch_speed≥3000mm/s優先(低速は全滅中) | 次AI | 根拠: `HANDOVER_MASTER_INDEX.md` §7.5.1。8連敗自動停止が発火していれば再開判断から | **進行中** |

## 1. 本日の成果 (詳細はCHANGELOG 2026-07-07)

### 制定した恒久ルール2本 (今後の全作業に適用)
- **死活再チェック** `docs/dead_project_recheck_protocol.md` — 常駐/定期通知は
  `heartbeat_manifest.json` 登録必須。毎日07:30検査。死亡は48h以内に復旧or正式停止。
  背景: P016納期通知がG3停止+監視役自身の死(6/18〜)で19日間無通知だった
- **成長ループ品質** `docs/growth_loop_quality_protocol.md` — T&E蓄積系は
  `growth_loop_manifest.json` 登録必須。G1物理妥当性/G2情報増加/G3基準相関/G4学習反映
  の4ゲートを毎日07:35独立監査。**ゲート判定へのLLM使用禁止**(決定論のみ)。
  AI許可は次パラメータ提案とlesson要約のみ=ローカルLLM qwen3:14b。
  背景: 樹脂充填377試行がKPI非物理(fill>110%が50%)+学習不在で空回りしていた

### Moldflowアプリ 3点セット (個票: `quality_incident_report_20260707_resin_fill_kpi_nonphysical_no_learning.md`)
- G1物理ゲート: `scripts/cae_te_engine.py` (alpha_max KPI + FAILED_NONPHYSICAL降格) — **配布待ち(§0-1)**
- 学習機構: `scripts/resin_fill_param_learner.py` + `cae_tri_track_openfoam_params.py` 組込 — **再起動待ち(§0-2)**
- ゴールデン: `data/cae_te_workspace/samples/moldflow/golden_plate_case.json` (25サイクル毎自動投入) + `scripts/moldflow_golden_case.py` (誤差推移を `data/workspace/moldflow_golden_error_log.jsonl` へ)

### リファクタ・修正
- `data/workspace/commercial_benchmark_maturity.py` — 宣言的ルール化+鮮度ゲート+verdict分類是正+KPI物理妥当性連動(樹脂充填 精度L4→L3へ正直化)
- `apps/mecha_motion_lab/index.html` — API停止時フォールバック+停滞警告
- `apps/cetol6sigma/index.html` — stale警告+読込失敗理由表示

### 調査結果 (実装なし・記録済み)
- red_lavie打ち抜き5連敗 = 既知の物理発散モード+DOE低速域+ゲート厳格化の複合。実機は健全 (`HANDOVER_MASTER_INDEX.md` §7.5.1)
- goto_targetスキル(Unity Cube追跡のGenesis移植)設計+タスクロジック実装済み。**着手はwalkゲート通過後** (`projects/AtsugiMechaCity/design/goto_target_skill_design.md`)

## 2. 新規ファイル一覧 (テスト実行方法つき)

| ファイル | テスト |
|---|---|
| `scripts/dead_project_recheck.py` + `data/workspace/heartbeat_manifest.json` | `cd data/workspace && python -m unittest tests.test_dead_project_recheck` (15件) |
| `scripts/growth_loop_audit.py` + `data/workspace/growth_loop_manifest.json` | `... tests.test_growth_loop_audit` (19件) |
| `scripts/resin_fill_param_learner.py` / `scripts/moldflow_golden_case.py` | `... tests.test_moldflow_3set` (18件) |
| 質量収支KPI (21:30追加: `cae_te_engine._extract_mass_balance_kpis` + golden/maturity L5行) | `... tests.test_mass_balance_kpi` (16件)。`moldflow_golden_case_SYNC_TMP.py` は同一内容バックアップ(削除可) |
| `data/workspace/tests/test_commercial_benchmark_maturity.py` | 同上 (19件) |
| `projects/AtsugiMechaCity/rl_integration/goto_target/goto_target_task.py` | 同フォルダで `python -m unittest test_goto_target_task` (23件) |
| `scripts/register_dead_project_recheck_task.bat` / `register_growth_loop_audit_task.bat` | ダブルクリック→同名.logで結果確認 |
| `docs/dead_project_recheck_protocol.md` / `docs/growth_loop_quality_protocol.md` | — |

## 3. セッション開始時チェック (更新済み)

`FABLE5_CONTINUATION_PROTOCOL_V2.md` §9 に2項目追加済み:
8. `dead_project_recheck_status.json` 確認 (checked_at>26hならチェッカー自身が死亡)
9. `growth_loop_audit_status.json` 確認 (FAKE_GROWTHは48h以内に是正orループ停止)

## 4. bd起票リスト (次セッション冒頭で登録)

```
bd create --title "[P1] LAVIEへG1物理ゲート入りengineペア配布(T051方式)" 
bd create --title "[P1] K10 tri-trackオーケストレータ再起動(学習サンプラ+ゴールデン発効)"
bd create --title "[P2] red_lavie DOEをpunch_speed>=3000mm/sへ誘導(低速域はデッキ対策とセット)"
bd create --title "[P2] moldflow_golden_case.py 日次実行のスケジュール化(監査チェーンへ)"
bd create --title "[P2] goto_target Env結線(blockedBy: walkゲート通過)- 設計書§8"
bd create --title "[P3] fleet_operations_status 定期実行の再登録(6/18から停止)"
bd create --title "[P3] PROMISES.md P026(死活再チェック)追記(保護ファイル・ユーザー承認済み文面はdead_project_recheck_protocol.md末尾)"
```

## 5. 注意 (ハマりどころ)

- **cae_te_log.json は全体書き換え方式** — 別プロセスから読む時は必ずリトライ読込か
  プレフィックス逐次デコード(`growth_loop_audit.load_trials_cae_te_log` が参照実装)
- **engine/gatesは必ずペア配布** (T051恒久ルール)。片方だけの配布が偽ERRORを生んだ
- **ゲートしきい値を勝手に緩めるな** (FMEA#2 RPN432)。G1の110%/1.05も同様
- **成長ループ新設時は growth_loop_manifest.json 登録が完成条件** (第1条)
- git push は本セッション環境から未実施 — 次セッションで `git status` 確認から
