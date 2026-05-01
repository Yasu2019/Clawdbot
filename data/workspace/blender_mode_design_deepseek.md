# Blenderモード改善設計書 (DeepSeek生成)

IATFビデオファクトリーのBlenderモード改善設計について、具体的な実装設計書を以下に示します。

---

# IATFビデオファクトリー Blenderモード改善設計書

## 概要
IATF 16949内部監査教材の3D動画自動生成システム「IATFビデオファクトリー」のBlenderモードにおいて、映像品質とアニメーションのリアリティを向上させるための設計を行います。既存の`blender_animator.py`をベースに、品質ルール達成と既知の問題点修正を目指します。

## 1. POSE_ROTATIONSシリアライズバグ修正

### 問題点
`POSE_ROTATIONS`のJSONシリアライズにバグがあり、`pose_rotations_json`と`pose_dict`が混在している。

### 修正方針
`POSE_ROTATIONS`を一貫した辞書形式で定義し、JSONとして正しく扱えるように修正します。これにより、ポーズデータの読み書きが安定します。

### 修正後のコードスニペット

```python
import json
import bpy
import mathutils

# 既存のPOSE_ROTATIONSを辞書形式で定義し直す
# 各ボーンの回転はEuler(X, Y, Z)で表現
# 例: 'neutral': {'BoneName': [X_rot, Y_rot, Z_rot]}

# 仮のPOSE_ROTATIONS定義（実際の内容に合わせて調整してください）
# 角度はラジアンで指定
POSE_ROTATIONS = {
    "neutral": {
        "Spine": [0.0, 0.0, 0.0],
        "Neck": [0.0, 0.0, 0.0],
        "Head": [0.0, 0.0, 0.0],
        "LeftArm": [0.0, 0.0, 0.0],
        "RightArm": [0.0, 0.0, 0.0],
        # ... 他のボーン
    },
    "point": {
        "Spine": [0.0, 0.0, 0.0],
        "RightArm": [0.0, -0.5, 0.0], # 例: 右腕を前に出す
        # ...
    },
    "arms_crossed": {
        "Spine": [0.0, 0.0, 0.0],
        "LeftArm": [0.0, 0.0, -1.0],
        "RightArm": [0.0, 0.0, 1.0],
        # ...
    },
    "bow": {
        "Spine": [0.5, 0.0, 0.0], # 例: 体を前傾させる
        "Neck": [0.2, 0.0, 0.0],
        # ...
    },
    "explain": {
        "Spine": [0.0, 0.0, 0.0],
        "LeftArm": [0.0, -0.3, 0.0],
        "RightArm": [0.0, 0.3, 0.0],
        # ...
    },
    "nod": {
        "Neck": [0.2, 0.0, 0.0], # 例: 頷きポーズ
        # ...
    }
}

def save_pose_rotations_to_json(filepath, pose_data):
    """
    POSE_ROTATIONSデータをJSONファイルに保存する。
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(pose_data, f, indent=4)

def load_pose_rotations_from_json(filepath):
    """
    JSONファイルからPOSE_ROTATIONSデータを読み込む。
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# 使用例:
# save_pose_rotations_to_json("pose_rotations.json", POSE_ROTATIONS)
# loaded_poses = load_pose_rotations_from_json("pose_rotations.json")
# print(loaded_poses["neutral"]["Spine"])

# set_pose関数は、この辞書構造を前提に修正
def set_pose(armature_obj, pose_name, frame):
    """
    指定されたポーズをアーマチュアに設定し、キーフレームを挿入する。
    """
    if pose_name not in POSE_ROTATIONS:
        print(f"Warning: Pose '{pose_name}' not found.")
        return

    bpy.context.scene.frame_set(frame)
    pose_data = POSE_ROTATIONS[pose_name]

    for bone_name, rotations in pose_data.items():
        if bone_name in armature_obj.pose.bones:
            pose_bone = armature_obj.pose.bones[bone_name]
            pose_bone.rotation_mode = 'XYZ' # Euler XYZを前提
            pose_bone.rotation_euler = mathutils.Euler(rotations, 'XYZ')
            pose_bone.keyframe_insert(data_path="rotation_euler", index=-1)
        else:
            print(f"Warning: Bone '{bone_name}' not found in armature '{armature_obj.name}'.")

```

## 2. setup_render 改善コード

### 問題点
解像度が1280x720、EEVEEサンプルが8。

### 修正方針
品質ルールに従い、解像度を1920x1080 (Full HD)、EEVEEサンプルを32以上に変更し、モーションブラーを追加します。

### 改善コード

