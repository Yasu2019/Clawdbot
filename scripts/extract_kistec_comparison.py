# -*- coding: utf-8 -*-
"""PANEL4MM残留応力(SIGX/Y/Z)の最終フレームVTKから、KISTEC実測点(Point A-H)
近傍の応力を抽出し比較する。2026-08-23 導入。

## 前提(確認済み事項)

- KISTEC測定座標系の原点 = 丸穴中心(HOLE_CENTER, STEP座標系で(185.657,-1882.188)mm)
  (試験結果_ミツイ精密_20260630.pdf Page3の顕微鏡写真で、緑十字線が丸穴中心と
  正確に一致することを視覚確認済み)
- 元座標(Point A-H)から回転後座標への変換はKabsch法で回転角29.99°(≈30°)・
  並進≈0と数値確定済み(残差0.0005-0.0015mm)
- 写真の水平方向(応力の方向)が本モデルのグローバルX/Y軸のどちらに対応するかは
  **未確定**(4パンチの見た目角度とSTEPモデルの実角度を突き合わせる必要がある。
  自動画像処理では暗領域の検出がノイズに埋もれ確定できなかった、2026-08-23)。
  この不確定性を考慮し、本スクリプトは「原点=丸穴中心」の変換のみ適用し、
  回転角は引数で調整可能にしておく(既定0、確定次第更新する)。

## 使い方

  python scripts/extract_kistec_comparison.py --vtk PANEL4MM_XXXA0YY.vtk --rotation-deg 0
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

HOLE_CENTER_MM = (185.657, -1882.188)  # STEP座標系(グローバル), mm

# KISTEC実測(試験結果_ミツイ精密_20260630.pdf)。回転後座標(mm)・残留応力(MPa)・信頼限界(MPa)
KISTEC_POINTS = {
    "A": {"xy_rot_mm": (0.008, 1.822), "stress_mpa": 7.92, "ci_mpa": 4.48},
    "B": {"xy_rot_mm": (0.673, 1.645), "stress_mpa": 0.64, "ci_mpa": 3.01},
    "C": {"xy_rot_mm": (0.171, 0.637), "stress_mpa": -5.49, "ci_mpa": 4.34},
    "D": {"xy_rot_mm": (0.614, 0.776), "stress_mpa": -1.36, "ci_mpa": 2.79},
    "E": {"xy_rot_mm": (0.679, 0.325), "stress_mpa": 4.34, "ci_mpa": 3.72},
    "F": {"xy_rot_mm": (0.330, -0.572), "stress_mpa": 9.21, "ci_mpa": 2.88},
    "G": {"xy_rot_mm": (0.425, -1.589), "stress_mpa": 5.94, "ci_mpa": 2.52},
    "H": {"xy_rot_mm": (1.296, -1.086), "stress_mpa": -0.65, "ci_mpa": 2.56},
}


def parse_vtk(path: str):
    """POINTSと全SCALARSフィールドを読む(build_inc188系で確立した頑健パーサ)。"""
    pts = None
    fields: dict[str, np.ndarray] = {}
    n = 0
    with open(path, "r", errors="replace") as f:
        while True:
            line = f.readline()
            if not line:
                break
            t = line.split()
            if not t:
                continue
            kw = t[0]
            if kw == "POINTS":
                n = int(t[1])
                v = []
                while len(v) < 3 * n:
                    v += f.readline().split()
                pts = np.array(v[: 3 * n], dtype=float).reshape(n, 3)
            elif kw in ("POINT_DATA", "CELL_DATA"):
                n = int(t[1])
            elif kw == "SCALARS":
                name = t[1]
                f.readline()  # LOOKUP_TABLE行
                v = []
                while len(v) < n:
                    v += f.readline().split()
                fields[name] = np.array(v[:n], dtype=float)
            elif kw == "VECTORS":
                name = t[1]
                v = []
                while len(v) < 3 * n:
                    v += f.readline().split()
                fields[name] = np.array(v[: 3 * n], dtype=float).reshape(n, 3)
    return pts, fields


def kistec_point_to_model_xy_mm(xy_rot_mm: tuple[float, float], rotation_deg: float) -> tuple[float, float]:
    """KISTEC回転後座標(原点=丸穴中心)を本モデルのグローバルXY(mm)へ変換する。"""
    x, y = xy_rot_mm
    theta = np.radians(rotation_deg)
    xr = x * np.cos(theta) - y * np.sin(theta)
    yr = x * np.sin(theta) + y * np.cos(theta)
    return HOLE_CENTER_MM[0] + xr, HOLE_CENTER_MM[1] + yr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vtk", required=True)
    ap.add_argument("--rotation-deg", type=float, default=0.0,
                    help="KISTEC回転後座標系->モデルグローバル座標系への追加回転角"
                         "(写真とSTEPモデルの向き対応が未確定のため既定0)")
    ap.add_argument("--stress-component", default="SIGX", choices=["SIGX", "SIGY", "SIGZ"],
                    help="KISTECの応力の方向に対応する成分(未確定のため要検討)")
    ap.add_argument("--search-radius-mm", type=float, default=0.5,
                    help="各測定点近傍で応力を平均する探索半径[mm]")
    a = ap.parse_args()

    pts, fields = parse_vtk(a.vtk)
    if a.stress_component not in fields:
        print(f"[エラー] VTKに{a.stress_component}が含まれていません。"
              f"利用可能: {list(fields.keys())}")
        return 1
    stress = fields[a.stress_component]
    mm = pts * 1e3

    print(f"{'点':4s}{'実測[MPa]':>12s}{'信頼限界':>10s}{'予測平均[MPa]':>14s}"
          f"{'予測std':>10s}{'近傍点数':>8s}{'判定':>8s}")
    for name, d in KISTEC_POINTS.items():
        gx, gy = kistec_point_to_model_xy_mm(d["xy_rot_mm"], a.rotation_deg)
        dist = np.hypot(mm[:, 0] - gx, mm[:, 1] - gy)
        near = dist < a.search_radius_mm
        if near.sum() == 0:
            print(f"{name:4s}{d['stress_mpa']:12.2f}{d['ci_mpa']:10.2f}"
                  f"{'--- 該当点なし ---':>14s}")
            continue
        pred_mean = stress[near].mean() / 1e6  # Pa -> MPa
        pred_std = stress[near].std() / 1e6
        ok = "OK" if abs(pred_mean - d["stress_mpa"]) < d["ci_mpa"] else "NG"
        print(f"{name:4s}{d['stress_mpa']:12.2f}{d['ci_mpa']:10.2f}"
              f"{pred_mean:14.2f}{pred_std:10.2f}{near.sum():8d}{ok:>8s}")

    print("\n⚠ rotation-deg未確定のため、この結果は暫定値。"
          "写真とSTEPモデルの向き対応を確定してから正式比較すること。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
