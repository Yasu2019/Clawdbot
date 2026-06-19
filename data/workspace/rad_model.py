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

    def set_inter_type25_penetration_fix(
        self,
        igap: int = 2,
        irem_i2: int = 2,
        igap0: int = 0,
        ishape: int = 2,
    ) -> "RadModel":
        """Fix TYPE25 contact for brick+SH3N skin (Igap=2 thickness, Ishape=2)."""
        for i, ln in enumerate(self._lines):
            if not re.match(r"/INTER/TYPE25/\d", ln.strip()):
                continue
            surf_di = _find_data_line_after_comment(self._lines, i, "surf_ID1")
            if surf_di >= 0:
                line = self._lines[surf_di]
                line = _replace_nth_number(line, 3, str(igap))
                line = _replace_nth_number(line, 4, str(irem_i2))
                self._lines[surf_di] = line
            shape_di = _find_data_line_after_comment(self._lines, i, "Igap0")
            if shape_di >= 0:
                line = self._lines[shape_di]
                line = _replace_nth_number(line, 0, str(igap0))
                line = _replace_nth_number(line, 1, str(ishape))
                self._lines[shape_di] = line
        return self

    def set_inter_type25_idel(self, idel: int = 2) -> "RadModel":
        """Set Idel on every /INTER/TYPE25 block (INC-075: Idel=2 for shearing with /FAIL)."""
        for i, ln in enumerate(self._lines):
            if not re.match(r"/INTER/TYPE25/\d", ln.strip()):
                continue
            surf_di = _find_data_line_after_comment(self._lines, i, "surf_ID1")
            if surf_di >= 0:
                self._lines[surf_di] = _replace_nth_number(self._lines[surf_di], 5, str(idel))
        return self

    def set_inter_type25_fric_all(self, fric: float) -> "RadModel":
        """Set Fric on Stfac line for every /INTER/TYPE25 block."""
        for i, ln in enumerate(self._lines):
            if not re.match(r"/INTER/TYPE25/\d", ln.strip()):
                continue
            di = _find_data_line_after_comment(self._lines, i, "Fric")
            if di < 0:
                di = _find_data_line_after_comment(self._lines, i, "Stfac")
            if di >= 0:
                self._lines[di] = _replace_nth_number(self._lines[di], 1, f"{fric:.6g}")
        return self

    def set_inter_type25_gap_punch(self, gap_m: float) -> "RadModel":
        """Set Gap_max_s/m on /INTER/TYPE25/1 (punch-material contact)."""
        for i, ln in enumerate(self._lines):
            if not re.match(r"/INTER/TYPE25/1\b", ln.strip()):
                continue
            di = _find_data_line_after_comment(self._lines, i, "Gap_max")
            if di >= 0:
                line = self._lines[di]
                line = _replace_nth_number(line, 3, f"{gap_m:.6g}")
                line = _replace_nth_number(line, 4, f"{gap_m:.6g}")
                self._lines[di] = line
            break
        return self

        """Set Inacti on a single /INTER/TYPE25/{inter_id} block."""
        pat = re.compile(rf"/INTER/TYPE25/{inter_id}\b")
        for i, ln in enumerate(self._lines):
            if not pat.match(ln.strip()):
                continue
            di = _find_data_line_after_comment(self._lines, i, "Inacti")
            if di >= 0:
                self._lines[di] = _replace_nth_number(self._lines[di], 2, str(inacti))
            break
        return self

    def set_prop_shell_ismstr(self, prop_id: int, ismstr: int) -> "RadModel":
        """Set Ismstr on /PROP/SHELL/{prop_id} data line."""
        pat = re.compile(rf"/PROP/SHELL/{prop_id}\b")
        for i, ln in enumerate(self._lines):
            if not pat.match(ln.strip()):
                continue
            di = _find_data_line_after_comment(self._lines, i, "Ishell")
            if di >= 0:
                self._lines[di] = _replace_nth_number(self._lines[di], 1, str(ismstr))
            break
        return self

    def add_brick_part_ext_surf(self, surf_id: int = 402, part_id: int = 2) -> "RadModel":
        """Append /SURF/PART/EXT/{surf_id} for external faces of solid material part."""
        insert_at = len(self._lines)
        for i, ln in enumerate(self._lines):
            if ln.strip().startswith("/INTER/TYPE25/"):
                insert_at = i
        block = [
            f"/SURF/PART/EXT/{surf_id}",
            "Material_Brick_External",
            f"{part_id:>10d}",
        ]
        self._lines[insert_at:insert_at] = block
        return self

    def set_inter_type25_secondary_surf(self, surf_id: int) -> "RadModel":
        """Set surf_ID2 (secondary) on all /INTER/TYPE25 blocks."""
        for i, ln in enumerate(self._lines):
            if not re.match(r"/INTER/TYPE25/\d", ln.strip()):
                continue
            surf_di = _find_data_line_after_comment(self._lines, i, "surf_ID1")
            if surf_di >= 0:
                self._lines[surf_di] = _replace_nth_number(self._lines[surf_di], 1, str(surf_id))
        return self

    def _collect_block_node_ids(self, block_prefix: str) -> set[int]:
        ids: set[int] = set()
        in_block = False
        for ln in self._lines:
            s = ln.strip()
            if s.startswith(block_prefix):
                in_block = True
                continue
            if in_block:
                if s.startswith("/") and not s.startswith("#"):
                    break
                parts = s.split()
                if parts and parts[0].isdigit():
                    for tok in parts[1:]:
                        if tok.isdigit():
                            ids.add(int(tok))
        return ids

    def translate_element_nodes_z(self, block_prefixes: list[str], dz_m: float) -> "RadModel":
        """Translate nodes referenced by element blocks (e.g. /TETRA4/1, /SH3N/101)."""
        node_ids: set[int] = set()
        for pref in block_prefixes:
            node_ids |= self._collect_block_node_ids(pref)
        if not node_ids:
            raise ValueError(f"no nodes found for blocks {block_prefixes}")
        in_node = False
        for i, ln in enumerate(self._lines):
            s = ln.strip()
            if s.startswith("/NODE"):
                in_node = True
                continue
            if in_node:
                if s.startswith("/") and not s.startswith("#"):
                    in_node = False
                    continue
                parts = s.split()
                if len(parts) >= 4 and parts[0].isdigit() and int(parts[0]) in node_ids:
                    z_new = float(parts[3]) + dz_m
                    self._lines[i] = f"{parts[0]:>10s}  {parts[1]} {parts[2]} {z_new:.12E}"
        return self

    def set_funct_y_plateau(self, func_id: int, y_m_s: float) -> "RadModel":
        """Set Y value on all FUNCT/{func_id} points except t=0."""
        pat = re.compile(rf"/FUNCT/{func_id}\b")
        for i, ln in enumerate(self._lines):
            if not pat.match(ln.strip()):
                continue
            j = i + 1
            while j < len(self._lines):
                s = self._lines[j].strip()
                if s.startswith("/") and not s.startswith("#"):
                    break
                if s.startswith("#") or not s:
                    j += 1
                    continue
                parts = s.split()
                if len(parts) >= 2:
                    t_val = float(parts[0])
                    if t_val > 0.0:
                        self._lines[j] = _replace_nth_number(self._lines[j], 1, f"{y_m_s:.5f}")
                j += 1
            break
        return self

    def set_impvel_fscale_y(self, impvel_id: int, fscale: float) -> "RadModel":
        """Set Fscale_y on /IMPVEL/{impvel_id} second data line."""
        pat = re.compile(rf"/IMPVEL/{impvel_id}\b")
        for i, ln in enumerate(self._lines):
            if not pat.match(ln.strip()):
                continue
            di = _find_data_line_after_comment(self._lines, i, "Fscale_y")
            if di >= 0:
                self._lines[di] = _replace_nth_number(self._lines[di], 1, f"{fscale:.5f}")
            break
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


def set_engine_noda_dt_min(engine_path: Path, dt_min: str | float) -> None:
    """Set minimum timestep (2nd number) on the data line after /DT/NODA/..."""
    raw = engine_path.read_bytes()
    crlf = b"\r\n" in raw
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    dt_str = f"{dt_min}" if isinstance(dt_min, str) else f"{dt_min:.6E}"
    for i, ln in enumerate(lines):
        if ln.strip().startswith("/DT/NODA") and i + 1 < len(lines):
            lines[i + 1] = _replace_nth_number(lines[i + 1], 1, dt_str)
            break
    else:
        raise ValueError(f"/DT/NODA block not found in {engine_path}")
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
