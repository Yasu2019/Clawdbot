# -*- coding: utf-8 -*-
"""INC-188: 破断要素を削除せず SPH 粒子へ変換する(Sol2SPH)。2026-08-18 導入。

## なぜ

GENE1+要素削除(build_inc188_slice3d.py)は E15(Eps_eff=1.5) で以下を起こした:
19要素は正常に破断削除できたが、t=1.0936-1.1029e-3s の約10us間に3要素が
近接連鎖破断し、直後に DM/M が 700サイクルで 0.28 -> 2.47e+55 まで指数的に
発散した(dt_min フロアは崩壊を遅延させるだけで防げなかった)。

Sol2SPH は要素削除の代わりに、破断要素をメッシュ接続を持たない SPH 粒子へ
転換する。要素接続が壊れることが崩壊の直接原因だったため、これは根拠のある
対策(Altair公式: https://help.altair.com/hwsolvers/rad/topics/solvers/rad/
solid_to_sph_option_intro_r.htm)。

## カード仕様の出典(実例デックは非公開のため公式リファレンスの記述に基づく)

/PROP/TYPE14(SOLID) 全22フィールド(公式ドキュメントより):
  line3: Isolid,Ismstr,Iale,Icpre,Itetra10,Inpts,Itetra4,Iframe,dn (9項目)
  line4: qa,qb,h,λv,μv (5項目)
  line5: Δtmin,Vdef_min,Vdef_max,APS_max,COL_min (5項目)
  line6: Ndir,sphpartID,Icontrol (3項目, Sol2SPH追加分・当プロジェクトで追記)

Sol2SPH の要件(公式): Isolid=1/2/24のみ、Iframe=1/2のみ、Ndir>=1。
現行デックは Isolid=14・Iframe=1 (既存カード実測)。Iframe=1 は要件を満たすが
Isolid は 24(HEPH, 物理砂時計制御)へ変更が必要。

/PROP/TYPE34(SPH) (公式ドキュメントより):
  line3: mp,beta,alpha,alpha_cs,skew_ID,h_1D
  line4: order,h,xi_stab,hmin,hmax
  line5: hcst
  Sol2SPH変換時: mp=0(自動計算), h=1.5*要素寸法/Ndir(推奨式), order=0(既定),
  xi_stab=0.3(引張不安定対策、公式推奨)

⚠ 実例デック(qa-tests/miniqa, ModelExchange)には Sol2SPH の完成例が
   見当たらなかった。上記は公式リファレンスの記述からの構築で、実行時の
   Starter エラー・エコー内容で正しさを検証する(このプロジェクトの方針:
   生成デックは必ずStarterで検算してから長時間ランに入れる)。

## 検証済みの標準構成(SPH2, 2026-08-19) — デフォルト値のまま呼び出せば再現する

Isolid=24 + Ndir/sphpartID/Icontrol=0 の行 + SPH粒子専用MAT_ID複製(/FAILなし)
の組合せで Starter 0 ERROR/1 WARNING(想定内)、Engine完走・DM/M最大3.28e-14
(ノイズレベル)・想定域外の粒子0/50,138点(0%)を確認済み。GENE1要素削除方式
(E15でDM/M暴走)からの根本的な改善として確立している。

## 未検証: 幾何品質トリガー(--vdef-min/--vdef-max/--asp-max/--col-min)

公式ドキュメントには Vdef_min/Vdef_max/ASP_max/COL_min という、GENE1とは
独立に要素形状の歪みだけでSPH変換を先行発火できるフィールドがあると記載
されている(要素が壊れきる前に変換できれば SPH1 で見た相当ひずみ1e20の
異常値カスケードを避けられる可能性)。しかし実例デックが見つからず、
2026-08-19 に2通りの配置(Icontrol=0のまま値だけ追加/Icontrol=1に変更)を
Starterで試したが、いずれも "WARNING ID 100213: unsupported field exists
at the end of line" が出て正しく解釈されている確証が得られなかった。
これらのCLIオプションは実装してあるが、指定しなければ(デフォルト0のまま)
上記の検証済み構成のまま生成される。値を指定して使う場合は自己責任で
Starterのエコー内容を必ず確認すること。正しい書式が判明したら本セクションと
add_sol2sph()のコメントを更新する。

usage:
  python scripts/build_inc188_sol2sph.py --tag SPH1 --eps-eff 1 --eps-s 1.0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023
sys.path.insert(0, str(Path(__file__).parent))

from build_inc188_slice3d import (  # noqa: E402
    build, i10, f20, TRIALS, DEFAULT_SHEAR_ELEM, DEFAULT_BAND, DEFAULT_COARSE,
    DEFAULT_CLEARANCE, DEFAULT_SLICE, DEFAULT_GAP_MAX, DEFAULT_STFAC, DEFAULT_NSTEP,
)

SPH_PROP_ID = 3      # 新規 /PROP/TYPE34
SPH_PART_ID = 5      # 新規 SPH パート(既存 part 1-4 と衝突しない番号)
SPH_MAT_ID = 3        # ブランク材料の複製(/FAIL なし)
NDIR = 2             # 2x2x2 = 8粒子/要素


def add_sol2sph(starter_path: Path, ndir: int, shear_elem: float,
                vdef_min: float = 0.0, vdef_max: float = 0.0,
                asp_max: float = 0.0, col_min: float = 0.0) -> None:
    text = starter_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # --- /PROP/SOLID/2 (ブランク) を Sol2SPH 対応へ書き換える ---
    i = next(k for k, ln in enumerate(lines) if ln.strip() == "/PROP/SOLID/2")
    data0 = i + 3  # 0:keyword 1:title 2:comment 3:data line1
    old = lines[data0]
    isolid = int(old[0:10])
    if isolid not in (1, 2, 24):
        # Isolid=24 (HEPH, 物理砂時計制御) へ変更。Sol2SPH の必須条件。
        lines[data0] = f"{i10(24)}" + old[10:]
    iframe_val = int(old[70:80])
    if iframe_val not in (1, 2):
        raise ValueError(f"Iframe={iframe_val} は Sol2SPH 非対応(1か2が必要): {old!r}")
    data2 = data0 + 2  # line3 = Δtmin,Vdef_min,Vdef_max,APS_max,COL_min
    # 2026-08-19 追加: GENE1(材料破壊則)とは独立な幾何品質トリガー。
    # SPH1で観測した「相当ひずみ1.0e+20」という異常値は、要素形状が完全に
    # 壊れる(ダイ角のせん断帯で板厚方向に潰れる)までGENE1だけを待っていた
    # ことが一因。ASP_max(伸び切り)・COL_min(潰れ)を先に効かせ、形状が
    # 壊れ始めた早い段階でSPH変換する。値は公式ドキュメントに推奨値の
    # 明記がなく、健全な立方体(縦横比1)に対する経験的な閾値。
    use_distortion_ctrl = any(v > 0 for v in (vdef_min, vdef_max, asp_max, col_min))
    if use_distortion_ctrl:
        lines[data2] = f"{f20(0.0)}{f20(vdef_min)}{f20(vdef_max)}{f20(asp_max)}{f20(col_min)}"
    # Icontrol: Starterの実測で"SOLID DISTORTION CONTROL FLAG"そのものと判明。
    # 0のままだとVdef_min/Vdef_max/ASP_max/COL_minは"unsupported field"警告
    # (WARNING ID 100213)と共に無視される。歪み制御(=このトリガー)を使う
    # 場合は Icontrol=1 が必須。
    icontrol = 1 if use_distortion_ctrl else 0
    sol2sph_line = f"{i10(ndir)}{i10(SPH_PART_ID)}{i10(icontrol)}"
    lines.insert(data2 + 1, sol2sph_line)

    # --- ブランク材料(MAT_ID=2)を複製し、/FAIL を外した MAT_ID=3 を作る ---
    # 2026-08-18 実証済みバグ対策: /FAIL/GENE1/2 は MAT_ID=2 に紐付く。SPH粒子
    # (/PART/5)がそのままMAT_ID=2を継承すると、変換後の粒子にも同じGENE1が
    # 効き続け、既に破断しきい値を超えた状態(ひずみ1e20等の異常値)のまま
    # 毎サイクル"RUPTURE OF SOLID ELEMENT"を再出力し続ける。SPH1実行で実測:
    # ユニーク要素1,888個が平均58,083回・最大105,559回再出力され、ログが
    # 38.8GB(1億9661万行)に肥大化した。物理特性は同一・/FAILだけを外した
    # 別MAT_IDをSPH粒子専用に用意して回避する。
    mat_start = next(k for k, ln in enumerate(lines) if ln.strip() == "/MAT/LAW2/2")
    j = mat_start + 1
    while not lines[j].startswith("/"):
        j += 1
    mat_data = lines[mat_start + 2:j]  # タイトル行を除いたデータ行群(物理値そのまま)
    mat_dup = [f"/MAT/LAW2/{SPH_MAT_ID}", "MR536_H34_AA5052_SPH_no_fail"] + mat_data

    # --- /PROP/TYPE34 (SPH) を末尾(/END の直前)に追加 ---
    h = 1.5 * shear_elem / ndir  # Altair 推奨式
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
        f"{i10(SPH_PROP_ID)}{i10(SPH_MAT_ID)}",  # /FAIL なしの複製材料
    ]

    end_idx = next(k for k, ln in enumerate(lines) if ln.strip() == "/END")
    lines = lines[:end_idx] + mat_dup + sph_prop + sph_part + lines[end_idx:]

    starter_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--shear-elem", type=float, default=DEFAULT_SHEAR_ELEM)
    ap.add_argument("--band", type=float, default=DEFAULT_BAND)
    ap.add_argument("--coarse", type=float, default=DEFAULT_COARSE)
    ap.add_argument("--clearance", type=float, default=DEFAULT_CLEARANCE)
    ap.add_argument("--tstop", type=float, default=0.0015)
    ap.add_argument("--slice", type=float, default=DEFAULT_SLICE, dest="slice_dx")
    ap.add_argument("--eps-pmax", type=float, default=None)
    ap.add_argument("--eps-eff", type=float, default=None)
    ap.add_argument("--eps-s", type=float, default=None)
    ap.add_argument("--volfrac", type=float, default=None)
    ap.add_argument("--gap-max", type=float, default=DEFAULT_GAP_MAX, dest="gap_max")
    ap.add_argument("--stfac", type=float, default=DEFAULT_STFAC)
    ap.add_argument("--nstep", type=int, default=DEFAULT_NSTEP)
    ap.add_argument("--ndir", type=int, default=NDIR)
    ap.add_argument("--vdef-min", type=float, default=0.0,
                    help="V/V0 がこれ未満で先行SPH変換(0=無効)。目安0.1")
    ap.add_argument("--vdef-max", type=float, default=0.0,
                    help="V/V0 がこれ超で先行SPH変換(0=無効)。目安8.0")
    ap.add_argument("--asp-max", type=float, default=0.0,
                    help="最大辺長/最小辺長がこれ超で先行SPH変換(0=無効)。目安5.0")
    ap.add_argument("--col-min", type=float, default=0.0,
                    help="最小辺長/最大辺長がこれ未満で先行SPH変換(0=無効)。目安0.12")
    a = ap.parse_args()

    starter, engine = build(a.tag, a.shear_elem, a.band, a.coarse, a.clearance, a.tstop,
                            a.slice_dx, a.eps_pmax, a.eps_eff, a.eps_s, a.volfrac,
                            a.gap_max, a.stfac, a.nstep)
    add_sol2sph(starter, a.ndir, a.shear_elem, a.vdef_min, a.vdef_max, a.asp_max, a.col_min)
    print(f"[sol2sph] Isolid->24, Ndir={a.ndir}, sphpartID={SPH_PART_ID}(PROP {SPH_PROP_ID}) を追記")
    print(f"[sol2sph] h(smoothing length)={1.5*a.shear_elem/a.ndir*1e6:.2f}um")
    if any(v > 0 for v in (a.vdef_min, a.vdef_max, a.asp_max, a.col_min)):
        print(f"[sol2sph] 幾何品質トリガー: Vdef_min={a.vdef_min:g} Vdef_max={a.vdef_max:g} "
              f"ASP_max={a.asp_max:g} COL_min={a.col_min:g}")
    print(f"[sol2sph] starter -> {starter}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
