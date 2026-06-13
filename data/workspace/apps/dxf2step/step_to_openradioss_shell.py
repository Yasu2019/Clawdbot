# -*- coding: utf-8 -*-
"""STEP -> OpenRadioss /NODE + /SHELL mesh (mid-surface proxy for sheet parts)."""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA = "clawstack.step_openradioss_shell.v1"


def _require_gmsh():
    try:
        import gmsh  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("gmsh required (pip install gmsh)") from exc


def _bbox_extents(step_path: Path) -> tuple[dict[str, float], int]:
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("step_shell")
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)
        extents = [xmax - xmin, ymax - ymin, zmax - zmin]
        thin_axis = int(min(range(3), key=lambda i: extents[i]))
        return {
            "xmin": xmin,
            "ymin": ymin,
            "zmin": zmin,
            "xmax": xmax,
            "ymax": ymax,
            "zmax": zmax,
            "length": extents[0],
            "width": extents[1],
            "height": extents[2],
        }, thin_axis
    finally:
        gmsh.finalize()


def extract_shell_mesh_from_step(
    step_path: Path,
    *,
    mesh_size_mm: float | None = None,
    thin_axis: int | None = None,
    max_shells: int = 800,
) -> dict[str, Any]:
    """Tessellate STEP mid-plane faces -> nodes + quad/tri shell elements."""
    bbox, auto_thin = _bbox_extents(step_path)
    axis = thin_axis if thin_axis is not None else auto_thin
    in_plane = [bbox["length"], bbox["width"], bbox["height"]]
    in_plane = sorted([in_plane[i] for i in range(3) if i != axis])
    base_mesh = mesh_size_mm
    if base_mesh is None:
        base_mesh = max(in_plane[1] / 8.0, in_plane[0] / 24.0, 0.8)

    last: dict[str, Any] | None = None
    for factor in (1.0, 1.5, 2.0, 3.0, 5.0, 8.0):
        candidate = _extract_shell_mesh_once(
            step_path,
            mesh_size_mm=base_mesh * factor,
            thin_axis=axis,
            bbox=bbox,
        )
        last = candidate
        if int(candidate.get("shell_count") or 0) <= max_shells:
            candidate["mesh_coarsen_factor"] = factor
            return candidate
    if last is None:
        raise RuntimeError("shell mesh extraction failed")
    last["mesh_coarsen_factor"] = 8.0
    last["shell_count_capped"] = True
    return last


def _extract_shell_mesh_once(
    step_path: Path,
    *,
    mesh_size_mm: float,
    thin_axis: int,
    bbox: dict[str, float],
) -> dict[str, Any]:
    _require_gmsh()
    import gmsh

    if not step_path.exists():
        raise FileNotFoundError(step_path)

    axis = thin_axis
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("step_shell")
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()

        face_tags: list[int] = []
        for dim, tag in gmsh.model.getEntities(2):
            try:
                umin, umax, vmin, vmax = gmsh.model.getParametrizationBounds(dim, tag)
                u = 0.5 * (umin + umax)
                v = 0.5 * (vmin + vmax)
                nx, ny, nz = gmsh.model.getNormal(dim, tag, u, v)
                normal = [nx, ny, nz]
                if abs(normal[axis]) >= 0.65 and normal[axis] > 0:
                    face_tags.append(tag)
            except Exception:
                continue

        if not face_tags:
            face_tags = [tag for dim, tag in gmsh.model.getEntities(2) if dim == 2]

        gmsh.model.addPhysicalGroup(2, face_tags, name="blank_mid")
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size_mm * 0.5)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.model.mesh.generate(2)

        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        tag_to_xyz: dict[int, tuple[float, float, float]] = {}
        for i, tag in enumerate(node_tags):
            tid = int(tag)
            tag_to_xyz[tid] = (
                float(coords[3 * i]),
                float(coords[3 * i + 1]),
                float(coords[3 * i + 2]),
            )

        raw_shells: list[tuple[int, int, int, int]] = []
        elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(2)
        for etype, etags, enodes in zip(elem_types, elem_tags, elem_node_tags):
            et = int(etype)
            flat = list(enodes)
            if et == 2:
                npe = 3
            elif et == 3:
                npe = 4
            elif et == 9:
                npe = 6
            elif et == 10:
                npe = 9
            else:
                continue
            for j in range(0, len(flat), npe):
                conn = [int(flat[j + k]) for k in range(npe)]
                if et in (2, 9):
                    raw_shells.append((conn[0], conn[1], conn[2], conn[2]))
                else:
                    raw_shells.append((conn[0], conn[1], conn[2], conn[3]))

        used = sorted({n for q in raw_shells for n in q})
        old_to_new = {old: idx for idx, old in enumerate(used, start=1)}
        nodes = [(old_to_new[t], *tag_to_xyz[t]) for t in used if t in tag_to_xyz]
        shells: list[tuple[int, int, int, int, int]] = []
        for eid, (n1, n2, n3, n4) in enumerate(raw_shells, start=1):
            shells.append(
                (
                    eid,
                    old_to_new[n1],
                    old_to_new[n2],
                    old_to_new[n3],
                    old_to_new.get(n4, old_to_new[n3]),
                )
            )

        mesh = {
            "schema": SCHEMA,
            "step_path": str(step_path),
            "bbox_mm": bbox,
            "thin_axis": axis,
            "mesh_size_mm": mesh_size_mm,
            "node_count": len(nodes),
            "shell_count": len(shells),
            "nodes": nodes,
            "shells": shells,
        }
        return _sanitize_and_orient_mesh(mesh)
    finally:
        gmsh.finalize()


