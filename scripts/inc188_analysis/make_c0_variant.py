# -*- coding: utf-8 -*-
"""Clone a built PANEL4MM deck pair with a new tag, a new /FAIL/COCKCROFT C0 and (optionally) a new tstop.

Only three things change (verified by a line diff printed at the end): the tag in names,
the C0 value on the /FAIL/COCKCROFT/2 data line, and tstop (+ animation interval tstop/N_ANIM)
in the engine deck. Mesh, material, contacts and punch motion are untouched.

usage: python make_c0_variant.py <src_dir> <base_tag> <new_tag> <c0_Pa> <out_dir> [tstop_s] [anim_dt_s]
"""
import sys
from pathlib import Path


def f20(v: float) -> str:
    return f"{v:>20.6G}" if abs(v) < 1e-3 or abs(v) >= 1e6 else f"{v:>20g}"


def main():
    src, base, new, c0, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], float(sys.argv[4]), Path(sys.argv[5])
    tstop = float(sys.argv[6]) if len(sys.argv) > 6 else None
    anim_dt = float(sys.argv[7]) if len(sys.argv) > 7 else 1.5e-5

    st = (src / f"PANEL4MM_{base}_0000.rad").read_text(encoding="utf-8").split("\n")
    n_c0 = 0
    for i, ln in enumerate(st):
        if ln.startswith("/FAIL/COCKCROFT/2"):
            j = i + 1
            while st[j].startswith("#"):
                j += 1
            old = st[j]
            st[j] = f20(c0) + old[20:]
            n_c0 += 1
    assert n_c0 == 1, f"expected one /FAIL/COCKCROFT/2 block, found {n_c0}"
    st = [ln.replace(f"PANEL4MM_{base}", f"PANEL4MM_{new}").replace(f"({base})", f"({new})") for ln in st]
    (out / f"PANEL4MM_{new}_0000.rad").write_text("\n".join(st), encoding="utf-8", newline="\n")

    en = (src / f"PANEL4MM_{base}_0001.rad").read_text(encoding="utf-8").split("\n")
    en = [ln.replace(f"PANEL4MM_{base}", f"PANEL4MM_{new}") for ln in en]
    if tstop is not None:
        k = [i for i, ln in enumerate(en) if ln.startswith("/RUN/")][0]
        en[k + 1] = f20(tstop)
        a = [i for i, ln in enumerate(en) if ln.startswith("/ANIM/DT")][0]
        en[a + 1] = f20(0.0) + f20(anim_dt)
    (out / f"PANEL4MM_{new}_0001.rad").write_text("\n".join(en), encoding="utf-8", newline="\n")

    # diff check against the source (names excluded)
    for suf in ("0000", "0001"):
        a = (src / f"PANEL4MM_{base}_{suf}.rad").read_text(encoding="utf-8").split("\n")
        b = (out / f"PANEL4MM_{new}_{suf}.rad").read_text(encoding="utf-8").split("\n")
        assert len(a) == len(b)
        d = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x.replace(base, new) != y]
        print(f"{suf}: {len(d)} changed lines besides the tag")
        for i, x, y in d:
            print(f"   L{i+1}: {x.strip()!r} -> {y.strip()!r}")


if __name__ == "__main__":
    main()
