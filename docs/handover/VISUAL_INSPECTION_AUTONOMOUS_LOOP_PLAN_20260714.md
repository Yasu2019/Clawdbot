# Visual Inspection AI 意味ゲート付き自律ループ設計案

作成: 2026-07-14 03:0x JST Fable5夜間自走 Run 2(Plan文書のみ・実装なし)
対象: `projects/visual_inspection_ai/scripts/idle_trainer.py` のタスクスケジューラ登録
必読前提: T019(北極星)/ T056(鮮度死活)/ P025(化粧SUCCESS禁止)/ P026(進化なしSUCCESS禁止)/ T058(CREATE_NO_WINDOW)

## 0. 意味ゲート(T019・登録前に全問YES必須)

1. 物理現象は何か → プレス部品の外観欠陥(傷/バリ/打痕)の画像異常検知。順送金型の品質保証工程に直結
2. カテゴリ/ソルバ整合 → PatchCore参照学習(T049/T050追補で既定化済み)。代替物理なし
3. 北極星KPI → 確定レビュー済み実部品画像による検知精度向上(全数評価ハーネスのAUROC/過検出率)
4. 無意味な繰り返しでないか → **新規確定データがない周回は学習せずSKIP**(§4)。ここが本設計の核
5. 学びの記録 → status JSON + trouble_history/bd へ

## 1. 現状分析(idle_trainer.py 読解結果)

| 項目 | 現状 | 問題 |
|---|---|---|
| リソースガード | `may_train()` あり(CPU35%/MEM88%/GPU30%/GPU空き5GB) | ✅ 良好。ただしディスク残量とプロセス多重は未検査 |
| データ十分性 | `min_confirmed_total=30` 件未満で学習スキップ | ⚠️ 累計判定のみ。**前回学習以降の新規件数を見ないため、同一データで毎時間再学習し得る**(P026違反リスク) |
| 状態出力 | stdout print のみ | ❌ 成果物(status file)なし → T056鮮度死活が不可能 |
| 失敗処理 | 例外時はプロセス死亡(loop内try無し) | ❌ fail_streak概念なし、無限クラッシュループ or 無言死 |
| ループ形態 | `while True + sleep(3600)` | ⚠️ 常駐型はT056の多重起動/亡霊問題を再生産する |
| SUCCESS定義 | `train_reference_challenger(promote=False)` の戻りをprint | ❌ 学習実行=成功扱い。評価メトリクス非依存(P025リスク) |

## 2. 起動形態: 常駐whileループではなくスケジューラ駆動 `--once`

- Task Scheduler が毎時 `--once` を起動(常駐化しない)。理由: T056の教訓「プロセス存在=生存」等式を最初から排除。1周=1プロセスなら亡霊・多重増殖・pidズレが構造的に発生しない
- 起動は `pythonw` + 子プロセスは `CREATE_NO_WINDOW`(T058。K10のCMD点滅事件の再発防止)
- 多重防止: 起動直後に**ポート/名前ではなくstatusファイルのlock節**(owner: pid+起動時刻+ホスト名、T059の正確なowner照合方式)で単一実行を保証。stale lock(後述の鮮度基準超過)は自動奪取可
- スケジューラ登録は既存タスクの有無を必ず確認してから(多重登録禁止 — agent_bridge運用と同じ)

## 3. 成果物鮮度ベース死活判定(T056)

- 新規成果物: `data/workspace/apps/growth_dashboard/visual_inspection_idle_status.json`
  - 毎周回、**SKIPでも必ず**更新(verdict/reasons/resources/pending件数/fail_streak/updated_at)
  - tri_track statusと同スキーマ思想(`clawstack.visual_inspection_idle.v1`)でダッシュボード統合可能に
- 死活判定: `updated_at` が `2×interval + margin`(=2.5h)より古ければ「死」と判定。プロセス一覧は見ない
- watchdog側(登録する場合)は「多重検知→全掃除→単一起動」+`-Restart`フラグ常設(T056参照実装: start_k10_tri_track_cae_watchdog.ps1 74fdc6a)。ただし§2のスケジューラ駆動なら watchdog自体を省略でき、Task Schedulerの次回起動が実質的な自己回復になる(推奨)

## 4. 化粧SUCCESS禁止(P025)の評価軸 + 進化必須(P026)

verdict は以下のみ許可(「学習が走った=SUCCESS」を禁止):