```python
import bpy

def setup_render(fps=30, total_frames=None):
    """
    レンダリング設定を改善する。
    - 解像度: 1920x1080 (Full HD)
    - EEVEEサンプル: 32
    - モーションブラー: 0.5
    - フレームレート: 30fps
    """
    scene = bpy.context.scene
    render = scene.render

    # レンダリングエンジンをEEVEEに設定
    render.engine = 'BLENDER_EEVEE'

    # 解像度設定
    render.resolution_x = 1920
    render.resolution_y = 1080
    render.resolution_percentage = 100 # 100%スケール

    # フレームレート設定
    scene.render.fps = fps
    scene.render.fps_base = 1.0

    # EEVEEサンプル設定
    scene.eevee.samples = 32 # 品質ルール: 32以上
    scene.eevee.taa_render_samples = 32 # TAAも同様に設定

    # モーションブラー設定
    render.use_motion_blur = True
    render.motion_blur_shutter = 0.5 # 0.5秒分のシャッター開度

    # 出力設定 (例: PNGシーケンス)
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_depth = '8'
    render.image_settings.compression = 15

    # 出力パス (必要に応じて設定)
    # render.filepath = "//output/" # 相対パス

    # シーンの終了フレーム設定
    if total_frames is not None:
        scene.frame_end = total_frames

    print("Render settings updated: 1920x1080, EEVEE Samples 32, Motion Blur 0.5")

```

## 3. カメラワーク自動化

### 問題点
カメラが固定1カメラ。

### 修正方針
7場面（オープニング/要求説明/現場監査/問題指摘/クローズ/改善/エンディング）ごとに複数のカメラを定義し、話者へのフォーカス切り替えロジックを実装します。シーンの進行に合わせてアクティブカメラを切り替え、Look Atコンストレイントで話者を追従させます。

### カメラ位置・角度定義
キャラクター配置を基準にカメラを定義します。
*   **bulma**: (0,0,0)
*   **goku**: (-1.5,0,0)
*   **gohan**: (1.5,0,0)

```python
import bpy
import mathutils
import math

# キャラクターの基準位置 (オブジェクト名とワールド座標)
CHARACTER_POSITIONS = {
    "bulma": mathutils.Vector((0, 0, 0)),
    "goku": mathutils.Vector((-1.5, 0, 0)),
    "gohan": mathutils.Vector((1.5, 0, 0)),
    # 必要に応じて他のキャラクターも追加
}

# カメラ設定の定義
# (位置, 回転_Euler_XYZ, 焦点距離, ターゲットキャラクター名)
CAMERA_PRESETS = {
    "opening_wide": {
        "location": (0, -7, 2.5), "rotation": (math.radians(75), 0, math.radians(0)),
        "focal_length": 35, "target": None
    },
    "bulma_medium": {
        "location": (0.5, -3, 1.5), "rotation": (math.radians(80), 0, math.radians(10)),
        "focal_length": 50, "target": "bulma"
    },
    "goku_medium": {
        "location": (-1.0, -3, 1.5), "rotation": (math.radians(80), 0, math.radians(-10)),
        "focal_length": 50, "target": "goku"
    },
    "gohan_medium": {
        "location": (1.0, -3, 1.5), "rotation": (math.radians(80), 0, math.radians(10)),
        "focal_length": 50, "target": "gohan"
    },
    "two_shot_center": {
        "location": (0, -4, 2.0), "rotation": (math.radians(80), 0, math.radians(0)),
        "focal_length": 35, "target": None # 複数人の中央を狙う
    },
    "close_up_bulma": {
        "location": (0.2, -1.5, 1.6), "rotation": (math.radians(85), 0, math.radians(5)),
        "focal_length": 85, "target": "bulma"
    },
    "close_up_goku": {
        "location": (-1.3, -1.5, 1.6), "rotation": (math.radians(85), 0, math.radians(-5)),
        "focal_length": 85, "target": "goku"
    },
    "ending_wide": {
        "location": (0, -7, 2.5), "rotation": (math.radians(75), 0, math.radians(0)),
        "focal_length": 35, "target": None
    },
}

def create_camera(name, location, rotation, focal_length):
    """新しいカメラを作成し、シーンに追加する"""
    bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=location, rotation=rotation)
    camera_obj = bpy.context.object
    camera_obj.name = name
    camera_obj.data.lens = focal_length
    return camera_obj

def setup_camera_rigs():
    """定義されたカメラプリセットに基づいてカメラオブジェクトを作成する"""
    cameras = {}
    for cam_name, props in CAMERA_PRESETS.items():
        cam_obj = create_camera(cam_name, props["location"], props["rotation"], props["focal_length"])
        cameras[cam_name] = cam_obj

        # ターゲットが指定されている場合、Look Atコンストレイントを設定
        if props["target"] and props["target"] in CHARACTER_POSITIONS:
            target_char_name = props["target"]
            # ターゲットオブジェクトとして、キャラクターのHeadボーン（またはArmatureオブジェクト自体）を使う
            # ここでは簡単のため、キャラクターのArmatureオブジェクトをターゲットとする
            # 実際の運用では、キャラクターのHeadボーンにEmptyを追従させ、それをターゲットにするのがより正確
            target_obj = bpy.data.objects.get(f"Armature_{target_char_name}") # 例: Armature_bulma
            if target_obj:
                track_constraint = cam_obj.constraints.new(type='TRACK_TO')
                track_constraint.target = target_obj
                track_constraint.track_axis = 'TRACK_NEGATIVE_Z' # カメラの向き
                track_constraint.up_axis = 'UP_Y' # カメラの上方向
            else:
                print(f"Warning: Target object 'Armature_{target_char_name}' not found for camera '{cam_name}'.")
        
        # カメラのDepth of Field設定 (オプション)
        cam_obj.data.dof.use_dof = True
        cam_obj.data.dof.focus_distance = 3.0 # 初期値
        cam_obj.data.dof.aperture_fstop = 2.8 # 浅い被写界深度

    return cameras

def animate_camera_shots(cameras, shot_timeline, fps):
    """
    ショットタイムラインに基づいてカメラを

---

## 4. ボディモーション改善コード

キャラクターに自然な動きを与えるためのボディモーション改善策を提案します。既存のアニメーションに加算する形で実装し、よりリアルな表現を目指します。

### 4.1. 呼吸モーション (Spine/Spine1)

**目的:** キャラクターに生命感を与えるため、胸部の微細な上下運動（呼吸）を追加します。
**変更点:** 現在のY軸±0.015radを±0.003radに修正し、より自然な振幅にします。
**対象ボーン:** `Spine`, `Spine1`
**軸:** Y軸 (ローカルY軸が左右方向を向いている場合、胸郭の膨らみに合わせてZ軸回転、またはY軸位置移動の方が自然な場合もありますが、指示に従いY軸回転で実装します。一般的にはZ軸回転かY軸位置移動が呼吸表現には適しています。)
**振幅:** ±0.003 rad
**周期:** 3〜4秒

```python
import bpy
import math

