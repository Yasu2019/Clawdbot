import argparse
import json
import subprocess
import sys

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.utils import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    checks = {}
    champion = registry.get_champion("demo_press_part")
    checks["champion_exists"] = bool(champion)
    if champion:
        model_path = config.paths.root / champion["path"]
        checks["champion_file_exists"] = model_path.exists()
        checks["champion_hash_matches"] = model_path.exists() and sha256_file(model_path) == champion["sha256"]
    required = ["README.md", "configs/app.yaml", "ui/index.html", "scripts/run_api.py"]
    checks["required_files"] = {name: (config.paths.root / name).exists() for name in required}
    if not args.skip_tests:
        completed = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=config.paths.root, capture_output=True, text=True)
        checks["pytest_returncode"] = completed.returncode
        checks["pytest_output"] = (completed.stdout + completed.stderr).strip()
    checks["passed"] = all(v for k, v in checks.items() if isinstance(v, bool)) and checks.get("pytest_returncode", 0) == 0
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    raise SystemExit(0 if checks["passed"] else 1)


if __name__ == "__main__":
    main()
