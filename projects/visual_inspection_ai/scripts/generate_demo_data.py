from __future__ import annotations

import argparse
import random

import cv2
import numpy as np

import _bootstrap

ROOT = _bootstrap.ROOT


def base_image(seed: int, shift: int = 0) -> np.ndarray:
    background = 19 + (seed % 3)
    surface = 203 + (seed % 5)
    image = np.full((480, 640, 3), background, np.uint8)
    x1, y1, x2, y2 = 100 + shift, 100, 540 + shift, 390
    cv2.rectangle(image, (x1, y1), (x2, y2), (surface, surface, surface), -1)
    cv2.circle(image, (320 + shift, 245), 40, (background, background, background), -1)
    # 圧縮可能な穏やかな照明むら。実画像のばらつきとは別物です。
    cv2.line(image, (105, 180), (535, 180), (surface - 1, surface - 1, surface - 1), 1)
    return image


def add_defect(image: np.ndarray, kind: str, seed: int) -> np.ndarray:
    rng = random.Random(seed)
    out = image.copy()
    if kind == "scratch":
        x, y = rng.randint(180, 430), rng.randint(150, 320)
        cv2.line(out, (x, y), (x + rng.randint(45, 100), y + rng.randint(-8, 8)), (35, 35, 35), rng.randint(2, 5))
    elif kind == "dent":
        center = (rng.randint(210, 430), rng.randint(160, 330))
        axes = (rng.randint(12, 25), rng.randint(8, 18))
        cv2.ellipse(out, center, axes, 0, 0, 360, (90, 90, 90), -1)
    elif kind == "burr":
        x = rng.randint(180, 470)
        points = np.array([[x, 100], [x + 15, 100], [x + 8, 75]], np.int32)
        cv2.fillPoly(out, [points], (205, 205, 205))
    elif kind == "stain":
        overlay = out.copy()
        cv2.circle(overlay, (rng.randint(200, 440), rng.randint(160, 325)), rng.randint(18, 38), (110, 105, 90), -1)
        cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)
    elif kind == "short_shot":
        cv2.rectangle(out, (470, 100), (540, 175), (20, 20, 20), -1)
    return out


def save_many(directory, count: int, prefix: str, kind: str | None = None, start: int = 0) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(start, start + count):
        image = base_image(index)
        if kind:
            image = add_defect(image, kind, index)
        cv2.imwrite(str(directory / f"{prefix}_{index:04d}.png"), image)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal", type=int, default=60)
    parser.add_argument("--defect", type=int, default=12)
    args = parser.parse_args()
    base = ROOT / "data/internal/demo_press_part"
    save_many(base / "train/good", args.normal, "normal")
    save_many(base / "fixed_test/good", 10, "normal_test", start=1000)
    kinds = ["scratch", "dent", "burr", "stain", "short_shot"]
    for group, kind in enumerate(kinds):
        save_many(base / "fixed_test/bad" / kind, args.defect, kind, kind, start=2000 + group * 100)
    upload = ROOT / "data/demo/upload_samples"
    save_many(upload, 3, "normal")
    for group, kind in enumerate(kinds):
        save_many(upload, 2, kind, kind, start=4000 + group * 10)
    print(f"Generated demo data under {base}")


if __name__ == "__main__":
    main()
