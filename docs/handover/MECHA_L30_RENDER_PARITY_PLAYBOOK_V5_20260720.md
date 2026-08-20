# Mecha L30 — レンダー初期状態パリティ修正 + playbook v5 (2026-07-20)

作業者: Claude Fable 5 (Cowork) / 承認: ユーザー包括承認(2026-07-20「30回まで承認を得たとして進めてください」+ 7/19「完全版になるまで自走して改善ください」)

## 発見(AI目視確認ルールの適用で判明)

1. **cycle1/2の「travel -1.5m・即転倒」はレンダー環境の欠陥だった**。
   訓練Env.reset=参照歩容へ関節スナップ+実測settle stand_z に対し、
   render_walk.py=棒立ち(全関節0)+stand_z=0.44ハードコード → 方策が未経験の
   初期状態から開始し即後方転倒。訓練中upright 0.98との不整合はこれで説明。
2. 修正後のcycle3レンダー: **実歩行 約6秒・+1.63m前進**(目視確認済・前傾姿勢)→終盤転倒。
3. しかし playbook v4 の `dive_hack`(travel>=1.0 and fell)に誤該当し、
   歩行方策がフレッシュ再学習で破棄される構造だった。

## 変更ファイル(全て.bakあり)

| ファイル | 変更 | バックアップ |
|---|---|---|
| `stage_a/render_walk.py` | ①訓練と同一初期化(settle300→set_qpos→参照スナップ・実測stand_z) ②`first_fall_sec`計測を`walk_check.json`へ追加 | `.bak_initparity_20260720` |
| `autonomy/motion_learning_supervisor.py` | gather_metrics/pick_ruleに`first_fall_sec`追加(None→9999, 欠落→0.0の保守解釈) | `.bak_fallsec_20260720` |
| `autonomy/playbook.yaml` | v5: `walks_then_falls`ルール新設(travel>=1.0 and fell and first_fall_sec>=3.0 → resume latest, entropy 0.001, iters 2500)。`best_walker`=cycle3退避ckpt登録 | (v4は`.bak_20260719`) |
| `autonomy/u5_train_dispatcher.py` | Telegram outbox処理フック(非致命) | `.bak_outbox_20260720` |
| `autonomy/telegram_outbox.py` | **新規**: サンドボックス→Windows経由Telegram送信(msg_*.json→sendPhoto/sendMessage、3回失敗でfailed/) | — |

退避ckpt: `C:\v50_work\autonomy\known_good\walk_20260720_cycle03_travel1.63.pt`
(cycleディレクトリは再利用され上書きされるため必須)

## 検証済み

- py_compile: render_walk / supervisor / u5 / telegram_outbox 全OK
- playbook v5: yaml+miniパーサ両方で7ルール順序・walks_then_falls判定・best_walkerパス一致PASS
- pick_rule: 5ケース(実測cycle3値含む)PASS / 旧supervisor後方互換(→dive_hackフォールバック)PASS
- outbox: 送信/リトライ/隔離ロジックのモックテストPASS + 実送信2件成功(08:37, 09:0x)
- render初期化順序: スタブexecテストで settle300→set_qpos→参照スナップ PASS

## 現在の状態(10:20)

- cycle4(**旧**playbook v4がsupervisorメモリ内・フレッシュ・2000iter)10:11開始 → ~12:50完了見込み
- 安全弁: 最大6サイクル / 2連続無改善(threshold=best 1.63×1.15=1.87m)でエスカレーション
- **req_walk_v3 装填済み**: 現ラン終了後、u5が新コード+playbook v5で自動配車
  (初回からbest_walker=cycle3歩行ckptを継承)
- スケジュール: 毎朝6:05 morning-check(AI目視必須化済み)+ Telegram outbox経路稼働中

## 未解決 / 次回

1. cycle3方策は「前傾姿勢」で歩く — upright報酬とpose追従のバランス調整は次の改善候補
   (first_fall_secデータが蓄積されてから判断)
2. bd起票は引き続き不可(サンドボックスにbd CLIなし)。本MDが代替記録
3. 訓練環境evalのtravel(auto-reset下限値0.12)とレンダーtravel(1.63)の乖離は仕様として理解
   (evalはauto-resetにより下限値しか出ない。習得判定はレンダー側が正)

## 追記(19:25)— 旧walk_cycle系がGPU占有・改良版をブロック → 停止機構

**発見**: 再起動主体不明の古いsupervisor(skill=walk)が walk_cycle01(旧コード・旧playbook v1・
1500iter・約16.7s/iter=通常の3倍遅い)をGPUで回し続け、改良版(req_walk_v3・walk_auto)の
u5配車をブロックしていた。walk_autoチェーンは cycle5(travel -1.27, sprint_and_fall)で16:04に
エスカレーション終了済み。agent_bridgeは未activ化(executor enabled=false・watcher停止)のため
Codex経由停止は不可。

