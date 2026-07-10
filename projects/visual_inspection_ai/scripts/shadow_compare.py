import argparse

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.champion_challenger import shadow_compare_folder
from inspection_ai.model_registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("folder")
    parser.add_argument("--product", default="demo_press_part")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    print(shadow_compare_folder(config, db, registry, args.product, args.version, config.paths.root / args.folder))


if __name__ == "__main__":
    main()
