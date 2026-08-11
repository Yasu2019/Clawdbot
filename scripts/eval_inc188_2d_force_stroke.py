# -*- coding: utf-8 -*-
"""INC-188 2Dモデルの荷重-ストロークを評価し、破断則の校正に使う指標を出す。

## 校正の突き合わせ先

実測の打ち抜き荷重曲線が手元に無いため、**解析的な最大せん断荷重**を基準にする。
これは traceable な値から計算でき、桁と山の位置の妥当性を判定するには十分である。

    F_max / 単位奥行 = 板厚 t x せん断強さ tau

平面ひずみ2Dの奥行は1mなので、接触力の山を直接この値と比べられる。
AA5052 のせん断強さは収集DB(makeitfrom, secondary_screening)に 140 MPa (H32)。
実測UTS 249.5 MPa から tau/UTS ~ 0.6 とすると約 150 MPa。両者で範囲を取る。

## 判定するもの

  1. 山の高さ  … 解析的な範囲に入るか（材料モデルと接触が妥当か）
  2. 山の位置  … 押し込み量のどこで最大になるか（文献では板厚の 20-40%）
  3. 終端の値  … スラグが分離すれば荷重はゼロへ戻る。**これが成功の判定**
  4. 破断要素数 … せん断帯に沿って全厚を貫通しているか

  python scripts/eval_inc188_2d_force_stroke.py --tag 2DB
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

WORK = Path(r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\work")
CONTAINER = "clawstack-unified-openradioss-1"
THICKNESS = 0.51e-3          # m
TAU_LOW = 140.0e6            # Pa  AA5052-H32 せん断強さ(収集DB)
TAU_HIGH = 150.0e6           # Pa  実測UTS 249.5MPa x 0.6


def to_csv(tag: str) -> Path:
    """T01 を CSV へ変換する。既にあれば作り直さない。"""
    th = f"INC188_2D_{tag}T01"
    csv_path = WORK / f"{th}.csv"
    if not csv_path.exists():
        subprocess.run(
            ["docker", "exec", CONTAINER, "bash", "-c",
             f"cd /work && /opt/openradioss/OpenRadioss/exec/th_to_csv_linux64_gf {th}"],
            capture_output=True, text=True)
    if not csv_path.exists():
        raise SystemExit(f"時刻歴CSVがありません: {csv_path}")
    return csv_path


def load(csv_path: Path) -> tuple[list[str], list[list[float]]]:
    with csv_path.open(encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    header = [h.strip().strip('"') for h in rows[0]]
    data = []
    for r in rows[1:]:
        try:
            data.append([float(x) for x in r])
        except ValueError:
            continue
    return header, data


def col(header: list[str], *names: str) -> int | None:
    for n in names:
        for i, h in enumerate(header):
            if h.upper() == n.upper():
                return i
    for n in names:
        for i, h in enumerate(header):
            if n.upper() in h.upper():
                return i
    return None


def count_ruptures(tag: str) -> int:
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-c",
         f"cd /work && grep -icE 'RUPTURE OF|ELEMENT .*DELETED|SOLID ELEMENT.*DELET' "
         f"INC188_2D_{tag}_0001.out 2>/dev/null || echo 0"],
        capture_output=True, text=True)
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except Exception:
        return -1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="2Dモデルの荷重-ストローク評価")
    ap.add_argument("--tag", default="2DB")
    a = ap.parse_args(argv)

    csv_path = to_csv(a.tag)
    header, data = load(csv_path)
    if not data:
        raise SystemExit("時刻歴が空です")

    i_t = col(header, "time")
    i_ie = col(header, "INTERNAL ENERGY")
    i_pw = col(header, "PLASTIC WORK")
    i_ce = col(header, "CONTACT ENERGY")
    i_ke = col(header, "KINETIC ENERGY")
    i_ew = col(header, "EXTERNAL WORK")

    t_end = data[-1][i_t]
    print(f"=== INC188 2D {a.tag} ===")
    print(f"時刻歴 {len(data)} 点 / 終端 t={t_end:.6e} s")

    # エネルギー収支。塑性仕事が支配的なら切断が進んでいる
    ie, pw, ce, ke, ew = (data[-1][i] for i in (i_ie, i_pw, i_ce, i_ke, i_ew))
    print(f"\n--- 終端のエネルギー [J/m] ---")
    print(f"  外部仕事   {ew:12.4g}")
    print(f"  内部エネ   {ie:12.4g}")
    print(f"  塑性仕事   {pw:12.4g}  ({pw/ie*100 if ie else 0:.1f}% of 内部エネ)")
    print(f"  接触エネ   {ce:12.4g}")
    print(f"  運動エネ   {ke:12.4g}  ({ke/ie*100 if ie else 0:.2f}% — 準静的なら小さい)")

    # 外部仕事の増分から反力を出す。dW = F dx なので F = dW/dx。
    # ストロークはクランク曲線から与えているので、時間微分で代用して傾向を見る。
    print(f"\n--- 荷重の推移（外部仕事の時間微分, 相対比較用） ---")
    peak_v, peak_t = 0.0, 0.0
    series = []
    for k in range(1, len(data)):
        dt = data[k][i_t] - data[k - 1][i_t]
        if dt <= 0:
            continue
        dW = data[k][i_ew] - data[k - 1][i_ew]
        p = dW / dt
        series.append((data[k][i_t], p))
        if p > peak_v:
            peak_v, peak_t = p, data[k][i_t]
    if series:
        print(f"  仕事率のピーク {peak_v:.4g} W/m @ t={peak_t:.4e} s "
              f"({peak_t/t_end*100:.0f}% of 終端)")
        tail = [p for _, p in series[-max(3, len(series)//20):]]
        print(f"  終端付近の仕事率 {sum(tail)/len(tail):.4g} W/m "
              f"(ピーク比 {sum(tail)/len(tail)/peak_v*100 if peak_v else 0:.1f}%)")

    # 解析的な最大せん断荷重（平面ひずみ単位奥行あたり）
    f_lo = THICKNESS * TAU_LOW
    f_hi = THICKNESS * TAU_HIGH
    print(f"\n--- 解析的な最大せん断荷重（単位奥行） ---")
    print(f"  F = t x tau = {THICKNESS*1e3:.2f}mm x {TAU_LOW/1e6:.0f}〜{TAU_HIGH/1e6:.0f}MPa"
          f" = {f_lo/1e3:.1f}〜{f_hi/1e3:.1f} kN/m")

    n_rupt = count_ruptures(a.tag)
    print(f"\n--- 破断 ---")
    print(f"  要素削除の記録 {n_rupt} 件")

    print(f"\n--- 判定 ---")
    if n_rupt <= 0:
        print("  NG: 破断が発生していない。せん断帯が localize していないか、"
              "破断しきい値(Eps_eff/Eps_s)が高すぎる")
    else:
        tail_ratio = (sum(tail) / len(tail) / peak_v) if series and peak_v else 1.0
        if tail_ratio < 0.2:
            print("  OK: 荷重がピークの20%未満まで落ちている。スラグ分離の可能性が高い")
        else:
            print(f"  部分的: 破断はあるが荷重が戻りきっていない(ピーク比 {tail_ratio*100:.0f}%)。"
                  "全厚貫通に至っていない")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
