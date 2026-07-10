import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.reference_training import train_reference_challenger
from inspection_ai.model_registry import ModelRegistry


def main() -> None:
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    if not registry.get_champion("demo_press_part"):
        print(train_reference_challenger(config, db, registry, "demo_press_part", promote=True, approved_by="bootstrap"))
    else:
        print("Champion already exists")


if __name__ == "__main__":
    main()
