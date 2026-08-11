# -*- coding: utf-8 -*-
"""Blender headless: 剛体リグの関節が「穴」を開けていないかを測るゲート（修正版）。

既存 projects/AtsugiMechaCity/qc_joint_separation.py の RULE④ は
「レスト時に親へ接触していた**子の頂点**が、スイープ後に親からどれだけ離れたか」
を測る。これは球ジョイントコア(RULE②)と原理的に噛み合わない:

  球は**面としては**回転不変だが、**個々の頂点は回転不変ではない**。
  コアは子ボーンにバインドされて一緒に回るため、コアを大きくするほど
  追跡頂点はピボットから遠ざかり、開口が大きく計測される。
  実測でも半径 0.85→2.5 に対し開口 0.75m→1.47m と単調悪化した。

そこで計測の向きを逆にする:

  レスト時に「子＋そのコア」へ接触していた**親の頂点**を記録し、
  スイープ後にそれが「子＋そのコア」の表面からどれだけ離れたかを測る。

親の頂点は動かない。球の表面は回転しても同じ集合を占める。よって
コアが関節を埋めている限り距離は小さいままで、埋まっていなければ開く。
「関節に穴が空いたか」という本来見たい量を、そのまま測れる。

## 実測結果（2026-08-11 / Zaku_Split_Rigged）— この修正でも通らなかった

  コアなし: 全13関節 FAIL（開口 0.44〜1.09m / tol 0.396m）
  コアあり: 全13関節 FAIL（開口 0.54〜1.24m / tol 0.531m）
           ※ scale=2.5 の球でモデル高が 18.00m → 24.14m に膨張。球が機体から露出している

一方、膝を20°曲げてレンダし**目視した結果、穴は空いていない**（太腿と脛が膝シェルを挟んで接触）。

つまり向きを反転しても足りない。根本は **max距離ベースの指標そのもの**にある:

  追跡頂点の「最大距離」は、四肢が回転しただけでも増える。例えば腿の裏側の
  接触頂点は、膝を曲げれば当然親から遠ざかる。これは穴ではなく単なる回転。
  max距離では「回転した(正常)」と「穴が空いた(異常)」を区別できない。

正しく測るなら、距離ではなく**開口部そのもの**を見る必要がある。候補:
  - 関節周りで親子の表面が作る閉曲面に、貫通する穴があるか（視線判定 / ray cast）
  - 関節断面での被覆率（周方向にどれだけ材料が残っているか）
  - レンダしてシルエット内に背景色が現れるか（最も直接的で、目視基準とも一致する）

このファイルは「向きを反転しても解決しない」ことの証跡として残す。ゲートとして
採用する前に、上記いずれかの指標へ置き換えること。

  blender --background --python qc_joint_gap.py -- --blend <blend> [--json <out>]
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector, kdtree

CONTACT_RATIO = 0.018   # レスト時に接触とみなす閾値（モデル高さ比）
TOL_RATIO = 0.022       # これを超える開口は「見える穴」
SWEEP_DEG = [-20, -12, -6, 6, 12, 20]
MAX_VERTS = 1500
CORE_PREFIX = "JointCore_"


def _args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag, default=None):
    a = _args()
    if flag in a:
        i = a.index(flag)
        if i + 1 < len(a):
            return a[i + 1]
    return default


def _sample(obj, cap=MAX_VERTS):
    n = len(obj.data.vertices)
    if n <= cap:
        return range(n)
    step = max(1, n // cap)
    return range(0, n, step)


def _world_pts(objs):
    pts = []
    for o in objs:
        mw = o.matrix_world
        for i in _sample(o):
            pts.append(mw @ o.data.vertices[i].co)
    return pts


def _kd(objs):
    pts = _world_pts(objs)
    if not pts:
        return None
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd


def _model_height(meshes):
    zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]
    return (max(zs) - min(zs)) if zs else 1.0


def run(blend_path, out_json=None):
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError("アーマチュアがありません")

    meshes = [o for o in scene.objects if o.type == "MESH"]
    height = _model_height(meshes)
    contact_th = CONTACT_RATIO * height
    tol = TOL_RATIO * height

    # ボーン -> そのボーンに剛体ペアレントされたメッシュ（装甲とコアを分けて持つ）
    armor: dict[str, list] = {}
    cores: dict[str, list] = {}
    for o in meshes:
        if o.parent_type != "BONE" or not o.parent_bone:
            continue
        (cores if o.name.startswith(CORE_PREFIX) else armor).setdefault(o.parent_bone, []).append(o)

    n_cores = sum(len(v) for v in cores.values())
    print(f"[gap] height={height:.2f}m contact_th={contact_th:.3f}m tol={tol:.3f}m cores={n_cores}")
    print(f"[gap] {'JOINT':14} {'PARENT':11} {'rest':>6} {'open':>6}  {'worst':>22} {'patch':>6}  RESULT")

    checks = []
    for bone in arm.data.bones:
        if bone.parent is None:
            continue
        child_name, parent_name = bone.name, bone.parent.name
        child_objs = armor.get(child_name, []) + cores.get(child_name, [])
        parent_objs = armor.get(parent_name, [])
        if not child_objs or not parent_objs:
            continue

        # レスト時: 「子+コア」へ接触している**親の**頂点を記録する（親は動かない）
        child_kd = _kd(child_objs)
        if child_kd is None:
            continue
        patch = []
        for o in parent_objs:
            mw = o.matrix_world
            for i in _sample(o):
                w = mw @ o.data.vertices[i].co
                if child_kd.find(w)[2] < contact_th:
                    patch.append(w)
        if not patch:
            checks.append({"joint": child_name, "parent": parent_name, "skipped": "no_contact_patch"})
            print(f"[gap] {child_name:14} {parent_name:11} {'-':>6} {'-':>6}  {'接触パッチなし':>22} {0:>6}  SKIP")
            continue

        rest_gap = max(child_kd.find(p)[2] for p in patch)

        pbone = arm.pose.bones[child_name]
        pbone.rotation_mode = "XYZ"
        original = tuple(pbone.rotation_euler)
        worst_open, worst_label = 0.0, "rest"
        for axis in range(3):
            for deg in SWEEP_DEG:
                rot = list(original)
                rot[axis] = original[axis] + math.radians(deg)
                pbone.rotation_euler = rot
                bpy.context.view_layer.update()
                kd_now = _kd(child_objs)
                if kd_now is None:
                    continue
                open_now = max(kd_now.find(p)[2] for p in patch)
                if open_now > worst_open:
                    worst_open = open_now
                    worst_label = f"{'xyz'[axis]}{deg:+d}deg->{open_now:.2f}m"
        pbone.rotation_euler = original
        bpy.context.view_layer.update()

        ok = worst_open <= tol
        checks.append({"joint": child_name, "parent": parent_name,
                       "rest_gap": round(rest_gap, 4), "open": round(worst_open, 4),
                       "worst": worst_label, "patch": len(patch), "pass": ok})
        print(f"[gap] {child_name:14} {parent_name:11} {rest_gap:6.2f} {worst_open:6.2f}  "
              f"{worst_label:>22} {len(patch):>6}  {'PASS' if ok else 'FAIL'}")

    graded = [c for c in checks if "pass" in c]
    failed = [c["joint"] for c in graded if not c["pass"]]
    result = {"schema": "clawstack.mecha_joint_gap.v1", "blend": str(blend_path),
              "model_height": round(height, 4), "tol": round(tol, 4), "cores": n_cores,
              "checks": checks, "failed": failed,
              "verdict": "PASS" if not failed else "FAIL"}
    print(f"[gap] VERDICT: {result['verdict']}"
          + (f"  失敗: {', '.join(failed)}" if failed else f"  ({len(graded)}関節すべて許容内)"))

    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[gap] report -> {out_json}")
    return result


if __name__ == "__main__":
    run(_arg("--blend"), _arg("--json"))
