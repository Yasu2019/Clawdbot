# Mecha階段昇段・Corridorマルチ地形 — セッション引き継ぎ (2026-07-27)

前提の必読: `data/workspace/memory/trouble_history.md` [T077][T078][T079] /
`C:\Users\yasu\.claude\projects\D--Clawdbot-Docker-20260125\memory\feedback_mecha_visual_inspection.md`(グローバルルール、07-27強化版) /
beads: `Clawdbot_Docker_20260125-o2iv`(階段昇段フォローアップissue)

## このセッションで確定した事実

1. **Phase2マルチ地形単一方策(corridor)は完了・成功**。9セグメント共有corridor
   (平地→昇段0.10m→平地→下り斜面8°→平地→上り斜面8°→平地→降段0.10m→平地)を実装し、
   単一方策で**平地(survival 0.98-1.0)・降段(0.33-0.62)・上り斜面(0.63-0.69)・下り斜面(0.75-0.81)**
   の4地形を実用survivalで達成。VERIFIED ckpt:
   `C:\v50_work\autonomy\known_good\walk_rsl_corridor_v2_20260727_4of5terrain_VERIFIED.pt`

2. **T078: corridor学習が「ためらい局所解」に陥っていた根本原因を特定・修正済み**。
   per-segment naturalness報酬マスク(平地区間だけnaturalness報酬を有効化する仕組み)が、
   「naturalness報酬は常時0」を前提に学習された既存warm-startチェックポイントと矛盾し、
   平地→階段の境界で方策が11秒以上完全静止する現象を誘発していた。
   **グローバル`--no-naturalness`(全区間常時無効)に戻すことで解消**。
   実装した`_naturalness_mask()`機構自体はコードに残置(将来のfine-tuning段階用)。

3. **【最重要・訂正】T079: 階段昇段(stairs_up)は、このプロジェクトのどのチェックポイントでも
   一度も本当に達成されたことがなかった**。
   - ユーザーがTelegramで階段昇段動画を見て「歩行ではなく足踏みに近い」と指摘 → 発端。
   - warm-start元として"ascent-capable"(survival 0.667-0.79)と扱っていた
     `C:\v50_work\autonomy\walk_rsl_stairs_h10_robust\latest.pt` を初めて目視したところ、
     階段の最初の段の縁で1.5秒以上完全に同一位置に留まり足踏みしただけで転倒。
   - `verify_policy.py`の`height_gained_m`を確認すると **0.03-0.06m(1段=0.10mにも未達)**。
     比較: 降段は-0.68〜-0.86m(ほぼ全10段)、上り斜面は0.30-0.38m(全斜面の7-9割)= 本物。
   - **根本原因**: `survival_rate`だけを見て`height_gained_m`を確認していなかった
     (グローバルルール違反の再発、T069とほぼ同一パターン)。降段・上り斜面は毎回目視していたが、
     昇段だけ「既にverified済み」を理由に目視を省略していた。

## 実施済み変更(このセッション)

| ファイル | 変更内容 |
|---|---|
| `projects/AtsugiMechaCity/rl_integration/stage_a/train_v50_walk_tracking.py` | `CORRIDOR_SEGMENTS`/`CORRIDOR_VARIANTS`/`_corridor_layout()`/`_corridor_dz()`追加。`terrain_xml`/`terrain_dz`にcorridor分岐(`"corridor"`と簡易版`"corridor_stairs_up"`両対応) |
| `projects/AtsugiMechaCity/rl_integration/stage_a/v50_walk_env.py` | corridor spawn(`_sample_corridor_spawn`, `corridor_spawn_max_segment`診断オプション付き)、`_naturalness_mask()`、**新規`_r_climb_progress`報酬項**(高さ進捗を直接報酬化、`reward_scales["climb_progress"]=1500.0`≒dt正規化後30.0)、`self.best_height`状態追加 |
| `projects/AtsugiMechaCity/rl_integration/stage_a/train_v50_walk_rsl.py` | `--terrain corridor/corridor_stairs_up`追加、`--corridor-fixed-start`、`--corridor-spawn-max-segment` |
| `projects/AtsugiMechaCity/rl_integration/stage_a/verify_policy.py` / `render_walk_rsl.py` | 上記corridor系フラグのpassthrough |
| `data/workspace/memory/trouble_history.md` | T077(降段検証)・T078(ためらい局所解)・T079(足踏み誤判定訂正)を記録 |

全てgit commit・push済み(`main`ブランチではなく`backup/openradioss-spm80-pre-rerun-20260725`ブランチ)。
コミット: `322382c672`(corridor実装)・`275b8eca5b`(beads)・`1083445e7d`(T079訂正)。

