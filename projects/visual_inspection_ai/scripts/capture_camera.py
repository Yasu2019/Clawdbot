import argparse
import time

import cv2

import _bootstrap


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--output", default="data/captured")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    output = _bootstrap.ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise SystemExit("カメラを開けません")
    try:
        for index in range(args.count):
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("撮影失敗")
            path = output / f"capture_{int(time.time() * 1000)}_{index:03d}.png"
            cv2.imwrite(str(path), frame)
            print(path)
            time.sleep(0.1)
    finally:
        camera.release()


if __name__ == "__main__":
    main()
