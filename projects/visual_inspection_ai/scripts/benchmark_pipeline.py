import argparse
import json
import statistics

import cv2

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.pipeline import InspectionPipeline


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", default="data/demo/upload_samples")
    parser.add_argument("--loops", type=int, default=3)
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    pipeline = InspectionPipeline(config, db, registry)
    times: list[float] = []
    paths = list((config.paths.root / args.images).glob("*.png"))
    for _ in range(args.loops):
        for path in paths:
            image = cv2.imread(str(path))
            result = pipeline.inspect_image(image, path.name, "demo_press_part")
            times.append(result.elapsed_ms["total"])
    if not times:
        raise SystemExit("画像がありません")
    print(json.dumps({
        "n": len(times),
        "p50_ms": percentile(times, 0.5),
        "p95_ms": percentile(times, 0.95),
        "max_ms": max(times),
        "mean_ms": statistics.mean(times),
    }, indent=2))


if __name__ == "__main__":
    main()
