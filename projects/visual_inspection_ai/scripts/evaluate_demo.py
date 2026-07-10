import argparse
import json

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.evaluation import evaluate_labeled_paths
from inspection_ai.model_registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="demo_press_part")
    parser.add_argument("--version")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    row = db.query_one("SELECT * FROM models WHERE version=?", (args.version,)) if args.version else registry.get_champion(args.product)
    if not row:
        raise SystemExit("モデルがありません")
    base = config.paths.root / "data/internal" / args.product / "fixed_test"
    labeled = [(path, "OK") for path in (base / "good").glob("*.png")]
    labeled += [(path, "NG") for path in (base / "bad").glob("**/*.png")]
    metrics = evaluate_labeled_paths(config.paths.root / row["path"], config.recipe(args.product), labeled)
    print(json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
