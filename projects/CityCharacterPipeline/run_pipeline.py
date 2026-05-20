"""CityCharacterPipeline — メインオーケストレーター

使い方:
    python run_pipeline.py --config configs/hon_atsugi_dom.yaml
    python run_pipeline.py --config configs/hon_atsugi_dom.yaml --animate

フロー:
    1. QC工程表・FMEA事前分析
    2. YAML config 読み込み・検証
    3. 地形データ準備（OSM/PLATEAU/blend_only）
    4. Blenderスクリプト生成
    5. Blender実行（静止画 or 動画）
    6. QAゲート（4項目スコアリング）
    7. 超リアル化後処理（SD img2img + PIL + Lanczos 2x）
    8. 知識記録（DB + Markdown + ByteRover）
    9. 合格なら次ステップ提案、不合格なら改善ヒント表示
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent

# パイプライン内モジュールをインポートできるよう追加
sys.path.insert(0, str(ROOT / "pipeline"))

import yaml  # type: ignore[import-untyped]

from scene_builder import generate_blender_script
from qa_scorer import score_render, print_qa_report
from terrain_builder import prepare_terrain
from post_processor import (
    post_process,
    post_process_compare,
    print_post_process_report,
    print_compare_report,
)
from knowledge_recorder import (
    record_trial,
    record_qc_process_chart,
    record_fmea,
    record_lesson,
    _DB_URL as _KR_DB_URL,
)
from material_enhancements import record_enhancements as _record_enhancements
from db_self_healer import replay_pending_queue

BLENDER_PATH = os.getenv(
    "BLENDER_PATH",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
)


# ══════════════════════════════════════════════════════════════
# 1. QC工程表 + FMEA 事前分析（コンソール表示）
# ══════════════════════════════════════════════════════════════
def _print_qc_preflight(config: dict):
    name = config.get("scene", {}).get("name", "unknown")
    print(f"\n{'='*60}", flush=True)
    print(f"  QC工程表（事前分析）: {name}", flush=True)
    print(f"{'='*60}", flush=True)
    steps = [
        ("Config読み込み",   "YAMLスキーマ",   "全フィールド存在"),
        ("Blend読み込み",    "オブジェクト数",  ">=1オブジェクト"),
        ("マテリアル強化",   "PBRテクスチャ",   "全建物・道路に適用"),
        ("ライティング",     "HDRI + 太陽",     "自然光再現"),
        ("接地AO",          "ShadowCatcher",   "足元影あり"),
        ("カメラ",           "構図・レンズ",    "被写体中央"),
        ("レンダリング",     "Cyclesサンプル数", "全黒なし・ノイズ最小"),
        ("QAゲート",         "4項目スコア",     "全項目>=3/5"),
    ]
    print(f"  {'#':2} {'工程':15} {'管理特性':15} {'判定基準'}", flush=True)
    print(f"  {'-'*55}", flush=True)
    for i, (step, ctrl, crit) in enumerate(steps, 1):
        print(f"  {i:2} {step:15} {ctrl:15} {crit}", flush=True)
    print(flush=True)

    print(f"  FMEA（高RPNリスク）:", flush=True)
    fmea_items = [
        ("マテリアル", "白箱未適用", "RPN=96", "アセット事前確認"),
        ("ライティング", "フラット照明", "RPN=84", "Nishita Sky + sun_energy>=5"),
        ("接地AO", "DOM浮き", "RPN=81", "embed_depth=0.75固定"),
        ("レンダリング", "全黒フレーム", "RPN=40", "samples>=64 + visual_qa gate"),
    ]
    for proc, fm, rpn, action in fmea_items:
        print(f"  ! [{rpn}] {proc}: {fm} → {action}", flush=True)
    print(f"{'='*60}\n", flush=True)


# ══════════════════════════════════════════════════════════════
# 2. Config 検証
# ══════════════════════════════════════════════════════════════
def _validate_config(config: dict) -> list[str]:
    errors = []
    required = [
        ("scene.name",   lambda c: c.get("scene", {}).get("name")),
        ("render.output_dir", lambda c: c.get("render", {}).get("output_dir")),
        ("character.height_m", lambda c: c.get("character", {}).get("height_m")),
    ]
    for field, getter in required:
        if not getter(config):
            errors.append(f"必須フィールド不足: {field}")
    return errors


def _deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


CAMERA_ANGLE_PRESETS: dict[str, dict] = {
    "config": {},
    "hero": {
        "camera": {"position": [14.0, -58.0, 13.0], "target": [0.0, 0.0, 9.0], "lens_mm": 45},
        "animation": {"camera_motion": {"type": "static"}},
    },
    "street_low": {
        "camera": {"position": [7.0, -44.0, 5.6], "target": [0.0, 0.0, 8.5], "lens_mm": 35},
        "animation": {"camera_motion": {"type": "static"}},
    },
    "telephoto": {
        "camera": {"position": [4.0, -95.0, 16.0], "target": [0.0, 0.0, 10.0], "lens_mm": 85},
        "animation": {"camera_motion": {"type": "static"}},
    },
    "orbit": {
        "camera": {"position": [10.0, -65.0, 14.0], "target": [0.0, 0.0, 9.0], "lens_mm": 45},
        "animation": {"camera_motion": {"type": "orbit", "orbit_radius": 62.0, "orbit_z": 11.0}},
    },
}


def _apply_camera_angle(config: dict, angle: str) -> dict:
    preset = CAMERA_ANGLE_PRESETS.get(angle)
    if preset is None:
        raise ValueError(f"Unknown camera angle preset: {angle}")
    if preset:
        _deep_update(config, preset)
    config.setdefault("camera", {})["angle_preset"] = angle
    return config


def _apply_render_profile(config: dict, profile: str, animate: bool) -> dict:
    render = config.setdefault("render", {})
    camera = config.setdefault("camera", {})
    lighting = config.setdefault("lighting", {})
    sun = lighting.setdefault("sun", {})
    post = config.setdefault("post_process", {})
    city = config.setdefault("city_enhancements", {})

    if profile == "preview":
        if animate:
            render.update({
                "engine": "BLENDER_EEVEE",
                "samples": 16,
                "resolution": [854, 480],
                "two_pass": False,
                "output_format": "FFMPEG",
            })
        else:
            render.setdefault("samples", 32)
            render.setdefault("resolution", camera.get("resolution", [1280, 720]))
        return config

    if profile == "standard":
        if animate:
            render.update({
                "engine": "BLENDER_EEVEE",
                "samples": 24,
                "resolution": [1280, 720],
                "two_pass": False,
                "output_format": "FFMPEG",
            })
        else:
            render.setdefault("engine", "CYCLES")
            render.setdefault("samples", 96)
            render.setdefault("resolution", camera.get("resolution", [1920, 1080]))
        sun["energy"] = max(float(sun.get("energy", 3.0)), 4.0)
        return config

    if profile == "photoreal":
        render.update({
            "engine": "CYCLES",
            "device": render.get("device", "CPU"),
            "samples": 96 if animate else 192,
            "resolution": [1920, 1080] if animate else camera.get("resolution", [2560, 1440]),
            "two_pass": False if animate else True,
            "output_format": "PNG",
            "denoiser": "OPENIMAGEDENOISE",
        })
        sun["energy"] = max(float(sun.get("energy", 3.0)), 5.5)
        lighting["hdri_strength"] = max(float(lighting.get("hdri_strength", 0.05)), 0.12)
        post["sd_enabled"] = bool(post.get("sd_enabled", True))
        post["sd_strength"] = min(float(post.get("sd_strength", 0.28)), 0.32)
        post["sd_strength_bg"] = max(float(post.get("sd_strength_bg", 0.45)), 0.42)
        post["sd_steps"] = max(int(post.get("sd_steps", 20)), 24)
        post["max_dimension"] = max(int(post.get("max_dimension", 768)), 960)
        post["upscale_factor"] = max(int(post.get("upscale_factor", 2)), 2)
        city.setdefault("windows", {}).setdefault("enabled", True)
        city.setdefault("road_markings", {}).setdefault("enabled", True)
        city.setdefault("traffic_lights", {}).setdefault("enabled", True)
        config.setdefault("contact_ao", {})["enabled"] = True
        config["contact_ao"]["strength"] = max(float(config["contact_ao"].get("strength", 0.7)), 0.8)
        return config

    raise ValueError(f"Unknown render profile: {profile}")


# ══════════════════════════════════════════════════════════════
# 3. Blender 実行
# ══════════════════════════════════════════════════════════════
def _run_blender(script_path: Path, timeout: int = 3600) -> dict:
    if not Path(BLENDER_PATH).exists():
        # Docker 内 Blender を試みる
        cmd = [
            "docker", "exec", "clawstack-unified-blender-1",
            "blender", "--background", "--python", str(script_path),
        ]
        print("[Pipeline] Docker内Blenderで実行します", flush=True)
    else:
        cmd = [BLENDER_PATH, "--background", "--python", str(script_path)]
        print(f"[Pipeline] ローカルBlenderで実行: {BLENDER_PATH}", flush=True)

    print(f"[Pipeline] コマンド: {' '.join(cmd[:4])} ...", flush=True)
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            timeout=timeout,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            print(f"[Pipeline] Blender終了コード: {result.returncode}", flush=True)
            return {"status": "blender_error", "render_sec": elapsed, "errors": [f"returncode={result.returncode}"]}
        return {"status": "done", "render_sec": elapsed, "errors": []}
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return {"status": "timeout", "render_sec": elapsed, "errors": ["timeout"]}
    except FileNotFoundError:
        return {"status": "blender_not_found", "render_sec": 0.0,
                "errors": [f"Blenderが見つかりません: {BLENDER_PATH}"]}


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    return safe.strip("_") or "city_character"


def _find_ffmpeg() -> str | None:
    candidates = [
        os.getenv("FFMPEG_PATH", ""),
        shutil.which("ffmpeg") or "",
        r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _assemble_animation_video(output_dir: Path, output_prefix: str, fps: int, scene_name: str) -> dict:
    frames_dir = output_dir / "frames"
    frames = sorted(frames_dir.glob(f"{output_prefix}_frame_*.png"))
    if not frames:
        return {"status": "no_frames", "path": "", "errors": [f"No PNG frames found in {frames_dir}"]}

    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        return {"status": "ffmpeg_not_found", "path": "", "errors": ["ffmpeg not found"]}

    video_path = output_dir / f"{_safe_filename(scene_name)}_walk.mp4"
    pattern = frames_dir / f"{output_prefix}_frame_%04d.png"
    cmd = [
        ffmpeg_path,
        "-y",
        "-framerate", str(int(fps) or 30),
        "-i", str(pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-crf", "18",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {"status": "ffmpeg_error", "path": str(video_path), "errors": [result.stderr[-1200:]]}
    return {"status": "done", "path": str(video_path), "errors": [], "frames": len(frames)}


# ══════════════════════════════════════════════════════════════
# メイン
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="CityCharacterPipeline")
    parser.add_argument("--config", required=True, help="YAMLコンフィグパス")
    parser.add_argument("--animate", action="store_true", help="動画モードで実行（静止画合格後）")
    parser.add_argument("--skip-qa",   action="store_true", help="QAゲートをスキップ（デバッグ用）")
    parser.add_argument("--dry-run",   action="store_true", help="Blenderを実際には実行しない")
    parser.add_argument(
        "--render-profile",
        choices=["preview", "standard", "photoreal"],
        default="preview",
        help="Render quality profile. preview is fast, photoreal is slower but YouTube-oriented.",
    )
    parser.add_argument(
        "--camera-angle",
        choices=sorted(CAMERA_ANGLE_PRESETS.keys()),
        default="config",
        help="Camera angle preset to apply on top of the YAML config.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    print(f"\n[Pipeline] 設定ファイル: {config_path}", flush=True)
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config = _apply_camera_angle(config, args.camera_angle)
    config = _apply_render_profile(config, args.render_profile, args.animate)
    print(
        f"[Pipeline] profile={args.render_profile} camera_angle={args.camera_angle}",
        flush=True,
    )

    scene_name = config.get("scene", {}).get("name", "unknown")
    output_dir = Path(config.get("render", {}).get("output_dir", f"output/{scene_name}"))
    output_prefix = config.get("render", {}).get("output_prefix", "render")
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 0: ペンディングDBキューのリプレイ ────────────────
    replayed = replay_pending_queue(_KR_DB_URL)
    if replayed:
        print(f"[Pipeline] ペンディングキュー: {replayed} 件をDBにリプレイ済み", flush=True)

    # ── Step 1: QC工程表 + FMEA 事前分析 ─────────────────────
    print("\n[1/8] QC工程表・FMEA 事前分析", flush=True)
    _print_qc_preflight(config)
    record_qc_process_chart(scene_name, config)

    # ── Step 2: Config 検証 ───────────────────────────────────
    print("[2/8] Config 検証", flush=True)
    errors = _validate_config(config)
    if errors:
        for e in errors:
            print(f"  [ERROR] {e}", flush=True)
        sys.exit(1)
    print("  Config OK", flush=True)

    # ── Step 3: 地形データ準備 ───────────────────────────────
    print("[3/8] 地形データ準備", flush=True)
    config = prepare_terrain(config, output_dir)

    # ── Step 4: Blenderスクリプト生成 ─────────────────────────
    print("[4/8] Blenderスクリプト生成", flush=True)
    if args.animate:
        config.setdefault("animation", {})["enabled"] = True
        config.setdefault("render", {}).setdefault("output_format", "PNG")
    blender_script = generate_blender_script(config)
    script_path = output_dir / "blender_scene_script.py"
    script_path.write_text(blender_script, encoding="utf-8")
    print(f"  スクリプト保存: {script_path}", flush=True)

    # ── Step 5: Blender 実行 ──────────────────────────────────
    print("[5/8] Blender 実行", flush=True)
    t0 = time.time()
    if args.dry_run:
        print("  [DRY-RUN] Blender実行をスキップします", flush=True)
        run_result = {"status": "dry_run", "render_sec": 0.0, "errors": []}
    else:
        anim_frames = config.get("animation", {}).get("total_frames", 0)
        blender_timeout = 7200 if (config.get("animation", {}).get("enabled") and anim_frames > 0) else 3600
        run_result = _run_blender(script_path, timeout=blender_timeout)
    render_sec = time.time() - t0

    # build_result.json を読み込む（Blenderスクリプトが出力）
    build_result_path = output_dir / "build_result.json"
    build_result = {}
    if build_result_path.exists():
        try:
            with open(build_result_path, encoding="utf-8") as f:
                build_result = json.load(f)
        except Exception:
            pass

    video_result = None
    if args.animate and not args.dry_run and run_result.get("status") == "done":
        video_result = _assemble_animation_video(
            output_dir,
            output_prefix,
            int(config.get("animation", {}).get("fps", 30)),
            scene_name,
        )
        if video_result.get("status") == "done":
            print(f"  [OK] MP4 assembled: {video_result['path']}", flush=True)
        else:
            print(f"  [WARN] MP4 assembly skipped: {video_result.get('status')}", flush=True)
            run_result.setdefault("errors", []).extend(video_result.get("errors", []))

    # ── Step 6: QAゲート ──────────────────────────────────────
    print("[6/8] QAゲート", flush=True)
    if args.skip_qa:
        qa_scores = {
            "material_realism": 3, "lighting": 3,
            "camera": 3, "character_integration": 3,
            "pass": True, "notes": "スキップ", "method": "skip",
        }
    else:
        qa_scores = score_render(output_dir, output_prefix, build_result)

    print_qa_report(qa_scores, scene_name)

    # ── Step 7: 超リアル化後処理 ──────────────────────────────
    print("[7/8] 超リアル化後処理", flush=True)
    render_file = output_dir / f"{output_prefix}_final.png"
    ultra_path = None
    compare_result = None
    if not args.animate and render_file.exists() and not args.dry_run:
        try:
            two_pass_mode  = config.get("render", {}).get("two_pass", False)
            compare_mode   = config.get("photo_bg", {}).get("compare", False)
            bg_path        = (output_dir / f"{output_prefix}_bg.png") if two_pass_mode else None

            if compare_mode and two_pass_mode:
                # SD版と実写写真版を両方生成して比較
                compare_result = post_process_compare(
                    render_file, output_dir / "ultra", config, bg_path=bg_path
                )
                print_compare_report(compare_result)
                ultra_path = compare_result.get("comparison_path") or compare_result.get("sd_path")
            else:
                ultra_path = post_process(render_file, output_dir / "ultra", config, bg_path=bg_path)
                print_post_process_report(ultra_path, render_file)
        except Exception as e:
            print(f"  [WARN] 後処理エラー（スキップ）: {e}", flush=True)
    else:
        print("  後処理スキップ（animate / dry-run / render未完了）", flush=True)

    # ── Step 8: 知識記録 ──────────────────────────────────────
    print("[8/8] 知識記録", flush=True)
    lessons = _make_lessons(qa_scores, run_result)
    record_fmea(scene_name, qa_scores, lessons)
    row_id = record_trial(
        scene_name  = scene_name,
        config      = config,
        qa_scores   = qa_scores,
        fmea        = {"lessons": lessons},
        output_path = str(output_dir),
        render_sec  = run_result.get("render_sec", render_sec),
        status      = "pass" if qa_scores.get("pass") else "fail",
        lessons     = lessons,
    )
    record_lesson(scene_name, lessons, qa_scores, config)
    # 質感強化パラメータを別テーブル(city_enhancements_log)に記録
    _record_enhancements(scene_name, config.get("city_enhancements", {}), _KR_DB_URL)
    print(f"  DB row_id: {row_id}", flush=True)

    # ── 結果サマリー ──────────────────────────────────────────
    print("\n" + "="*60, flush=True)
    if qa_scores.get("pass"):
        print("  PASS QAゲート合格", flush=True)
        if not args.animate and not args.dry_run:
            print("\n  次のステップ:", flush=True)
            print(f"  動画生成: python run_pipeline.py --config {args.config} --animate", flush=True)
    else:
        print("  FAIL QAゲート不合格 — 以下の改善を検討してください:", flush=True)
        _print_improvement_hints(qa_scores, config)

    print(f"\n  Blenderレンダー: {render_file}", flush=True)
    if compare_result:
        if compare_result.get("sd_path"):
            print(f"  SD img2img版   : {compare_result['sd_path']}", flush=True)
        if compare_result.get("photo_path"):
            print(f"  実写写真版     : {compare_result['photo_path']}", flush=True)
        if compare_result.get("comparison_path"):
            print(f"  比較画像       : {compare_result['comparison_path']}", flush=True)
    elif ultra_path:
        print(f"  超リアル画像   : {ultra_path}", flush=True)
    if video_result and video_result.get("path"):
        print(f"  MP4動画        : {video_result['path']}", flush=True)
    print(f"  レンダー時間: {run_result.get('render_sec', render_sec):.1f}s", flush=True)
    print("="*60 + "\n", flush=True)

    return 0 if qa_scores.get("pass") else 1


def _make_lessons(qa_scores: dict, run_result: dict) -> str:
    parts = []
    if qa_scores.get("material_realism", 5) < 3:
        parts.append("ambientCGアセットをpipeline実行前にダウンロードし、パスを確認すること")
    if qa_scores.get("lighting", 5) < 3:
        parts.append("Nishita Sky + sun_energy>=5 + fill_lights 2灯を必ず設定すること")
    if qa_scores.get("camera", 5) < 3:
        parts.append("カメラtargetをキャラクター重心（height_m/2）に合わせること")
    if qa_scores.get("character_integration", 5) < 3:
        parts.append("embed_depth=0.75固定 + ShadowCatcher必須。Mixamoポーズfbxを使用すること")
    errors = run_result.get("errors", [])
    if errors:
        parts.append(f"Blenderエラー: {'; '.join(errors)}")
    return " / ".join(parts) if parts else "全項目合格。このパラメータ設定を再利用推奨。"


def _print_improvement_hints(qa_scores: dict, config: dict):
    if qa_scores.get("material_realism", 5) < 3:
        amb = config.get("materials", {}).get("ambientcg_dir", "")
        print(f"  • マテリアル: ambientcg_dir={amb} のアセットを確認", flush=True)
    if qa_scores.get("lighting", 5) < 3:
        energy = config.get("lighting", {}).get("sun", {}).get("energy", 0)
        print(f"  • ライティング: sun_energy={energy} → 推奨>=5.0", flush=True)
    if qa_scores.get("camera", 5) < 3:
        print("  • カメラ: target の z をキャラ身長 / 2 に調整", flush=True)
    if qa_scores.get("character_integration", 5) < 3:
        embed = config.get("character", {}).get("grounding", {}).get("embed_depth", 0)
        print(f"  • 接地AO: embed_depth={embed} → 推奨 0.75", flush=True)


if __name__ == "__main__":
    sys.exit(main())
