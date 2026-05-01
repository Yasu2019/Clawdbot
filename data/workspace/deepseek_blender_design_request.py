"""
DeepSeek V4 Pro への Blenderモード設計依頼
LiteLLM経由で送信し、設計書をMarkdownで保存する
"""
import requests, json, os, sys
from pathlib import Path

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")
OUTPUT_PATH = Path("d:/Clawdbot_Docker_20260125/data/workspace/blender_mode_design_deepseek.md")

PROMPT = """
# 依頼: IATFビデオファクトリー Blenderモード改善設計

## 背景
IATF 16949内部監査教材の3D動画を自動生成するシステム（IATFビデオファクトリー）において、
Blenderモード（3Dキャラクターアニメーション）の品質向上設計を依頼します。

## 現在実装済みの blender_animator.py の内容

```python
# 実装済み機能:
# - add_jaw_bone(armature_obj)      : 顎ボーン追加（リップシンク用）
# - add_eyelid_bones(armature_obj)  : 瞼ボーン追加（瞬き用）
# - animate_breathing(arm, fps, total_frames) : 呼吸（Spine Y軸 sin波 ±0.015rad）
# - animate_blink(arm, fps, total_frames)     : ランダム瞬き（3〜6秒間隔）
# - animate_lipsync(arm, phoneme_timeline, fps): Rhubarbフォネームから顎回転
# - set_pose(arm, pose_data, frame)           : ポーズ設定+キーフレーム挿入
# - setup_render: EEVEE, 1280x720, 8サンプル, 30fps
# - POSE_ROTATIONS: neutral/point/arms_crossed/bow/explain/nod
# - キャラクター配置: bulma(0,0,0), goku(-1.5,0,0), gohan(1.5,0,0) etc.
```

## 品質ルール（必須達成）

```
1. 解像度: 1920x1080 (Full HD) 必須
2. EEVEEサンプル: 32以上
3. カメラワーク: 固定1カメラ禁止 → 場面ごとにアングル変化（正面/斜め45°/クローズアップ）
4. トランジション: シーン切り替えにフェードイン/アウト（0.5秒）
5. 字幕: 全セリフに白字+黒縁テロップ（音声同期）
6. 呼吸周期: Spine/Spine1ボーン Y軸±0.003, 周期3〜4秒
7. 頷き: Neckボーン X軸 発話区切りで0.05〜0.1rad
8. 重心移動: Hipsボーン 会話中に微細な左右揺れ
9. 発話強調: Spine2ボーン 重要発言時に前傾+0.05rad
10. 足: Mixamoモデルの足が地面を滑らないよう固定
```

## motion_lab パイプライン（参考）

```yaml
stages:
  - retarget: hips_aligned, feet_aligned, hands_not_twisted
  - physics_refine: center_of_mass, foot_contact_stable (Cascadeur preferred)
  - secondary_motion: cloth/hair/jiggle_bones
  - cinematic_render: camera_framing, lighting, motion_blur, depth_of_field
  - ai_quality_review: foot_sliding, jitter, unnatural_timing, clipping
```

## 既知の問題点（修正必須）

1. POSE_ROTATIONSのJSONシリアライズにバグあり（pose_rotations_jsonとpose_dictが混在）
2. 解像度が1280x720（1920x1080に変更必要）
3. EEVEEサンプルが8（32以上に変更必要）
4. カメラが固定1カメラ（場面ごとにカメラ切り替え必要）
5. 字幕なし（FFmpegで焼き込み or Blenderテキストオブジェクト）
6. ボディモーションの数値が不正確（呼吸±0.015rad→±0.003rad、頷き未実装）
7. 足接地固定なし（IKコンストレイント未設定）

## 依頼内容

以下の設計書をMarkdown形式で作成してください：

### 1. POSE_ROTATIONSシリアライズバグ修正
- 修正後の正しいコードスニペット

### 2. setup_render 改善コード
- 1920x1080, 32サンプル, motion_blur 0.5

### 3. カメラワーク自動化
- 7場面（オープニング/要求説明/現場監査/問題指摘/クローズ/改善/エンディング）ごとのカメラ位置・角度定義
- キャラクター話者へのカメラフォーカス切り替えロジック（Blender Python）

### 4. ボディモーション改善コード
- 呼吸: ±0.003rad, 3〜4秒周期（現在±0.015rad→修正）
- 頷き: Neckボーン X軸 0.05〜0.1rad（発話タイミングから算出）
- 重心移動: Hipsボーン 左右±0.01rad 4秒周期
- 発話強調: Spine2ボーン 前傾+0.05rad

### 5. 足接地IKコンストレイント
- Mixamorig:LeftFoot / RightFoot を地面(Z=0)にFloor Constraintで固定するBlender Pythonコード

### 6. 字幕焼き込み方法
- Blender TextオブジェクトでOR FFmpegのどちらが良いか判断と実装方針

### 7. フェードイン/アウト トランジション
- Blender Pythonでシーン切り替え時にフェードを実装する方法

### 8. cinema_motion_qa.py 統合方法
- レンダリング後にcinema_motion_qa.pyを自動実行してボーンジャンプを検出する統合コード

### 9. 優先度と実装順序
- 上記1〜8の優先度（高/中/低）と推奨実装順序

出力は日本語のMarkdown形式で、コードスニペットを含む具体的な設計書にしてください。
"""

def call_deepseek(prompt: str, model: str = "google/gemini-2.5-flash") -> str:
    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "あなたはBlender Python + 3Dアニメーション専門のシニアエンジニアです。具体的なコードスニペットを含む実装設計書を日本語で出力してください。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 6000,
        "temperature": 0.3,
    }
    print(f"[deepseek_design] モデル: {model}", flush=True)
    print("[deepseek_design] 送信中...", flush=True)

    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers=headers, json=payload, timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        used_model = result.get("model", model)
        print(f"[deepseek_design] 受信完了 ({len(content)}文字, model={used_model})", flush=True)
        return content
    except Exception as e:
        print(f"[deepseek_design] ERROR: {e}", flush=True)
        # フォールバック: local_fast
        if model != "local_fast":
            print(f"[deepseek_design] {model}失敗 → local_fast にフォールバック", flush=True)
            return call_deepseek(prompt, "local_fast")
        raise

if __name__ == "__main__":
    design = call_deepseek(PROMPT)
    OUTPUT_PATH.write_text(
        f"# Blenderモード改善設計書 (DeepSeek生成)\n\n{design}",
        encoding="utf-8"
    )
    print(f"\n[deepseek_design] 保存完了: {OUTPUT_PATH}", flush=True)
    print("\n--- 設計書の冒頭 ---")
    print(design[:1000])
