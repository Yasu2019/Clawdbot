import argparse

import _bootstrap
from inspection_ai.datasets.governance import load_registry, safe_download


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_id")
    args = parser.parse_args()
    records = load_registry(_bootstrap.ROOT / "configs/datasets/registry.yaml")
    record = next((item for item in records if item.get("id") == args.dataset_id), None)
    if not record:
        raise SystemExit("台帳にありません")
    output = safe_download(record, _bootstrap.ROOT / "data/external/approved" / args.dataset_id)
    print(output)


if __name__ == "__main__":
    main()