def _tri_area(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> float:
    ax, ay, az = a
    bx, by, bz = b
    cx, cy, cz = c
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    cxp = uy * vz - uz * vy
    cyp = uz * vx - ux * vz
    czp = ux * vy - uy * vx
    return 0.5 * math.sqrt(cxp * cxp + cyp * cyp + czp * czp)


def _shell_corners(n1: int, n2: int, n3: int, n4: int) -> list[int]:
    if n4 == 0 or n4 == n3:
        return [n1, n2, n3]
    return [n1, n2, n3, n4]


def _sanitize_and_orient_mesh(mesh: dict[str, Any]) -> dict[str, Any]:
    """Drop degenerate shells; map mid-plane to y=0 (OpenRadioss press template)."""
    nodes = list(mesh.get("nodes") or [])
    shells_in = list(mesh.get("shells") or [])
    thin_axis = int(mesh.get("thin_axis") or 1)
    if not nodes or not shells_in:
        return mesh

    remapped: list[tuple[int, float, float, float]] = []
    node_map: dict[int, tuple[float, float, float]] = {}
    for nid, x, y, z in nodes:
        coords = [x, y, z]
        if thin_axis == 0:
            nx, ny, nz = coords[1], 0.0, coords[2]
        elif thin_axis == 2:
            nx, ny, nz = coords[0], 0.0, coords[1]
        else:
            nx, ny, nz = coords[0], 0.0, coords[2]
        remapped.append((nid, nx, ny, nz))
        node_map[nid] = (nx, ny, nz)

    xs = [c[0] for c in node_map.values()]
    zs = [c[2] for c in node_map.values()]
    min_x, min_z = min(xs), min(zs)
    remapped = [(nid, x - min_x, y, z - min_z) for nid, x, y, z in remapped]
    node_map = {nid: (x, y, z) for nid, x, y, z in remapped}

    remapped, node_map, shells_in = _merge_coincident_nodes(remapped, shells_in, tol_mm=0.05)

    clean_shells: list[tuple[int, int, int, int, int]] = []
    next_eid = 1
    dropped = 0
    for _eid, n1, n2, n3, n4 in shells_in:
        corners = _shell_corners(n1, n2, n3, n4)
        if len(set(corners)) < len(corners):
            dropped += 1
            continue
        pts = [node_map[c] for c in corners]
        n1, n2, n3, n4 = _orient_shell_nodes(n1, n2, n3, n4, node_map)
        corners = _shell_corners(n1, n2, n3, n4)
        if len(set(corners)) < len(corners):
            dropped += 1
            continue
        pts = [node_map[c] for c in corners]
        if len(corners) == 3:
            area = _tri_area(pts[0], pts[1], pts[2])
            n4_out = n3
        else:
            edges = [
                _dist3(pts[0], pts[1]),
                _dist3(pts[1], pts[2]),
                _dist3(pts[2], pts[3]),
                _dist3(pts[3], pts[0]),
            ]
            if min(edges) <= 0.25:
                dropped += 1
                continue
            n4_out = n4
            area = _tri_area(pts[0], pts[1], pts[2]) + _tri_area(pts[0], pts[2], pts[3])
        if area <= 1e-6:
            dropped += 1
            continue
        clean_shells.append((next_eid, n1, n2, n3, n4_out))
        next_eid += 1

    mesh["nodes"] = remapped
    mesh["shells"] = clean_shells
    mesh["node_count"] = len(remapped)
    mesh["shell_count"] = len(clean_shells)
    mesh["shells_dropped"] = dropped
    mesh["oriented_to_y_midplane"] = True
    return mesh


def _dist3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _signed_area_xz(pts: list[tuple[float, float, float]]) -> float:
    signed = 0.0
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i][0], pts[i][2]
        x2, z2 = pts[(i + 1) % n][0], pts[(i + 1) % n][2]
        signed += x1 * z2 - x2 * z1
    return signed * 0.5


