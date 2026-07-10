import argparse
import json

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.reference_training import train_reference_challenger
from inspection_ai.model_registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="demo_press_part")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--approved-by", default="local_user")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    result = train_reference_challenger(config, db, registry, args.product, args.promote, args.approved_by)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
