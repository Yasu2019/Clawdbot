import argparse
import json

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.autoencoder import train_autoencoder
from inspection_ai.learning.reference_training import collect_good_images
from inspection_ai.utils import compact_timestamp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="demo_press_part")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    paths = collect_good_images(config, db, args.product)
    output = config.paths.root / "models/work" / f"{args.product}_ae_{compact_timestamp()}.pt"
    print(json.dumps(train_autoencoder(paths, output, args.epochs, args.size), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
