import argparse

import _bootstrap
from inspection_ai.detection.anomalib_adapter import build_anomalib_train_command, run_checked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Patchcore")
    parser.add_argument("--data-root", default="data/anomalib/demo_press_part")
    parser.add_argument("--category", default="demo_press_part")
    parser.add_argument("--output", default="models/anomalib_runs")
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()
    command = build_anomalib_train_command(
        args.model,
        _bootstrap.ROOT / args.data_root,
        args.category,
        _bootstrap.ROOT / args.output,
    )
    print(" ".join(command))
    if not args.print_only:
        run_checked(command)


if __name__ == "__main__":
    main()
