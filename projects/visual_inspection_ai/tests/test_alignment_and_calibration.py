# -*- coding: utf-8 -*-
"""アライメント前段+しきい値校正の回帰テスト(unittest互換=pytestでも収集可)。"""
import glob
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inspection_ai.detection.alignment import align_translation
from inspection_ai.detection.reference_model import ReferenceDifferenceDetector, ReferenceModelTrainer
from inspection_ai.preprocessing.image_ops import apply_roi

DEMO = ROOT / "data" / "internal" / "demo_press_part"


def _make_detector(alignment="ecc"):
    recipe = yaml.safe_load((ROOT / "configs" / "products" / "demo_press_part.yaml").read_text(encoding="utf-8"))
    recipe["model"]["alignment"] = alignment
    good = sorted(glob.glob(str(DEMO / "train" / "good" / "*.png")))
    size = recipe["model"]["input_size"]
    out = Path(tempfile.mkdtemp()) / "ref.npz"
    ReferenceModelTrainer().train(good, out, (int(size[0]), int(size[1])), roi=recipe["image"].get("roi"))
    return ReferenceDifferenceDetector(out, recipe), recipe


def _score(det, recipe, path_or_img):
    img = cv2.imread(str(path_or_img)) if isinstance(path_or_img, (str, Path)) else path_or_img
    roi, offset = apply_roi(img, recipe.get("image", {}).get("roi"))
    return det.predict(roi, offset=offset)[0]


class TestAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.det, cls.recipe = _make_detector("ecc")
        cls.det_none, cls.recipe_none = _make_detector("none")
        cls.good = sorted(glob.glob(str(DEMO / "fixed_test" / "good" / "*.png")))

    def test_exact_translation_recovery(self):
        yy, xx = np.mgrid[0:120, 0:160].astype(np.float32)
        ref = 0.5 + 0.3 * np.sin(xx / 9.0) * np.cos(yy / 7.0)
        cv2.circle(ref, (80, 60), 22, 1.0, -1)
        cv2.rectangle(ref, (20, 20), (50, 45), 0.1, -1)
        M = np.float32([[1, 0, 4], [0, 1, -3]])
        shifted = cv2.warpAffine(ref, M, (160, 120), borderMode=cv2.BORDER_REPLICATE)
        aligned, dx, dy, ok = align_translation(shifted, ref)
        self.assertTrue(ok)
        self.assertAlmostEqual(dx, 4.0, delta=0.5)
        self.assertAlmostEqual(dy, -3.0, delta=0.5)
        self.assertLess(np.abs(aligned - ref)[8:-8, 8:-8].mean(), 0.01)

    def test_shift_robust_good_stays_good(self):
        img = cv2.imread(self.good[0])
        M = np.float32([[1, 0, 6], [0, 1, -5]])
        shifted = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
        base = _score(self.det, self.recipe, img).anomaly_score
        with_align = _score(self.det, self.recipe, shifted).anomaly_score
        without = _score(self.det_none, self.recipe_none, shifted).anomaly_score
        self.assertLess(with_align, base * 3 + 1e-3, "ECC補正後は良品水準に戻るべき")
        self.assertGreater(without, with_align * 5, "補正なしはズレで大幅悪化するはず")

    def test_defect_detection_preserved(self):
        bad = sorted(glob.glob(str(DEMO / "fixed_test" / "bad" / "**" / "*.png"), recursive=True))
        good_scores = [_score(self.det, self.recipe, p).anomaly_score for p in self.good]
        bad_scores = [_score(self.det, self.recipe, p).anomaly_score for p in bad]
        self.assertGreater(min(bad_scores), max(good_scores), "アライメント込みでも良/不良は分離すべき")

    def test_excessive_shift_fails_safe(self):
        ref = (np.random.RandomState(1).rand(120, 160)).astype(np.float32)
        unrelated = (np.random.RandomState(2).rand(120, 160)).astype(np.float32)
        _, dx, dy, ok = align_translation(unrelated, ref, max_shift_px=24)
        self.assertFalse(ok, "無関係画像は相関ゲートで無補正フォールバック(安全側)")


class TestCalibratedThresholds(unittest.TestCase):
    def test_recipe_thresholds_classify_demo_correctly(self):
        det, recipe = _make_detector("ecc")
        review_t = float(recipe["model"]["review_threshold"])
        ng_t = float(recipe["model"]["ng_threshold"])
        self.assertLess(review_t, ng_t)
        goods = sorted(glob.glob(str(DEMO / "fixed_test" / "good" / "*.png")))
        bads = sorted(glob.glob(str(DEMO / "fixed_test" / "bad" / "**" / "*.png"), recursive=True))
        for p in goods:
            self.assertLess(_score(det, recipe, p).anomaly_score, review_t, f"良品がREVIEW以上: {p}")
        for p in bads:
            self.assertGreaterEqual(_score(det, recipe, p).anomaly_score, ng_t, f"不良がNG未満: {p}")


class TestScaleCalibration(unittest.TestCase):
    def test_estimate_scale_known_length(self):
        from inspection_ai.measurement.calibration import estimate_scale
        img = np.zeros((100, 200, 3), np.uint8)
        cal = estimate_scale(img, (10.0, 50.0), (110.0, 50.0), 2.0, "t")
        self.assertAlmostEqual(cal.mm_per_pixel, 0.02, places=9)


if __name__ == "__main__":
    unittest.main()
