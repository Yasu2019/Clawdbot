import argparse
import json

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.champion_challenger import compare_candidate
from inspection_ai.model_registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--product", default="demo_press_part")
    parser.add_argument("--minimum-accuracy", type=float, default=0.90)
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    report = compare_candidate(config, db, registry, args.product, args.version, args.minimum_accuracy)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
