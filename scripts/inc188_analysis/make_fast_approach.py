# -*- coding: utf-8 -*-
"""Clone the P1r19 deck with a faster punch approach through the air gap (INC-188, 2026-09-27).

P1r19 (round punch first): round punch bottom z=1.800 mm, blank top z=1.005 mm at the hole ->
0.795 mm of air at 5 mm/ms = contact at t=0.159 ms, i.e. ~48 % of the 0.33 ms run is air travel.
Here the punch covers 0.745 mm in the first 0.05 ms, then continues at the original 5 mm/ms
(contact at 0.06 ms, stroke end 3 mm unchanged). The stripper closes its 0.19 mm by 0.04 ms
(its final gap to the blank is 5 um, so it does not load the blank either way).
Post-contact cutting speed and everything else (mesh, material, contacts) are unchanged.
Old time t maps to new time t - 0.099 ms after contact; old tstop 0.33 ms ~ new 0.231 ms.

usage: python make_fast_approach.py <dir> <src_tag> <new_tag>
"""
import sys
from pathlib import Path


def f20(v: float) -> str:
    return f"{v:>20.6G}" if (v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e6)) else f"{v:>20g}"


NEW = {
    "Punch_Stroke": [(0.0, 0.0), (5.0e-5, -7.45e-4), (5.01e-4, -3.0e-3), (6.0e-3, -3.0e-3)],
    "Stripper_Close": [(0.0, 0.0), (4.0e-5, -1.9e-4), (6.0e-3, -1.9e-4)],
}


def main():
    d, src, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    st = (d / f"PANEL4MM_{src}_0000.rad").read_text(encoding="utf-8").split("\n")
    out, i, done = [], 0, []
    while i < len(st):
        ln = st[i]
        if ln.startswith("/FUNCT/") and i + 1 < len(st) and st[i + 1].strip() in NEW:
            name = st[i + 1].strip()
            out += [ln, st[i + 1]]
            j = i + 2
            while st[j].startswith("#"):
                out.append(st[j]); j += 1
            old = []
            while not st[j].startswith("/"):
                old.append(st[j].strip()); j += 1
            out += [f20(x) + f20(y) for x, y in NEW[name]]
            print(f"{name}: {old} -> {[(x, y) for x, y in NEW[name]]}")
            done.append(name)
            i = j
            continue
        out.append(ln)
        i += 1
    assert sorted(done) == sorted(NEW), f"functions patched: {done}"
    out = [ln.replace(f"PANEL4MM_{src}", f"PANEL4MM_{new}").replace(f"({src})", f"({new})") for ln in out]
    (d / f"PANEL4MM_{new}_0000.rad").write_text("\n".join(out), encoding="utf-8", newline="\n")
    en = (d / f"PANEL4MM_{src}_0001.rad").read_text(encoding="utf-8").replace(f"PANEL4MM_{src}", f"PANEL4MM_{new}")
    (d / f"PANEL4MM_{new}_0001.rad").write_text(en, encoding="utf-8", newline="\n")
    print(f"lines {len(st)} -> {len(out)}")


if __name__ == "__main__":
    main()
