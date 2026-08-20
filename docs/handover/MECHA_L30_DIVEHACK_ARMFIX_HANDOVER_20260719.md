# Mecha Motion Lab — dive_hack対策 + 腕関節分離修正 引き継ぎ (2026-07-19)

作業者: Claude Fable 5 (Cowork session) / ユーザー承認: 2026-07-19「この2点、着手ください。完全版になるまで自走して改善ください」

## 背景(必読の文脈)

- walk_cycle01 (C:\v50_work\autonomy\walk_cycle01) が **dive_hack** でエスカレーション
  (metrics: vx=0.082, travel=1.513, fell=true, min_upright=0.0。
  理由: "travel is fall-and-crawl; reward gating may be insufficient")
- 7/1配信候補動画は関節ゲートが正しく **HOLD_JOINT_DETACHMENT** 判定
  (腕系6関節全FAIL・脚系6関節PASS)。ゲートは健全。壊れているのは腕のリグ側。
- ゲート実測: 全腕関節でマーカーと胴体/腕メッシュの距離が常時1.1〜1.4m
  → **アーマチュアがメッシュ本体から大きく変位しており、腕メッシュは何にも
  駆動されていない「置物」だった**(INC-134/T033/T035系譜の根本原因)。
- 関連: T067(GPU lost→再起動で回復済みの模様。cycle01は学習完走している)、
  T066(モックml_supervisor廃止済み。実チェーン=motion_learning_supervisor)。

## 変更ファイル(全て変更前.bakあり)

### 1. rl_integration/stage_a/train_v50_walk_tracking.py (.bak_divehack_20260719)
dive_hack対策(報酬ゲート強化):
- `gate = upright ** 2` → `gate = ((upright - 0.85) / 0.15).clamp(0,1) ** 2`
  (前傾ダイブ中 upright~0.7 でも~0.5残っていた部分報酬をゼロ化。
   速度/前進報酬は upright>0.85 からのみ立ち上がる)
- 転倒カット `upright < 0.65` → `0.75`(ダイブ軌道の早期打切り)
- 転倒ペナルティ `-5` → `-10`(初速ダイブの割引報酬合計を確実に負へ)
- 他は不変更(ネットワーク/PPO/環境/質量再配分)

### 2. rl_integration/autonomy/playbook.yaml (.bak_20260719) — v4
- `dive_hack`: escalate → **フレッシュ自動再学習**
  `{type: retrain, resume: best_walker(=空=フレッシュ), entropy: 0.002, init_log_std: -0.9, iterations: 2000}`
  (P025-R1「意味ゲート停止時の自動改善」2026-07-18ユーザー指示に整合。
   ダイブ方策のcheckpoint継承は有害なのでフレッシュ)
- 安全弁不変更: max_cycles 6 / 2連続無改善エスカレーション

### 3. v50_final_walk_preview.py (.bak_armfix_20260719) — 腕のメッシュ駆動化
- 腕クラスタ定義を追加(v50_joint_attachment_gate.py と同一名。**対で保守**)
- `snap_arm_chains()`: 腕チェーン全体を胴体外側面へXスナップ(ギャップ閉鎖、
  内側方向のみ移動、SHOULDER_OVERLAP=0.03)
- `arm_pivots()`: 肩/肘/手首ピボットをメッシュ境界から算出(脚のleg_pivot_y同思想)
- animate(): 腕を剛体FK駆動(t_torso合成→肩回転→肘回転。脚と同パターン)。
  ゲート用マーカー(V50_RIG_MARKER_*)もFK計算点に毎フレーム配置
- 肩ソケットはbone headでなくメッシュ由来肩ピボットに生成
- アーマチュアは任意化(欠損してもレンダー可能。ポーズは互換のため残置)
- 調整ノブ: `ELBOW_SIGN = -1.0`(初回レンダーで肘の曲がりが逆なら+1.0へ反転)

## 実施済み検証(サンドボックス内・オフライン)

1. py_compile: trainer / supervisor / preview 全てOK
2. playbook v4: yamlパーサ・内蔵miniパーサ両方で
   dive metrics → `dive_hack {retrain, fresh, entropy 0.002, ils -0.9, iters 2000}` を確認、
   learned判定・順序回帰なし
3. プレビュー幾何: bpy/mathutilsスタブ注入テスト(T053方式)で
   - Xスナップがギャップ(0.2/0.25m)を正確に閉鎖
   - ピボットがクラスタ境界上に算出される
   - 12フレームFKで関節ギャップ成長 = 5.6e-17(ゲート許容0.068に対し厳密ゼロ)
   - rest距離もゲート許容(0.232)内

## 未実施(Windows側でしか出来ない) — 次のアクション

1. **学習再開**(GPU必須。T067の後に再起動済みであること):
   ```powershell
   cd D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\autonomy
   Start-Process -WindowStyle Hidden C:\v50_work\genesis_venv\Scripts\python.exe `
     -ArgumentList "motion_learning_supervisor.py","--skill","walk","--iterations","1500" `
     -RedirectStandardOutput "D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\real_supervisor_stdout.log" `
     -RedirectStandardError  "D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\real_supervisor_stderr.log"
   ```
   playbook v4により dive_hack 再発時も自動でフレッシュ再学習(最大6サイクル)。
2. **プレビュー修正の実機検証**: 次回プロモーション時に
   v50_joint_attachment_gate が自動判定(fail-closed: 不合格ならTelegram自動ブロック)。
   手動で先行確認する場合は overnight ループ or:
   `blender --background <v50 blend> --python v50_final_walk_preview.py -- --blend <blend> --out-dir <dir>`
   → 出力の v50_joint_attachment_gate_report.json で腕6関節PASSを確認。
   肘が逆曲がりなら ELBOW_SIGN を +1.0 に。
3. **bd起票**(サンドボックスにbd CLIなし・未実施):
   - 「playbook v4 dive_hack自動再学習の効果測定」
   - 「preview腕FKの実機ゲート検証」
   - 「v50_joint_attachment_gate.py とpreviewの腕クラスタ定義の単一ソース化」

## ロールバック手順

```powershell
cd D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity
copy rl_integration\stage_a\train_v50_walk_tracking.py.bak_divehack_20260719 rl_integration\stage_a\train_v50_walk_tracking.py
copy rl_integration\autonomy\playbook.yaml.bak_20260719 rl_integration\autonomy\playbook.yaml
copy v50_final_walk_preview.py.bak_armfix_20260719 v50_final_walk_preview.py
```

## FMEA(要点)

| 故障モード | 影響 | 検出 | 対策 |
|---|---|---|---|
| ハードゲートが厳しすぎ学習停滞 | travel低迷 | supervisor no_improve 2回 | 自動エスカレーション(安全弁) |
| 転倒カット0.75が歩行初期の揺れを誤検知 | エピソード短縮 | falls急増をログで確認 | 0.70へ緩和(1行) |
| 肘の回転方向が逆 | 見た目不自然(分離はしない) | 初回レンダー目視 | ELBOW_SIGN反転 |
| スナップ量過大で腕が胴体へ食込み | 見た目 | レンダー目視 | SHOULDER_OVERLAP縮小 |
| クラスタ名がblendと不一致 | 腕が動かない(旧状態のまま) | ゲートFAIL維持=配信ブロック | gateと同名定義済み・要実機確認 |
