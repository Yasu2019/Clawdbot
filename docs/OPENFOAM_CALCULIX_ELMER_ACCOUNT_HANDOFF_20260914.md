# OpenFOAM / CalculiX / Elmer 別アカウント引継ぎ

作成: 2026-09-14 20:42 JST  
作業ルート: `D:/Clawdbot_Docker_20260125`

## 1. 引継ぎ方針

この会話のセッションIDや別アカウントの認証情報はファイルへ保存しない。
別アカウントでは、このMDとリポジトリを開き、下記の「再開前チェック」を実行してから新世代の出力先へ再開する。
既存ジョブの停止・削除・上書きはしない。

## 2. 2026-09-14 20:42時点の実行状態

- OpenFOAM / `ccx` / Elmer の solver本体プロセス: **検出なし**。
- `ClawstackVivobookOpenFOAMResume`: 登録済み、最終実行 `2026-09-03 18:50:50`、結果 `267009`。成功計算として扱わない。
- `OpenFOAM_76Case_Hourly_Telegram`: Ready相当、最終結果0。別系統の定時タスクであり、本引継ぎ対象と混同しない。
- `ClawstackCAETrialEngine`: 定時タスク、最終結果1。所有者不明のため変更しない。
- 稼働中の `vivobook_openfoam_resume_watchdog.py`、fleet監視、Docker/WSL、通知系は既存所有者のため変更しない。
- OpenFOAM再開watchdogは存在するが、solver実行中の証拠ではない。

## 3. 主要な計算成果物

### OpenFOAM

- 既存比較記録: `artifacts/box_roundhole_v5/openfoam_calculix_comparison_r1/`
- 注意: `open_top_shell_run2` は `time=2.2` までの未監査実行記録であり、完成した非等温・圧縮性・充填結果ではない。
- 旧 `polymerInterFoam` 再開は単位・圧力・CFL問題で失敗した。新規世代フォルダを使い、旧時刻ディレクトリを直接再利用しない。

### CalculiX

- mesh: `artifacts/box_roundhole_v5/ccx_mesh_bridge_r1/mesh.inp`
- mesh SHA256: `7d15bb597d53930929744091a79381bf07c869a79a83221e08cbc78885eee4e0`
- cooling benchmark: `artifacts/box_roundhole_v5/ccx_cooling_benchmark_r2/`
- packing/structural results: `artifacts/box_roundhole_v5/packing_integrated_dt025_r1/`
- 既存benchmarkは仮想一様冷却であり、実測PVT・完全保圧連成・接触を含まない。

### Elmer

- screening case: `artifacts/box_roundhole_v5/elmer_coupling_l1/`
- `case.sif` は線形弾性＋結果出力のscreening設定。
- `openfoam_fem_comparison.json` の判定は `SOLVER_PASS_SCREENING_ONLY`、engineering claimは `NONE`。
- Elmer結果をOpenFOAMの実圧力場として逆利用しない。

### 最新のボイド一方向計算

- フルC3D4: 67,165要素、物理温度＋同一工程の規定CCX保圧荷重から局所seed気泡ODE。
- 最新batch: `artifacts/void_box_ccx_oneway_all_20260914_r1/`
- 線形再構築・時間刻み比較:
  - `batch_linear_reconstruction_dt001_r1/`
  - `batch_linear_reconstruction_dt0005_r1/`
  - `linear_reconstruction_time_sensitivity_dt001_dt0005_r1.json`
- 空間監査: `c3d4_diffusion_graph_audit_r4.json`
- 最新共有状態: `data/workspace/apps/moldflow_cae_studio/coupling_status.json`
- これは仮想・未校正・一方向候補場であり、核生成率、実ボイド確率、CT予測、完全連成ではない。

## 4. 再開前チェック

PowerShell:

```powershell
Set-Location D:\Clawdbot_Docker_20260125
python -m json.tool data\workspace\apps\moldflow_cae_studio\coupling_status.json
Get-Process | Where-Object {$_.ProcessName -match 'foam|ccx|elmer|mpirun'}
Get-FileHash artifacts\box_roundhole_v5\ccx_mesh_bridge_r1\mesh.inp -Algorithm SHA256
python -m pytest tests\test_c3d4_gas_diffusion.py tests\test_void_element_history_batch.py tests\test_void_classical_nucleation.py -q
```

期待値: solver本体プロセスなし、mesh SHAが上記と一致、関連テストPASS。

