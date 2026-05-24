from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="UTF-8 CSVをExcelで開きやすいUTF-8-SIG CSVへ変換")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8", newline="") as src:
        text = src.read()

    args.output.write_text(text, encoding="utf-8-sig", newline="")
    print(f"saved: {args.output}")


if __name__ == "__main__":
    main()
