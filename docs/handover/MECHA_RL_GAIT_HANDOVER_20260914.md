# 二足歩行RL 引き継ぎ — 2026-09-14

現行ベスト **v139_ankle_knee010**（124条件を評価済み）。押し出しは解決、残るは膝と歩幅。
このファイルだけで再開できるように、パス・現状・地雷をすべて書く。

---

## 1. すぐ使うパス

| 用途 | パス |
|---|---|
| 作業ルート（キュー・結果・順位表）| `C:\v50_work\autonomy\` |
| 学習・診断コード | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a\` |
| Python（専用venv・これ以外使わない）| `C:\v50_work\genesis_venv\Scripts\python.exe` |
| 参照モーション | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_b\refs\v50_ref_LEVELWALK_ankle30.json` |
| 元MJCF | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\artifacts\v50_mecha.xml` |
| 登録済み方策 | `C:\v50_work\autonomy\known_good\`（`registry.json` が台帳）|
| 知見ノート | `D:\Clawdbot_Docker_20260125\docs\knowledge\mecha_rl_*.md` |
| ダッシュボード出力 | `...\data\workspace\apps\mecha_motion_lab\` と `...\growth_dashboard\` |

### 主要ファイル

| ファイル | 役割 |
|---|---|
| `autonomy\queue.json` | 実験キュー。`runs[]` に上から投入。`hold:true` で保留 |
| `autonomy\leaderboard.tsv` | 全条件の採点。`gait_trustworthy=yes` の行だけ信用する |
| `autonomy\watchdog_queue.ps1` | 5分ごと。空きスロットを埋める・保険を投入/退避 |
| `autonomy\autodiag.ps1` | 15分ごと。完走を自動診断→採点→ダッシュボード更新 |
| `autonomy\autogen_runs.py` | キューが浅いと現行最良から一因子変えた条件を自動生成 |
| `stage_a\train_v50_walk_rsl.py` | 学習（rsl_rl PPO, 4096env）|
| `stage_a\diag_gait_quality.py` | 歩容診断（8相・歩行比など）。`--json-out` で機械可読 |
| `stage_a\verify_policy.py` | 登録ゲート用の検証 |
| `stage_a\render_walk_rsl.py` | 動画フレーム生成 |
| `stage_a\train_v50_walk_tracking.py` | 機体定義（`build_model_xml`）・`DOF_NAMES`・KP/KV |
| `scripts\build_youtube_history.py` | YouTube用の歴史動画 |
| `scripts\send_walk_history_telegram.py` | Telegram送信 |
| `scripts\update_mecha_rl_status.py` | ダッシュボード用JSON/HTML生成 |

### タスクスケジューラ

```
MechaRL_Queue     5分ごと  watchdog_queue.ps1
MechaRL_AutoDiag 15分ごと  autodiag.ps1
```

---

## 2. 現状（2026-09-14 21:52）

**v139_ankle_knee010** / score 23.5 / 転倒 0/256 / 登録済み・運用域 0.75–1.05 m/s

```
--reward-scale feet_air_time=60.0,stride_advance=4.0,lateral_drift=-2.0,
  foot_lift_symmetry=-20.0,lin_vel_z=-0.3,double_support_ratio=-160.0,base_height=-40.0