def apply_breathing_motion(armature_name="Armature", start_frame=0, end_frame=250, amplitude=0.003, period=3.5):
    """
    指定されたアーマチュアのSpine/Spine1ボーンに呼吸モーションを適用します。
    既存のFカーブに加算される形でキーフレームを挿入します。
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature or armature.type != 'ARMATURE':
        print(f"Error: Armature '{armature_name}' not found or not an armature.")
        return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    bones_to_affect = ['Spine', 'Spine1']
    fps = bpy.context.scene.render.fps
    
    for bone_name in bones_to_affect:
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            print(f"Warning: Bone '{bone_name}' not found in armature '{armature_name}'.")
            continue

        # Y軸回転 (rotation_euler[1]) に呼吸モーションを追加
        # 既存のFカーブに影響を与えないように、新しいFカーブトラックを作成するか、
        # 既存のFカーブにオフセットとして追加する方法が考えられます。
        # ここでは、既存のFカーブに加算する形でキーフレームを挿入します。
        # Fカーブモディファイア (Noise) を使う方が非破壊的で調整しやすいですが、
        # Pythonで直接キーフレームを打つ場合は、既存の値を読み取って加算します。

        # より非破壊的な方法として、NLAトラックにアクションを追加するか、
        # Fカーブモディファイア (Noise) をPythonで設定する方が望ましいです。
        # ここでは直接キーフレームを打つ例を示しますが、運用時はFカーブモディファイアを推奨します。

        # Fカーブモディファイア (Noise) を使用する推奨実装
        # まず、Y軸にキーフレームがなければダミーのキーフレームを打つ
        pose_bone.keyframe_insert(data_path="rotation_euler", index=1, frame=start_frame)
        
        fcurve = armature.animation_data.action.fcurves.find(f'pose.bones["{bone_name}"].rotation_euler', index=1)
        if fcurve:
            # Noiseモディファイアを追加
            mod = fcurve.modifiers.new(type='NOISE')
            mod.strength = amplitude # 振幅
            mod.scale = fps * period / (2 * math.pi) # 周期 (スケールが大きいほどゆっくり)
            mod.offset = 0.0 # オフセット
            mod.use_additive = True # 加算モード
            print(f"Applied Noise modifier to {bone_name}.rotation_euler[1] for breathing.")
        else:
            print(f"Warning: F-curve for {bone_name}.rotation_euler[1] not found. Cannot apply Noise modifier.")
            # Fカーブがない場合は、手動でキーフレームを打つ代替案
            # for frame in range(start_frame, end_frame + 1):
            #     time_in_seconds = frame / fps
            #     # 既存の回転値を取得し、呼吸モーションを加算
            #     current_rot_y = pose_bone.rotation_euler[1]
            #     breathing_offset = amplitude * math.sin(time_in_seconds * (2 * math.pi / period))
            #     pose_bone.rotation_euler[1] = current_rot_y + breathing_offset
            #     pose_bone.keyframe_insert(data_path="rotation_euler", index=1, frame=frame)
            # print(f"Applied breathing motion to {bone_name}.rotation_euler[1] via keyframes.")

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Breathing motion applied.")

# 実行例:
# apply_breathing_motion(armature_name="Armature", start_frame=0, end_frame=250, amplitude=0.003, period=3.5)
```

### 4.2. 頷きモーション (Neck)

**目的:** 発話タイミングに合わせて、キャラクターが頷く動作を追加します。
**対象ボーン:** `Neck`
**軸:** X軸 (前傾)
**振幅:** 0.05〜0.1 rad (発話の重要度に応じて調整)
**タイミング:** `timeline`データの発話開始・終了タイミングから算出。

**`timeline`データ例 (JSON形式を想定):**
```json
[
    {"frame_start": 10, "frame_end": 30, "text": "こんにちは。", "emphasis": 0.1},
    {"frame_start": 60, "frame_end": 90, "text": "重要な発表です。", "emphasis": 0.8},
    {"frame_start": 120, "frame_end": 140, "text": "はい、承知しました。", "emphasis": 0.3}
]
```

```python
import bpy
import json
import math

def apply_nodding_motion(armature_name="Armature", timeline_path="timeline.json", base_amplitude=0.05, max_amplitude_factor=2.0):
    """
    指定されたアーマチュアのNeckボーンに頷きモーションを適用します。
    timelineデータの発話タイミングと強調度に応じてX軸回転を挿入します。
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature or armature.type != 'ARMATURE':
        print(f"Error: Armature '{armature_name}' not found or not an armature.")
        return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    pose_bone = armature.pose.bones.get('Neck')
    if not pose_bone:
        print(f"Warning: Bone 'Neck' not found in armature '{armature_name}'.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    try:
        with open(timeline_path, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Timeline file '{timeline_path}' not found.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{timeline_path}'.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    for entry in timeline_data:
        frame_start = entry['frame_start']
        frame_end = entry['frame_end']
        emphasis = entry.get('emphasis', 0.5) # 強調度 (0.0 - 1.0)

        # 強調度に応じて振幅を調整 (例: 0.5 -> base_amplitude, 1.0 -> base_amplitude * max_amplitude_factor)
        amplitude = base_amplitude + (base_amplitude * (max_amplitude_factor - 1.0) * emphasis)
        amplitude = min(amplitude, base_amplitude * max_amplitude_factor) # 上限設定

        # 頷き動作: 発話開始から少しずつ前傾し、ピークに達した後、発話終了までに元の位置に戻る
        # 例: 発話開始から1/4でピーク、発話終了の1/4手前で元の位置
        nod_peak_frame = frame_start + (frame_end - frame_start) / 4
        nod_return_frame = frame_end - (frame_end - frame_start) / 4

        # キーフレーム挿入
        # 1. 発話開始前 (現在の位置)
        pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=frame_start - 5) # 少し前から準備
        # 2. 頷きピーク (前傾)
        pose_bone.rotation_euler[0] = amplitude # X軸回転
        pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=nod_peak_frame)
        # 3. 頷き維持 (少し戻すか、そのまま維持)
        # pose_bone.rotation_euler[0] = amplitude * 0.8 # 少し戻す場合
        # pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=nod_peak_frame + (nod_return_frame - nod_peak_frame) / 2)
        # 4. 元の位置に戻る
        pose_bone.rotation_euler[0] = 0.0
        pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=nod_return_frame)
        # 5. 発話終了後 (元の位置を維持)
        pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=frame_end + 5)

        # 補間タイプを調整 (Ease-in/out)
        fcurve = armature.animation_data.action.fcurves.find(f'pose.bones["Neck"].rotation_euler', index=0)
        if fcurve:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER' # 滑らかな補間
                kp.handle_left_type = 'AUTO'
                kp.handle_right_type = 'AUTO'

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Nodding motion applied.")

