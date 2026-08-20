# FEM Impact DOE01 引継ぎ（2026-07-29）

更新日時: 2026-07-29 04:34 JST  
プロジェクト: `D:\Clawdbot_Docker_20260125`

## 1. 最重要事項

ユーザーが分析を求めている対象は、次のモデルだけである。

```text
input=test_practical_doe01.in
case=/home/yasu/clawstack_satellite/impact_bundle/AUTO_FIX_ORIENTATION_20250804/Impact/160um_Panel_20250725/Rough_Mesh
analysis_end_time=0.0063
original_requested_job=tri-thinkpad-fem_impact-af1ba91d
```

`test.in` は対象外である。過去に誤って選択された
`tri-thinkpad-fem_impact-e3308e18`、`tri-thinkpad-fem_impact-8e44893f`
などを、今後の分析・再計算・進捗通知に使用してはならない。

## 2. 現在の状態

- FEM Impact の設定は `Rough_Mesh/test_practical_doe01.in` のみ有効。
- `test.in`、`test_practical_forming.in`、FEM bench の新規スケジュールは無効。
- 2026-07-29 04:34 JST の進捗スナップショットでは、DOE01 の新しい VTK は
  `0.003100 / 0.006300`、進捗 `49.206%`。
- 同スナップショットの状態は `running=true`、`last_error=null`。
- 直近のリモート確認では、ThinkPad 上で exact input
  `test_practical_doe01.in` の `run.Impact` が1プロセス稼働し、
  CPU 約387%、RAM 約14.8%を使用していた。
- オーケストレータの状態ファイルは、直近完了扱いの試行
  `tri-thinkpad-fem_impact-d624b1c4` を `timeout` / `FAILED`
  と記録している。設定の `max_timeout_sec=7200` により、解析完了前に
  約2時間で試行が失敗扱いとなる。

注意: 同じ共有ケースの VTK を複数の試行モニターが参照しているため、
表示される trial ID と実際に計算中の起動単位が一致しない場合がある。
入力名、ケースパス、solver PID、VTK の更新時刻を組み合わせて確認すること。

## 3. 実施済みの修正

### 対象モデルの固定

`data/workspace/cae_workload_router.yaml`

- `Rough_Mesh/test_practical_doe01.in` のみ有効化。
- `test.in` と `test_practical_forming.in` の新規スケジュールを無効化。
- FEM Impact bench schedule を無効化。

### 0%ループ・誤進捗対策

`scripts/fem_impact_progress_telegram.py`

- `--not-before-epoch` を追加。
- VTK は job start と input mtime より新しいものだけを採用。
- mtime で除外してから simulation time 順に選択。
- exact solver の実在確認後だけ開始通知。
- solver 起動待ちを600秒に設定。

`scripts/k10_tri_track_cae_orchestrator.py`

- localhost port `47653` による singleton guard を追加。
- 現ジョブより古い PNG/VTK を再利用しない。
- `run.Impact` の一括停止を禁止し、exact case/input だけを対象化。
- 進捗モニターへ freshness 条件を渡す。

`scripts/test_fem_impact_progress_telegram.py`

- VTK freshness と選択順序の回帰テストを追加。

## 4. 未解決事項

1. `max_timeout_sec=7200` が解析時間より短く、DOE01 が約2時間ごとに
   `timeout` となって再投入されている。
2. 過去の DOE01 進捗モニターが複数残っている。確認された trial には
   `a3aed168`、`f225c4b7`、`8fd42b9d`、`bbe23fad`、`44eda069`、
   `caafd368`、`90091d3d`、`d624b1c4`、`e9adf00f` がある。
3. 複数モニターが同じ共有 VTK を読み、重複通知または trial ID の混同を
   起こす可能性がある。
4. 空の一時状態ファイル `9005b93f.tmp` が確認されている。

推奨する次の修正は、ユーザーの明示承認を得てから、DOE01 の旧モニターだけを
整理し、タイムアウトを解析完了まで十分な値に延長することである。
forming 監視、他トラック、他ホストのジョブは対象に含めない。

## 5. 保全対象（停止禁止）

ローカルには、以前からの `test_practical_forming.in` 用進捗モニターが残っている。
確認済みの親子 PID は次のとおり。

```text
25984 -> 25464  trial=3fcfe012
34824 -> 7204   trial=6d63c845
```

これらは現ユーザー指示の DOE01 とは別の旧作業であり、今回停止・削除していない。
所有者はローカルユーザー `yasu` の既存 CAE 自動化。現在の主な計算負荷は
ThinkPad 上の DOE01 solver で、forming モニター自体のローカル負荷は小さい。

また、OpenFOAM、OpenRadioss、Docker コンテナ、他ホストの計算には触れていない。

## 6. 次担当者の確認手順

1. `test_practical_doe01.in` の exact solver が1個だけ存在するか確認する。
2. 最新 VTK の mtime が現在の solver 起動後であることを確認する。
3. simulation time が前回値 `0.003100` から増えているか確認する。
4. DOE01 の旧モニター整理が必要なら、PID・trial・影響を提示してユーザー承認を得る。
5. 承認後も DOE01 旧モニターだけを停止し、forming と他トラックが無傷であることを確認する。
6. `max_timeout_sec` 延長後、同じケースへの再投入が止まり、単一 trial で完走することを確認する。

## 7. 証跡

- `docs/incidents/fem_impact_target_mismatch_20260727.md`
- `data/workspace/.beads_issues.jsonl`
- `data/workspace/k10_tri_track_cae_status.json`
- `data/workspace/k10_tri_track_cae_log.jsonl`
- `data/workspace/fem_impact_progress/`
- `data/workspace/cae_workload_router.yaml`

今回の引継ぎ作成では読み取り確認だけを行い、プロセス停止、ファイル削除、
Docker 再起動、計算の再投入は行っていない。