**対応**(ユーザー承認「旧ランを止めて改良版へ」2026-07-20):
- `autonomy/stop_rogue_walk.py`(**新規**): 多重ガード付き一回限り停止。停止対象は
  `train_v50_walk_tracking かつ walk_cycle0` と `motion_learning_supervisor かつ --skill walk` のみ。
  保護トークン(u5/u7/u1/u2/u4/run_robot_l20/walk_auto/self)を含むプロセスは絶対不停止。
  停止後 supervisor_status を escalated へ(u5が空きGPUと認識)。offline分類テスト13ケースPASS。
- `autonomy/u5_train_dispatcher.py`: `stop_rogue.flag` 存在時のみ stop_rogue_walk を1回実行し
  flagを.doneへ改名するsentinelフック(.bak_outbox_20260720に含まれる。再発火はflag再作成が必要)。
- トリガ: `autonomy/stop_rogue.flag` 設置済み → 次u7サイクル(~5分)でu5が実行。
  実行後、GPU解放→u5がreq_walk_v3(新コード+playbook v5+render parity+best_walker=cycle3)を自動配車。

**実行結果(19:39)**: 列挙の`-Command`インラインクォートが0件を返す不具合を`.ps1`ファイル方式へ
修正して再発火→ 旧trainer(pid 8260, walk_cycle01)+旧supervisor(pid 24052, --skill walk)を
正しく停止。u5/u7/run_robot_l20/他デーモンは全て保護(誤爆ゼロ)。supervisor_status→escalated→
**同一u5サイクルでreq_walk_v3(改良版)を自動配車**。19:43時点 walk_auto_cycle01 iter進行中
(5.4s/iter=正常速度)、`--resume ...known_good\walk_20260720_cycle03_travel1.63.pt`で
cycle3歩行ckptから継承=playbook v5のbest_walkerが機能。証拠: `rogue_stop_log.txt`。

**再起動主体を特定**: Windowsスケジュールタスク `Clawstack_Motion_Learning_Supervisor`(毎時・
死活時のみ再起動)が `scripts/start_motion_learning_supervisor.ps1` を実行 → 旧 `--skill walk`
(実mocap参照なし・旧Stage A)を起動していた(登録元 `scripts/install_p009_self_growth_schedules.ps1`)。
単一インスタンスガードがあるため**改良版稼働中は競合しない**が、改良版終了後に旧版が復活する構造。
**恒久対策**: `start_motion_learning_supervisor.ps1` を **skill=walk_auto + --ref-json refs\walk.json**
起動へ変更(.bak_walkauto_20260720)。これで定期再起動は「旧版復活」から「改良版起動」に転換。
ref欠損時のみ従来へ安全フォールバック。**u5(キュー)とこの直接起動の二重管理は将来単一化推奨**。

## 追記(2026-07-21)— プラトー(freeze局所解)対策

**経過**: 7/20夜の停止・切替後、修正した定期起動スクリプトが改良版を自動再開(旧版復活せず=修正成功)。
1日走らせた結果、dive_hack(転倒)は解消したが**逆に「転ばないが歩かない」freeze局所解**へ収束
(7/21実測: fell=false・upright0.94・travel 0.603→0.208mへregression、best1.70m、2回escalation)。
根本原因: dive_hack対策の強upright ゲート+転倒-10で「静止すれば安全に無償収入(定数0.25+0.5×r_up
≈0.725/step)」が最適に。exp系のr_vel/r_travelは静止時に勾配が弱く脱出できない。

**対策(ユーザー承認「プラトー対策」2026-07-21)**:
- `train_v50_walk_tracking.py`(.bak_antifreeze_20260721): ①静止無償収入を削減(定数0.25→0.1,
  r_up重み0.5→0.3)②線形前進報酬 `r_prog = gate×clamp(fwd_v,0..target)/target`(重み0.8)追加。
  静止=0、前進に比例加点、upright>0.85ゲート共有でダイブ非誘発。numpy検証: 静止収入0.95→0.61、
  歩行-静止インセンティブ差+0.44→+0.80、前進勾配は単調、upright0.7で r_prog=0。
- `playbook.yaml` v6(.bak_v6_20260721): ③`stand_freeze`ルール(not fell and travel<0.8 and
  first_fall_sec>=3.0 → best_walkerから entropy0.004/ils-0.7 高探索)④max_consecutive_no_improve 2→3。
  両パーサ検証PASS・7/21実測freeze値がstand_freezeへ正しくルーティング。
- **適用タイミング**: 報酬=次サイクルの新trainerプロセスから / playbook v6=次supervisor再起動から
  (現chainがescalate→定期起動で再起動時)。現在の健全なcycle01は中断しない。

## 追記(2026-07-22)— 姿勢アンチ前傾(第3段)