--arm-kp-scale 0.15 --knee-kp-soft 0.10 --knee-kp-phase 0.72,0.15
--ankle-kp-soft 0.25 --ankle-kp-phase 0.45,0.72 --cmd-vx-min 0.60 --cmd-vx-max 1.20
```

| 指標 | v139 | 人間 | 状態 |
|---|---|---|---|
| 荷重応答期 | 10.7 | 12 | ほぼ達成 |
| 立脚中期 | 19.0 | 19 | **達成** |
| 立脚終期（押し出し）| 20.0 | 19 | **達成** |
| 前遊脚期 | 6.7 | 12 | **動かせないと判定** |
| 膝ピーク | 48.6° | 60° | 未達 |
| 歩幅/脚長 | 1.20 | 1.5–1.6 | 未達 |
| 歩行比 | 0.00597 | 0.0065 | 92% |

---

## 3. 解決済み（再検証しないこと）

**押し出し（立脚終期 8.5% → 24.5%）**
足首KPを**立脚終期の位相 0.45–0.72 だけ ×0.25** に落とす。報酬では10仮説すべて失敗した。
離地時の足部ピッチが +1°＝足が平らなまま離れており、底屈が幾何学的に不可能だったため。
→ `docs/knowledge/mecha_rl_pushoff_solved_phase_windowed_ankle_20260909.md`

**同型の成功3例**：腕 KP×0.15、膝 KP×0.10（遊脚窓 0.72–0.15）、足首 KP×0.25（立脚終期）。
**例外**：股関節は緩めると**悪化**（立脚終期が 1.0% に消滅）。送り出しの駆動そのものだから。

---

## 4. 未解決と、潰した経路

### 前遊脚 6.7%（人間12%）— **打ち止め推奨**

報酬係数3種（単脚支持・両脚支持罰・滞空報酬）、位相窓3種すべてで動かず。
離地時刻が位相 0.7 付近に固定されており、動かそうとすると歩容全体が壊れる。
前遊脚は立脚率から幾何学的に決まる量（両脚支持 = 2×(立脚率−50%)）で、
立脚率 57% が動かない限り 7% から動かない。

### 膝 48.6°（人間60°）— 22条件外し

| 疑ったもの | 実測 | 結果 |
|---|---|---|
| 機体の可動域 | **−10〜+65°** | 制約ではない |
| 参照モーション | **57°を教えている** | 不足ではない |
| ゲイン・位相窓（19条件）| 最高 49.9°（足趾40）| 打ち止め |
| 平滑化の罰（速度・加速度）| 弱めると 44.7° | 悪化 |
| 主要な罰4種（対称性等）| すべて悪化 | 否定 |

**膝は「浅い」だけでなく形が違う**（未着手の切り口）:

| 周期 | 0% | 20% | 40% | 60% | 70% | 80% |
|---|---|---|---|---|---|---|
| v139 | 19.8 | 25.3 | 2.2 | 11.8 | 24.2 | **48.6** |
| 人間 | 12 | 8 | 5 | **48** | **62** | 40 |

立脚中に曲がりすぎ（20%で25.3° 対 人間8°）、ピークが10%遅い（80% 対 70%）。
**ピーク値ではなくタイミングを狙う条件が次の一手。**

### 歩幅/脚長 1.20（人間1.5–1.6）— 実験中

股関節の振幅は **49.5°（人間 約50°）ですでに振り切っている**ので矢状面では伸びない。
→ **T104: 受動の股ヨー（骨盤回旋の代用）を実装済み・検証中**（次章）

---

## 5. 実行中の実験（T104）

この機体には鉛直軸まわりの関節が**1つも無かった**（18関節すべて矢状面/前額面）。
`upper_leg_{L,R}` に**受動ヨー**を注入する。骨格は `torso → upper_leg` なので
上半身を動かさず脚だけ回る。

```
--hip-yaw-stiffness 200|120|60|30 --hip-yaw-range 10.0
```

`y1_hipyaw200/120/60/30` の4条件が投入済み。**モータ無し・DOF_NAMES に載せない**ので
観測200・行動16は不変＝v139のチェックポイントをそのまま使える。

**判定**：歩幅/脚長 と 重心左右振幅（0.024m 対 人間0.04–0.06m）が同時に増え、
位相構成（立脚中期19.0 / 終期20.0）が崩れないこと。
効果があれば能動化（観測218・行動18、ゼロから約4時間）を検討する。

---

## 6. 地雷（同じ事故を繰り返さないために）

### 実験計画

1. **一因子試験は 1000 反復で行う。3000 は使わない。**
   v139 から**何も変えず**3000反復足した対照が、因子を変えた6本と**同一の崩れ方**をした
   （立脚中期 19.0 → 4.97）。3000 では因子の差より漂流が支配する。+1000 は人間域を保つ。
   → `docs/knowledge/mecha_rl_training_drift_confound_20260913.md`

2. **「A を変えたら B になった」の前に、A を変えずに同じ手間をかけた対照を取る。**

3. **生存者バイアス。** 診断は転倒しなかった env だけで歩容を計算する。
   転倒率が高い条件ほど少数の生存者が良く見える。`leaderboard.tsv` の
   `gait_trustworthy` 列が `NO-survivor-bias` の行は歩容の数値を信用しない。

4. **最適な設定と最適な停止点は別物。** v139 は「最良の停止点」であって、
   同じ設定で学習を続けると崩れる。

### ツール

5. **機体オプションは4ツール全部に通す。**（学習・診断・検証・レンダラ）
   渡し漏れで「別機体で測る」事故を**4回**起こした
   （08-29 `--height-scan` / 09-06 レンダラのゲイン / 09-08 `--hip-kp-soft` /
   09-08 レンダラの引数定義漏れで全条件クラッシュ）。
   `autodiag.ps1` は `diag_gait_quality.py --help` から受理フラグを機械的に取得して
   転送するので、**両方に実装すれば自動で渡る**。手書きの許可リストは廃止済み。

6. **`.ps1` は ASCII のみ。** PowerShell 5.1 は BOM無しUTF-8を ANSI として読む。

7. **日本語を出す Python は入口で UTF-8 固定。** リダイレクト時に cp932 になり、
   計算を終えた直後・結果を書く直前に落ちる（自動診断が5時間空回りした）。

8. **argparse の help に素の `%` を書かない**（`%%`）。`--help` が ValueError で落ちる。

9. **`diag_*.txt` は UTF-16。** PowerShell のリダイレクトがそう書く。Python で読むなら
   `decode('utf-16')`。

10. **PowerShell が書く JSON は BOM 付き。** Python 側は `encoding='utf-8-sig'`。

### 運用

11. **GPUを空転させない。** 状態は必ず `nvidia-smi` で確認する。status.json の
    iteration は最後に書かれた値であって動作の証拠ではない。

12. **キューを空にしない。** 空になると保険（`vcont_*`）が走るが、これは条件を変えないので
    **情報が増えない**。保険が23回起動した実績あり。`ALARM_queue.txt` が出ていたら枯渇。

13. **タスクの exit 0 は成果の証明ではない。** 成果物（診断JSONの件数）を数える。

---

## 7. 再開手順

```powershell
# 1. 状態確認
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
Get-Content C:\v50_work\autonomy\leaderboard.tsv | Select-Object -First 5
Get-ChildItem C:\v50_work\autonomy\ALARM_*.txt   # あれば異常