def _normal_y(p1: tuple[float, float, float], p2: tuple[float, float, float], p3: tuple[float, float, float]) -> float:
    ux, _, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    vx, _, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
    return ux * vz - uz * vx


def _orient_shell_nodes(
    n1: int,
    n2: int,
    n3: int,
    n4: int,
    node_map: dict[int, tuple[float, float, float]],
) -> tuple[int, int, int, int]:
    """Ensure +Y normal (OpenRadioss press blank mid-plane convention)."""
    tri = n4 == 0 or n4 == n3
    if not tri:
        ny1 = _normal_y(node_map[n1], node_map[n2], node_map[n3])
        ny2 = _normal_y(node_map[n1], node_map[n3], node_map[n4])
        if ny1 * ny2 <= 0:
            ordered = _order_convex_quad([n1, n2, n3, n4], node_map)
            n1, n2, n3, n4 = ordered[0], ordered[1], ordered[2], ordered[3]
    ny = _normal_y(node_map[n1], node_map[n2], node_map[n3])
    if ny >= 0:
        return n1, n2, n3, n4
    if tri:
        return n1, n3, n2, n3
    return n1, n4, n3, n2


def _order_convex_quad(nids: list[int], node_map: dict[int, tuple[float, float, float]]) -> list[int]:
    cx = sum(node_map[n][0] for n in nids) / len(nids)
    cz = sum(node_map[n][2] for n in nids) / len(nids)
    ordered = sorted(nids, key=lambda n: math.atan2(node_map[n][2] - cz, node_map[n][0] - cx))
    ny = _normal_y(node_map[ordered[0]], node_map[ordered[1]], node_map[ordered[2]])
    if ny < 0:
        ordered.reverse()
    return ordered


def _merge_coincident_nodes(
    nodes: list[tuple[int, float, float, float]],
    shells: list[tuple[int, int, int, int, int]],
    *,
    tol_mm: float,
) -> tuple[list[tuple[int, float, float, float]], dict[int, tuple[float, float, float]], list[tuple[int, int, int, int, int]]]:
    """Merge nodes closer than tol_mm; reindex shells."""
    parent = {nid: nid for nid, _, _, _ in nodes}

    def find(nid: int) -> int:
        while parent[nid] != nid:
            parent[nid] = parent[parent[nid]]
            nid = parent[nid]
        return nid

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    coords = {nid: (x, y, z) for nid, x, y, z in nodes}
    nids = [nid for nid, _, _, _ in nodes]
    for i, a in enumerate(nids):
        for b in nids[i + 1 :]:
            if _dist3(coords[a], coords[b]) <= tol_mm:
                union(a, b)

    groups: dict[int, list[int]] = {}
    for nid in nids:
        groups.setdefault(find(nid), []).append(nid)

    old_to_new: dict[int, int] = {}
    new_nodes: list[tuple[int, float, float, float]] = []
    for new_id, (_root, members) in enumerate(sorted(groups.items(), key=lambda kv: min(kv[1])), start=1):
        xs = [coords[m][0] for m in members]
        ys = [coords[m][1] for m in members]
        zs = [coords[m][2] for m in members]
        cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
        new_nodes.append((new_id, cx, cy, cz))
        for m in members:
            old_to_new[m] = new_id

    new_shells: list[tuple[int, int, int, int, int]] = []
    for eid, n1, n2, n3, n4 in shells:
        new_shells.append(
            (
                eid,
                old_to_new[n1],
                old_to_new[n2],
                old_to_new[n3],
                old_to_new.get(n4, old_to_new[n3]),
            )
        )
    node_map = {nid: (x, y, z) for nid, x, y, z in new_nodes}
    return new_nodes, node_map, new_shells


def _format_node(nid: int, x: float, y: float, z: float) -> str:
    """Match press_blanking template: I8 + 3x E12.2 coords."""
    return f"{nid:8d}{x:12.2f}{y:12.2f}{z:12.2f}"


