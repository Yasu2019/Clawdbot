# -*- coding: utf-8 -*-
"""INC-188: turn a freshly built PANEL4MM deck (GENE1) into the P1r38f material/solver setup (2026-10-12):
  * /FAIL/GENE1 -> /FAIL/BIQUAD c1..c5 = 2.0 / 1.0 / 0.45 / 0.35 / 0.45 with element-size factor /FUNCT/9
    (1.0 up to L_el 22 um, 0.5 from 50 um; El_ref 1 um) - same as P1r38f;
  * engine deck copied from the P1r38f template (CST2 0.6 ns nodal mass scaling, brick deletion 0.3 ns,
    RFILE 5000, animation every 15 us).
Then run make_station_deck.py --src <out> to get the station-by-station deck.

usage: python derive_biquad_deck.py <src_starter_0000.rad> <out_tag> [--workdir W] [--engine-template P]
"""
import argparse
import os
import re


def f20(v):
    return f"{float(v):>20.7G}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("tag")
    ap.add_argument("--workdir", default="E:/ClawstackData/clawstack_v2_data/work")
    ap.add_argument("--engine-template", default="E:/ClawstackData/clawstack_v2_data/work/chk38/PANEL4MM_P1r38x_0001.rad")
    a = ap.parse_args()
    src = open(a.src, newline="").read().replace(chr(13) + chr(10), chr(10))   # builder writes CRLF; station script expects LF
    m = re.search(r"^PANEL4MM_(\S+)\s*$", src, re.M)
    old = m.group(1)
    i = src.index("/FAIL/GENE1/2\n")
    j = re.compile(r"^(#---1|/)", re.M).search(src, i + 14).start()
    blk = ("/FAIL/BIQUAD/2\n#                 C1                  C2                  C3                  C4                  C5\n"
           + "".join(f20(v) for v in (2.0, 1.0, 0.45, 0.35, 0.45)) + "\n"
           + "#        P_THICKFAIL    M_FLAG    S_FLAG          INST_START            FCT_IDEL              EI_REF\n"
           + f20(0) + "         0         1" + f20(0) + "          " + f"{9:>10d}" + f20(1e-6) + "\n")
    s = src[:i] + blk + src[j:]
    fn = ("/FUNCT/9\nBIQUAD_size_factor_vs_Lel_um\n#                  X                   Y\n"
          + "".join(f20(x) + f20(y) + "\n" for x, y in [(0, 1), (22, 1), (50, 0.5), (1000, 0.5)]))
    k = s.index("/FUNCT/1\n")
    s = s[:k] + fn + s[k:]
    s = s.replace(old, a.tag)
    assert s.count("/FAIL/BIQUAD/2") == 1 and s.count("/FUNCT/9\n") == 1
    open(os.path.join(a.workdir, f"PANEL4MM_{a.tag}_0000.rad"), "w", newline="").write(s)
    eng = open(a.engine_template, newline="").read()
    tmpl_tag = re.search(r"^/RUN/PANEL4MM_(\S+?)/", eng, re.M).group(1)
    open(os.path.join(a.workdir, f"PANEL4MM_{a.tag}_0001.rad"), "w", newline="").write(eng.replace(tmpl_tag, a.tag))
    print(f"{a.tag}: BIQUAD + size factor from {os.path.basename(a.src)} (old tag {old}); engine from {os.path.basename(a.engine_template)}")


if __name__ == "__main__":
    main()