# 実行例:
# apply_nodding_motion(armature_name="Armature", timeline_path="path/to/your/timeline.json", base_amplitude=0.05, max_amplitude_factor=2.0)
```

### 4.3. 重心移動 (Hips)

**目的:** キャラクターが静止している際にも、微細な重心移動を加えることで、より生き生きとした印象を与えます。
**対象ボーン:** `Hips`
**軸:** Y軸 (左右への傾き)
**振幅:** ±0.01 rad
**周期:** 4秒

```python
import bpy
import math

def apply_hips_sway_motion(armature_name="Armature", start_frame=0, end_frame=250, amplitude=0.01, period=4.0):
    """
    指定されたアーマチュアのHipsボーンに重心移動（左右への揺れ）モーションを適用します。
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature or armature.type != 'ARMATURE':
        print(f"Error: Armature '{armature_name}' not found or not an armature.")
        return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    pose_bone = armature.pose.bones.get('Hips')
    if not pose_bone:
        print(f"Warning: Bone 'Hips' not found in armature '{armature_name}'.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    fps = bpy.context.scene.render.fps

    # 呼吸モーションと同様に、Fカーブモディファイア (Noise) を使用することを推奨
    pose_bone.keyframe_insert(data_path="rotation_euler", index=1, frame=start_frame) # Y軸回転
    
    fcurve = armature.animation_data.action.fcurves.find(f'pose.bones["Hips"].rotation_euler', index=1)
    if fcurve:
        mod = fcurve.modifiers.new(type='NOISE')
        mod.strength = amplitude
        mod.scale = fps * period / (2 * math.pi)
        mod.offset = 0.0
        mod.use_additive = True
        print(f"Applied Noise modifier to Hips.rotation_euler[1] for sway motion.")
    else:
        print(f"Warning: F-curve for Hips.rotation_euler[1] not found. Cannot apply Noise modifier.")

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Hips sway motion applied.")

# 実行例:
# apply_hips_sway_motion(armature_name="Armature", start_frame=0, end_frame=250, amplitude=0.01, period=4.0)
```

### 4.4. 発話強調モーション (Spine2)

**目的:** 重要発言時に、キャラクターがわずかに前傾することで、発言の重要性を強調します。
**対象ボーン:** `Spine2`
**軸:** X軸 (前傾)
**振幅:** +0.05 rad
**タイミング:** `timeline`データの発話タイミングと強調度から算出。

```python
import bpy
import json
import math

def apply_emphasis_motion(armature_name="Armature", timeline_path="timeline.json", emphasis_threshold=0.7, tilt_amount=0.05):
    """
    指定されたアーマチュアのSpine2ボーンに発話強調モーションを適用します。
    timelineデータのemphasisが閾値を超えた場合に前傾させます。
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature or armature.type != 'ARMATURE':
        print(f"Error: Armature '{armature_name}' not found or not an armature.")
        return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    pose_bone = armature.pose.bones.get('Spine2')
    if not pose_bone:
        print(f"Warning: Bone 'Spine2' not found in armature '{armature_name}'.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    try:
        with open(timeline_path, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Timeline file '{timeline_path}' not found.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{timeline_path}'.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    for entry in timeline_data:
        frame_start = entry['frame_start']
        frame_end = entry['frame_end']
        emphasis = entry.get('emphasis', 0.0)

        if emphasis >= emphasis_threshold:
            # 前傾動作: 発話開始から徐々に前傾し、発話終了までに元の位置に戻る
            tilt_in_frame = frame_start + 5 # 5フレームかけて前傾
            tilt_out_frame = frame_end - 5 # 5フレームかけて戻る

            # キーフレーム挿入
            # 1. 発話開始前 (現在の位置)
            pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=frame_start - 5)
            # 2. 前傾ピーク
            pose_bone.rotation_euler[0] = tilt_amount
            pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=tilt_in_frame)
            # 3. 前傾維持
            pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=tilt_out_frame)
            # 4. 元の位置に戻る
            pose_bone.rotation_euler[0] = 0.0
            pose_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=frame_end + 5)

            # 補間タイプを調整
            fcurve = armature.animation_data.action.fcurves.find(f'pose.bones["Spine2"].rotation_euler', index=0)
            if fcurve:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.handle_left_type = 'AUTO'
                    kp.handle_right_type = 'AUTO'

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Emphasis motion applied.")

