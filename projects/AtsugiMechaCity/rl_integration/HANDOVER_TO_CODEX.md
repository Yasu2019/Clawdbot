# V50 メカ強化学習統合 — Codex引き継ぎドキュメント

作成日: 2026-06-30  
作成者: Claude Sonnet 4.6 (Claude Code)  
引き継ぎ先: Codex

---

## 1. プロジェクト背景と目標

**リポジトリ:** `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity`  
**ブランチ:** `feat/mecha-autorig`  

### 目的
Blenderで手作りしたV50メカ（sin波アニメーション）を、RL（強化学習）による物理的に正しい自然歩行に段階的にアップグレードする。

### 現在の状態（このセッション終了時点）
- **フェーズ1完了:** RL統合フォルダとアーティファクト生成スクリプト群を作成・動作確認済み
- **フェーズ2未着手:** DiffMimic / Genesis RL での実際のトレーニング

---

## 2. V50メカ現在のアーキテクチャ

### ソースファイル

| ファイル | 役割 |
|---------|------|
| `v50_armature_builder.py` | アーマチュア（骨格）生成。Chest→UpperArm→LowerArm→Hand階層 |
| `v50_final_walk_preview.py` | 歩行アニメーション生成。sin波数式ベース |
| `diagnostics/.../robot_walk_v50_armature_build.blend` | 最新のソースBlendファイル |

### アニメーション方式（sin波）
```python
# v50_final_walk_preview.py L177-182
swing_l = 7.0 * math.sin(cycle)      # 股関節 ±7°
knee_l  = 6.0 * max(0.0, -math.sin)  # 膝 最大6°（片方向のみ）
foot_l  = -3.0 * max(0.0, -math.sin) # 足首 最大-3°
# トルソ: Z bob=0.025m, Z sway=1.2°
```

### 脚関節ワールド座標（v50_final_walk_preview.py L164-171）
```python
pivots = {
    "hip_L":   Vector((-0.20, y, 0.02)),
    "knee_L":  Vector((-0.24, y, -0.50)),
    "ankle_L": Vector((-0.25, y, -0.88)),
    "hip_R":   Vector(( 0.22, y,  0.02)),
    "knee_R":  Vector(( 0.25, y, -0.50)),
    "ankle_R": Vector(( 0.26, y, -0.88)),
}
# y = torso_center.y ≈ -1.331 (Blender scene depth, collapse to 0 for RL)
```

### アームボーン構成
- 骨格: `Chest → UpperArm_L/R → LowerArm_L/R → Hand_L/R`
- 制約: UpperArm=ball(3DOF)、LowerArm/Hand=hinge(1DOF)
- `Hand_L` はメッシュなし（仮想ターミナル）
- 肩/肘/手首のワールド座標は `*_SHARED_CORE` オブジェクトから取得:

```
shoulder_L: (-0.518, 0, 0.541)   elbow_L: (-0.438, 0, 0.205)   wrist_L: (-0.460, 0, -0.165)
shoulder_R: ( 0.503, 0, 0.532)   elbow_R: ( 0.455, 0, 0.190)   wrist_R: ( 0.480, 0, -0.135)
```

### メカ寸法
- 高さ: **1.936m**、幅: **1.485m**（Blenderバウンドボックス実測）
- 想定質量: **280kg**（v50_amp_config.yaml デフォルト）

---

## 3. 調査済みリソース（Beadsに保存済み）

### モーションデータベース（優先順）

| データセット | ライセンス | 形式 | 特徴 | URL |
|------------|-----------|------|------|-----|
| **100STYLES** | CC BY 4.0 | BVH | 4M+フレーム、100歩行スタイル、**最優先** | https://zenodo.org/record/6778383 |
| **PHUMA** | Apache-2.0 | HuggingFace | 73h、物理検証済ヒューマノイドロコモーション | `caisar/phuma` |
| CMU MoCap | Public Domain | BVH | Subject35(歩行)、Subject09(走行) | mocap.cs.cmu.edu |
| AMASS | Academic | SMPL NPZ | 11451モーション、PHC/MDMの学習基盤 | amass.is.tue.mpg.de |
| Bandai Namco Research | CC BY-NC | BVH | 3000+クリップ、格闘+スタイライズ、アニメ品質 | GitHub |
| AIST++ | CC BY 4.0 | SMPL 60fps | 1408シーケンス、ダンス/動的ヒップモーション | aist.go.jp |