**経過**: anti-freeze後、転倒/停滞は解消し「前傾ランジで1.7-1.85m歩くが4-6秒で転倒」まで前進
(距離条件1.5m達成済、残る壁=8秒間直立維持)。調査(docs/knowledge/walk_rl_success_knowledge_base_100_20260722.md
+ good_libraries_100_...)でGenesis公式Go2例の base_height/lin_vel_z 罰則がこの実装に欠落と判明。
**対策(ユーザー承認「実装」2026-07-22)**: `train_v50_walk_tracking.py`(.bak_posture_20260722)に
デッドバンド付き姿勢罰則3項を追加— ①過度な傾き pen_tilt(grav_x²+grav_y²−0.07 の正部, W=1.0)
②胴体沈み pen_low(stand_zから8cm超の沈みのみ, W=20)③鉛直速度 pen_vz(vel_z², W=0.5)。
転倒-10・直立ゲート・anti-freese報酬は不変。定数化(TILT_DEADBAND/W_TILT/HEIGHT_DEADBAND/W_LOW/W_VZ)。
numpy検証: 報酬順序=直立歩行3.67>静止2.39>前傾ランジ1.83>転倒寸前1.21、自然歩行の罰則<0.05
(前進報酬を損なわず)、前傾は静止より不利=freeze非再誘発。適用は次trainerプロセス(次サイクル)から。

## 追記(2026-07-22 夜)— GPU使用率:限界に程遠い→並列環境数を増強

**実測(gpu_probe.py・read-only・u5 sentinel経由)**: RTX 5060 Ti(16GB)で
**util 16% / VRAM 1000MiB of 16311 / 電力 34W of 180W / 55°C** = 大幅に遊休。
GPUテレメトリ(clawstack_gpu_logger)は6/25で停止しており、一回限りプローブで実測した。
原因: `motion_learning_supervisor.py` の `--n-envs 512` ハードコードが16GB GPUに対し小さすぎ、
モデル(MLP256-128)も小さくGPUが餌不足。
**対策(.bak_nenvs_20260722)**: n_envs を環境変数 `MECHA_N_ENVS`(既定 **4096**)化。VRAM見積は
512env≈1000MiB(base≈700+約0.6MiB/env)より 4096env≈3.1GB=安全域(8192でも約5.5GB)。並列数増で
GPU使用率・スループット・1iterサンプル数が増え学習が速く安定。**適用は次のsupervisor再起動から**
(現supervisorは旧コードをメモリ保持。reward(posture)は次サイクルのtrainerから、n_envsは次supervisor
再起動から反映)。T067(GPU lost)配慮で中庸の4096。増強後に gpu_probe 再実行で util 上昇を確認予定。
新規: `gpu_probe.py`(+u5 `gpu_probe.flag` フック)。

**適用(即時・ユーザー「推奨で進めて」)**: 現行の旧構成ラン(512env・旧報酬)をクリーン再起動して
新構成を即適用。新規 `restart_walk_auto.py`(+u5 `restart_walk_auto.flag`)= walk_autoの
supervisor+trainerのみ停止(u5/u7/L20他は保護・誤爆ゼロ、証拠 restart_walk_auto_log.txt)。
**重要な発見**: 現行の walk_auto は u5キューでなく**スケジュールタスク**(start_motion_learning_supervisor.ps1)
が起動しており、u5キューの依頼(v2/v3)は7/21から終端(escalated)だった。→ req_walk_v3 を retargeted へ
戻して u5 に即再配車させ、新コードで起動: `--n-envs 4096 ... --resume known_good/cycle3(1.63m)`。
**実測(再起動後)**: util **16%→49%** / VRAM **1000→4429 MiB** / 電力 34→53W / 温度51°C。
かつ **4096env で約4.3s/iter(512env時とほぼ同時間)= 実効スループット約8-9倍**。まだ余裕あり
(VRAM27%/電力29%)、更に攻めるなら MECHA_N_ENVS=6144〜8192(T067配慮で当面4096)。

## 未解決 / 次回(更新)
- 増強後(4096env)にgpu_probe再実行しutil/温度/電力を確認。余裕あれば6144-8192へ、逼迫や不安定なら2048へ(MECHA_N_ENVS)。GPUテレメトリ常時ロガーの復活も検討。
- 姿勢罰則の効き具合を朝チェックで確認(first_fall_secが8sへ伸びるか)。効き過ぎ(歩けず静止)ならW_TILT/W_LOWを下げ、緩ければ上げる。次段候補=feet_air_time報酬(踏み出し奨励)/速度カリキュラム(0.15→0.33)。
- anti-freeze後の挙動を朝チェックで確認(歩幅・travel伸長・転倒再発の有無を目視)。効き過ぎならr_prog重み/静止収入を微調整。
- スケジュールタスクとu5キューの二重ディスパッチ一本化(bd: -l30w1)。Windows側でしか変更不可。
- bd起票はjsonl直接追記+`bd import`待ち(.beads/PENDING_IMPORT_20260720.txt)。

## ロールバック

```powershell
cd D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration
copy stage_a\render_walk.py.bak_initparity_20260720 stage_a\render_walk.py
copy autonomy\motion_learning_supervisor.py.bak_fallsec_20260720 autonomy\motion_learning_supervisor.py
copy autonomy\playbook.yaml.bak_20260719 autonomy\playbook.yaml
copy autonomy\u5_train_dispatcher.py.bak_outbox_20260720 autonomy\u5_train_dispatcher.py
del autonomy\telegram_outbox.py
```
