# -*- coding: utf-8 -*-
"""Blender headless: 分割済みメカFBXの部品を、指定軸の平面でさらに分割する。

膝・肘のように「1部品に複数の関節がまたがっている」状態を解消するための道具。
剛体ペアレント(parent_type='BONE')は 1部品=1ボーン が前提なので、
関節をまたぐ部品が残っていると、その関節は曲がらない。

切断位置は決め打ちせず、**断面が最も細くなる位置**を自動探索する。
メカの関節は必ずくびれているため、これが実形状に沿った切断位置になる。

  blender --background --python split_parts.py -- <in_fbx> <cuts_json> <out_fbx> [report_json]
"""
import bpy
import bmesh
import json
import sys
from pathlib import Path
from mathutils import Vector

AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def argv_after():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def world_bbox(objs):
    pts = []
    for o in objs:
        pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
    mins = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    maxs = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mins, maxs


def cross_section_extent(obj, axis_i, pos, slab):
    """pos を中心とする薄いスラブ内の頂点が、他2軸方向にどれだけ広がっているかを返す。

    関節のくびれでは、この広がり(=断面の外接矩形の対角)が極小になる。
    """
    others = [i for i in (0, 1, 2) if i != axis_i]
    lo, hi = pos - slab * 0.5, pos + slab * 0.5
    mins = [float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf")]
    n = 0
    mw = obj.matrix_world
    for v in obj.data.vertices:
        w = mw @ v.co
        if lo <= w[axis_i] <= hi:
            n += 1
            for k, oi in enumerate(others):
                mins[k] = min(mins[k], w[oi])
                maxs[k] = max(maxs[k], w[oi])
    if n < 8:
        return None, n
    d0, d1 = maxs[0] - mins[0], maxs[1] - mins[1]
    return (d0 * d0 + d1 * d1) ** 0.5, n


def find_waist(obj, axis_i, lo_w, hi_w, samples=64):
    """[lo_w, hi_w] の範囲で「くびれ」を探す。

    単純な最小値では駄目。四肢は先端(足首/手首)に向かって細くなるので、
    最小値は必ず探索範囲の端に落ちる。膝・肘は**局所**極小なので、
    両隣より細く、かつ左右の盛り上がりが大きい(prominenceが高い)点を選ぶ。
    """
    span = hi_w - lo_w
    if span <= 0:
        return None, [], "empty_range"
    slab = span / samples * 2.0
    profile = []
    for i in range(samples + 1):
        pos = lo_w + span * i / samples
        ext, n = cross_section_extent(obj, axis_i, pos, slab)
        profile.append({"pos": pos, "extent": ext, "verts": n})

    vals = [(i, p["extent"]) for i, p in enumerate(profile) if p["extent"] is not None]
    if len(vals) < 5:
        return None, profile, "too_few_samples"

    idx = {i: v for i, v in vals}
    keys = sorted(idx)
    best = None
    # 端は候補から外す（そこは切断ではなく単なる先細り）
    for k in keys[2:-2]:
        v = idx[k]
        left = [idx[j] for j in keys if j < k]
        right = [idx[j] for j in keys if j > k]
        if not left or not right:
            continue
        if v >= min(left) and v >= min(right):
            continue  # 局所極小ではない
        prominence = min(max(left) - v, max(right) - v)
        if prominence <= 0:
            continue
        if best is None or prominence > best[0]:
            best = (prominence, profile[k]["pos"], v)

    if best is None:
        mid = keys[len(keys) // 2]
        return profile[mid]["pos"], profile, "fallback_midpoint"
    return best[1], profile, "waist"


def bisect(obj, axis_i, pos, keep_positive):
    """obj を平面で切り、片側だけ残す。切断面は塞ぐ。

    bmesh の clear_inner は「法線の負側を消す」、clear_outer は「正側を消す」。
    つまり正側を残したいときに立てるのは clear_inner。ここを逆にすると、
    2つの出力の名前が入れ替わる（実際に l_upperarm と l_forearm が逆になった）。
    """
    normal = [0.0, 0.0, 0.0]
    normal[axis_i] = 1.0
    co = [0.0, 0.0, 0.0]
    co[axis_i] = pos

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    # bisect_plane はローカル座標で動くため、平面をローカルへ持ち込む
    inv = obj.matrix_world.inverted()
    co_local = inv @ Vector(co)
    no_local = (inv.to_3x3() @ Vector(normal)).normalized()
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm, geom=geom, plane_co=co_local, plane_no=no_local,
        clear_inner=keep_positive, clear_outer=not keep_positive, use_snap_center=False,
    )
    # 切り口を塞ぐ（開いたままだと剛体パーツとして扱いにくい）
    open_edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if open_edges:
        bmesh.ops.holes_fill(bm, edges=open_edges)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return obj


def main():
    argv = argv_after()
    if len(argv) < 3:
        raise SystemExit("usage: in_fbx cuts_json out_fbx [report_json]")
    in_fbx, cuts_json, out_fbx = Path(argv[0]), Path(argv[1]), Path(argv[2])
    report_path = Path(argv[3]) if len(argv) > 3 else None

    cfg = json.loads(cuts_json.read_text(encoding="utf-8"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(in_fbx))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    gmin, gmax = world_bbox(meshes)
    span = gmax - gmin
    print(f"[split] input parts={len(meshes)}")

    by_name = {o.name: o for o in meshes}
    report = {"input_parts": len(meshes), "cuts": []}

    for cut in cfg.get("cuts", []):
        name = cut["part"]
        obj = by_name.get(name)
        if obj is None:
            print(f"[split] SKIP {name}: 見つかりません")
            report["cuts"].append({"part": name, "status": "not_found"})
            continue
        axis_i = AXIS_INDEX[cut.get("axis", "z").lower()]

        # 探索範囲は「部品自身のbbox」を基準にする。モデル全体の正規化座標で指定すると
        # 部品の外を指してしまい、片側が空になる（part_9で実際に起きた）。
        pmin, pmax = world_bbox([obj])
        p_lo, p_hi = pmin[axis_i], pmax[axis_i]
        p_span = p_hi - p_lo
        f_lo, f_hi = cut.get("search_local", [0.2, 0.8])
        lo_w = p_lo + p_span * f_lo
        hi_w = p_lo + p_span * f_hi

        pos = cut.get("at_world")
        profile, how = [], "explicit"
        if pos is None and cut.get("at") is not None:
            pos = gmin[axis_i] + span[axis_i] * float(cut["at"])
        if pos is None and cut.get("at_local") is not None:
            pos = p_lo + p_span * float(cut["at_local"])
        if pos is None:
            pos, profile, how = find_waist(obj, axis_i, lo_w, hi_w)
        if pos is None:
            print(f"[split] SKIP {name}: 探索範囲に頂点がありません ({how})")
            report["cuts"].append({"part": name, "status": "no_verts", "how": how})
            continue

        norm_pos = (pos - gmin[axis_i]) / span[axis_i] if span[axis_i] else 0.0
        n_lo, n_hi = cut.get("names", [f"{name}_a", f"{name}_b"])

        # 正側を残したコピーと、負側を残した元、の2つに分ける
        dup = obj.copy()
        dup.data = obj.data.copy()
        bpy.context.collection.objects.link(dup)

        bisect(obj, axis_i, pos, keep_positive=False)
        bisect(dup, axis_i, pos, keep_positive=True)
        obj.name, dup.name = n_lo, n_hi
        # bound_box は依存グラフ更新まで古い値のままになる。連続切断で
        # 「切った片方の範囲」を読むため、ここで確定させる。
        bpy.context.view_layer.update()

        # 生成物も検索表へ登録する。こうしないと「切った片方をさらに切る」連続切断ができない
        # （腰+スカート一体の部品を 腰 / 左スカート / 右スカート へ分けるのに必要）。
        by_name[n_lo] = obj
        by_name[n_hi] = dup

        v_lo, v_hi = len(obj.data.vertices), len(dup.data.vertices)
        local_pos = (pos - p_lo) / p_span if p_span else 0.0
        print(f"[split] {name} axis={cut.get('axis','z')} at={norm_pos:.3f} "
              f"(部品内 {local_pos:.3f}, {how}) -> {n_lo}({v_lo}v) / {n_hi}({v_hi}v)")
        entry = {"part": name, "status": "ok", "axis": cut.get("axis", "z"),
                 "at_normalized": round(norm_pos, 4),
                 "at_local": round(local_pos, 4), "how": how,
                 "results": [{"name": n_lo, "verts": v_lo}, {"name": n_hi, "verts": v_hi}]}
        if profile:
            entry["profile_min_extent"] = min(
                (p["extent"] for p in profile if p["extent"] is not None), default=None)
        report["cuts"].append(entry)
        if v_lo == 0 or v_hi == 0:
            print(f"[split] WARNING {name}: 片側が空です。切断位置が部品の外にあります")
            entry["status"] = "empty_side"

    final = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    report["output_parts"] = len(final)
    report["part_names"] = sorted(o.name for o in final)
    print(f"[split] output parts={len(final)}")

    out_fbx.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, path_mode="COPY",
                             embed_textures=True)
    print(f"[split] exported -> {out_fbx}")

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[split] report -> {report_path}")


if __name__ == "__main__":
    main()