### RLフレームワーク（優先順）

| フレームワーク | ライセンス | 速度 | 特徴 |
|--------------|-----------|------|------|
| **DiffMimic** | Apache-2.0 | 10-20x RL比 | 既存Blenderキーフレーム→物理Valid、**最速始動** |
| **Genesis** | Apache-2.0 | 43M FPS(RTX4090) | rigid+FEM+MPM+fluid、`pip install genesis-world` |
| Isaac Lab + AMP/ASE | BSD-3 | 高速 | URDF/MJCF/USD、テキスト/キーフレーム入力対応 |
| PHC / PULSE | MIT | 標準 | AMASS 40h+学習済みチェックポイントあり |
| ProtoMotions + MaskedMimic | Apache-2.0 | 高速 | AMASS 5000+パターン対応 |

### モーション生成アルゴリズム（将来参照）

| アルゴリズム | ライセンス | 特徴 |
|------------|-----------|------|
| **MoMask** | MIT | CVPR2024 SOTA (FID=0.045)、テキスト→モーション |
| **CLoSD** | MIT | ICLR2025、閉ループ拡散+RL物理トラッカー |
| **SinMDM** | MIT | 非ヒューマノイドスケルトン対応、BVH1本→バリエーション |
| OmniControl | MIT | 空間的関節制約 |
| MoCapAnything | research | 動画+メカリグ→メカスケルトンBVH（安定版待ち） |

### ビデオMoCap（手軽な入口）

| ツール | 価格 | 特徴 |
|-------|------|------|
| DeepMotion Animate3D | 無料〜$50/月 | 最簡単、動画→BVH |
| WHAM | 無料 | CVPR2024、世界座標グラウンド付き |
| ROMP/TRACE | Apache-2.0 | BVH/FBX直接出力、Blenderアドオンあり |

---

## 4. 今回作成したRLフォルダ構成

```
projects/AtsugiMechaCity/rl_integration/
├── v50_urdf_exporter.py          # URDF生成（13リンク/12DOF）
├── v50_mjcf_builder.py           # MuJoCo MJCF生成
├── v50_reference_motion_exporter.py  # sin波→AMP JSON + BVH
├── v50_amp_config.yaml           # トレーニング設定
├── v50_pipeline_runner.py        # ワンコマンドで全アーティファクト生成
├── HANDOVER_TO_CODEX.md          # このファイル
└── artifacts/                    # 生成済みファイル（git管理済み）
    ├── v50_mecha.urdf             # Isaac Lab / ROS用
    ├── v50_mecha.xml              # MuJoCo用（.gitignore除外、再生成可）
    ├── v50_ref_motion.json        # AMP参照モーション（96フレーム）
    └── v50_ref_motion.bvh         # Cascadeur / Auto-Rig Pro用
```

### アーティファクト再生成コマンド（Blender不要）
```bash
cd projects/AtsugiMechaCity/rl_integration
python v50_pipeline_runner.py --out-dir ./artifacts --mass 280
```

---

## 5. 生成アーティファクトの仕様

### URDF (`artifacts/v50_mecha.urdf`)
- **13リンク:** torso + upper/lower/foot × 2脚 + upper/lower/hand × 2腕
- **12DOF:** hip/knee/ankle × 2 + shoulder/elbow/wrist × 2
- 全関節 revolute（回転軸 X: 前後方向）
- 質量配分: torso 40% / upper_leg 8%×2 / lower_leg 5%×2 / foot 2%×2 / upper_arm 4%×2 / lower_arm 2.5%×2 / hand 1%×2

### MJCF (`artifacts/v50_mecha.xml`)
- free joint (root) + 12 hinge joints
- カプセルgeom（床接触用foot sphereあり）
- PDアクチュエータ（gear比: hip=400, knee=300, ankle=200, shoulder=200, elbow=150, wrist=80）
- 24個センサー（jointpos + jointvel × 12）

