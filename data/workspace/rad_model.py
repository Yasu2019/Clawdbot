"""rad_model.py — OpenRadioss .rad keyword-aware field modifier.

Replaces fragile str.replace() patching with block-aware, comment-guided
field replacement that preserves fixed-width formatting.

Usage:
    from rad_model import RadModel, set_engine_tstop

    m = RadModel("4mmx4mm_ASSY_20260105_0000.rad")
    m.set_fail_gene1(eps_eff=0.40).set_inter_type25_all(inacti=6, vc=1.2)
    m.write("run48_0000.rad")
    print(m.verify())

    set_engine_tstop(Path("4mmx4mm_ASSY_20260105_0001.rad"), tstop=0.025)
"""
from __future__ import annotations

import re
from pathlib import Path


def _replace_nth_number(line: str, n: int, new_val: str) -> str:
    """Replace the nth number (0-indexed) in a line, preserving total field width.

    Field width = (whitespace before token) + (token length).  The new value is
    right-justified in that width, so the total line length never changes even
    when the new value has more digits than the original.
    """
    pattern = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][+-]?\d+)?')
    parts: list[str] = []
    last = 0
    count = 0
    replaced = False
    for m in pattern.finditer(line):
        if count == n:
            # field_width = preceding whitespace + original token length
            field_width = (m.start() - last) + len(m.group(0))
            parts.append(new_val.rjust(field_width))
            last = m.end()
            replaced = True
        else:
            # Keep non-target tokens (including their preceding whitespace)
            parts.append(line[last:m.end()])
            last = m.end()
        count += 1
    parts.append(line[last:])
    if not replaced:
        raise ValueError(f"token index {n} not found in line: {line!r}")
    return "".join(parts)