def _format_shell_line(eid: int, n1: int, n2: int, n3: int, n4: int, *, skew_id: int = 1) -> str:
    """Match template /SHELL: six I10 fields (eid, skew, n1..n4)."""
    n4_out = 0 if n4 == n3 else n4
    return f"{eid:10d}{skew_id:10d}{n1:10d}{n2:10d}{n3:10d}{n4_out:10d}"


def _format_grnod_line(nid: int) -> str:
    return f"{int(nid):8d}"


def _patch_prop_shell_thickness(content: str, thickness_mm: float) -> str:
    """Update /PROP/SHELL hm + Thick lines preserving template fixed-width layout."""
    hm_old = (
        "              0.010               0.010               0.010               0.010               0.010"
    )
    hm_new = (
        f"              {thickness_mm:.3f}               {thickness_mm:.3f}"
        f"               {thickness_mm:.3f}               {thickness_mm:.3f}"
        f"               {thickness_mm:.3f}"
    )
    if hm_old in content:
        content = content.replace(hm_old, hm_new, 1)
    thick_old = "         5                         1.2                   0                   2         1"
    thick_new = (
        f"         5                         {thickness_mm:.1f}                   0                   2         1"
    )
    if thick_old in content:
        content = content.replace(thick_old, thick_new, 1)
    return content


def _boundary_node_groups(nodes: list[tuple[int, float, float, float]]) -> dict[str, list[int]]:
    if not nodes:
        return {"left": [], "right": [], "punch": []}
    xs = [x for _, x, _, _ in nodes]
    zs = [z for _, _, _, z in nodes]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    span_x = max(max_x - min_x, 1e-6)
    span_z = max(max_z - min_z, 1e-6)
    tol_x = span_x * 0.02
    tol_z = span_z * 0.05
    mid_x = 0.5 * (min_x + max_x)
    left = [n for n, x, _, _ in nodes if abs(x - min_x) <= tol_x]
    right = [n for n, x, _, _ in nodes if abs(x - max_x) <= tol_x]
    punch = [
        n
        for n, x, _, z in nodes
        if abs(z - max_z) <= tol_z and abs(x - mid_x) <= span_x * 0.2
    ]
    if len(punch) < 2:
        punch = sorted(
            [n for n, _, _, z in nodes if abs(z - max_z) <= tol_z],
            key=lambda nid: next(x for nn, x, _, _ in nodes if nn == nid),
        )[: max(2, len(punch))]
    return {"left": left[:8], "right": right[:8], "punch": punch[:8]}


def _rewrite_grnod_blocks(content: str, groups: dict[str, list[int]]) -> str:
    def _block(grnod_id: int, title: str, nids: list[int]) -> str:
        lines = [f"/GRNOD/NODE/{grnod_id}", title] + [_format_grnod_line(n) for n in nids[:20]]
        return "\n".join(lines) + "\n"

    if groups.get("left"):
        content = re.sub(
            r"(?m)^/GRNOD/NODE/101\n.*?(?=^/GRNOD|^/BCS|^/FUNCT|^/IMPDISP|^/CNTACT|^/END|\Z)",
            _block(101, "clamp_left_nodes", groups["left"]),
            content,
            count=1,
            flags=re.DOTALL,
        )
    if groups.get("right"):
        content = re.sub(
            r"(?m)^/GRNOD/NODE/102\n.*?(?=^/GRNOD|^/BCS|^/FUNCT|^/IMPDISP|^/CNTACT|^/END|\Z)",
            _block(102, "clamp_right_nodes", groups["right"]),
            content,
            count=1,
            flags=re.DOTALL,
        )
    if groups.get("punch"):
        content = re.sub(
            r"(?m)^/GRNOD/NODE/103\n.*?(?=^/GRNOD|^/BCS|^/FUNCT|^/IMPDISP|^/CNTACT|^/END|\Z)",
            _block(103, "punch_contact_nodes", groups["punch"]),
            content,
            count=1,
            flags=re.DOTALL,
        )
    return content


