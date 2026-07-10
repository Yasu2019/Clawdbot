import argparse
from pathlib import Path

import yaml

import _bootstrap


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("product_id")
    parser.add_argument("--name", required=True)
    parser.add_argument("--template", default="configs/products/_template.yaml")
    args = parser.parse_args()
    if not args.product_id.replace("_", "").replace("-", "").isalnum():
        raise SystemExit("product_idは英数字、_、-のみです")
    source = _bootstrap.ROOT / args.template
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["product"]["id"] = args.product_id
    data["product"]["name"] = args.name
    output = _bootstrap.ROOT / "configs/products" / f"{args.product_id}.yaml"
    if output.exists():
        raise SystemExit(f"既に存在します: {output}")
    output.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
