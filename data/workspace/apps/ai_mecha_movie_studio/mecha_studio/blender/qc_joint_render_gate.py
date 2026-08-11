# -*- coding: utf-8 -*-
"""Blender headless: 関節が「貫通穴」を開けたかをレンダで判定するQCゲート。

距離ベースの指標（子頂点→親表面の最大距離）は使えない。四肢が回転すれば遠い接触点は
当然離れるため、「回転した（正常）」と「穴が空いた（異常）」を区別できないからである
（実測: 距離ゲートは全関節FAIL、しかし膝20°屈曲を目視すると穴は無い）。

そこで目視と同じものを機械に見せる:

  背景を透過にしてレンダし、アルファ0の画素のうち**画像の縁から到達できない**ものを数える。
  縁から到達できない透明画素 = シルエットに囲まれた抜け = 見て分かる穴。

レスト姿勢にも構造的な抜け（腕と胴の隙間など）はあるので、レストを基準にした
**増分**で判定する。回転しても穴が増えなければPASS。

  blender --background --python qc_joint_render_gate.py -- --blend <blend> \
      [--json <out>] [--images <dir>] [--res 256] [--sweep 20] [--max-hole-ratio 0.004]
"""
import bpy
import json
import math
import sys
from collections import deque
from pathlib import Path
from mathutils import Vector

DEFAULT_RES = 256
DEFAULT_SWEEP = 20.0
# シルエット面積に対する穴の増分がこの比を超えたらFAIL
DEFAULT_MAX_HOLE_RATIO = 0.004
ALPHA_TH = 0.5
CORE_PREFIX = "JointCore_"
# 関節を覗く方向（前寄りと横寄り）。片方から見えない穴を拾うため複数用意する
VIEW_DIRS = [(-0.85, -0.5, 0.15), (0.0, -1.0, 0.12), (-1.0, 0.05, 0.10)]


def _argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag, default=None):
    a = _argv()
    if flag in a:
        i = a.index(flag)
        if i + 1 < len(a):
            return a[i + 1]
    return default


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def pick_engine(current):
    avail = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for n in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        if n in avail:
            return n
    return current


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (mn + mx) / 2, (mx - mn)


def count_enclosed_holes(png_path, res, save_mask=False):
    """透明画素のうち、画像の縁から到達できないもの（=囲まれた穴）の画素数を返す。

    save_mask=True なら判定根拠を _mask.png として書き出す
    （不透明=灰 / 外側の背景=白 / 囲まれた穴=赤）。FAIL時に人が目で確認できるようにする。

    戻り値: (hole_px, silhouette_px)
    """
    img = bpy.data.images.load(str(png_path))
    try:
        px = img.pixels[:]           # RGBA float の平坦配列
        w, h = img.size
        alpha = [px[i * 4 + 3] for i in range(w * h)]
    finally:
        bpy.data.images.remove(img)

    opaque = [a >= ALPHA_TH for a in alpha]
    silhouette_px = sum(1 for o in opaque if o)

    # 縁から透明領域を塗りつぶす（外側の背景）
    seen = bytearray(w * h)
    q = deque()

    def push(i):
        if not seen[i] and not opaque[i]:
            seen[i] = 1
            q.append(i)

    for x in range(w):
        push(x)                      # 上端
        push((h - 1) * w + x)        # 下端
    for y in range(h):
        push(y * w)                  # 左端
        push(y * w + (w - 1))        # 右端

    while q:
        i = q.popleft()
        x, y = i % w, i // w
        if x > 0:
            push(i - 1)
        if x < w - 1:
            push(i + 1)
        if y > 0:
            push(i - w)
        if y < h - 1:
            push(i + w)

    # 透明なのに外側から到達できない = 囲まれた穴
    holes = [i for i in range(w * h) if not opaque[i] and not seen[i]]

    if save_mask and holes:
        mask = bpy.data.images.new(Path(png_path).stem + "_mask", width=w, height=h, alpha=False)
        buf = [0.0] * (w * h * 4)
        for i in range(w * h):
            c = (0.35, 0.35, 0.38) if opaque[i] else ((1.0, 1.0, 1.0) if seen[i] else (1.0, 0.0, 0.0))
            buf[i * 4:i * 4 + 4] = [c[0], c[1], c[2], 1.0]
        mask.pixels = buf
        mask.filepath_raw = str(Path(png_path).with_name(Path(png_path).stem + "_mask.png"))
        mask.file_format = "PNG"
        mask.save()
        bpy.data.images.remove(mask)

    return len(holes), silhouette_px


