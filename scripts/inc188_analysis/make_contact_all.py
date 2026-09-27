# -*- coding: utf-8 -*-
"""Punch-blank contact that keeps working after solid erosion (INC-188, 2026-09-27).

Found in P1r19fc3p5: the blank contact surface is /SURF/PART/EXT (t=0 external faces only). Once the
top layer under the round punch eroded (f006), no new faces entered the contact and the punch sank
through the slug (live blank centroids inside the punch volume 0 -> 3,104 -> 8,011 -> 12,158 at
f006/f007/f008/f010; at t=0.24 ms 4,276 live elements sit ABOVE the punch top). The cut 'stall'
and the insensitivity to C0 come from this, not from the failure criterion.

Change (only in the interface whose surf_ID1 is the punch surface 400 = part 4; the deck's interface
titles are shifted: 'Stripper_Blank_Contact' is the punch one, verified from part z positions):
  - new /SURF/PART/ALL/201 on the blank part 2 (all solid faces, internal ones included)
  - surf_ID2 200 -> 201
  - Idel 2 -> 1 (an internal face is removed only when BOTH its solids are deleted)
Die and stripper interfaces are unchanged.

usage: python make_contact_all.py <dir> <src_tag> <new_tag>
"""
import sys
from pathlib import Path


def main():
    d, src, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    st = (d / f"PANEL4MM_{src}_0000.rad").read_text(encoding="utf-8").split("\n")
    out, n_int, n_surf = [], 0, 0
    i = 0
    while i < len(st):
        ln = st[i]
        if ln.startswith("/SURF/PART/EXT/200/"):
            out += st[i:i + 3]
            out += ["/SURF/PART/ALL/201/0", "Surf_Part_2_all_faces", "         2"]
            n_surf += 1
            i += 3
            continue
        if ln.startswith("/INTER/TYPE25/"):
            j = i + 2
            while st[j].startswith("#"):
                j += 1
            f = [st[j][k:k + 10] for k in range(0, 90, 10)]
            if int(f[0]) == 400:
                assert int(f[1]) == 200 and int(f[7]) == 2, f
                f[1] = f"{201:>10d}"
                f[7] = f"{1:>10d}"
                out += st[i:j] + ["".join(f) + st[j][90:]]
                print(f"{st[i+1].strip()}: {st[j].rstrip()!r} -> {out[-1].rstrip()!r}")
                n_int += 1
                i = j + 1
                continue
        out.append(ln)
        i += 1
    assert n_int == 1 and n_surf == 1, (n_int, n_surf)
    out = [x.replace(f"PANEL4MM_{src}", f"PANEL4MM_{new}").replace(f"({src})", f"({new})") for x in out]
    (d / f"PANEL4MM_{new}_0000.rad").write_text("\n".join(out), encoding="utf-8", newline="\n")
    en = (d / f"PANEL4MM_{src}_0001.rad").read_text(encoding="utf-8").replace(f"PANEL4MM_{src}", f"PANEL4MM_{new}")
    (d / f"PANEL4MM_{new}_0001.rad").write_text(en, encoding="utf-8", newline="\n")
    print(f"lines {len(st)} -> {len(out)}")


if __name__ == "__main__":
    main()