def _find_data_line_after_comment(lines: list[str], block_start: int, comment_hint: str) -> int:
    """Return index of first non-comment data line after a comment containing comment_hint.

    Stops at the next keyword line (starts with '/') to stay within the block.
    """
    found_comment = False
    for i in range(block_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("/") and stripped[1:2].isalpha():
            break
        if stripped.startswith("#") and comment_hint.lower() in stripped.lower():
            found_comment = True
            continue
        if found_comment and stripped and not stripped.startswith("#"):
            return i
    return -1


class RadModel:
    """Block-aware OpenRadioss starter deck (.rad) modifier."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        raw = self.path.read_bytes()
        self._crlf = b"\r\n" in raw
        text = raw.decode("utf-8", errors="replace")
        if self._crlf:
            text = text.replace("\r\n", "\n")
        self._lines = text.split("\n")

    def _find_blocks(self, keyword: str) -> list[int]:
        return [i for i, ln in enumerate(self._lines) if ln.strip().startswith(keyword)]

    def set_fail_gene1(self, eps_eff: float, mat_id: int = 2) -> "RadModel":
        """Set Eps_eff in /FAIL/GENE1/<mat_id>.

        Target line structure (Card 3):
            fct_IDps[I10]  Eps_dot_ps[F20]  Eps_max[F20]  Eps_eff[F20]  Eps_vol[F20]
        Eps_eff is token index 3.
        """
        blocks = self._find_blocks(f"/FAIL/GENE1/{mat_id}")
        if not blocks:
            raise ValueError(f"/FAIL/GENE1/{mat_id} not found")
        for block_start in blocks:
            di = _find_data_line_after_comment(self._lines, block_start, "Eps_eff")
            if di < 0:
                raise ValueError(f"Eps_eff data line not found after /FAIL/GENE1/{mat_id}")
            self._lines[di] = _replace_nth_number(self._lines[di], 3, f"{eps_eff:.6g}")
        return self

    def set_inter_type25_all(self, inacti: int, vc: float) -> "RadModel":
        """Set Inacti and VISs in every /INTER/TYPE25/{n} block.

        Target line structure:
            I_BC[I10]  IVIS2[I10]  Inacti[I10]  VISs[F20]
        Inacti is token index 2, VISs is token index 3.
        """
        for i, ln in enumerate(self._lines):
            if re.match(r"/INTER/TYPE25/\d", ln.strip()):
                di = _find_data_line_after_comment(self._lines, i, "Inacti")
                if di >= 0:
                    line = self._lines[di]
                    line = _replace_nth_number(line, 2, str(inacti))
                    line = _replace_nth_number(line, 3, f"{vc:.6g}")
                    self._lines[di] = line
        return self

    def set_inter_type25_contact(
        self,
        gap_max: float = 0.01,
        stfac_punch: float = 0.05,
        stfac_die: float = 1e-4,
        stfac_strip: float = 1e-4,
    ) -> "RadModel":
        """Set Gap_max and Stfac on /INTER/TYPE25/1..3 blocks."""
        stfac_map = {1: stfac_punch, 2: stfac_die, 3: stfac_strip}
        for i, ln in enumerate(self._lines):
            m = re.match(r"/INTER/TYPE25/(\d+)", ln.strip())
            if not m:
                continue
            inter_id = int(m.group(1))
            if inter_id not in stfac_map:
                continue
            gap_di = _find_data_line_after_comment(self._lines, i, "Gap_max")
            if gap_di >= 0:
                line = self._lines[gap_di]
                # Gap_max_s / Gap_max_m are the 4th and 5th numbers (0-based index 3, 4)
                line = _replace_nth_number(line, 3, f"{gap_max:.6g}")
                line = _replace_nth_number(line, 4, f"{gap_max:.6g}")
                self._lines[gap_di] = line
            st_di = _find_data_line_after_comment(self._lines, i, "Stfac")
            if st_di >= 0:
                sf = stfac_map[inter_id]
                self._lines[st_di] = _replace_nth_number(self._lines[st_di], 0, f"{sf:.6g}")
        return self

    def write(self, path: Path | None = None) -> Path:
        out = Path(path) if path else self.path
        text = "\n".join(self._lines)
        if self._crlf:
            text = text.replace("\n", "\r\n")
        out.write_bytes(text.encode("utf-8"))
        return out

    def verify(self) -> dict[str, object]:
        """Return current values of key parameters for sanity-check."""
        result: dict[str, object] = {}
        for block_start in self._find_blocks("/FAIL/GENE1/2"):
            di = _find_data_line_after_comment(self._lines, block_start, "Eps_eff")
            if di >= 0:
                tokens = self._lines[di].split()
                result["Eps_eff"] = float(tokens[3]) if len(tokens) >= 4 else None
        for i, ln in enumerate(self._lines):
            if re.match(r"/INTER/TYPE25/1\b", ln.strip()):
                di = _find_data_line_after_comment(self._lines, i, "Inacti")
                if di >= 0:
                    tokens = self._lines[di].split()
                    result["Inacti"] = int(tokens[2]) if len(tokens) >= 3 else None
                    result["VC"] = float(tokens[3]) if len(tokens) >= 4 else None
                break
        return result


def set_engine_tstop(engine_path: Path, tstop: float) -> None:
    """Set TSTOP on the line immediately after /RUN/... in the engine file."""
    raw = engine_path.read_bytes()
    crlf = b"\r\n" in raw
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    for i, ln in enumerate(lines):
        if ln.strip().startswith("/RUN/") and i + 1 < len(lines):
            lines[i + 1] = _replace_nth_number(lines[i + 1], 0, f"{tstop:.10f}")
            break
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    engine_path.write_bytes(text.encode("utf-8"))


def set_engine_ams_scale(engine_path: Path, scale: float) -> None:
    """Set AMS scale on the data line after /DT/AMS/... in the engine file."""
    raw = engine_path.read_bytes()
    crlf = b"\r\n" in raw
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    for i, ln in enumerate(lines):
        if ln.strip().startswith("/DT/AMS") and i + 1 < len(lines):
            lines[i + 1] = _replace_nth_number(lines[i + 1], 0, f"{scale:.5f}")
            break
    else:
        raise ValueError(f"/DT/AMS block not found in {engine_path}")
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    engine_path.write_bytes(text.encode("utf-8"))


def set_engine_dt_min(engine_path: Path, dt_min: str | float) -> None:
    """Set minimum timestep (2nd number) on the data line after /DT/AMS/..."""
    raw = engine_path.read_bytes()
    crlf = b"\r\n" in raw
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    dt_str = f"{dt_min}" if isinstance(dt_min, str) else f"{dt_min:.6E}"
    for i, ln in enumerate(lines):
        if ln.strip().startswith("/DT/AMS") and i + 1 < len(lines):
            lines[i + 1] = _replace_nth_number(lines[i + 1], 1, dt_str)
            break
    else:
        raise ValueError(f"/DT/AMS block not found in {engine_path}")
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    engine_path.write_bytes(text.encode("utf-8"))


def read_engine_params(engine_path: Path) -> dict[str, object]:
    """Return TSTOP, AMS scale, and dt_min from engine file."""
    raw = engine_path.read_bytes()
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    result: dict[str, object] = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("/RUN/") and i + 1 < len(lines):
            toks = lines[i + 1].split()
            if toks:
                result["tstop"] = float(toks[0])
        if s.startswith("/DT/AMS") and i + 1 < len(lines):
            toks = lines[i + 1].split()
            if len(toks) >= 2:
                result["ams_scale"] = float(toks[0])
                result["dt_min"] = toks[1]
    return result
