import argparse
import shutil
from pathlib import Path

import _bootstrap
from inspection_ai.utils import compact_timestamp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="backups")
    args = parser.parse_args()
    target = _bootstrap.ROOT / args.output / f"inspection_backup_{compact_timestamp()}"
    target.mkdir(parents=True, exist_ok=True)
    for rel in ["configs", "models", "data/inspection.db", "data/inspection.db-wal", "data/inspection.db-shm"]:
        src = _bootstrap.ROOT / rel
        if not src.exists():
            continue
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    archive = shutil.make_archive(str(target), "zip", root_dir=target)
    shutil.rmtree(target)
    print(archive)


if __name__ == "__main__":
    main()
