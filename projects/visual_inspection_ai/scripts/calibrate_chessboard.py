import argparse
import json
from pathlib import Path

import _bootstrap
from inspection_ai.measurement.calibration import calibrate_chessboard


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--cols", type=int, required=True, help="内側コーナー列数")
    parser.add_argument("--rows", type=int, required=True, help="内側コーナー行数")
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--output", default="configs/calibration/camera.json")
    args = parser.parse_args()
    folder = _bootstrap.ROOT / args.folder
    paths = [p for p in folder.glob("**/*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}]
    result = calibrate_chessboard(paths, (args.cols, args.rows), args.square_mm)
    output = _bootstrap.ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    print(f"RMS reprojection error={result['rms_reprojection_error']:.6f}")


if __name__ == "__main__":
    main()