# 実行例:
# apply_emphasis_motion(armature_name="Armature", timeline_path="path/to/your/timeline.json", emphasis_threshold=0.7, tilt_amount=0.05)
```

---

## 5. 足接地 Floor Constraint コード

キャラクターの足が地面にめり込んだり浮いたりするのを防ぐため、`Floor

---

IATFビデオファクトリーBlenderモード設計書

## 6. 字幕焼き込み方法

ビデオファクトリーの文脈において、字幕の焼き込み方法は、実用性、保守性、処理速度の観点から慎重に選択する必要があります。Blender TextオブジェクトとFFmpegの2つの主要なアプローチを比較検討し、推奨方法とそのコード例を提示します。

### 6.1. Blender Textオブジェクト vs FFmpeg 比較

| 項目         | Blender Textオブジェクト                               | FFmpeg                                                               |
| :----------- | :----------------------------------------------------- | :------------------------------------------------------------------- |
| **実用性**   | - Blender内で完結し、WYSIWYGで配置・スタイル設定が可能。<br>- 3D空間での配置やアニメーションが容易。<br>- テキスト量が多いとBlenderファイルが重くなる可能性。 | - Blenderレンダリングとは独立した

---

IATFビデオファクトリーBlenderモード設計書（続き）

## 6. 字幕焼き込み方法

