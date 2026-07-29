# メカ歩行・階段昇降 報酬設計ルール（人間工学・生体力学データ基準）

> 作成: 2026-07-27（T079b調査の続き）。目的: 偶然の成功待ちをやめ、実測された人間の生体力学データ
> から逆算した具体的な報酬項・目標数値を先に定義し、次回以降の学習改善はこのルールと照合してから
> 着手する。歩行・階段昇降含む「あらゆる動作」に適用する共通ルールとして扱う。
>
> 参照先: `projects/AtsugiMechaCity/rl_integration/stage_a/v50_walk_env.py`（reward_scales / `_r_*`）

## このセッションで発見した根本的なギャップ

以下の実測値（本セッション中の`render_walk_rsl.py` WALK_CHECK出力）は、いずれも人間の
歩行周期の基準値から大きく外れている。**「急ぎすぎて転倒」問題の根本原因はここにある可能性が高い**。

| チェックポイント | double_support_frac | single_support_frac |
|---|---|---|
| **人間の基準値**(文献) | **≈0.20** | **≈0.80** |
| corridor_v2(平地、4/5地形達成版) | 0.758〜0.797 | 0.198〜0.31 |
| stairs_climbrew_fresh(750iter) | 0.917 | 0.059 |
| stairs_climbrew_v2(1000〜5000iter) | 0.542〜0.61 | 0.31〜0.418 |

**解釈**: 全チェックポイントが両足接地(double support)に偏りすぎている(人間の3〜4倍)。
これは「片脚支持中に重心を支持脚の上へ移動させる」制御ができていないため、方策が
片脚支持を避け両足接地に留まろうとしている結果と考えられる（実測データによる裏付け:
下記ルール1参照。股関節・足首rollは動いているが胴体の左右位置が振動せず単調にドリフト
=支持脚上への重心移動になっていない）。

## ルール1: 片脚支持中は重心を支持脚の直上へ移動させる（最優先）

**人間のデータ**: 単脚支持期には骨盤・体幹が支持脚側へ移動し、身体重心(CoM)を支持足の
直上に位置させることでバランスを取る。CoMは各単脚支持期に支持足の外側境界へ向けて
移動する傾向があり、これを能動的に制御しないと内外側方向の不安定化が起きる
(股関節での制御、または遊脚での接地位置調整の両方が使われる)。

**現状の実装との差分**: `_r_orientation`(reward_scales: -5.0)は重力ベクトルのx,y成分を
一律にペナルティ化しており、「支持脚の上へ意図的に重心を寄せる」ことと「バランスを崩して
傾く」ことを区別できていない。これが片脚支持中の適切な重心移動を妨げている可能性がある。

**推奨実装**: LIPM(倒立振子モデル)ベースの目標重心を計算し、それに対する追従誤差を
報酬化する(単純な垂直姿勢への固定ではなく)。
```
p̂_com = p_zmp + (z/g) * k_p * (v_cmd - v)   # LIPM由来の目標重心オフセット
r_com_track = exp(-‖p̂_com - p_com‖ - |z_target - z| - (|ω_roll| + |ω_pitch|))
```
`p_zmp`は支持脚の接地点(単脚支持なら現在の支持足位置、両脚支持なら両足の中間)。
既存の`_r_orientation`を置き換えるか、並存させて重み調整する。

## ルール2: 歩行周期の時間配分は定量目標に合わせる

**人間のデータ**: 立脚期(stance)60% / 遊脚期(swing)40%。両脚接地(double support)は
歩行周期全体の約20%(各stance開始・終了時に10%ずつ)。片脚支持は残り約80%。
**歩行速度が遅いほどdouble support比率は増える**(今回の全チェックポイントの歩行速度が
指令値より遅い/不安定であることと整合する)。

**推奨実装**: `double_support_frac`が0.20に近づくよう明示的に誘導する報酬項を追加する
(現状は`single_foot_contact`(scale 1.0)が単脚接地を評価しているが、目標比率との
乖離を直接ペナルティ化する項がない)。例:
```python
def _r_double_support_ratio(self):
    # ウィンドウ平均のdouble_support実測値を人間の目標比率(0.20)に近づける
    return -((self.double_support_ema - 0.20).clamp(min=0.0)) ** 2
```

## ルール3: 速度追従は安定性が確保されて初めて評価する（Reward Fusion）

**文献**: LIPM誘導RL(arXiv:2509.09106)は `r_t = r_stable + r_stable * r_linloco` という
乗算的統合を採用し、安定性報酬(r_stable)が低いときは速度追従報酬(r_linloco)の影響を
自動的に抑制する。これにより「速く進むために不安定になる」戦略を構造的に防ぐ。

