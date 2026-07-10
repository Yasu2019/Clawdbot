# -*- coding: utf-8 -*-
"""参照画像への並進アライメント(位置ズレ耐性の前段)。

画素単位差分は治具ズレ数pxで偽NGを量産する。ECC(並進)で基準mean画像へ
位置合わせしてから差分を取る。決定論・cv2のみ。失敗時は無補正で続行し
diagnosticsに記録する(fail-open: 位置合わせ不能はスコア上昇として現れ、
REVIEW側に倒れる=安全側)。
"""
from __future__ import annotations

import cv2
import numpy as np


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    """中央領域の正規化相互相関(誤収束検出用)。"""
    h, w = a.shape[:2]
    ay, ax = int(h * 0.1), int(w * 0.1)
    a_c = a[ay:h - ay, ax:w - ax].astype(np.float32)
    b_c = b[ay:h - ay, ax:w - ax].astype(np.float32)
    a_c = a_c - a_c.mean()
    b_c = b_c - b_c.mean()
    denom = float(np.sqrt((a_c * a_c).sum() * (b_c * b_c).sum()))
    if denom < 1e-12:
        return 0.0
    return float((a_c * b_c).sum() / denom)


def align_translation(
    image01: np.ndarray,
    reference01: np.ndarray,
    max_shift_px: float = 24.0,
    iterations: int = 60,
    eps: float = 1e-5,
    min_corr: float = 0.5,
) -> tuple[np.ndarray, float, float, bool]:
    """image01(float32 0-1)をreference01へ並進アライメント。

    戻り値: (整列済み画像, dx, dy, 成功フラグ)。次の場合は無補正で返す(安全側):
    ①ECC不収束 ②推定シフトがmax_shift_px超(大ズレ/誤収束)
    ③整列後の正規化相関がmin_corr未満(無関係画像・誤収束の検出)
    """
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, int(iterations), float(eps))
    try:
        _, warp = cv2.findTransformECC(
            reference01, image01, warp, cv2.MOTION_TRANSLATION, criteria, None, 5)
    except cv2.error:
        return image01, 0.0, 0.0, False
    dx, dy = float(warp[0, 2]), float(warp[1, 2])
    if abs(dx) > max_shift_px or abs(dy) > max_shift_px:
        return image01, dx, dy, False
    h, w = image01.shape[:2]
    aligned = cv2.warpAffine(
        image01, warp, (w, h),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE)
    if _ncc(aligned, reference01) < min_corr:
        return image01, dx, dy, False
    return aligned, dx, dy, True