def inject_contact_for_step_shell(
    content: str,
    mesh: dict[str, Any],
    *,
    friction_mu: float = 0.08,
) -> tuple[str, dict[str, Any]]:
    """Optional TYPE7 contact (press template uses IMPDISP; default off)."""
    if os.environ.get("OPENRADIOSS_STEP_SHELL_CONTACT", "0").strip() not in {"1", "true", "True"}:
        return content, {"contact_injected": False, "reason": "impdisp_template_default"}
    if re.search(r"(?m)^/(CNTACT|INTER)/", content):
        return content, {"contact_injected": False, "reason": "existing_contact"}
    nodes = mesh.get("nodes") or []
    groups = _boundary_node_groups(nodes)
    punch = groups.get("punch") or []
    if len(punch) < 2:
        return content, {"contact_injected": False, "reason": "punch_nodes_insufficient"}
    block = (
        "/CNTACT/TYPE7/2\n"
        "Contact_PunchSheet_STEP\n"
        f"#  surf_id1 surf_id2      mu\n"
        f"         2         0{friction_mu:10.4f}\n"
        "$ STEP shell: part 2 sheet vs rigid punch via GRNOD 103 IMPDISP\n"
    )
    content = re.sub(r"(?m)^/END\s*$", block + "/END\n", content, count=1)
    return content, {
        "contact_injected": True,
        "contact_type": "TYPE7/2",
        "friction_mu": friction_mu,
        "punch_nodes": punch[:8],
    }


def inject_shell_mesh_into_rad(
    rad_content: str,
    mesh: dict[str, Any],
    *,
    part_id: int = 2,
    thickness_mm: float,
) -> tuple[str, dict[str, Any]]:
    """Replace /NODE and /SHELL/{part_id} blocks; update shell thickness in /PROP/SHELL."""
    nodes = mesh.get("nodes") or []
    shells = mesh.get("shells") or []
    if not nodes or not shells:
        raise ValueError("empty shell mesh")

    node_block = "/NODE\n" + "\n".join(_format_node(n, x, y, z) for n, x, y, z in nodes) + "\n"
    shell_lines = [f"/SHELL/{part_id}"] + [
        _format_shell_line(eid, n1, n2, n3, n4) for eid, n1, n2, n3, n4 in shells
    ]
    shell_block = "\n".join(shell_lines) + "\n"

    content = re.sub(r"(?m)^/NODE\n.*?(?=^/SHELL)", node_block, rad_content, count=1, flags=re.DOTALL)
    content = re.sub(
        rf"(?m)^/SHELL/{part_id}\n.*?(?=^/GRNOD|^/BCS|^/FUNCT|^/IMPDISP|^/CNTACT|^/END|\Z)",
        shell_block,
        content,
        count=1,
        flags=re.DOTALL,
    )

    groups = _boundary_node_groups(nodes)
    content = _rewrite_grnod_blocks(content, groups)
    content, contact_meta = inject_contact_for_step_shell(content, mesh)
    content = _patch_prop_shell_thickness(content, thickness_mm)

    meta = {
        "schema": SCHEMA,
        "part_id": part_id,
        "thickness_mm": thickness_mm,
        "node_count": len(nodes),
        "shell_count": len(shells),
        "step_path": mesh.get("step_path"),
        "bbox_mm": mesh.get("bbox_mm"),
        "contact": contact_meta,
        "note": "STEP mid-plane shell mesh injected into press template",
    }
    return content, meta


def validate_shell_rad_references(content: str, *, part_id: int = 2) -> tuple[bool, list[str]]:
    issues: list[str] = []
    node_section = re.search(r"(?m)^/NODE\n(.*?)(?=^/SHELL)", content, re.DOTALL)
    if not node_section:
        return False, ["missing_node_block"]
    node_ids = {
        int(m.group(1))
        for m in re.finditer(r"(?m)^\s*(\d+)\s+[-0-9.]", node_section.group(1))
    }
    if not node_ids:
        return False, ["no_nodes"]
    max_nid = max(node_ids)
    shell_section = re.search(rf"(?m)^/SHELL/{part_id}\n(.*?)(?=^/GRNOD|^/BCS|^/FUNCT|^/IMPDISP|^/CNTACT|^/END|\Z)", content, re.DOTALL)
    if not shell_section:
        return False, ["missing_shell_block"]
    for line in shell_section.group(1).splitlines():
        line = line.rstrip()
        if not line.strip() or line.startswith("$") or line.startswith("#"):
            continue
        if len(line) < 60:
            issues.append(f"shell_line_short:{len(line)}")
            continue
        fields = [line[i : i + 10] for i in range(0, 60, 10)]
        try:
            refs = [int(fields[i]) for i in (2, 3, 4, 5)]
        except ValueError:
            issues.append(f"shell_parse_fail:{line[:40]}")
            continue
        for ref in refs:
            if ref != 0 and ref not in node_ids:
                issues.append(f"undefined_node:{ref}")
    return len(issues) == 0, issues[:20]