# 2. 手動で1ティック回す（スロットが空いていれば投入される）
powershell -NoProfile -ExecutionPolicy Bypass -File C:\v50_work\autonomy\watchdog_queue.ps1

# 3. 条件を足す: queue.json の runs[] に追記（total は 1000）
#    seed は現行最良の latest.pt を指す
```

診断の手動実行:

```powershell
$env:PYTHONIOENCODING='utf-8'
C:\v50_work\genesis_venv\Scripts\python.exe `
  D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a\diag_gait_quality.py `
  --ckpt C:\v50_work\autonomy\v139_ankle_knee010\latest.pt --label test `
  --ref-json D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/rl_integration/stage_b/refs/v50_ref_LEVELWALK_ankle30.json `
  --n-envs 256 --seconds 20 --cmd-vx 0.9 --passive-toe --height-scan `
  --arm-kp-scale 0.15 --knee-kp-soft 0.10 --knee-kp-phase 0.72,0.15 `
  --ankle-kp-soft 0.25 --ankle-kp-phase 0.45,0.72
```

---

## 8. 成果物

| | |
|---|---|
| YouTube用動画 | `C:\v50_work\youtube\mecha_walk_history.mp4`（15クリップ・94秒・v139まで）|
| Downloads | `C:\Users\yasu\Downloads\mecha_walk_history_20260911.mp4` |
| ダッシュボード | `http://localhost:8088/apps/mecha_motion_lab/mecha_rl_status.html`（15分ごと自動更新）|

動画の字幕は**簡単な英語のみ・ノウハウ非記載**の方針。更新は
`scripts\build_youtube_history.py` の `CLIPS` に追記して再実行。
公開前に必ず `fell: false` とフレーム目視の**両方**で確認すること
（09-06 に転倒した動画を作った）。

---

## 9. 関連ノート

- `docs/knowledge/mecha_rl_pushoff_solved_phase_windowed_ankle_20260909.md` — 押し出しの解法
- `docs/knowledge/mecha_rl_training_drift_confound_20260913.md` — 対照の欠如と漂流
- `docs/knowledge/mecha_rl_autodiag_silent_failure_20260908.md` — 自動化の沈黙故障
- `docs/knowledge/mecha_rl_autonomous_loop_root_cause_20260907.md` — 自律ループの真因
- `C:\Users\yasu\.claude\CLAUDE.md` — 運用ルール（0章・A章・B〜E章）