## `_r_climb_progress`報酬項の設計(T079対応・新規追加)

```python
def _r_climb_progress(self):
    dz = V50.terrain_dz(self.pos[:, V50.FWD_AXIS], self.cfg["terrain"], self.stair_h)
    gain = (dz - self.best_height).clamp(min=0.0)
    self.best_height = torch.maximum(self.best_height, dz)
    return gain
```
- `survival_rate`だけでなく`height_gained_m`を直接報酬化。既存の`feet_air_time`/`single_foot_contact`は
  「指令速度>0.1」のみでゲートされ実際の変位と無関係なため、その場足踏みでも稼げてしまう
  (T079の根本原因)。この項は実際に高さが増えた分だけ発火するため、足踏みでは永遠に0。
- 平地では`terrain_dz`が一定なので自動的に無害(既存の平地/降段/斜面学習への影響なし、サニティテスト済み)。
- **スケール1500.0は暫定値**(dt正規化により実効30.0、全報酬項は`* self.dt`される規約のため)。
  1.0mの完全昇段でエピソード全体を通じて合計報酬≒30となるよう逆算した見積もり。要チューニング。

### Web調査で得た知見(実装前に反映済み)
- 階段昇段特有の「立ち止まり」対策として"height-based gating"(高さ進捗のみ報酬化)・
  "minimum velocity threshold"が文献で有効と報告。
- モーションキャプチャ由来の階段専用参照歩容("prior knowledge")の導入で学習速度40-60%向上の報告あり
  → 本プロジェクトには平地用の`--ref-json`参照歩容機構(`gait_reference()`)が既にあるが、
    **階段専用の参照はまだ一度も作られていない**(将来の拡張候補)。
- Sources: PMC9432737(階段昇段関節位相)/ arXiv:2105.08328(sim-to-real階段踏破)/
  Effects of Prior Knowledge for Stair Climbing(ICARM 2024)

## 追記(同日深夜、PC再起動後の続き)

`climb_progress`単体(scale 1500)では2回の再学習(異なるwarm-start)を試しても
「階段の縁で完全静止」局所解を脱せなかった。**T079b: 明示的な停滞ペナルティ
`climb_stagnation`を追加**(stall_steps*dt、stairs/slope_up限定でゲート、scale -8.0)、
`climb_progress`もscale 1500→3000へ引き上げ。

結果: 「完全静止」局所解は解消(目視確認済み)。方策は**階段の縁で前足を段の上に乗せ
体全体で段差へ飛び込むように挑戦する**明確に異なる行動を獲得。ただし急ぎすぎて
(vx実測0.77-0.88m/s、指令0.25m/sを大幅超過)t=1.2-1.3s前後で転倒する新パターンに収束。
1000→1500→2500(累計)→5000iterまで延長したが、量的微増(final_travel 1.43→1.65m)の
みで質的ブレークスルー(生存・完全昇段)には至らず。**プラトー状態**と判断しこのセッションでは
一旦保留。

チェックポイント: `C:\v50_work\autonomy\walk_rsl_stairs_climbrew_v2\latest.pt`(5000iter、未VERIFIED)
コマンド系列: `walk_rsl_stairs_climbrew_fresh`(750iter、resume-surgery元)→
`walk_rsl_stairs_climbrew_v2`(climb_stagnation追加後、1000→2500→5000iter)

**次回セッション優先候補**(beads `o2iv`に詳細記載):
1. 明示的な速度上限ペナルティ(急行動0.8m/s級を抑制する具体的拘束) — 未着手・最優先
2. `climb_progress`/`climb_stagnation`スケールの再チューニング(現状が強すぎ/弱すぎのどちらかを再検証)
3. 階段専用参照歩容(mocapベース、既存`--ref-json`機構経由) — 文献上最も効果的だが実装コスト大
4. reverse curriculum(段の途中スポーンで探索の壁を迂回)
5. さらなる長期学習は収穫逓減の兆候ありのため優先度低

**追記(同日深夜、ユーザーからの「バランス制御はできているか」という質問を受けて)**:
実測診断の結果、片脚支持中に胴体が支持脚の上へ意図的に移動する挙動(重心シフト)が
できておらず、単調な横ドリフトになっていることが判明。これを受けて人間工学・生体力学の
文献調査を実施し、**`docs/mecha_biomechanics_reward_design_rules.md`** にルール化した
(LIPM誘導CoM追従報酬・歩行周期比率目標・Reward Fusion的ゲーティング等)。
全チェックポイントで`double_support_frac`が人間基準(≈0.20)の3-4倍(0.54-0.92)という
定量的な裏付けもあり。次回セッションは上記1-5番の前に、まずこのルールドキュメントの
ルール1(CoM追従報酬の実装)を検討することを推奨。

