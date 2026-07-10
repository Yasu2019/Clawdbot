import csv
import importlib.metadata
from pathlib import Path

import _bootstrap


def main() -> None:
    output = _bootstrap.ROOT / "data/reports/installed_dependencies.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        rows.append({
            "name": dist.metadata.get("Name", ""),
            "version": dist.version,
            "license": dist.metadata.get("License", ""),
            "homepage": dist.metadata.get("Home-page", ""),
        })
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "version", "license", "homepage"])
        writer.writeheader()
        writer.writerows(rows)
    print(output)


if __name__ == "__main__":
    main()