Blenderで動画に字幕を焼き込む方法として、Blenderのテキストオブジェクトを利用する方法と、レンダリング後に外部ツールFFmpegを利用する方法が考えられます。それぞれの実用性、保守性、処理速度を比較し、推奨方法とそのコード例を示します。

### 比較表

| 項目       | Blenderテキストオブジェクト                               | FFmpeg (レンダリング後合成)                               |
| :--------- | :-------------------------------------------------------- | :-------------------------------------------------------- |
| **実用性** | - Blender内で直接編集・配置・アニメーションが可能。<br>- フォント、色、サイズ、影、3D配置など、高度なスタイリングが容易。<br>- 複雑なアニメーションや3D空間での配置が必要な場合に有利。 | - レンダリング後に外部ツールで合成。<br>- ASS/SRTなど標準的な字幕フォーマットを利用可能。<br>- 大量の字幕や外部データ連携に適している。<br>- Blenderのレンダリング負荷を軽減。 |
| **保守性** | - Blenderファイル内に情報が完結するため、管理しやすい。<br>- 字幕の変更にはBlenderファイルを開き、再レンダリングが必要。<br>- 大量の字幕や頻繁な変更には不向き。 | - 字幕ファイル（例: .ass, .srt）と動画ファイルが分離されるため、字幕の変更が容易。<br>- Blenderファイルを再レンダリングする必要がない。<br>- 外部スクリプトやデータベースとの連携が容易。 |
| **処理速度** | - レンダリング時にBlenderがテキストを画像として生成するため、レンダリング時間が若干増加する可能性がある。<br>- 特に複雑なテキストや多数のテキストオブジェクトがある場合、影響が大きい。 | - Blenderのレンダリングとは独立して行われるため、Blenderのレンダリング時間には影響しない。<br>- FFmpegによる字幕合成は非常に高速で、数秒から数十秒で完了する。 |
| **用途**   | - 表現豊かな字幕、3D空間に配置された字幕、アニメーションするロゴなど。 | - 大量生産される定型的な字幕、多言語対応、字幕の頻繁な更新、レンダリング負荷軽減。 |

### 推奨方法

IATFビデオファクトリーのような「ファクトリー」という文脈では、**FFmpegによるレンダリング後合成**を推奨します。

**理由:**
1.  **レンダリング負荷の軽減:** Blenderのレンダリング時間を短縮し、全体の処理時間を最適化できます。
2.  **高い保守性:** 字幕内容の変更や多言語対応の際に、Blenderファイルを再レンダリングすることなく、字幕ファイルのみを更新して高速に合成し直すことが可能です。
3.  **自動化との親和性:** 外部の字幕データ（例: データベースからの抽出、翻訳サービスからの出力）を標準的な字幕フォーマットに変換し、FFmpegで自動的に合成するワークフローを構築しやすいです。

ただし、もし字幕自体に複雑な3DアニメーションやBlenderのシーンとの密接な連携が必要な場合は、Blenderテキストオブジェクトの利用も検討します。本設計書では、一般的な字幕焼き込みを想定し、FFmpegを推奨します。

### 推奨方法のコード例 (FFmpegによる字幕合成)

この例では、Blenderで動画がレンダリングされた後、Pythonの`subprocess`モジュールを使ってFFmpegコマンドを実行し、字幕ファイル（`.ass`形式を想定）を動画に焼き込みます。