## 5. 最新局所ボイド計算を別アカウントで再現する場合

```powershell
Set-Location D:\Clawdbot_Docker_20260125
python scripts\solve_void_element_history_batch.py `
  --config artifacts\void_box_ccx_oneway_all_20260914_r1\adapter_config.json `
  --history artifacts\void_box_ccx_oneway_all_20260914_r1\history.csv `
  --mesh artifacts\box_roundhole_v5\ccx_mesh_bridge_r1\mesh.inp `
  --source-manifest config\ccx_box_void_history_source_all_r1.json `
  --output artifacts\void_box_ccx_oneway_all_20260914_r1\handoff_replay_r1 `
  --max-step-s 0.01 --seed-radius-factor 1.0 `
  --spatial-diffusion --diffusion-scheme linear_reconstruction
```

出力先は必ず新しい世代名にする。既存 `r1` の上書きは禁止。

## 6. 次に実装・計算すべき順序

1. OpenFOAMの同一工程から、物理 `T(K), p(abs), alpha, U, rho` を同一mesh・同一時刻で抽出する。
2. その履歴をC3D4へ保存的に転送し、現在の仮想CCX規定圧力を置換する。
3. OpenFOAM→CalculiXへ温度・保圧・固有ひずみ・拘束解除を接続する。
4. Elmerは独立熱／構造比較として使い、結果差を記録する。
5. 粗密メッシュ3水準、時間刻み3水準、保存則、再始動再現性を確認する。
6. 実測PVT/Cross-WLF/CTE/結晶化/ガス溶解度を校正用・検証用に分離して投入する。

## 7. 正直な完了判定

現時点で通っているのは、局所ボイドODE、C3D4要素対応、保存型線形再構築、
仮想CCX温度・規定圧力の一方向計算、数値単体試験です。
OpenFOAMの非等温圧縮性樹脂充填と、CalculiX/Elmerを含む完全二方向連成は未完了です。
「solverが起動した」「screening出力がある」だけでは完成扱いにしない。

## 8. 参照文書

- `docs/CAE_ARBITRARY_3D_IMPLEMENTATION_AGENDA_20260914.md`
- `docs/OPENFOAM_CALCULIX_HANDOFF_20260912.md`
- `data/workspace/memory/void_local_physics_20260914.md`
- `docs/INCIDENT_LOG.md`
- `data/state/Obsidian Vault/60_PC_Logs/CAE_INC-194_20260914.md`

## 9. 2026-09-14 再開プリフライト改善 (10項目)

`scripts/cae_resume_preflight.py` を追加した。旧ジョブを停止せず、次の10項目を読み取り専用で確認する。

1. 作業ルート存在
2. 共有ステータスJSON存在
3. C3D4メッシュ存在
4. 引継ぎMD存在
5. ステータスJSON形式
6. ステータス名の明示
7. メッシュSHA256一致
8. solver本体プロセス不在（watchdog・自身のプロセスを誤検出しない）
9. 未使用の新世代出力先
10. 未校正・screening等の制限事項の明示

検証結果: `tests/test_cae_resume_preflight.py` 11件PASS、連成関連回帰テスト25件PASS。
実機プリフライト結果は `artifacts/resume_preflight_20260914_r2/preflight.json` に保存した。
判定は `start_new_generation_only`。既存成果物・定時タスク・watchdogは変更していない。

## 10. 8項目の本体接続契約

`scripts/cae_multiphysics_contract.py` と `tests/test_cae_multiphysics_contract.py` を追加した。
OpenFOAMの同一時刻ディレクトリから `T, p, alpha, U, rho` を読み、セル数・有限値・単位方向の妥当性・alpha範囲を検証する。
CalculiX転送は明示的な重なり行列による体積積分補正を行い、相対保存誤差を記録する。
粗密／時間刻み比較は相対L2収束判定、材料カードはPVT/Cross-WLF/CTEと実測フラグを分離して扱う。
8段階（充填、5場同時性、保存的転送、冷却収縮反り、Elmer比較、ボイド連成契約、収束性、校正）を一つの契約JSONへ出力できる。
実測フラグがない材料は `VIRTUAL_OR_INCOMPLETE`、ボイドは `FIELD_CONTRACT_ONLY` とし、完成計算や実材料精度を偽装しない。
回帰テスト: 本体接続契約7件を含む合計43件PASS。

## 11. 2026-09-19 CAEワーカーSSH永続化

各PCで短時間にSSH接続不能になる問題を調査し、稼働中の解析を停止せずに次を適用した。

- メインLAVIE、赤LAVIE、Vivobook: `sshd` と `Tailscale` を自動起動にし、異常終了時の3段階再起動を設定。
- 同3台: AC電源時の自動スリープ、蓋閉じスリープ、復帰時ロックを無効化。
- メインLAVIE、赤LAVIE: Realtek 8822BE Wi-Fi の `MSPower_DeviceEnable.Enable` を `False` に変更し、OSによるアダプター電源断を禁止。
- Vivobook: MediaTek MT7902ドライバーは `AllowComputerToTurnOffDevice` を `Unsupported` と報告するため、サービス復旧とスリープ防止のみ適用。
- ThinkPad Ubuntu: `ssh`/`tailscaled` は enabled/active、sleep/suspend/hibernate targetsはmasked。`ClientAliveInterval 60`、`ClientAliveCountMax 3`、`TCPKeepAlive yes` を追加し、NetworkManager接続 `E440973A1E43-5G` のWi-Fi省電力を `disable` に変更。
- K10: 現在のシェルに管理者権限がなく、`sshd` は `Manual` のまま。管理者PowerShellで自動起動・回復設定が必要。

保全事項: 赤LAVIEで実行中の `apt-get install -y openfoam14` (確認時PID 597) は停止・上書きしていない。
検証: メインLAVIE、赤LAVIE、Vivobook、ThinkPadに対し、独立したSSH接続を2巡連続で成功確認した。
Beads記録: `Clawdbot_Docker_20260125-yhil`。

## 12. 2026-09-19 3台OpenFOAM事前評価

ユーザー承認により、メインLAVIE、赤LAVIE、ThinkPadのOpenFOAM-14導入完了後に、穴付き箱ケースの未校正事前評価を自動開始する。

- 赤LAVIEとThinkPadは既存の`apt-get install -y openfoam14`を保全して完了待ち。
- メインLAVIEは`/opt/openfoam14`未導入・既存solverなしを確認し、`scripts/install_openfoam14_ubuntu2604.sh`で公式リポジトリから導入開始。
- 3台へ`box_roundhole_r17_preflight_base_20260919.tar.gz`と`run_openfoam14_box_preflight.sh`を配置済み。
- アーカイブSHA256: `40B12FCAC6554176191B6D2D8F9CEE950CFBD2FCF5BE09350C23E8812435117C`。
- 初回は2 MPI、最大3600秒、`endTime=0.001`、`maxCo=0.25`、`maxAlphaCo=0.15`、`maxDeltaT=1e-6`。
- real `T,p,alpha,U,rho`履歴が同一mesh・同一時刻で合格した場合のみ、CalculiX/Elmerの反り・収縮・ヒケとボイド入力適格性へ進む。
- 実測校正前であり、初回結果は`VIRTUAL_SCREENING_UNCALIBRATED`。製品精度やボイド確定を主張しない。

監視: heartbeat `openfoam-calculix-elmer-improvement-until-midnight` を3台監視へ更新（10分間隔）。
Beads: `Clawdbot_Docker_20260125-xflk`。

### OpenRadioss後続導入

各ホストの短時間OpenFOAM評価が起動し、最初の有効チェックポイントと安定ログを確認した後にOpenRadiossを導入する。

- 固定版: 公式GitHub release `latest-20260728`
- asset: `OpenRadioss_linux64.zip`
- SHA256: `598ed7b2905a7bacc8d1781470c250ac79d7558c39ba962768edf3644644fe33`
- installer: `scripts/install_openradioss_linux64_20260728.sh`
- install root: `/opt/openradioss/latest-20260728`、`/opt/openradioss/current`をsymlink
- acceptance: `starter_linux64_gf`と`engine_linux64_gf`が実行可能、`ldd`にmissing libraryなし
- stale-task rule: 既存starter/engine、apt/dpkg、OpenFOAM solverと競合する場合は導入を開始しない
- OpenRadioss入力ケースは未指定なので、現段階では導入・依存関係スモークまで。解析は自動開始しない

## 13. 2026-09-19 短時間評価の初回障害と保守再試行

ThinkPadの初回2 MPI評価は`0.00075`までチェックポイントを保存した後、
時刻`0.0008346 s`で`Negative initial temperature T0: -0.086537941`により停止した。
直前の最大Courant数は約0.2504であり、失敗世代
`/opt/openfoam_runs/box_roundhole_r17_thinkpad_preflight_20260919`は証拠として保持する。
初回結果は`solver_exit_code=1`、`fatal_count=3`であり、成功扱いしない。

再試行では旧世代を上書きせず、`scripts/run_openfoam14_box_preflight.sh`の安定化ゲートを
`maxCo=0.10`、`maxAlphaCo=0.02`、`maxDeltaT=2e-7`へ保守化した。新世代
`/opt/openfoam_runs/box_roundhole_r17_thinkpad_preflight_r2_20260919`を2 MPIで開始した。

OpenRadiossの初回導入は、同梱された`libhm_reader_linux64.so`と`libapr-1.so.0`を
`ldd`検証時の`LD_LIBRARY_PATH`へ渡していなかったため、誤ってmissing判定となった。
installerを修正し、実行環境と同じlibrary pathで再検証した結果、starter/engineの実行属性と
`ldd` missingなしを確認した。導入先は`/opt/openradioss/latest-20260728`、
`/opt/openradioss/current`symlinkである。

赤LAVIEはOpenFOAM-14 (`20260724`) の導入完了と`foamVersion=OpenFOAM-14`を確認し、
旧aptプロセスが存在しない状態で新規ケース
`/opt/openfoam_runs/box_roundhole_r17_red_preflight_20260919`を2 MPIで開始した。
メインLAVIEはOpenFOAM未導入のままSSH banner timeoutとなり、再接続後に公式installerを
再投入する。既存ジョブや部分導入ファイルは削除しない。

追跡更新: ThinkPadの保守再試行(r2)も`maxCo=0.10`で`0.0005`保存後、
`T0=-0.050457559`の熱力学反転で停止したため、成功扱いしない。赤LAVIEは
`0.0005`まで保存したが、外部中断で終了し`preflight_result.json`未生成のため、
同様に未完了扱いとする。両ケースのログ・チェックポイントは保持している。
メインLAVIEは現在、公式OpenFOAM installerの`apt/dpkg`処理が実行中であり、
その処理が完了するまで評価を開始しない。

2026-09-19 09:05 JST追跡: 赤LAVIEのOpenRadiossは
`/opt/openradioss/current/exec/starter_linux64_gf`とengineが実行可能で、
実行環境を反映した`ldd`でmissingなしを確認した。インストール途中のSSH切断後も
成果物は保持されており、解析入力は投入していない。メインLAVIEはapt/dpkg処理中の
負荷によりSSH banner timeoutが発生しているため、導入完了確認まで触らない。

## 14. 2026-09-19 負温度停止への新規世代ガード

`scripts/run_openfoam14_box_preflight.sh` に第6引数`thermal_guard`（既定`1`）を追加した。
新規ケースに`system/fvConstraints`が存在しない場合だけ、OpenFOAMの
`limitTemperature`（`T=273.15..650 K`、`cellZone all`）を生成してから分解・実行する。
既存の`fvConstraints`は上書きしない。これにより、Courant数を下げるだけでは防げなかった
`Negative initial temperature`を、熱方程式の試行値が物理範囲外へ進む前に抑止する。
ThinkPad上で更新スクリプトの`bash -n`をPASS確認した。旧失敗世代は再利用せず、次回は新世代へ適用する。

root systemd unitでMPIを起動すると、ログイン環境がないためOpen MPIの`opal_init`
が`Unable to get the user home directory`で停止する事象も確認した。runnerはroot時に
`HOME=/root`と`OMPI_ALLOW_RUN_AS_ROOT{,_CONFIRM}=1`を設定するよう更新し、3件の静的回帰テストをPASSした。
root unitの実行は新世代・独立unitに限定し、既存ケースや計算プロセスは停止しない。

ThinkPad r5では`maxCo=0.10`でも速度発散によりCourant数が急増しSIGFPEとなったため、
runnerの新規`fvConstraints`へ`limitMag(U,max=20 m/s)`を追加した。これはゲート速度2 m/sに
対する数値暴走ガードであり、材料物性や製品精度を意味しない。新世代r6以降へ適用し、
旧世代r2/r5のログ・チェックポイントは保持する。

## 15. 2026-09-19 09:50 JST 停止理由・チェックポイントの自動記録

既存runnerを置換せず、`scripts/run_openfoam14_box_preflight_v2.sh`を追加した。
新世代でのみ使用する保守版runnerで、開始時に`preflight_started.json`を作成し、
終了時に`preflight_result.json`へ次を記録する。

- `stop_reason`: `completed` / `budget_timeout` / `interrupted` /
  `floating_point_exception` / `negative_temperature` /
  `incomplete_checkpoint` / `solver_error`
- `checkpoint_valid`: `alpha.polymer,T,p_rgh,U,rho`が同一processor時刻に存在する場合のみtrue
- `checkpoint_fields`: 同時刻で検出した`alpha.polymer,T,p_rgh,U,rho`の一覧。rho欠落は下流連成へ昇格させない
- `started_utc`、`elapsed_wall_s`、solver exit code、fatal marker数

これにより、Windows/WSLの電源断・SSH切断でsolverが中断しても、部分時刻をfull-fill
完走と誤認せず、次世代の再開候補を機械的に選別できる。既存ケースを停止・上書きせず、
新世代ディレクトリへ適用する。静的回帰テストは7件PASS。

さらに`start_openfoam14_wsl_detached.ps1`を追加した。Windows側で新しいunitを
`systemd-run --no-block`へ渡した後、独立したWSL keepalive子プロセスをunitが終端するまで
 維持する。SSHセッション終了だけでWSLが破棄される環境向けで、unitがactive/activatingの
 場合は重複投入を拒否する。旧unitのstop/kill/restartは行わず、起動条件・PID・unit・caseを
 `wsl_detached_launch.json`へ記録する。PowerShell構文解析もPASSした。

ThinkPad r6の実ログでは、`limitMag(U,max=20)`が選択されたにもかかわらず、
`Time=0.000769435 s`付近でCourant maxが`4.3e9`、その後`2.47e43`へ跳ね、
`thermophysicalPredictor`内でSIGFPEとなった。これは単なる熱範囲外ではなく、圧力・速度の
フィードバック発散である。v2 runnerに第7引数`pressure_guard`（既定1）を追加し、新世代の
`system/fvSolution`で`solvers.p_rgh`をPCG/DIC、`relTol=0`へ保守化する処理を入れた。
既存fvSolutionは消去せず、設定できない形式では元の辞書を保持して証跡を残す。初版v2をr8へ
適用した際、PCGへ変更したのに`preconditioner`が追加されずFOAM FATAL IO ERRORとなったため、
同じ`p_rgh`ブロックへDICを追加する補正を入れた。r8は入力不整合として失敗扱い・保持し、
修正版を次世代へ適用する。初回修正版配布時にheredoc内Pythonのインデント不備も検出され、
除去して再検証した。さらに短時間runで必ずcheckpointを書けるよう、`endTime<0.0005 s`
では`writeInterval=endTime/2`へ自動調整し、FPE trapping起動バナーをSIGFPEと数えないよう
検出パターンを厳密化した。次世代へは修正版のみを配布し、静的回帰テストは9件PASS。

10:08 JSTに修正版をThinkPadへ投入し、r10 (`clawstack-of-preflight-thinkpad-r12`)を開始。
`DICPCG`での`p_rgh`反復を確認し、10:10 JST時点で`Time=9.0e-5 s`、最大Courant約0.0049、
FATAL/SIGFPEなしでactive。これは安定化検証中であり、endTime=0.0002 s完走および同一時刻の
全履歴が揃うまでfull-fillや連成解析の入力適格とは判定しない。

10:15 JSTに修正版をr11 (`clawstack-of-preflight-thinkpad-r13`)へ適用し、
`DICPCG`で`Time=9.86e-5 s`までFATAL/SIGFPEなしで進行中。r10/r11とも、完走manifestと
同一時刻のcheckpoint監査が完了するまで downstream coupling はHOLDとする。

追跡結果: r11は`elapsed_wall_s=153`で`endTime=0.0002 s`を完走し、
`stop_reason=completed`、`checkpoint_valid=true`、`alpha.polymer,T,p_rgh,U,rho`の同時刻履歴をPASS。
最終平均alphaは`0.00021890739`であり、充填率は約0.022%に過ぎないためfull-fillではない。
従ってこの世代は「安定短時間履歴の抽出」だけを合格とし、反り・ヒケ・収縮・ボイド・
CalculiX/Elmer本解析へはまだ昇格させない。証跡は
`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r11/`へ保全した。

再開経路の検証: r11の`0.0002 s` processor checkpointからr12を新世代複製し、
`resume_mode=1`（`startFrom latestTime`、再分解なし）で`endTime=0.0004 s`まで194秒で完走。
manifestは`checkpoint_valid=true`、`alpha.polymer,T,p_rgh,U,rho`をPASSし、最終平均alphaは
`0.00043701684`。電源断／SSH切断後に同じcheckpointから継続できるコード経路はPASSしたが、
充填率は約0.044%であり、full-fill・製品評価・CalculiX/Elmer本解析への昇格はまだ行わない。
証跡は`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r12/`へ保全した。

同フォルダの`checkpoint_audit.json`を新規`validate_openfoam_checkpoint.py`で検証した。
processor0/1の`nCells=25756`に対し、`alpha.polymer,T,p_rgh,U,rho`をすべて同一時刻
`0.0004`で25756要素として確認し、`status=PASS`。uniform alphaフィールドもmesh cell数へ
正規化して判定する。これでCalculiX/Elmerへ渡す前の同一mesh・同一時刻契約を自動監査できる。

r13はr12の`0.0004 s`から`resume_mode=1`で継続し、`endTime=0.001 s`を569秒で完走した。
`stop_reason=completed`、`checkpoint_valid=true`、DICPCG、fatal_count=0、最終平均alphaは
`0.0010254738`（約0.10%）。r13のprocessor0/1はnCells=25756で5フィールドの同時刻監査もPASS。
これは安定継続の実証でありfull-fillではない。次の延長計算でも同じresume・監査ゲートを必須とし、
CalculiX/Elmer・反り・ヒケ・収縮・ボイド評価へはfull-fill履歴が得られるまで昇格させない。
証跡は`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r13/`。

09:48 JST時点の実行状態:

- ThinkPad r6 (`clawstack-of-preflight-thinkpad-r8`): active、2 MPI、温度・速度ガード下で
  `Time=0.000296 s`まで安定。完走判定前であり、結果を製品精度とは扱わない。
- 赤LAVIE r5: WSLセッション終了により`09:48:41`停止、`preflight_result.json`未生成。
  ログ・processor checkpointは保持し、停止原因を「WSL/ホスト外部中断」と記録する。
- メインLAVIE: WSLは起動可能だが、r5ケースは未作成。旧世代を再利用せず、runner v2の
  新世代を投入する場合は、Windows側で独立起動できることを確認してから行う。

runner v2に任意の`CHECKPOINT_AUDIT_SCRIPT`呼び出しを追加し、終了時に
`preflight_checkpoint_audit.json`とログを生成する。監査スクリプトが未配置でもsolver結果を
壊さず、配置済みThinkPadでは次世代から自動監査を有効化する。静的回帰テストは14件PASS。

ThinkPad r14 (`clawstack-of-preflight-thinkpad-r16`) はr13の`0.001 s` checkpointから
`resume_mode=1`で`0.0015 s`まで409秒で完走した。`solver_exit_code=0`、`fatal_count=0`、
`stop_reason=completed`、`checkpoint_valid=true`であり、最終時刻は`alpha.polymer,T,p_rgh,U,rho`
を同一mesh・同一時刻で保持する。外部監査もprocessor0/1とも`nCells=25756`、5場すべて
25756要素で`status=PASS`となった。成果物は
`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r14/`へ保全した。
この履歴は安定スクリーニング合格であり、平均充填率・full-fill・実測校正・製品評価の
代替ではない。なお、チェックポイント監査スクリプトを直接実行できるよう先頭shebangを
追加し、ローカル回帰テストは14件PASSを維持した。

12:03 JSTの3台プロセス再監査では、ThinkPadのr14 unitはinactiveで完走manifestを維持し、
OpenFOAM/MPI/apt/dpkg/ccx/Elmer/OpenRadioss実行プロセスは見つからなかった。赤LAVIEと
メインLAVIEもWSL内でOpenFOAM-14が確認でき、対象solver/installerプロセスは見つからない。
赤LAVIEにはOpenRadiossも存在するが、メインLAVIEには未導入。赤LAVIEの旧r1〜r5、
メインLAVIEの旧r1〜r3ケースには完走manifestがなく、最古ケース・ログは保持し、再利用や
削除はしていない。赤LAVIEでは基礎アーカイブのSHA256が既知値と一致し、保守runner v2・
チェックポイント監査・WSL detached launcherをWindowsユーザーフォルダへ追加配置した。
ただしWSL/systemdの状態確認コマンドが無出力のまま長時間応答せず、起動・再開unitの健全性を
確認できなかったため、新しい計算は投入していない。メインLAVIEはSSH自体は応答した後、
同様にWSL監査が遅延した。両機の計算再開は、WSL応答性と新規systemd unit起動・keepaliveを
確認できてからとし、既存ケースは停止・上書きしない。

同日12:20 JST、WSL/systemd状態確認コマンドが無出力で長時間待ち続ける運用上の弱点に対し、
`start_openfoam14_wsl_detached.ps1`の読み取り専用事前確認を20秒上限に変更した。上限超過時は
診断ジョブのみを停止し、fail-closedで例外終了する（OpenFOAM unitや既存solverは停止しない）。
PowerShell構文解析PASS、関連回帰15件PASS。実機WSLが長時間応答しない場合は新規投入を拒否し、
ホスト復帰後に再監査する。

ThinkPad r14ログの終端は`Phase-1 volume fraction=0.0015213772`（時刻0.0015 s）で、
407秒の計算でも平均充填率は約0.152%に留まる。単純線形外挿では平均alpha=1まで総計約74.3時間
となるが、これは1.5 msだけからの概算であり予測保証ではない。電力を浪費する延長を避け、
同一条件のままfull-fillまで走らせず、まずゲート流量・ベント境界 flux とスケール、粗密メッシュ・
時間刻みの妥当性を検証する。安定化のために根拠なく時間刻みを増やしたり、partial-fillを完了と
表示しない。計算率証跡は`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r14/rate_projection.json`。

13:00 JST、時間刻み上限を実験変数として指定・記録できるようrunner v2に任意第9引数
`maxDeltaT`を追加した（既定値は2e-7 s）。r14実測ではCo max=0.0363、interface Co max=0.0042
だったため、別ケース世代r15で3e-7 sを試験した。r15はCo max=0.0555、interface Co max=0.0049で、
保守上限0.10/0.02内に留まったが、endTime=0.0018 sへ到達した最終状態はcheckpoint未出力で、
最新保存時刻0.00175 sのためrunnerはfail-closedで`incomplete_checkpoint`とした。原因は
`writeInterval=0.00025 s`がendTimeを割り切らず、要求時刻の場が保存されなかったこと。

このためrunnerの書出し周期をendTimeに整合させ、最大0.00025 s程度ごとの保存を保ちつつ、
最終時刻も書くよう`writeInterval=endTime/N`へ設定する変更を実装した。r16はr15の有効な
0.00175 s checkpointから再開し、`writeInterval=0.000225 s`で0.0018 sまで27秒で完走。
`alpha.polymer,T,p_rgh,U,rho`すべて同一時刻・同一meshで監査PASS、fatal 0、Phase-1平均率
0.0018181（約0.182%）であり、full-fillではない。3e-7 sの短い比較区間では計算速度向上は
確認できておらず、これ以上の時間刻み増加は行わない。r15/r16とも別世代として保持し、r15の
不完全終端checkpointも失敗証跡として残す。関連テスト16件PASS。成果物は
`artifacts/dispatch/three_node_preflight_20260919/thinkpad_r15/`および`thinkpad_r16/`。

13:15 JSTの再監査で、ThinkPadのsolverではない孤立診断shellを確認した。親PID 72434/72578は
前回の読み取り専用コマンドで`source /opt/openfoam14/etc/bashrc`した際にParaView初期化を呼び、
子PID 72579 `pvdataserver --version`待ちで21分停止していた（0% CPU、約1.1% RAM）。これは
私が起動した診断処理とプロセス系譜で確認し、SIGTERMで当該4 PIDだけを終了、消滅を確認した。
foamRun/mpirunおよびr18 unitには触れていない。以後、診断ではOpenFOAM環境をsourceしないか、
必要な場合は`source /opt/openfoam14/etc/bashrc ParaView_TYPE=none`を使う。

13:27 JST、赤LAVIEではSHA256検証済みの基礎archive・runner v2・監査scriptをユーザープロファイルへ
stage済みで、短時間r6を新規作成しようとしたが、`sudo install -d /opt/...`がパスワード待ちになり、
約1.5分、PID 452 `sudo install`と親PID 343 bashが0% CPUで停止した。これは今回の私の準備処理と
判別し、SIGTERMで当該2 PIDのみ終了、`/opt/...r6` target不在・solver非稼働を確認した。archive展開も
solver起動も実行されていない。以後はroot権限を要求せず、WSLユーザーの書込可能な`$HOME`配下へ
新規caseを展開する方式に変更する。停止後のWSL/SSHはリセットされ、実機作業を保留中。メインLAVIEも
直近監査でSSH timeout。既存r1〜r5/r1〜r3ケースとThinkPad r14〜r16は変更なし。

13:44 JST、`start_openfoam14_wsl_detached.ps1`のWSL状態照会をさらにfail-closed化した。
従来は`systemctl is-active`の表示文字列だけを見ていたため、SSH/WSLエラー文字列を`inactive`と
誤認する余地があった。読み取り専用Jobから出力と終了コードを返し、systemdの正常なinactive (3)
だけを新規起動可能とし、WSL異常終了や`failed`等の曖昧状態では拒否する。先行の20秒上限も維持。
PowerShell構文解析PASS、関連17テストPASS。赤LAVIE側にはまだ改訂版launcherを再配置していない。

## 16. 2026-09-19 Red LAVIE r6 停止RCAとlauncher改善

- r6 case: `/home/yns-lavie/openfoam_runs/box_roundhole_r17_red_preflight_r6_20260919`
- 事実: `preflight_started.json`あり、`preflight_result.json`なし。ログは`Time=4.4e-06`までで、unitは約16秒後に停止。現時点のRed LAVIEではUbuntu/Docker WSL停止、foamRun/mpirun非稼働。既存r1-r5は保持。
- 停止の正確な引き金は未確定。systemd単独ではWSLを生存させず、リモートセッション配下のプロセスもセッション終了で停止し得るため、ホスト側の所有者が必要という設計上の問題として扱う（r6の直接原因と断定しない）。
- `scripts/start_openfoam14_wsl_detached.ps1`を改訂: 一意名Task Scheduler worker、WSL readiness marker、readiness確認後のみsolver dispatch、20/25/30秒bounded call、dispatch exit/output記録、状態不明時fail-closed。指定unitだけでなくWSL内の`foamRun`/`mpirun`全体を読み取り専用で監査し、既存solverが一つでもあればtask登録/solver dispatchを拒否する。削除時はランダムworker設定fingerprint一致を確認し、既存unit/タスクを自動停止・上書きしない。全引数をWSL照会前に検証し、`-ValidateOnly`で外部副作用なしに検査できる。worker終了時はmonitor exit/outputとrunner `stop_reason`をhost manifestへ追記し、target-time完了とterminal非成功結果、invalid result、never-active、result未生成、monitor失敗を区別する。
- 検証: PowerShell AST parse PASS、対象テスト25 PASS。埋込みBashの`bash -n`、strict JSON schema/stop_reason確認（途中書込みを考慮した最大5回retry）、`completed` / `incomplete_checkpoint` / 不正JSON分類、Task Scheduler削除helperのモック実行（fingerprint不一致および複数actionは削除拒否）、active solver発見時のfail-closed順序を検証。`-ValidateOnly`正常経路とNaN終了時刻拒否を実Windows PowerShellで確認し、WSL/task/solver操作なし。直近変更前snapshot: branch `backups/openfoam-launcher-post-input-20260919`, commit `74e1e4fb7e`; 初期snapshot: branch `backups/openfoam-launcher-prechange-20260919`, commit `8060cf0d35`; archive SHA256 `07EF620386BF14367955E4D2A59AAF4A43097FB21B6822485731E69217596C84`。
- 未実施: Redへの改訂版配置、Task Scheduler/WSLの実機スモーク、OpenFOAM solver再開。次はsolverを走らせない短いライフサイクル試験を新規caseで行い、タスク状態・WSL readiness・manifest・後片付けを確認する。ログインユーザーのinteractive sessionが前提で、Windows電源OFFをまたぐsolver自動再開は未実装。
- Beads: `Clawdbot_Docker_20260125-xflk`; memory key `openfoam-red-lavie-keepalive-20260919`; incident `INC-195`。
- Microsoft一次資料: [WSL systemd](https://learn.microsoft.com/en-us/windows/wsl/systemd), [Start-Process](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1)。
