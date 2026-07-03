# カノニカル骨格仕様 (Canonical Mecha Skeleton) v1.0-draft

作成日: 2026-07-03 | bd: `Clawdbot_Docker_20260125-6li` | 状態: **draft — ユーザー承認で凍結**
根拠: `docs/troubleshooting/fable5_mecha_multirobot_scaleup_decision_20260703.md` §1(DOFギャップ) + ユーザー要求「後からスキルを自由に追加(介助/工場作業/MOST/サーブリッグ/格闘技/スポーツ)」

## 0. 設計原理（これを壊す変更は全学習資産を無効化する）

1. **全機体が同一のDOFレイアウト(順序・数)を共有**する。機体差は「DOFロックマスク」(その機体で固定されるDOFの表)で表現する。
   - 理由: GPU並列(バッチ)学習は構造の同一性が前提。ロック方式なら30機体(形状違い)が**同一の観測・行動空間**で混在バッチ学習できる。V50のような矢状面リグも「多数のDOFがロックされた機体」として自然に収容。
2. **Tier制**: スキル難度に応じてDOF群を段階的に解放。上位Tierは下位Tierの上位互換(順序は不変、ロック解除のみ)。
3. **DOF順序は本仕様で固定**。方策・AMP discriminator・参照モーションJSONは全てこの順序に従う。追加は**末尾のみ**許可(挿入禁止)。

## 1. DOFレイアウト定義（順序固定・全29アクチュエートDOF + root）

root: free joint 6DOF (tx ty tz rx ry rz) — 非アクチュエート

| idx | DOF名 | 軸 | Tier | 主用途 |
|---|---|---|---|---|
| 0 | waist_yaw | Z | 1 | ドア開け・格闘の体幹回旋 |
| 1 | hip_L_pitch | X | 1 | 歩行スイング |
| 2 | hip_L_roll | Y | 1 | 横安定・横移動 |
| 3 | hip_L_yaw | Z | 2 | 方向転換・蹴り |
| 4 | knee_L_pitch | X | 1 | 歩行 |
| 5 | ankle_L_pitch | X | 1 | 接地 |
| 6 | ankle_L_roll | Y | 2 | 不整地・横安定 |
| 7-12 | (右脚、同構成) | | | hip_R_pitch/roll/yaw, knee_R_pitch, ankle_R_pitch/roll |
| 13 | shoulder_L_pitch | X | 1 | 腕振り |
| 14 | shoulder_L_roll | Y | 1 | **ドア開け必須**(外転) |
| 15 | shoulder_L_yaw | Z | 1 | **ドア開け必須**(内外旋) |
| 16 | elbow_L_pitch | X | 1 | 腕振り・リーチ |
| 17 | wrist_L_pitch | X | 2 | 作業(MOST/サーブリッグ) |
| 18 | wrist_L_roll | Y | 2 | 作業 |
| 19 | wrist_L_yaw | Z | 2 | 作業 |
| 20 | gripper_L | 抽象1DOF(0=開,1=閉) | 2 | **つかむ(Therblig: Grasp)の抽象化** |
| 21-28 | (右腕、同構成) | | | shoulder_R_p/r/y, elbow_R_p, wrist_R_p/r/y, gripper_R |

- **Tier 1 (移動系)** = 上記のTier1行のみ解放(waist+脚8+肩肘8=17DOF)。walk/run/stand/sit/door-open(肩3DOFで到達可能)。
- **Tier 2 (上肢作業系)** = +hip_yaw/ankle_roll/手首9×2/グリッパー。工場作業・MOST・サーブリッグ・介助の大半。**手指はグリッパー1DOFに抽象化**(把持対象は「グリッパー接触点への固定コンストレイント」で代替 — DOF爆発回避)。
- **Tier 3 (手指・顔) = 予約のみ**。idx 29以降に将来追加(末尾追加ルールに適合)。格闘技・スポーツの高度な手技はTier3までの間、Tier2グリッパー近似で学習する。

## 2. DOFロックマスク

機体マニフェスト(`mecha_rig_manifest.schema.yaml`)に `dof_locks: [dof名のリスト]` を必須フィールドとして持つ。

- ロックされたDOFは: シミュレータでは関節固定(または高剛性PDで0固定)、方策の行動出力は無視、観測には「ロックフラグベクトル」として供給。
- **V50の例**: 現リグは矢状面1DOF構成のため、`hip_*_roll/yaw, ankle_*_roll, shoulder_*_roll/yaw(※), wrist_*, gripper_*, waist_yaw` をロック。※肩3DOF化改修(MJCFエクスポータのball joint化)が完了したら肩ロックを解除。
- 形態ベクトル(§3)+ロックマスクで、方策は「この機体で何ができるか」を知る。

## 3. 方策への機体条件付け（形態ベクトル）

観測に以下を連結（30機体混在バッチの前提）:

```
morphology_vector = [height, total_mass, per-link長さ(正規化), per-link質量比, dof_lock_mask(29bit)]
```

## 4. スキル条件付け（one-hot禁止 — 開放語彙対応）

- 方策: `π(a | s, z_skill, morphology)`、AMP discriminator: `D(s, s' | z_skill)`
- `z_skill` ∈ R^64: **学習可能なスキル埋め込みテーブル**(スキル登録簿の行ごとに1ベクトル)。新スキル追加は「テーブルに行追加+短期ファインチューン」で済み、**方策アーキテクチャの作り直し不要**。
- 将来拡張: z_skillをモーションエンコーダ(参照クリップ→埋め込み)またはテキストエンコーダ出力に置換可能な次元(64)で予約。
- 正直な制約: 新スキル追加時にファインチューンは必要(ゼロショットではない)。回避不能なコストとして明記。

## 5. 命名・座標規約

- 関節名: `<部位>_<L|R>_<pitch|roll|yaw>`(本表の通り)。pitch=X軸(前後スイング)、roll=Y軸、yaw=Z軸。Z上向き・Y奥行き(Blender/MJCF共通、INC-140検証済み)。
- 参照モーションJSON: `DOFOrder`は本表のidx順。旧V50形式(12DOF)からの変換は「該当DOFへ射影+残りは0」。

## 6. V50への影響(移行タスク)

1. MJCFエクスポータ(`v50_mjcf_builder.py`)を本レイアウト+ロックマスク出力に改修
2. 肩をball joint(3DOF)化 → ロック解除
3. 参照モーション(`v50_ref_motion.json`)を29DOF形式に変換
4. Genesisスモークを29DOF版で再実行(既存スモークはキュー④で12DOF版PASS済み)

## 7. 凍結手続き

- [ ] ユーザーレビュー(特に: グリッパー抽象化の許容、Tier2のDOF選定、64次元埋め込み)
- [ ] 凍結後は `v1.0` に昇格し、変更は「末尾追加」のみ。本ファイルに改訂履歴を追記。