def starter_preflight_rad(
    rad_content: str,
    *,
    run_dir: Path,
    input_file: str,
    docker_exe: str,
    docker_image: str,
    timeout_sec: int = 120,
) -> tuple[bool, str]:
    """Run OpenRadioss starter only; return (ok, log snippet)."""
    import subprocess

    run_dir.mkdir(parents=True, exist_ok=True)
    dest = run_dir / input_file
    dest.write_bytes(rad_content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))
    mount = str(run_dir.resolve()).replace("\\", "/").replace("D:", "/d").replace("d:", "/d")
    cmd = [
        docker_exe,
        "run",
        "--rm",
        "-v",
        f"{mount}:/workspace",
        "-w",
        "/workspace",
        docker_image,
        "bash",
        "-c",
        f"starter_linux64_gf -i {input_file} -nthread 2 2>&1",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False, "starter_preflight_timeout"
    except OSError as exc:
        return False, str(exc)
    out = (result.stdout or "") + (result.stderr or "")
    bad = (
        "INPUT ERROR" in out
        or "UNDEFINED NODE" in out
        or "ERROR IN SHELL DEFINITION" in out
        or "ERROR TERMINATION" in out
    )
    ok = not bad and result.returncode in (0, 3)
    return ok, out[-2000:]


def _remove_shell_element(content: str, *, part_id: int, shell_eid: int) -> str:
    pattern = rf"(?m)^\s*{int(shell_eid):10d}\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*\r?\n"
    return re.sub(pattern, "", content, count=1)


def starter_prune_invalid_shells(
    rad_content: str,
    *,
    part_id: int,
    run_dir: Path,
    input_file: str,
    docker_exe: str,
    docker_image: str,
    max_drop: int = 8,
) -> tuple[str, bool, list[int]]:
    """Drop failing /SHELL rows reported by starter until pass or max_drop."""
    content = rad_content
    dropped: list[int] = []
    for _ in range(max_drop):
        ok, log = starter_preflight_rad(
            content,
            run_dir=run_dir / f"prune_{len(dropped)}",
            input_file=input_file,
            docker_exe=docker_exe,
            docker_image=docker_image,
        )
        if ok:
            return content, True, dropped
        match = re.search(r"SHELL ID=\s*(\d+)", log)
        if not match:
            break
        shell_eid = int(match.group(1))
        if shell_eid in dropped:
            break
        content = _remove_shell_element(content, part_id=part_id, shell_eid=shell_eid)
        dropped.append(shell_eid)
    return content, False, dropped


def resolve_step_from_manifest(manifest: dict[str, Any], manifest_path: Path | None) -> Path | None:
    step_raw = manifest.get("step_path") or (
        (manifest.get("physics_handoff") or {}).get("moldflow") or {}
    ).get("step_path")
    if not step_raw:
        return None
    candidates: list[Path] = []
    step_p = Path(str(step_raw))
    if step_p.is_absolute() and step_p.exists():
        return step_p
    if manifest_path is not None:
        base = manifest_path.parent
        candidates.append(base / step_p.name)
        candidates.append(base / "combined.step")
        fcstd = manifest.get("fcstd_path")
        if fcstd:
            candidates.append(base / Path(str(fcstd)).with_suffix(".step").name)
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def apply_step_shell_deck(
    rad_content: str,
    manifest: dict[str, Any],
    manifest_path: Path | None,
    category: str,
    *,
    mesh_size_mm: float | None = None,
) -> tuple[str, dict[str, Any] | None]:
    if category not in ("press_blanking", "press_blanking_stripper", "press_bending"):
        return rad_content, None
    step_path = resolve_step_from_manifest(manifest, manifest_path)
    if step_path is None:
        return rad_content, None
    thickness = float(
        manifest.get("sheet_thickness_mm")
        or (manifest.get("physics_handoff") or {}).get("openradioss", {}).get("thickness_mm")
        or 1.2
    )
    mesh = extract_shell_mesh_from_step(step_path, mesh_size_mm=mesh_size_mm)
    part_id = 2 if category.startswith("press_blank") else 1
    content, meta = inject_shell_mesh_into_rad(
        rad_content, mesh, part_id=part_id, thickness_mm=thickness
    )
    meta["geometry_source"] = "step_shell"
    meta["category"] = category
    return content, meta


def write_step_shell_meta(run_dir: Path, meta: dict[str, Any]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "step_shell_deck_meta.json"
    slim = {k: v for k, v in meta.items() if k not in ("nodes", "shells")}
    out.write_text(json.dumps(slim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
