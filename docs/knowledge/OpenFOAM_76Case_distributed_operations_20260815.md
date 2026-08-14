# OpenFOAM 76Case 分散計算・欠陥解析 運用ノウハウ

更新: 2026-08-15 JST  
正本: `docs/knowledge/OpenFOAM_76Case_distributed_operations_20260815.md`  
Beads: `Clawdbot_Docker_20260125-d5ye`

## 目的

76Case樹脂充填を、K10と複数PCで安全に並行計算し、充填・ウェルドライン・ボイド・収縮・ヒケ・反り評価へ段階的につなぐ。

## 基本設計

- Wi-Fi/Tailscale越しの単一MPIジョブは使わない。通信断が全rankを止めるため。
- PCごとに独立ケースを配置し、パラメータ比較・粗格子・詳細格子を並行する。
- K10の詳細powerLawケースを基準系、他PCの粗格子を早期スクリーニング系とする。
- 旧ジョブは必ず事前監査し、明示承認なしに停止・削除・上書きしない。
- ケース、コンテナ、ログ、チェックポイントは一意名にする。
- Dockerは `--restart=no`。停止期限があるPCはSIGINT停止とwatchdog再開を使う。

## ケースと品質

- 詳細H3: 9,216,745 cells、OpenCFD 2512、interFoam、polymer/air VOF、powerLaw。
- 高速格子: 174,260 cells。4 mm代表セル、1.2 mm境界セル。
- 粗格子では元の微小ベントが消えたため、保持された中央ゲート区間の反対側へ数値ベントを設定。
- 高速格子: gate 135 faces、vent 53 faces。
- 修復後も low-quality face tets 17面、concave cells 3個が残る。早期探索用であり最終検証用ではない。
- 粗格子の数値ベントや定粘度近似は必ず「screening surrogate」と明記する。

## 重要な失敗と対処

1. 8 mm格子では薄肉形状が3セルまで消失しcfMeshがSIGSEGV。4 mm/1.2 mmへ戻す。
2. OpenFOAM環境パスはイメージにより異なる。2512は `/usr/lib/openfoam/openfoam2512/etc/bashrc`。
3. `turbulenceProperties` 欠落で起動失敗。詳細ケースのlaminar設定をコピーする。
4. Foundation OpenFOAM 14はOpenCFDのpowerLaw/Newtonian名を受け付けず、constantモデルへ変換が必要。
5. Foundation 14では `cAlpha` が廃止。interfaceCompression schemeを使う。
6. Foundation 14では `constant/momentumTransport` が必要。
7. MPI slot不足時は、物理コアを超える意図がある場合のみ `--oversubscribe`。
8. Windows SSH公開鍵は管理者なら `C:\ProgramData\ssh\administrators_authorized_keys`、ACLはSYSTEM/Administratorsのみ。
9. WSLはWindowsユーザー単位。Scheduled TaskをSYSTEMで作ると対象ディストリビューションを操作できない。Interactiveユーザーで登録する。
10. Docker DesktopをSSHから直接起動するとセッション終了時に停止する場合がある。Interactive Scheduled Taskで常駐させる。

## ノード運用

- K10: 詳細12 MPI + 高速4 MPI。
- VivoBook MHN15: 10 MPI。Foundation 14互換の定粘度近似。参加期限に合わせwatchdogと安全停止。
- ThinkPad L590: 6 MPI、OpenCFD 2512 powerLaw。
- 赤LAVIE: 6 MPI、OpenCFD 2512 powerLaw。既存worker/monitorを保持。
- メインLAVIE: 8 MPI、OpenCFD 2512 powerLaw。旧 `claw_resume_u105_09` とSJP/n8nを保持。
- G3: 3 MPI、OpenCFD 2512 powerLaw。明示承認後、旧app sidekiq/web/db/redis/n8nの5本を一時停止。削除なし。
- 合計計画値: 49 MPI ranks。

## 判定階層

1. 粗格子充填で到達時間、未充填、合流位置を抽出。
2. 温度依存Cross-WLF、充填・保圧を追加。
3. pVT・固化履歴から体積収縮、ボイド、ヒケ指標を作る。
4. 圧力・温度・固化収縮を構造格子へ写像。
5. 残留応力・冷却差から反りを解析。
6. Moldflow相当を主張する前に実測または基準ソフトで校正する。

## 回収・再開

- `startFrom latestTime` と短い `writeInterval` を使う。
- 期限前はSIGINTで停止し、最新時刻を確認する。
- リモートPC切断後もローカルDocker/WSL計算は継続可能だが、スリープ禁止・Tailscale/sshd自動起動を設定する。
- 回収時はログ末尾の `Time`、`Phase-1 volume fraction`、圧力残差、continuity error、コンテナ状態を同時保存する。

## 安全ルール

- 旧コンテナは停止前に名前、Compose project、workdir、restart policy、CPU/RAM、mountを記録。
- 停止承認は対象名を列挙して取得する。
- `docker stop` と削除を区別する。停止ではvolume/imageを保持する。
- 温度センサーが疑わしい端末は重計算へ投入しない。
- 秘密鍵、パスワード、トークンは知識記録へ保存しない。