| verdict | 条件 |
|---|---|
| `SUCCESS` | 新規確定レビュー≥N件で学習実行 **かつ** 全数評価ハーネス(T050追補)の評価メトリクス(AUROC/欠陥検出数/過検出率)が算出・記録された **かつ** 直前SUCCESSとの差分(データ件数 or メトリクス)が可測 |
| `SKIP_NO_NEW_DATA` | 前回学習以降の新規確定レビュー<N件(既定N=5、累計30件条件は初回のみ)。**再学習しない** |
| `SKIP_RESOURCE` | may_train() NG(理由列挙) |
| `FAILED` | 学習/評価が例外・タイムアウト |
| `FAILED_NO_EVOLUTION` | 学習は完走したがメトリクス・データ件数とも前回と完全同一(P026) |
| `STOPPED_MEANING_GATE` | fail_streak到達(§5) |

- 実装時の要点: DBに `last_trained_review_id`(または学習時点のREVIEWED件数)を記録し、差分件数で判定。メトリクスは status JSON の `last_success.metrics` に数値で残す(「見た目のSUCCESS通知」だけを禁止する評価軸)
- promote(champion昇格)は自律ループでは行わない(`promote=False`維持)。昇格はメトリクス比較レポートを添えて手動承認 — 実機検査品質に直結するため

## 5. fail_streak自動停止(P026系・tri_trackと同方式)

- `FAILED`/`FAILED_NO_EVOLUTION` の連続回数を status JSON で永続カウント(SKIPはカウント外・リセットもしない)
- `fail_streak >= 5` で `meaning_gate.stopped=true` を書き込み、以降の周回は起動即終了(スケジューラは残すがno-op)。解除は原因記録+手動フラグクリアのみ
- 閾値5の根拠: 1周1h・データ蓄積待ちが主動作のループで8連敗を待つ意味が薄い。5連敗=同一原因の可能性大
- 停止時Telegram通知は1回のみ(連投禁止)

## 6. リソースガード(既存 may_train の拡張点)

- 既存: CPU/MEM/GPU使用率+GPU空きメモリ → そのまま採用
- 追加すべき項目:
  1. **ディスク残量**: D:残量<20GBで学習スキップ(T048系。学習成果物・チェックポイントが100MB超になる場合は `F:\clawstack_data\visual_inspection\` へ — 2026-07-12ユーザー指示)
  2. **学習サブプロセスのタイムアウト**: `timeout` ラップ必須(T050: subprocess timeoutは子を殺さない。Windowsネイティブなら Job Object か finally句 taskkill /T)
  3. **時間帯ガード(任意)**: ユーザー作業時間帯(9-18時)はCPU閾値を厳しく(35→25%)する等

## 7. 実装時の変更対象(参考・本Runでは未実施)

- `projects/visual_inspection_ai/scripts/idle_trainer.py` — verdict体系/status出力/fail_streak/差分学習判定
- `projects/visual_inspection_ai/src/inspection_ai/learning/resource_guard.py` — ディスク残量追加
- 新規: スケジューラ登録ps1(既存タスク検出+単一登録+pythonw+CREATE_NO_WINDOW)
- 登録前検証: py_compile → `--once` 手動1周(SKIP_NO_NEW_DATAで正常終了すること)→ status JSON目視 → 登録

## 8. QC工程表 / FMEA(要約)

| 工程 | 管理ポイント | 故障モード | 対策(本設計での対応) |
|---|---|---|---|
| 登録 | タスク重複 | 多重登録→多重学習 | 登録前検出+lock節(§2) |
| 周回 | status更新 | 無言死・亡霊 | 鮮度死活+スケジューラ駆動(§3) |
| 学習判定 | 新規データ差分 | 同一データ再学習(化粧SUCCESS) | SKIP_NO_NEW_DATA(§4) |
| 学習実行 | タイムアウト | プロセス残留・GPU占有 | timeoutラップ(§6) |
| 評価 | メトリクス記録 | 学習完走=成功と誤認 | メトリクス必須のSUCCESS定義(§4) |
| 失敗継続 | fail_streak | 無限クラッシュループ | 5連敗自動停止(§5) |

FTA頂上事象「無意味な自律ループ化(T019再発)」の切断点は §4のSKIP_NO_NEW_DATA(データが増えない限り何もしない)。これが本設計の最重要ゲート。