```python
import bpy
import subprocess
import os

def burn_subtitles_with_ffmpeg(
    input_video_path: str,
    subtitle_file_path: str,
    output_video_path: str,
    ffmpeg_path: str = "ffmpeg" # 環境変数にffmpegが設定されていれば"ffmpeg"でOK
):
    """
    FFmpegを使用して動画に字幕を焼き込む関数。

    Args:
        input_video_path (str): 入力動画ファイルのパス。
        subtitle_file_path (str): 字幕ファイル（.assまたは.srt）のパス。
        output_video_path (str): 出力動画ファイルのパス。
        ffmpeg_path (str): FFmpeg実行ファイルのパス。
    """
    if not os.path.exists(input_video_path):
        print(f"エラー: 入力動画ファイルが見つかりません: {input_video_path}")
        return
    if not os.path.exists(subtitle_file_path):
        print(f"エラー: 字幕ファイルが見つかりません: {subtitle_file_path}")
        return

    # FFmpegコマンドの構築
    # -i: 入力ファイル
    # -vf: ビデオフィルタ (subtitlesフィルタで字幕を焼き込む)
    # -c:v: ビデオコーデック (元のコーデックをコピー)
    # -c:a: オーディオコーデック (元のコーデックをコピー)
    # -y: 既存の出力ファイルを上書き
    command = [
        ffmpeg_path,
        "-i", input_video_path,
        "-vf", f"subtitles='{subtitle_file_path}'", # Windowsではパスのエスケープに注意
        "-c:v", "copy", # ビデオコーデックはコピー
        "-c:a", "copy", # オーディオコーデックはコピー
        "-y", # 既存の出力ファイルを上書き
        output_video_path
    ]

    print(f"FFmpegコマンドを実行中: {' '.join(command)}")
    try:
        # subprocess.runでコマンドを実行
        # check=True: エラーが発生した場合にCalledProcessErrorを発生させる
        # capture_output=True: 標準出力と標準エラー出力をキャプチャ
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("FFmpeg実行成功:")
        print(result.stdout)
        if result.stderr:
            print("FFmpeg標準エラー出力:")
            print(result.stderr)
        print(f"字幕焼き込み済み動画が保存されました: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg実行中にエラーが発生しました: {e}")
        print(f"標準出力: {e.stdout}")
        print(f"標準エラー出力: {e.stderr}")
    except FileNotFoundError:
        print(f"エラー: FFmpegが見つかりません。パスを確認してください: {ffmpeg_path}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

# --- Blenderレンダリング後の処理に組み込む例 ---
def render_and_burn_subtitles(
    output_dir: str,
    base_filename: str,
    subtitle_filename: str,
    final_output_filename: str
):
    """
    Blenderでレンダリングし、その後FFmpegで字幕を焼き込む一連の処理。
    """
    scene = bpy.context.scene

    # レンダリング設定
    render_output_path_no_sub = os.path.join(output_dir, f"{base_filename}.mp4")
    scene.render.filepath = render_output_path_no_sub
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM' # 品質設定
    scene.render.ffmpeg.gopsize = 18 # キーフレーム間隔
    scene.render.ffmpeg.audio_codec = 'AAC'

    print(f"Blenderレンダリング開始: {render_output_path_no_sub}")
    bpy.ops.render.render(animation=True)
    print("Blenderレンダリング完了。")

    # 字幕ファイルのパス
    subtitle_file_path = os.path.join(output_dir, subtitle_filename) # 例: "subtitles.ass"
    # 最終的な出力動画ファイルのパス
    final_output_video_path = os.path.join(output_dir, final_output_filename) # 例: "final_video_with_sub.mp4"

    # FFmpegで字幕を焼き込む
    burn_subtitles_with_ffmpeg(
        input_video_path=render_output_path_no_sub,
        subtitle_file_path=subtitle_file_path,
        output_video_path=final_output_video_path,
        ffmpeg_path="ffmpeg" # 必要に応じてFFmpegのフルパスを指定
    )

    # 元の字幕なし動画を削除するかどうかは要件による
    # os.remove(render_output_path_no_sub)

# --- 実行例 ---
if __name__ == "__main__":
    # このスクリプトはBlenderのPythonコンソールまたはスクリプトエディタで実行することを想定
    # Blender外でテストする場合は、bpy.context.sceneなどのBlender固有のオブジェクトは利用できません。

    # ダミーのファイルパス（実際の運用では動的に生成または取得）
    output_directory = "/tmp/iatf_renders" # 出力ディレクトリ
    os.makedirs(output_directory, exist_ok=True)

    # ダミーの字幕ファイルを作成 (テスト用)
    dummy_subtitle_path = os.path.join(output_directory, "test_subtitle.ass")
    with open(dummy_subtitle_path, "w", encoding="utf-8") as f:
        f.write("""
[Script Info]
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,これはテスト字幕です。
Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,IATFビデオファクトリーへようこそ！
""")
    print(f"ダミー字幕ファイルを作成しました: {dummy_subtitle_path}")

    # Blenderレンダリングと字幕焼き込みを実行
    # render_and_burn_subtitles(
    #     output_dir=output_directory,
    #     base_filename="rendered_video_no_sub",
    #     subtitle_filename="test_subtitle.ass",
    #     final_output_filename="final_video_with_sub.mp4"
    # )

    # 注意: 上記の render_and_burn_subtitles はBlender環境で実行する必要があります。
    # このスクリプトを単体で実行する場合、Blenderのシーンやレンダリングは行われません。
    # 既にレンダリング済みの動画ファイルがある場合のテスト例:
    # burn_subtitles_with_ffmpeg(
    #     input_video_path=os.path.join(output_directory, "rendered_video_no_sub.mp4"),
    #     subtitle_file_path=dummy_subtitle_path,
    #     output_video_path=os.path.join(output_directory, "final_video_with_sub_standalone.mp4")
    # )
```

