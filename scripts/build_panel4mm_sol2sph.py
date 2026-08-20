# -*- coding: utf-8 -*-
"""PANEL4MM(実形状フル3D)へ Sol2SPH・校正済みEps_eff・引き抜き/残留応力抽出を適用する。
2026-08-20 導入。

## 背景

build_panel4mm_3d_blanking.py の PANEL4MM_P2 はパンチ下降のみ(tstop=0.6ms)・
Eps_eff=0.12(参照デックの既定値、未校正)・GENE1要素削除方式・かつ
/DT/NODA/0(dt_minが無視される既知バグ)のまま実行されていた。

INC188 slice3d での校正(C3〜SPH_085)により Eps_eff=0.85(Eps_s=1.0)が
文献帯20-40%に最も良く整合する値と判明し、また GENE1要素削除は数値発散の
リスクがあるため Sol2SPH(要素削除の代わりにSPH粒子へ変換)が確立している。
KISTEC実測X線残留応力データ(Point A-H)との比較に向け、本スクリプトで
(1)dt_minバグ修正 (2)Sol2SPH適用 (3)Eps_eff=0.85適用 (4)パンチ・ストリッパー
引き抜き+静定フェーズの追加、を行う。

## 忠実度の制約(重要・報告時に必ず明記)

PANEL4MMの要素サイズは100um(板厚方向5層)。せん断帯は文献で21-44umのため、
切断エッジ近傍の局所応力(=KISTEC測定点そのもの)を精度良く解けない可能性が
高い。ユーザー合意のうえ、まずは現行100umで実行し符号・オーダーの定性的な
傾向のみ確認する方針とした(2026-08-20)。定量一致にはメッシュ細分化が必要。

## Sol2SPH構造の確認(slice3dと同一参照デック由来のため同じフィールド配置)

PANEL4MMのBlank Part(PID=2)は tetra_prop()で Isolid=1・Iframe=1 を使用。
Sol2SPHの要件(Isolid∈{1,2,24}, Iframe∈{1,2})を既に満たすため、slice3dと
異なりIsolid変更は不要。PROP/SOLIDの3行構造(9+5+5フィールド)もslice3dと
同一のため、build_inc188_sol2sph.pyのadd_sol2sph()と同じ手順が使える。

## 引き抜き・静定フェーズの設計

/IMPDISP がFUNCT参照で変位を直接規定し、Tstop=1.0e30(無期限)のため、
FUNCT自体にデータ点を追加するだけで動作を延長できる(IMPDISP構造の変更は
不要)。パンチ(FUNCT/1)・ストリッパー(FUNCT/2)を同じタイミングで元位置へ
戻し、その後 SETTLE_T だけ保持して弾性波を減衰させる。

usage:
  python scripts/build_panel4mm_sol2sph.py --tag P3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023
sys.path.insert(0, str(Path(__file__).parent))

from build_panel4mm_3d_blanking import (  # noqa: E402
    build, i10, f20, DEFAULT_BLANK_ELEM, DEFAULT_TOOL_ELEM, DEFAULT_STROKE,
    DEFAULT_SPEED, DEFAULT_GAP_MAX, DEFAULT_STFAC, DEFAULT_NSTEP,
)

SPH_PROP_ID = 5      # 新規 /PROP/TYPE34 (既存 PROP 1,2 と衝突しない)
SPH_PART_ID = 5       # 新規 SPH パート (既存 PART 1-4 と衝突しない)
SPH_MAT_ID = 3        # ブランク材料の複製(/FAIL なし)
NDIR = 2               # 2x2x2 = 8粒子/要素
DT_MIN = 5.0e-11       # slice3d 校正と同じフロア


def add_sol2sph(starter_path: Path, ndir: int, elem: float) -> None:
    """PANEL4MM の Blank(PID=2, PROP=2)へ Sol2SPH を適用する。"""
    lines = starter_path.read_text(encoding="utf-8").splitlines()

    i = next(k for k, ln in enumerate(lines) if ln.strip() == "/PROP/SOLID/2")
    data0 = i + 3
    old = lines[data0]
    isolid = int(old[0:10])
    if isolid not in (1, 2, 24):
        lines[data0] = f"{i10(24)}" + old[10:]
    iframe_val = int(old[70:80])
    if iframe_val not in (1, 2):
        raise ValueError(f"Iframe={iframe_val} は Sol2SPH 非対応: {old!r}")
    data2 = data0 + 2
    sol2sph_line = f"{i10(ndir)}{i10(SPH_PART_ID)}{i10(0)}"
    lines.insert(data2 + 1, sol2sph_line)

    # ブランク材料(MAT_ID=2)を複製し /FAIL を外した MAT_ID=3 を作る。
    # 2026-08-18 slice3dで実証済みのバグ対策: /FAIL/GENE1/2はMAT_ID=2に紐付き、
    # SPH粒子がそのままMAT_ID=2を継承すると変換後も破断判定が再評価され続け、
    # ログが数万倍に肥大化・一部粒子が異常な位置へ飛散する。
    mat_start = next(k for k, ln in enumerate(lines) if ln.strip() == "/MAT/LAW2/2")
    j = mat_start + 1
    while not lines[j].startswith("/"):
        j += 1
    mat_data = lines[mat_start + 2:j]
    mat_dup = [f"/MAT/LAW2/{SPH_MAT_ID}", "MR536_H34_AA5052_SPH_no_fail"] + mat_data

    h = 1.5 * elem / ndir
    sph_prop = [
        f"/PROP/TYPE34/{SPH_PROP_ID}",
        "Sol2SPH_Particles",
        "#                 Mp                Beta               Alpha            Alpha_cs    Skew_ID    h_1D",
        f"{f20(0.0)}{f20(0.0)}{f20(0.0)}{f20(0.0)}{i10(0)}{f20(0.0)}",
        "#     order                   h              Xi_stab                Hmin                Hmax",
        f"{i10(0)}{f20(h)}{f20(0.3)}{f20(0.0)}{f20(0.0)}",
        "#               Hcst",
        f"{f20(0.0)}",
    ]
    sph_part = [
        f"/PART/{SPH_PART_ID}",
        "Sol2SPH_Blank_Part",
        "#    Prop_ID     Mat_ID",
        f"{i10(SPH_PROP_ID)}{i10(SPH_MAT_ID)}",
    ]

    end_idx = next(k for k, ln in enumerate(lines) if ln.strip() == "/END")
    lines = lines[:end_idx] + mat_dup + sph_prop + sph_part + lines[end_idx:]
    starter_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_eps_eff(starter_path: Path, eps_eff: float, eps_s: float) -> None:
    """/FAIL/GENE1/2 の Eps_eff・Eps_s を書き換える。

    参照デック(INC188AC_shear_coupon_0000.rad)で実測確認済みの固定オフセット:
      /FAIL/GENE1/2 の6行後: fct_IDps,Eps_dot_ps,Eps_max,Eps_eff,Eps_vol (既定0.12)
      /FAIL/GENE1/2 の8行後: Eps_min,Eps_s,fct_IDg12,fct_IDg13,fct_IDe1c (既定Eps_s=0.1)
    slice3d校正はEps_s=1.0で行っているため、参照既定値のままだと校正結果と
    一致しない。両方を明示的に書き換える。
    """
    lines = starter_path.read_text(encoding="utf-8").splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.strip() == "/FAIL/GENE1/2")
    assert "Eps_eff" in lines[i + 5], f"想定外の行: {lines[i+5]!r}"
    lines[i + 6] = f"{i10(0)}{f20(0.0)}{f20(0.0)}{f20(eps_eff)}{f20(0.0)}"
    assert "Eps_s" in lines[i + 7], f"想定外の行: {lines[i+7]!r}"
    lines[i + 8] = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
    starter_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extend_retraction(engine_path: Path, starter_path: Path, t_stop_orig: float,
                      stroke: float, retract_t: float, settle_t: float) -> float:
    """FUNCT/1(パンチ)・FUNCT/2(ストリッパー)へ引き抜き+静定の点を追加し、
    /RUN と /ANIM/DT・DM_MIN対応(CST2)を新しい tstop へ延長する。
    IMPDISP の Tstop=1e30 なので FUNCT 側にデータ点を足すだけで反映される。
    """
    lines = starter_path.read_text(encoding="utf-8").splitlines()
    t_retract_done = t_stop_orig + retract_t
    t_final = t_retract_done + settle_t

    # FUNCT/1(パンチ): 0 -> -stroke(t_stop_orig) -> 0(引き抜き完了) -> 0(静定保持)
    i1 = next(k for k, ln in enumerate(lines) if ln.strip() == "/FUNCT/1")
    d1 = i1 + 3
    j1 = d1
    while j1 < len(lines) and not lines[j1].startswith("/"):
        j1 += 1
    lines[d1:j1] = [
        f"{f20(0.0)}{f20(0.0)}",
        f"{f20(t_stop_orig)}{f20(-stroke)}",
        f"{f20(t_retract_done)}{f20(0.0)}",
        f"{f20(t_final)}{f20(0.0)}",
    ]

    # FUNCT/2(ストリッパー): 既存の閉じきり点(STRIPPER_CLOSE_T)はそのまま残し、
    # パンチと同時に元位置(0)へ戻す(材料を挟んだまま応力を測る意味がないため)。
    i2 = next(k for k, ln in enumerate(lines) if ln.strip() == "/FUNCT/2")
    d2 = i2 + 3
    j2 = d2
    while j2 < len(lines) and not lines[j2].startswith("/"):
        j2 += 1
    lines[d2:j2] = [
        f"{f20(0.0)}{f20(0.0)}",
        lines[d2 + 1],
        f"{f20(t_retract_done)}{f20(0.0)}",
        f"{f20(t_final)}{f20(0.0)}",
    ]
    starter_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    elines = engine_path.read_text(encoding="utf-8").splitlines()
    elines[1] = f20(t_final)
    elines[2] = "/DT/NODA/CST2/0"
    elines[3] = f"{f20(0.9)}{f20(DT_MIN)}"
    for k, ln in enumerate(elines):
        if ln.strip() == "/ANIM/DT":
            elines[k + 1] = f"{f20(0.0)}{f20(t_final / 60)}"
    engine_path.write_text("\n".join(elines) + "\n", encoding="utf-8")
    return t_final


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--blank-elem", type=float, default=DEFAULT_BLANK_ELEM)
    ap.add_argument("--tool-elem", type=float, default=DEFAULT_TOOL_ELEM)
    ap.add_argument("--stroke", type=float, default=DEFAULT_STROKE)
    ap.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    ap.add_argument("--gap-max", type=float, default=DEFAULT_GAP_MAX, dest="gap_max")
    ap.add_argument("--stfac", type=float, default=DEFAULT_STFAC)
    ap.add_argument("--nstep", type=int, default=DEFAULT_NSTEP)
    ap.add_argument("--eps-eff", type=float, default=0.85)
    ap.add_argument("--eps-s", type=float, default=1.0)
    ap.add_argument("--ndir", type=int, default=NDIR)
    ap.add_argument("--retract-frac", type=float, default=1.0,
                    help="引き抜き所要時間 = t_stop_orig * この係数")
    ap.add_argument("--settle-frac", type=float, default=2.0,
                    help="静定保持時間 = t_stop_orig * この係数")
    a = ap.parse_args()

    starter, engine = build(a.tag, a.blank_elem, a.tool_elem, a.stroke, a.speed,
                            a.gap_max, a.stfac, a.nstep)
    t_stop_orig = a.stroke / a.speed
    add_sol2sph(starter, a.ndir, a.blank_elem)
    set_eps_eff(starter, a.eps_eff, a.eps_s)
    t_final = extend_retraction(engine, starter, t_stop_orig, a.stroke,
                                t_stop_orig * a.retract_frac, t_stop_orig * a.settle_frac)
    print(f"[sol2sph] Ndir={a.ndir}, sphpartID={SPH_PART_ID}(PROP {SPH_PROP_ID}), "
          f"h={1.5*a.blank_elem/a.ndir*1e6:.1f}um")
    print(f"[eps_eff] {a.eps_eff}  [eps_s] {a.eps_s}")
    print(f"[retract] t_stop_orig={t_stop_orig*1e3:.3f}ms -> t_final={t_final*1e3:.3f}ms "
          f"(引き抜き{t_stop_orig*a.retract_frac*1e3:.3f}ms + 静定{t_stop_orig*a.settle_frac*1e3:.3f}ms)")
    print(f"[deck] starter -> {starter}")
    print(f"[deck] engine  -> {engine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