### 参照モーション (`artifacts/v50_ref_motion.json`)
```json
{
  "schema": "clawstack.v50_reference_motion.amp.v1",
  "Loop": "wrap",
  "FrameDuration": 0.0417,
  "TotalFrames": 96,
  "DOFOrder": ["root_x","root_y","root_z","root_rx","root_ry","root_rz",
               "hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R",
               "shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R"],
  "Frames": [...]
}
```

---

## 6. Codexへの推奨タスク（優先順）

### タスク A: DiffMimic スモークテスト（最優先・最速）
```bash
# 前提: pip install mujoco (>=3.0)
python -c "
import mujoco
m = mujoco.MjModel.from_xml_file('artifacts/v50_mecha.xml')
d = mujoco.MjData(m)
print('nq:', m.nq, 'nv:', m.nv, 'nu:', m.nu)
mujoco.mj_step(m, d)
print('qpos:', d.qpos[:7])
print('OK: MuJoCo loads V50 MJCF cleanly')
"
# 問題がなければ DiffMimic でトレーニング:
# git clone https://github.com/diffmimic/diffmimic
# python diffmimic/train.py --mjcf artifacts/v50_mecha.xml \
#                           --ref_motion artifacts/v50_ref_motion.json
```

### タスク B: Genesis RL 環境ラッパー作成
```bash
pip install genesis-world
# genesis_v50_env.py を作成:
# - genesis.Genesis() で物理シミュレーター初期化
# - v50_mecha.xml をロード
# - v50_amp_config.yaml の reward定義を実装
# - 4096並列環境でPPOループ
```

**参照:** [Genesis RL チュートリアル](https://genesis-world.readthedocs.io)

### タスク C: 参照モーション品質アップ（スタイル改善）
```bash
# 100STYLES ダウンロード (CC BY 4.0, 無料)
# URL: https://zenodo.org/record/6778383
# → BVH を Auto-Rig Pro でV50スケルトンにリターゲット
# → v50_reference_motion_exporter.py の代わりにBVHリーダーを実装
# → v50_amp_config.yaml の reference_motion.path を更新

# または PHUMA (物理検証済):
# huggingface-cli download caisar/phuma
```

### タスク D: Isaac Lab 統合（最終目標・最高品質）
```bash
git clone https://github.com/isaac-sim/IsaacLab
# artifacts/v50_mecha.urdf を IsaacLab の robot assets に登録
# AmpHumanoidEnv をテンプレートとして V50Env を作成
# artifacts/v50_ref_motion.json を AMP discriminator に入力
```

---

## 7. 既知の制約・注意事項

| 項目 | 内容 |
|------|------|
| 脚軸方向 | 全関節 `axis="1 0 0"`（Blender X軸=前後）。MuJoCoで足滑りが出たら `axis="0 1 0"` に変更 |
| Hand_Lメッシュ | Blender側でメッシュなし（仮想ターミナル）。URDFのhand_Lは質量1%の球体で代替 |
| 参照モーション品質 | sin波ベースのため非物理的（足滑りあり）。DiffMimic/CLoSDは自動補正するが、100STYLESに差し替えると大幅改善 |
| MJCF除外 | `.gitignore` が `*.xml` を除外。`v50_pipeline_runner.py` で再生成すること |
| 座標系 | Blender Y深度（約-1.331）は全関節でY=0に正規化済み。Blender Z上=MuJoCo Z上（同一） |
| MuJoCo バージョン | `compiler angle="degree"` を使用。MuJoCo 3.x は `angle` 属性を無視（デフォルトrad）→ 要確認 |

---

## 8. 関連Beads Issue

```bash
bd show q00   # DiffMimic スモークテスト (P2, open)
```

---

## 9. 参照コミット

```
e996725d1  feat(mecha-autorig): add RL integration scaffold for V50 mecha
b41525240  docs: add ChatGPT handover report for bipedal mecha walk autorigging
```

---

## 10. 連絡事項

- このセッションで調査した全ノウハウは `bd memories` に保存済み（キーワード: `motion`, `RL`, `dataset`, `MoCap`）
- モデルルーティング: 重タスク（設計/実装）は `google/gemini-2.5-flash`、軽タスクは `local_fast`
- LiteLLM: `http://localhost:4001`（コンテナ内は `http://litellm:4000`）
