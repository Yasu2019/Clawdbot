# 3Dモデル生成前 GPU 競合隔離で ScheduledTask 無効化に失敗

- 日時: 2026-07-30 JST
- Beads: `Clawdbot_Docker_20260125-hc0l`
- 目的: 新規3Dキャラクター生成前に、別件のRobot L20 GPU学習と自動再起動要因を一時停止する。
- ユーザー承認: PID 26716、PID 24960、および関連3タスクの一時停止・一時無効化を明示承認。

## 観測事実

- PID 26716: `run_robot_l20_autonomous_loop.py`, batch 229。
- PID 24960: `robot_l20_autonomous_watchdog.py`。
- 両PIDは承認後に停止し、停止確認済み。
- 対象タスク:
  - `Clawstack_Motion_Learning_Supervisor`
  - `Clawstack_Robot_L20_Autonomous_Loop`
  - `Clawstack_Robot_L20_Watchdog`
- `Disable-ScheduledTask` は3件とも `HRESULT 0x80070005 / Access is denied`。
- タスク状態は `Ready` のままであり、自動再起動リスクが残る。
- 操作直後GPUは0%、VRAM 4160 MiB。
- 新規3D生成は未開始。既存モデル・設定・出力は未変更。

## 5 Why

1. なぜ競合隔離が完了しなかったか: ScheduledTaskを無効化できなかった。
2. なぜ無効化できなかったか: 現在のPowerShellに必要な管理者権限がなかった。
3. なぜ通常権限で実行したか: タスク状態のread-only確認は通常権限で可能だったが、変更権限は別だった。
4. なぜ事前に権限を判定できなかったか: 対象タスクのACL確認を実施していなかった。
5. なぜ生成を止めたか: watchdogが生成中にGPU学習を再開するとVRAM競合・OOM・成果物破損の危険があるため。

## Fishbone / FTA

- 権限: ScheduledTask変更に昇格権限が必要。
- 自動化: watchdogと定期タスクが停止したプロセスを再起動できる。
- GPU: 同時学習でVRAMが急増し得る。
- 品質: OOMや処理中断はモデル・動画の検証不能につながる。
- 最上位事象: 3D生成中に旧GPU学習が再開する。
  - OR: watchdog定期実行
  - OR: autonomous loop定期実行
  - OR: motion supervisor定期実行

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| タスク無効化の権限不足 | 旧GPU処理が再起動 | 8 | 7 | 4 | 224 | 管理者PowerShellで対象3件のみ無効化 |
| プロセスだけ停止 | watchdogが再生成 | 8 | 8 | 3 | 192 | タスク状態Disabledを生成前ゲートにする |
| 競合したまま生成 | OOM・成果物不完全 | 9 | 6 | 5 | 270 | GPUプロセスとVRAMを連続監視 |

## 対策案（ユーザー承認待ち）

1. 管理者PowerShellで対象3タスクだけを一時無効化する。
2. 状態が `Disabled` であることをread-onlyで検証する。
3. PID 26716/24960および同じコマンド系統が再起動していないことを検証する。
4. GPUが安定して空いていることを確認してから、別バージョンの3D生成を開始する。
5. 生成完了後も自動再有効化せず、ユーザーへ状態を報告する。

## 回復・ロールバック

- 停止したRobot L20プロセスの成果物は削除していない。
- 対象タスクは無効化できておらず、元の `Ready` 状態のまま。
- 生成は開始していないため、3D成果物のロールバックは不要。

## Scope limits

- ScheduledTask ACLの具体的な付与主体は未確認。
- 管理者実行なしでは対象3タスクを安全に無効化できることは証明されていない。
- Web検索は不要。原因はローカルWindows権限エラーとして確定している。

## 承認後の対策実施・検証

- ユーザーが管理者PowerShellで対象3タスクを無効化し、完了を通知。
- 3タスクすべて `Disabled` を確認。
- 無効化直前に同じ承認済み系統が新PIDで再起動していた:
  - PID 26652 / 2868: `train_v50_walk_tracking.py`
  - PID 29472: `run_robot_l20_autonomous_loop.py`
  - PID 18096: `robot_l20_autonomous_watchdog.py`
- コマンドラインが承認済みプロセス系統と一致することを検証後、この4 PIDだけを停止。
- 停止後、同じコマンド系統は不在。検査用PowerShell自身のみ検索結果に含まれた。
- 最終GPU状態: utilization 0%、VRAM 120 / 16311 MiB。
- 無関係なプロセス、モデル、成果物、タスクには変更を加えていない。