## 現在進行中の状態(2026-07-27夜、このセッション終了時点)

**学習実行中**: `climb_progress`報酬を使った昇段再学習。
- warm-start元を`walk_rsl_stairs_h10_robust`(足踏み習慣が染みついた既存stairsチェックポイント)から
  **`known_good/walk_rsl_natural_gait_ADOPTED.pt`(平地専用・階段を見たことがない)への`--resume-surgery`**
  に切り替え済み(足踏み局所解を「学習し直す」のではなく「最初から作らせない」狙い)。
- コマンド:
  ```
  cd projects/AtsugiMechaCity/rl_integration/stage_a
  C:/v50_work/genesis_venv/Scripts/python.exe train_v50_walk_rsl.py ^
    --terrain stairs --height-scan --stair-height 0.10 --no-naturalness ^
    --n-envs 2048 ^
    --resume "C:/v50_work/autonomy/known_good/walk_rsl_natural_gait_ADOPTED.pt" --resume-surgery ^
    --iterations 750 ^
    --out "C:/v50_work/autonomy/walk_rsl_stairs_climbrew_fresh"
  ```
- 出力先: `C:\v50_work\autonomy\walk_rsl_stairs_climbrew_fresh\`
  (ログ: `train_stdout2.log`。最初の2回の起動試行はcwd誤り+システムメモリ逼迫(WinError 1455、
  commit charge 82.9/91.5GB=91%)で失敗、3回目にn_envsを3072→2048へ落として成功)
- セッション終了時点: it100/750、return 1.94、正常進行中(クラッシュなし)。

**同じ`climb_progress`報酬で`stairs_h10_robust`からwarm-startした先行実験**
(`C:\v50_work\autonomy\walk_rsl_corridor_stairs_up_climbrew\`, 500iter完了済み)は、
目視でまだ足踏みパターンが残存(既存の悪癖が強すぎて500iterでは脱却できず)と判定済み
——このため上記の「平地専用checkpointからのresume-surgery」に方針転換した。

## 次セッションのTODO(優先順)

1. **`walk_rsl_stairs_climbrew_fresh`の完了確認**(it750到達、`DONE`/`EVAL:`ログ確認)。
2. **`verify_policy.py --terrain stairs`でフレッシュ再ロード検証** — `survival_rate`と
   **`height_gained_m`を必ずセットで確認**(T079の教訓。survival=0.0の場合height_gainedは
   nullで報告されない仕様のため、その場合は目視必須)。
3. **`render_walk_rsl.py`で必ず目視確認** — 階段に対するロボットの相対位置がフレームごとに
   本当に変化しているか(背景基準)を確認。静止していないか、実際に登っているかを判定。
4. 改善が見られない場合の次の一手候補:
   - `climb_progress`のスケール(1500.0)を増減して再実験
   - イテレーション数を増やす(750→1500など)
   - 明示的な「停滞ペナルティ」(高さ増加がN秒無い場合にペナルティ)を追加
   - 階段専用の参照歩容(mocapベース)を新規作成し`--ref-json`的に導入
5. `Clawdbot_Docker_20260125-o2iv`(beads)を最新状況で更新、成功したら`known_good/`へ保存し
   `trouble_history.md`にT080として結果を記録。
6. GPUメモリ/システムメモリの逼迫が頻発している(このセッションだけでVRAM系クラッシュ4回、
   システムcommit逼迫1回)。長時間セッション後は`nvidia-smi`と
   `Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit'`(PowerShell)を学習前に確認する習慣を推奨。

## 制約・注意事項

- **Bashツールのcwdはコマンドごとにリセットされることがある**(このセッションで複数回、
  `cd ... &&`を省略して意図しないディレクトリで実行し失敗した)。genesis_venv実行時は
  必ず`cd /d/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/rl_integration/stage_a && ...`
  を明示すること。
- corridor学習・階段学習とも、他のDockerコンテナ(comfyui/rv6-img2img/ai_image_gen/gemma4-eval等)
  とGPU/システムメモリを共有しており、n_envs=4096でクラッシュする場合は3072→2048と段階的に下げる。
- `walk_rsl_corridor_v2`(4/5地形達成版)と`walk_rsl_stairs_h10_robust`(実は足踏み)を混同しないこと。
  後者はwarm-start元として今後使わない(足踏み習慣を持ち込むため)。
