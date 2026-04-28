"""自然言語指示 → Blender Pythonパッチ生成 (DeepSeek V4 Pro)。"""
import json, os, requests, tempfile, subprocess
from pathlib import Path

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")

# コード生成はDeepSeek V4 Pro優先
EDIT_MODELS = [
    "opencode-go/deepseek-v4-pro",
    "google/gemini-2.5-flash",
    "local_fast",
]

SYSTEM_PROMPT = """あなたはBlender Python APIの専門家です。
既存のBlenderシーン(.blend)または骨格情報に対して、
ユーザーの指示に従ったBlender Pythonスクリプトパッチを生成します。

【ルール】
- 出力はBlender Python実行可能なコードのみ（説明不要）
- bpyを使ってbone回転・位置をキーフレームで設定する
- 既存のアニメーションを壊さないようにframe_set()を適切に使う
- import文は最小限にする
"""


def _call_llm(model: str, user_prompt: str) -> str | None:
    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                "max_tokens": 4000,
                "temperature": 0.3,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [{model}] {e}")
        return None


def generate_patch(
    instruction: str,
    timestamp_sec: float,
    character: str,
    video_meta: dict,
) -> str:
    """自然言語指示からBlenderパッチスクリプトを生成する。"""
    user_prompt = (
        f"動画の {timestamp_sec:.1f}秒 時点で、キャラクター「{character}」に対して以下の指示を実行するBlenderスクリプトを生成してください。\n\n"
        f"指示: {instruction}\n\n"
        f"フレームレート: 30fps → {timestamp_sec:.1f}秒 = {int(timestamp_sec * 30)}フレーム\n"
        f"アーマチュア名: {character}_armature (見つからなければ最初のARMATURE)\n\n"
        "Mixamoボーン名例: mixamorig:Head, mixamorig:Neck, mixamorig:LeftArm, mixamorig:RightArm, mixamorig:Spine\n"
        "顎ボーン: jaw_bone, 瞼ボーン: eyelid_L, eyelid_R\n\n"
        "回転はXYZオイラー角(ラジアン)で指定してください。"
    )

    for model in EDIT_MODELS:
        raw = _call_llm(model, user_prompt)
        if not raw:
            continue
        # コードブロック除去
        if "```" in raw:
            parts = raw.split("```")
            for p in parts:
                if p.startswith("python"):
                    raw = p[6:].strip()
                    break
                elif "\n" in p and "import bpy" in p:
                    raw = p.strip()
                    break
        return raw

    return "# パッチ生成失敗 — 全モデルエラー\nprint('patch generation failed')"


def apply_patch_to_blend(
    blend_path: Path,
    patch_script: str,
    blender_bin: str = "blender",
) -> bool:
    """blendファイルにパッチを適用して上書き保存する。"""
    save_script = (
        patch_script
        + "\nbpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)\n"
    )
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(save_script)
        script_path = Path(tmp.name)

    cmd = [
        blender_bin, "--background",
        str(blend_path),
        "--python", str(script_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    script_path.unlink(missing_ok=True)
    return result.returncode == 0


def render_segment(
    blend_path: Path,
    start_frame: int,
    end_frame: int,
    frames_out: Path,
    blender_bin: str = "blender",
) -> bool:
    """指定フレーム区間のみレンダリングする。"""
    render_script = f"""
import bpy
scene = bpy.context.scene
scene.frame_start = {start_frame}
scene.frame_end   = {end_frame}
scene.render.filepath = r"{str(frames_out)}/frame_"
bpy.ops.render.render(animation=True, write_still=True)
"""
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(render_script)
        script_path = Path(tmp.name)

    cmd = [
        blender_bin, "--background",
        str(blend_path),
        "--python", str(script_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    script_path.unlink(missing_ok=True)
    return result.returncode == 0