## 7. フェードイン/アウト（シーン切り替え）

Blender PythonでCompositorノードを使用して、レンダリング結果にフェードイン/アウト効果を実装します。これにより、シーンの開始時や終了時に滑らかな切り替えを実現できます。

### 実装方針

1.  **Compositorの有効化:** シーンのノードベースコンポジティングを有効にします。
2.  **ノードのセットアップ:**
    *   `Render Layers`ノード: レンダリング結果の画像を取得します。
    *   `Color`ノード: フェードアウト/インの際に使用する色

---

```python
# 8. QAスクリプト統合コード

import bpy
import subprocess
import os
from datetime import datetime

def run_qa_script_post_render(scene):
    """
    レンダリング完了後にQAスクリプトを呼び出し、結果をJSONで保存するハンドラ。
    """
    qa_script_path = os.path.join(os.path.dirname(__file__), "cinema_motion_qa.py")
    
    if not os.path.exists(qa_script_path):
        print(f"Error: QA script not found at {qa_script_path}")
        return

    # 出力ディレクトリとファイル名の設定
    output_dir = os.path.join(bpy.path.abspath("//"), "qa_results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_json_path = os.path.join(output_dir, f"qa_report_{timestamp}.json")

    try:
        # subprocessでQAスクリプトを実行
        # BlenderのPython環境とは異なる独立したPythonで実行することを想定
        # 例: sys.executable を使用してBlenderのPythonで実行するか、
        # 外部のPythonインタプリタを指定する
        python_executable = "python" # または os.sys.executable
        
        result = subprocess.run(
            [python_executable, qa_script_path, "--output", output_json_path],
            capture_output=True,
            text=True,
            check=True # エラー時にCalledProcessErrorを発生させる
        )
        print(f"QA Script Output:\n{result.stdout}")
        if result.stderr:
            print(f"QA Script Error Output:\n{result.stderr}")
        print(f"QA script executed successfully. Report saved to: {output_json_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error running QA script: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print(f"Error: Python executable '{python_executable}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# レンダリング完了後のハンドラとして登録
# bpy.app.handlers.render_post.append(run_qa_script_post_render)

# 注意: このコードはBlenderのテキストエディタで実行するか、アドオンとしてロードする必要があります。
# ハンドラを登録解除する場合は以下を使用:
# bpy.app.handlers.render_post.remove(run_qa_script_post_render)
```

## 9. 優先度と実装順序（最重要）

| # | セクション | 優先度 | 工数目安 | 効果 | 前提条件 |
|---|-----------|--------|---------|------|---------|
| 1 | 概要 | 高 | 0.5人日 | 全体像の共有、認識合わせ | なし |
| 2 | モード切り替えとUI | 高 | 2人日 | ユーザー操作の基盤、モードの可視化 | 1. 概要 |
| 3 | オペレーター定義 | 中 | 3人日 | 主要機能の実装、コアロジック | 2. モード切り替えとUI |
| 4 | プロパティとデータ構造 | 中 | 2人日 | データ管理の基盤、拡張性 | 3. オペレーター定義 |
| 5 | 描画とビューポート表示 | 中 | 4人日 | 視覚的なフィードバック、ユーザー体験向上 | 4. プロパティとデータ構造 |
| 6 | イベントハンドリング | 中 | 3人日 | ユーザーインタラクション、応答性 | 5. 描画とビューポート表示 |
| 7 | データ永続化とファイルI/O | 低 | 2人日 | 作業内容の保存・復元、信頼性 | 4. プロパティとデータ構造 |
| 8 | QAスクリプト統合コード | 低 | 1人日 | 品質保証の自動化、開発効率向上 | 3. オペレーター定義 (QA対象機能の実装) |