**現状の実装との差分**: 現在の`_compute_reward()`は全報酬項を単純加算しており、
速度・進捗系の報酬(`forward_progress`, `climb_progress`)と安定性系の報酬(`orientation`,
`base_height`)が独立に効いている。**今回観測された「急ぎすぎて転倒」(vx実測0.77-0.88m/s、
指令0.25m/sを3倍超過)は、まさにこの文献が警告する失敗モードそのもの**。

**推奨実装**: `climb_progress`・`forward_progress`を安定性項(upright/base_height誤差の
関数)で乗算的にゲートする。安定性が低い間は速度・登坂報酬の実効値を減衰させる。

## ルール4: 腕振りは脚の角運動量を打ち消す方向に逆位相で動く

**人間のデータ**: 脚の振り出しで生じる角運動量を、腕を反対方向へ振ることで打ち消す
(骨盤帯と肩甲帯は互いに逆回転する体幹の counter-rotation を伴う)。単なる装飾的な
動きではなく、角運動量保存によるバランス機能を持つ。

**現状の実装との差分**: `pose_prior`が参照歩容(sin波)への追従を評価しており、
参照歩容自体に腕の逆位相スイングは含まれている可能性が高いが、**実際の角運動量が
打ち消されているかを直接評価する報酬項は無い**。階段昇段のような不安定な場面でこそ
腕によるバランス機能が重要になるため、優先度は中。

## ルール5: 努力最小化（エネルギー・関節負荷）は既存実装とおおむね整合

**人間のデータ**: 実験的な歩行データでは遊脚期の筋活動はほぼ休止し、立脚期でも
同時多筋収縮(co-contraction)は低い。関節角度は生体力学的な可動域制限を超えない。
垂直地面反力(GRF)は体重の1.2倍を超えない範囲に収まる。

**現状の実装との整合**: `action_rate`(-0.01)・`dof_vel`(-1e-4)・`dof_acc`(-2.5e-7)・
`action_jerk`(-0.008)が努力最小化・滑らかさに相当し、既存実装は文献の方向性と一致している。
**追加候補**: 地面反力(GRF)が体重の1.2倍を超えた場合の明示的ペナルティ(Genesisが
接触力を取得できるか要確認、未実装)。優先度は低(現状の失敗モードとは無関係)。

## 適用対象の範囲

このルールは階段昇段に限らず、**平地歩行・降段・斜面昇降を含む全ての移動動作**の
報酬設計に適用する。特にルール1・2・3は現在4/5地形達成済みのcorridor_v2でも
double_support_fracが人間基準の3.8倍(0.758 vs 0.20)であり、階段昇段固有の問題ではなく
**プロジェクト全体の歩行報酬設計に共通する改善余地**と判断する。

## 次のアクション（優先順）

1. ルール1(CoM追従報酬)を`v50_walk_env.py`に実装し、`orientation`と比較検証
2. ルール3(Reward Fusion的なゲーティング)を`climb_progress`/`forward_progress`に適用
3. ルール2(double_support比率報酬)を追加
4. 上記を組み込んだ状態で階段昇段を再学習し、目視+`double_support_frac`実測値の
   両方で0.20への接近を確認
5. ルール4・5は階段昇段が解決した後の仕上げ段階で検討

## Sources
- [Control of human gait stability through foot placement (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6030625/)
- [Center of mass and base of support interaction during gait](https://smithengineering.queensu.ca/mme/faculty/deluzio/jam/files/04.08.2011_Renata.pdf)
- [LIPM-Guided Reinforcement Learning for Stable and Perceptive Locomotion in Bipedal Robots (arXiv:2509.09106)](https://arxiv.org/html/2509.09106)
- [Bipedal robot center of pressure feedback simulation for center of mass learning](https://www.researchgate.net/publication/381077733_Bipedal_robot_center_of_pressure_feedback_simulation_for_center_of_mass_learning)
- [The Gait Cycle - Physiopedia](https://www.physio-pedia.com/The_Gait_Cycle)
- [Relationships between trunk rotation and arm swing in human walking (PubMed)](https://pubmed.ncbi.nlm.nih.gov/8336064/)
- [Control and function of arm swing in human walking and running](https://www.researchgate.net/publication/23963817_Control_and_function_of_arm_swing_in_human_walking_and_running)
- [Emergence of natural and robust bipedal walking by learning from biologically plausible objectives (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12002607/)
- [Deep Reinforcement Learning for Bipedal Locomotion: A Brief Survey (arXiv:2404.17070)](https://arxiv.org/html/2404.17070v1)
