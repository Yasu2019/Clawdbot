# -*- coding: utf-8 -*-
"""Read-only structural audit for an OpenRadioss block-format starter deck."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
import re
from pathlib import Path


KEYWORD = re.compile(r"^/([A-Z0-9_]+)(?:/[^\s]+)?")


def audit(path: Path, rupture_log: Path | None = None) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    nodes: dict[int, tuple[float, float, float]] = {}
    part_nodes: dict[int, set[int]] = {}
    element_counts: dict[int, dict[str, int]] = {}
    element_nodes: dict[int, tuple[int, ...]] = {}
    tetra_by_part: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    block = ""
    block_id = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("/"):
            pieces = stripped.split("/")
            block = pieces[1].upper() if len(pieces) > 1 else ""
            block_id = int(pieces[2]) if len(pieces) > 2 and pieces[2].isdigit() else 0
            continue
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        if block == "NODE" and len(tokens) >= 4:
            try:
                nodes[int(tokens[0])] = tuple(float(v) for v in tokens[1:4])
            except ValueError:
                pass
        elif block in {"TETRA4", "BRICK", "SH3N", "SHELL"} and len(tokens) >= 4:
            try:
                ordered_node_ids = tuple(int(v) for v in tokens[1:])
                node_ids = set(ordered_node_ids)
                element_id = int(tokens[0])
            except ValueError:
                continue
            if block in {"TETRA4", "BRICK"}:
                element_nodes[element_id] = ordered_node_ids
            if block == "TETRA4" and len(ordered_node_ids) == 4:
                tetra_by_part.setdefault(block_id, []).append((element_id, ordered_node_ids))
            part_nodes.setdefault(block_id, set()).update(node_ids)
            counts = element_counts.setdefault(block_id, {})
            counts[block] = counts.get(block, 0) + 1

    parts: dict[str, object] = {}
    for part_id, node_ids in sorted(part_nodes.items()):
        coords = [nodes[n] for n in node_ids if n in nodes]
        if not coords:
            continue
        mins = [min(p[axis] for p in coords) for axis in range(3)]
        maxs = [max(p[axis] for p in coords) for axis in range(3)]
        parts[str(part_id)] = {
            "nodes": len(coords),
            "elements": element_counts.get(part_id, {}),
            "bbox_min_m": mins,
            "bbox_max_m": maxs,
            "size_m": [maxs[i] - mins[i] for i in range(3)],
        }
        qualities: list[float] = []
        min_edges: list[float] = []
        volumes: list[float] = []
        worst_id = None
        worst_quality = float("inf")
        for element_id, tetra_nodes in tetra_by_part.get(part_id, []):
            if any(node_id not in nodes for node_id in tetra_nodes):
                continue
            p0, p1, p2, p3 = (nodes[node_id] for node_id in tetra_nodes)
            vectors = tuple(tuple(point[a] - p0[a] for a in range(3)) for point in (p1, p2, p3))
            cross = (
                vectors[1][1] * vectors[2][2] - vectors[1][2] * vectors[2][1],
                vectors[1][2] * vectors[2][0] - vectors[1][0] * vectors[2][2],
                vectors[1][0] * vectors[2][1] - vectors[1][1] * vectors[2][0],
            )
            volume = abs(sum(vectors[0][a] * cross[a] for a in range(3))) / 6.0
            points = (p0, p1, p2, p3)
            edge_sq = [
                sum((points[i][a] - points[j][a]) ** 2 for a in range(3))
                for i in range(4) for j in range(i + 1, 4)
            ]
            edge_sum = sum(edge_sq)
            quality = 12.0 * (3.0 * volume) ** (2.0 / 3.0) / edge_sum if edge_sum else 0.0
            qualities.append(quality)
            min_edges.append(math.sqrt(min(edge_sq)))
            volumes.append(volume)
            if quality < worst_quality:
                worst_quality, worst_id = quality, element_id
        if qualities:
            parts[str(part_id)]["tetra_quality"] = {
                "min_mean_ratio": min(qualities),
                "mean_mean_ratio": sum(qualities) / len(qualities),
                "below_0_1": sum(value < 0.1 for value in qualities),
                "min_edge_m": min(min_edges),
                "min_volume_m3": min(volumes),
                "total_volume_m3": sum(volumes),
                "bbox_fill_ratio": sum(volumes) / math.prod(maxs[i] - mins[i] for i in range(3)),
                "worst_element_id": worst_id,
            }

    result: dict[str, object] = {"deck": str(path), "node_count": len(nodes), "parts": parts}
    if rupture_log:
        log_text = rupture_log.read_text(encoding="utf-8", errors="replace")
        rupture_sequence = [
            (int(element_id), float(time_s))
            for element_id, time_s in re.findall(
                r"RUPTURE OF SOLID ELEMENT\s*:\s*(\d+)\s+AT TIME\s*:\s*([0-9.E+-]+)",
                log_text,
            )
        ]
        rupture_ids = {element_id for element_id, _ in rupture_sequence}
        centroids = []
        for element_id in rupture_ids:
            coords = [nodes[node_id] for node_id in element_nodes.get(element_id, ()) if node_id in nodes]
            if coords:
                centroids.append(tuple(sum(point[axis] for point in coords) / len(coords) for axis in range(3)))
        result["rupture"] = {
            "reported_unique": len(rupture_ids),
            "mapped": len(centroids),
            "centroid_min_m": [min(p[a] for p in centroids) for a in range(3)] if centroids else None,
            "centroid_max_m": [max(p[a] for p in centroids) for a in range(3)] if centroids else None,
        }
        if rupture_sequence:
            first_time = min(time_s for _, time_s in rupture_sequence)
            first_ids = {
                element_id for element_id, time_s in rupture_sequence
                if time_s <= first_time + 1.0e-7
            }
            first_centroids = []
            for element_id in first_ids:
                coords = [nodes[n] for n in element_nodes.get(element_id, ()) if n in nodes]
                if coords:
                    first_centroids.append(tuple(sum(p[a] for p in coords) / len(coords) for a in range(3)))
            result["rupture"]["first_time_s"] = first_time
            result["rupture"]["first_100ns_count"] = len(first_ids)
            result["rupture"]["first_100ns_centroid_min_m"] = (
                [min(p[a] for p in first_centroids) for a in range(3)] if first_centroids else None
            )
            result["rupture"]["first_100ns_centroid_max_m"] = (
                [max(p[a] for p in first_centroids) for a in range(3)] if first_centroids else None
            )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rupture-log", type=Path)
    args = parser.parse_args()
    result = audit(args.deck, args.rupture_log)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"deck={result['deck']} nodes={result['node_count']}")
        for part_id, data in result["parts"].items():
            print(
                f"part={part_id} nodes={data['nodes']} elements={data['elements']} "
                f"min={data['bbox_min_m']} max={data['bbox_max_m']} size={data['size_m']}"
            )
        if "rupture" in result:
            print(f"rupture={result['rupture']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
