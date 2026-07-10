import argparse
import json
import time

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.reference_training import train_reference_challenger
from inspection_ai.learning.resource_guard import may_train
from inspection_ai.model_registry import ModelRegistry


def run_once(product_id: str) -> None:
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    allowed, state, reasons = may_train(config.learning)
    print(json.dumps({"may_train": allowed, "resources": state.__dict__, "reasons": reasons}, ensure_ascii=False))
    if not allowed:
        return
    row = db.query_one(
        "SELECT COUNT(*) AS c FROM reviews r JOIN inspections i ON i.id=r.inspection_id "
        "WHERE r.status='REVIEWED' AND r.use_for_training=1 AND i.product_id=?",
        (product_id,),
    )
    pending = int(row["c"])
    if pending < int(config.learning.get("min_confirmed_total", 30)):
        print(f"確定学習候補が不足: {pending}")
        return
    print(train_reference_challenger(config, db, registry, product_id, promote=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="demo_press_part")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=3600)
    args = parser.parse_args()
    if args.once:
        run_once(args.product)
        return
    while True:
        run_once(args.product)
        time.sleep(max(3600, args.interval))


if __name__ == "__main__":
    main()
