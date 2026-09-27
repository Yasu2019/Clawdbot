# INC-188 OpenRadioss 自動運用（2026-09-28 時点）

解析PC（K10）の OpenRadioss 計算を、人が見ていなくても止めずに回すための仕組みの一覧。

## 動いているもの

| 名前 | 起動方法 | 役割 | 記録先（data/workspace/） |
|---|---|---|---|
| `watch_openradioss_task.ps1` | タスク `INC188_OpenRadioss_Watchdog`（5分ごと） | 監視・自動再開・完走後の後処理・メモリ上限・キュー・通知 | `openradioss_watch_state.txt`, `ALARM_openradioss_p1r13_16.txt`（Telegram にも送信） |
| `c0_bisect_keeper.ps1` | タスク `INC188_C0Bisect_Keeper`（10分ごと） | 下の常駐スクリプトが落ちていたら起動し直す | `frame_monitor_log.txt`, `c0_bisect_log.txt` |
| `frame_monitor.sh` | keeper が起動 | 新しいアニメーションフレームごとに、パンチの素通りと丸穴の分離を判定 | `round_hole_frames.tsv`, `ALARM_round_hole.txt` |
| `engine_mem_log.sh` | keeper が起動 | エンジンのメモリ（RSS）と解析時刻を1分ごとに記録 | `engine_mem_log.tsv` |
| `engine_ctl.sh` | コンテナ内 `/work` に配置 | エンジンの RSS 取得・停止・生存確認（watchdog から呼ぶ） | — |

## watchdog がすること

1. **コンテナが止まっていたら `docker start`**（09-28 05:40 に外部から `docker stop` された件の対策）
2. **エンジンが止まっていたら（ログが10分以上更新なし×2回）再開用ファイルから再開**
3. **メモリ上限**：エンジンの RSS が 10 GB を超え、かつ再開用ファイルが 6 分以内に書かれていれば、停止してそのファイルから再開する（失うのは最大数分）。
   接触を内部面込み（`/SURF/PART/ALL`）にしたことで RSS が毎分 85〜120 MB 増えるため。
4. **完走したら後処理**（`finalize_runs.sh`：全フレームの VTK 化、時系列、全面スキャン）
5. **キュー**：エンジンが1本も動いていなければ `openradioss_queue.txt` の先頭を起動する。
   条件＝デッキが work にある・過去に起動していない・ホストの空きRAMが 8 GB 以上。
6. **通知**：`ALARM_round_hole.txt` に新しい行（初めての分離、パンチの素通り）が出たら転送する。

## よく使う操作

- 次に回す計算を積む：デッキ `PANEL4MM_<tag>_0000.rad` / `_0001.rad` を `clawstack_v2/data/work/` に置き、
  `data/workspace/openradioss_queue.txt` に `<tag>` を1行追記する。
- 監視対象：`data/workspace/openradioss_watch_tags.txt`（キューが起動時に自動で追記）
- 接触修正入りのデッキを作る：
  - 新規：`build_panel4mm_3d_blanking.py`（`--punch-contact-surface all` が既定）
  - 既存デッキから：`make_contact_all.py <dir> <src_tag> <new_tag>`
- フレーム監視を止める：`data/workspace/frame_monitor.disabled` を作る。

## 注意

- **エンジンのプロセス判定は、コマンドラインが `/opt/openradioss/` で始まるものだけにする。**
  `*engine_linux64_gf*` のような前方一致なしのパターンは、判定している自分のシェルにも一致する（09-28 に発生）。
- keeper の「動いているか」は、コマンドラインにスクリプト名を含む bash.exe があるかで見ている。
  スクリプト名を含む Bash コマンドから keeper を試すと「動いている」と誤判定するので、PowerShell から試す。
- 他のプロジェクト（MechaRL）と RAM を共有している。OpenRadioss 側は約 14 GB 以内と伝えてある。
- 使わなくなったもの：`c0_bisect.sh`（→ `c0_bisect_frames.sh`）、`launch_after.sh`（→ watchdog のキュー）。