def run(blend_path, out_json=None, images_dir=None, res=DEFAULT_RES,
        sweep=DEFAULT_SWEEP, max_hole_ratio=DEFAULT_MAX_HOLE_RATIO):
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError("アーマチュアがありません")
    meshes = [o for o in scene.objects if o.type == "MESH"]
    center, span = bounds(meshes)
    model_size = span.length

    tmp_dir = Path(images_dir) if images_dir else Path(bpy.app.tempdir) / "qc_joint_render"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    scene.render.engine = pick_engine(scene.render.engine)
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True      # 背景=アルファ0。これが穴の検出面になる

    bpy.ops.object.light_add(type="SUN", location=(model_size, -model_size, center.z + model_size))
    key = bpy.context.object
    key.data.energy = 3.0
    look_at(key, center)

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.clip_start = max(model_size * 0.001, 0.01)
    cam.data.clip_end = model_size * 10.0

    # ボーン -> 剛体ペアレントされたメッシュ（コア含む）
    by_bone: dict[str, list] = {}
    for o in meshes:
        if o.parent_type == "BONE" and o.parent_bone:
            by_bone.setdefault(o.parent_bone, []).append(o)

    print(f"[hole] res={res} sweep=±{sweep:.0f}deg views={len(VIEW_DIRS)} "
          f"max_hole_ratio={max_hole_ratio}")
    print(f"[hole] {'JOINT':14} {'PARENT':11} {'rest_px':>8} {'worst_px':>8} {'growth':>8} "
          f"{'ratio':>8}  {'worst':>16}  RESULT")

    want_mask = images_dir is not None

    def render_to(path):
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        return count_enclosed_holes(path, res, save_mask=want_mask)

    checks = []
    for bone in arm.data.bones:
        if bone.parent is None:
            continue
        # armor_follower 用に生成された Follow_* ボーンは構造関節ではない。
        # 測っても常に増分0で、関節数だけ膨れて所要時間が跳ね上がる（実測 71秒 -> 401秒）。
        if bone.name.startswith("Follow_"):
            continue
        child, parent = bone.name, bone.parent.name
        child_objs = by_bone.get(child, [])
        if not child_objs or not by_bone.get(parent):
            continue

        pivot = arm.matrix_world @ bone.head_local
        _, cspan = bounds(child_objs)
        dist = max(cspan.length * 1.1, model_size * 0.10)

        pbone = arm.pose.bones[child]
        pbone.rotation_mode = "XYZ"
        original = tuple(pbone.rotation_euler)

        worst_growth, worst_label, worst_ratio = 0.0, "rest", 0.0
        rest_total, sil_total = 0, 0

        for vi, dv in enumerate(VIEW_DIRS):
            cam.location = pivot + Vector(dv).normalized() * dist
            look_at(cam, pivot)

            pbone.rotation_euler = original
            bpy.context.view_layer.update()
            rest_px, rest_sil = render_to(tmp_dir / f"{child}_v{vi}_rest.png")
            rest_total += rest_px
            sil_total += rest_sil

            for axis in (0, 2):          # 主要な曲げ軸（X）と捻り（Z）
                for deg in (sweep, -sweep):
                    rot = list(original)
                    rot[axis] = original[axis] + math.radians(deg)
                    pbone.rotation_euler = rot
                    bpy.context.view_layer.update()
                    tag = f"{child}_v{vi}_{'xyz'[axis]}{int(deg):+d}"
                    hole_px, sil_px = render_to(tmp_dir / f"{tag}.png")
                    growth = max(0, hole_px - rest_px)
                    ratio = growth / max(sil_px, 1)
                    if ratio > worst_ratio:
                        worst_growth, worst_ratio = growth, ratio
                        worst_label = f"v{vi} {'xyz'[axis]}{int(deg):+d}"

            pbone.rotation_euler = original
            bpy.context.view_layer.update()

        ok = worst_ratio <= max_hole_ratio
        checks.append({"joint": child, "parent": parent,
                       "rest_hole_px": rest_total, "worst_growth_px": worst_growth,
                       "worst_ratio": round(worst_ratio, 5), "worst": worst_label,
                       "silhouette_px": sil_total, "pass": ok})
        print(f"[hole] {child:14} {parent:11} {rest_total:8} {worst_growth:8} "
              f"{worst_growth:8} {worst_ratio:8.5f}  {worst_label:>16}  {'PASS' if ok else 'FAIL'}")

    failed = [c["joint"] for c in checks if not c["pass"]]
    result = {"schema": "clawstack.mecha_joint_hole.v1", "blend": str(blend_path),
              "res": res, "sweep_deg": sweep, "max_hole_ratio": max_hole_ratio,
              "checks": checks, "failed": failed,
              "verdict": "PASS" if not failed else "FAIL"}
    print(f"[hole] VERDICT: {result['verdict']}"
          + (f"  穴が増えた関節: {', '.join(failed)}" if failed
             else f"  ({len(checks)}関節すべて穴の増加なし)"))
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"[hole] report -> {out_json}")
    return result


if __name__ == "__main__":
    run(_arg("--blend"), _arg("--json"), _arg("--images"),
        int(_arg("--res", DEFAULT_RES)), float(_arg("--sweep", DEFAULT_SWEEP)),
        float(_arg("--max-hole-ratio", DEFAULT_MAX_HOLE_RATIO)))
