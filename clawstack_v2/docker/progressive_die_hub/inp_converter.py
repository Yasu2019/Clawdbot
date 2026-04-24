"""
inp_converter.py — Prepomax/CalculiX .inp → OpenRadioss .rad 変換

対応:
  - 単位系: MM_TON_S_C (mm, tonne, s) → kg / m / s
  - 要素: C3D4 → TETRA4
  - 材料: 弾性のみ → LAW1 / 弾性+塑性 → LAW2
  - 境界条件: *Boundary + *Amplitude → /IMPVEL + /FUNCT
  - 接触: *Contact pair → /INTER/TYPE25
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# ── 単位変換係数 (MM_TON_S_C → kg/m/s) ──────────────────────────────────────
_MM_TO_M   = 1e-3       # 長さ
_TONNE_TO_KG = 1e3      # 質量  (1 tonne = 1000 kg)
# 密度: t/mm³ → kg/m³  = ×1e3 / (1e-3)³ = ×1e12
_DENSITY_FACTOR = 1e12
# 弾性係数: MPa → Pa = ×1e6
_MODULUS_FACTOR = 1e6
# 応力: MPa → Pa = ×1e6
_STRESS_FACTOR  = 1e6


class InpConverter:
    def __init__(self, inp_text: str):
        self._lines = inp_text.splitlines()
        self.nodes: Dict[int, Tuple[float, float, float]] = {}
        self.elements: Dict[str, List[Tuple]] = {}  # elset_name → [(eid, n1,n2,n3,n4),...]
        self.materials: Dict[str, dict] = {}
        self.sections: List[Tuple[str, str]] = []   # [(elset, mat_name),...]
        self.amplitudes: Dict[str, List[Tuple[float, float]]] = {}
        self.boundaries: List[dict] = []
        self.contact_pairs: List[Tuple[str, str]] = []
        self.step_end_time: float = 0.035
        self.dt_min: float = 5e-7
        self._parse()

    # ── パーサ ────────────────────────────────────────────────────────────────

    def _parse(self):
        i = 0
        lines = self._lines
        while i < len(lines):
            raw = lines[i].strip()
            low = raw.lower()

            if low.startswith('*node') and not low.startswith('*node print') \
                    and not low.startswith('*node output'):
                i = self._parse_nodes(i + 1)
            elif low.startswith('*element'):
                elset = self._kw_param(raw, 'elset') or f'part_{len(self.elements)}'
                i = self._parse_elements(i + 1, elset)
            elif low.startswith('*material'):
                name = self._kw_param(raw, 'name') or f'mat_{len(self.materials)}'
                i = self._parse_material(i + 1, name)
            elif low.startswith('*solid section'):
                elset  = self._kw_param(raw, 'elset') or ''
                mat    = self._kw_param(raw, 'material') or ''
                self.sections.append((elset, mat))
                i += 1
            elif low.startswith('*amplitude'):
                name = self._kw_param(raw, 'name') or f'amp_{len(self.amplitudes)}'
                i = self._parse_amplitude(i + 1, name)
            elif low.startswith('*contact pair'):
                i = self._parse_contact_pairs(i + 1)
            elif low.startswith('*boundary'):
                amp = self._kw_param(raw, 'amplitude')
                i = self._parse_boundary(i + 1, amp)
            elif low.startswith('*dynamic'):
                # *Dynamic, ...\n  dt_init, end_time, dt_min, dt_max
                if i + 1 < len(lines):
                    vals = [v.strip() for v in lines[i + 1].split(',')]
                    try:
                        self.step_end_time = float(vals[1])
                        self.dt_min        = float(vals[2]) if len(vals) > 2 else 5e-7
                    except (ValueError, IndexError):
                        pass
                i += 2
            else:
                i += 1

    def _kw_param(self, line: str, key: str) -> Optional[str]:
        m = re.search(rf'{key}\s*=\s*([^,\n]+)', line, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _is_keyword(self, line: str) -> bool:
        s = line.strip()
        return s.startswith('*') and not s.startswith('**')

    def _parse_nodes(self, start: int) -> int:
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            if not raw or raw.startswith('**'):
                i += 1
                continue
            if self._is_keyword(raw):
                break
            parts = raw.split(',')
            if len(parts) >= 4:
                nid = int(parts[0])
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                self.nodes[nid] = (x * _MM_TO_M, y * _MM_TO_M, z * _MM_TO_M)
            i += 1
        return i

    def _parse_elements(self, start: int, elset: str) -> int:
        elems = self.elements.setdefault(elset, [])
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            if not raw or raw.startswith('**'):
                i += 1
                continue
            if self._is_keyword(raw):
                break
            parts = raw.split(',')
            if len(parts) >= 5:
                eid = int(parts[0])
                ns  = [int(p) for p in parts[1:5]]
                elems.append((eid, ns[0], ns[1], ns[2], ns[3]))
            i += 1
        return i

    def _parse_material(self, start: int, name: str) -> int:
        mat = {'name': name, 'density': 7800.0, 'E': 2.1e11, 'nu': 0.28,
               'plastic': None}
        self.materials[name] = mat
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            low = raw.lower()
            if self._is_keyword(raw) and not low.startswith('*density') \
                    and not low.startswith('*elastic') \
                    and not low.startswith('*plastic') \
                    and not low.startswith('*expansion') \
                    and not low.startswith('*conductivity') \
                    and not low.startswith('*specific heat'):
                break
            if low.startswith('*density'):
                i += 1
                if i < len(self._lines):
                    try:
                        rho_inp = float(self._lines[i].strip().split(',')[0])
                        mat['density'] = rho_inp * _DENSITY_FACTOR
                    except ValueError:
                        pass
            elif low.startswith('*elastic'):
                i += 1
                if i < len(self._lines):
                    vals = self._lines[i].strip().split(',')
                    try:
                        mat['E']  = float(vals[0]) * _MODULUS_FACTOR
                        mat['nu'] = float(vals[1]) if len(vals) > 1 else 0.3
                    except ValueError:
                        pass
            elif low.startswith('*plastic'):
                plastic_pts = []
                i += 1
                while i < len(self._lines):
                    pr = self._lines[i].strip()
                    if not pr or pr.startswith('**') or self._is_keyword(pr):
                        break
                    vals = pr.split(',')
                    if len(vals) >= 2:
                        try:
                            plastic_pts.append((float(vals[0]) * _STRESS_FACTOR,
                                                float(vals[1])))
                        except ValueError:
                            pass
                    i += 1
                mat['plastic'] = plastic_pts
                continue
            i += 1
        return i

    def _parse_amplitude(self, start: int, name: str) -> int:
        pts: List[Tuple[float, float]] = []
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            if not raw or raw.startswith('**'):
                i += 1
                continue
            if self._is_keyword(raw):
                break
            vals = [v.strip() for v in raw.split(',')]
            for j in range(0, len(vals) - 1, 2):
                try:
                    pts.append((float(vals[j]), float(vals[j + 1])))
                except ValueError:
                    pass
            i += 1
        self.amplitudes[name] = pts
        return i

    def _parse_contact_pairs(self, start: int) -> int:
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            if not raw or raw.startswith('**'):
                i += 1
                continue
            if self._is_keyword(raw):
                break
            parts = [p.strip() for p in raw.split(',')]
            if len(parts) >= 2:
                self.contact_pairs.append((parts[0], parts[1]))
            i += 1
        return i

    def _parse_boundary(self, start: int, amplitude: Optional[str]) -> int:
        i = start
        while i < len(self._lines):
            raw = self._lines[i].strip()
            if not raw or raw.startswith('**'):
                i += 1
                continue
            if self._is_keyword(raw):
                break
            parts = [p.strip() for p in raw.split(',')]
            if len(parts) >= 3:
                try:
                    nid  = int(parts[0])
                    dof1 = int(parts[1])
                    dof2 = int(parts[2])
                    val  = float(parts[3]) if len(parts) > 3 else 0.0
                    self.boundaries.append({
                        'node': nid, 'dof1': dof1, 'dof2': dof2,
                        'value': val * _MM_TO_M, 'amplitude': amplitude
                    })
                except ValueError:
                    pass
            i += 1
        return i

    # ── RAD 生成 ──────────────────────────────────────────────────────────────

    def _build_parts(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """elset→prop_id, elset→mat_id のマッピングを返す"""
        mat_ids   = {name: idx + 1 for idx, name in enumerate(self.materials)}
        prop_ids:  Dict[str, int] = {}
        mat_map:   Dict[str, int] = {}
        prop_counter = 1
        for elset, mat_name in self.sections:
            prop_ids[elset] = prop_counter
            mat_map[elset]  = mat_ids.get(mat_name, 1)
            prop_counter += 1
        return prop_ids, mat_map, mat_ids

    def generate_starter(self, title: str = 'Converted from Prepomax') -> str:
        prop_ids, elset_mat_map, mat_ids = self._build_parts()

        lines = []
        lines.append('#RADIOSS STARTER')
        lines.append('/BEGIN')
        lines.append(title)
        lines.append('      2022         0')
        lines.append('                  kg                   m                   s')
        lines.append('                  kg                   m                   s')
        lines.append('/TITLE')
        lines.append(title)

        # ── ノード ─────────────────────────────────────────────────────────────
        lines.append('/NODE')
        for nid, (x, y, z) in sorted(self.nodes.items()):
            lines.append(f'{nid:>10d} {x:>20.12E} {y:>20.12E} {z:>20.12E}')

        # ── 要素 ──────────────────────────────────────────────────────────────
        for elset, elems in self.elements.items():
            part_id = list(self.elements.keys()).index(elset) + 1
            lines.append(f'/TETRA4/{part_id}')
            for eid, n1, n2, n3, n4 in elems:
                lines.append(f'{eid:>10d}{n1:>10d}{n2:>10d}{n3:>10d}{n4:>10d}')

        # ── 材料 ──────────────────────────────────────────────────────────────
        for mat_name, mat in self.materials.items():
            mid = mat_ids[mat_name]
            if mat['plastic']:
                # LAW2 (弾塑性)
                sy  = mat['plastic'][0][0] if mat['plastic'] else 2e8
                uts = mat['plastic'][-1][0] if len(mat['plastic']) > 1 else sy * 1.5
                eps_max = mat['plastic'][-1][1] if mat['plastic'] else 1.0
                # 冪乗硬化近似: n ≈ 最終塑性歪み
                n = max(0.05, min(0.5, eps_max))
                lines.append(f'/MAT/LAW2/{mid}')
                lines.append(mat_name)
                lines.append(f'#              RHO_I')
                lines.append(f'           {mat["density"]:.4f}')
                lines.append(f'#                  E                  NU')
                lines.append(f'          {mat["E"]:.4E}               {mat["nu"]:.3f}')
                b = max(0.0, uts - sy)
                lines.append(f'#                  a                   b                   n'
                              f'           EPS_p_max               Xmax')
                lines.append(f'          {sy:.4E}           {b:.4E}                {n:.4f}'
                              f'               {eps_max:.2f}               5.0')
                for _ in range(3):
                    lines.append('                 0.0                 0.0                 0.0'
                                 '                 0.0                 0.0')
            else:
                # LAW1 (弾性)
                lines.append(f'/MAT/LAW1/{mid}')
                lines.append(mat_name)
                lines.append(f'#              RHO_I')
                lines.append(f'           {mat["density"]:.4f}')
                lines.append(f'#                  E                  NU')
                lines.append(f'          {mat["E"]:.4E}               {mat["nu"]:.3f}')
                lines.append('                   0                   0                   0'
                             '                   0                   0')

        # ── プロパティ（SOLID） ───────────────────────────────────────────────
        for elset, pid in prop_ids.items():
            lines.append(f'/PROP/SOLID/{pid}')
            lines.append(f'#   Isolid    Ismstr                               Dn'
                         f'                Qa                Hm')
            lines.append('        14         4             0.00000             0.00000'
                         '             0.50000')
            lines.append('                   0                   0                   0'
                         '                   0                   0')

        # ── スキンシェルプロパティ（接触用） ──────────────────────────────────
        lines.append('/PROP/SHELL/999')
        lines.append('Skin_Property')
        lines.append('#   Ishell    Ismstr      Ish3n    Idrill')
        lines.append('         1         2         2         0')
        lines.append('             0.00000             0.00000             0.00000'
                     '             0.00000             0.00000')
        lines.append('             5.00000             0.00100             0.00000'
                     '             0.00000             0.00000             0.00000')
        lines.append('                   0                   0                   0'
                     '                   0                   0')

        # ── PART ─────────────────────────────────────────────────────────────
        for elset in self.elements:
            part_id = list(self.elements.keys()).index(elset) + 1
            pid     = prop_ids.get(elset, 1)
            mid     = elset_mat_map.get(elset, 1)
            lines.append(f'/PART/{part_id}')
            lines.append(elset)
            lines.append(f'#    Prop_ID     Mat_ID')
            lines.append(f'         {pid}         {mid}')

        # ── スキンサーフェス PART ────────────────────────────────────────────
        for elset in self.elements:
            part_id    = list(self.elements.keys()).index(elset) + 1
            skin_part  = part_id + 100
            mid        = elset_mat_map.get(elset, 1)
            lines.append(f'/PART/{skin_part}')
            lines.append(f'{elset}_Skin')
            lines.append(f'#    Prop_ID     Mat_ID')
            lines.append(f'       999         {mid}')

        # ── サーフェス定義 ───────────────────────────────────────────────────
        for elset in self.elements:
            part_id    = list(self.elements.keys()).index(elset) + 1
            skin_part  = part_id + 100
            surf_id    = part_id * 100 + 200
            lines.append(f'/SURF/PART/{surf_id}/0')
            lines.append(f'{elset}_Skin_Surf')
            lines.append(f'       {skin_part}')
            lines.append('')

        # ── 振幅関数 /FUNCT ───────────────────────────────────────────────────
        funct_id_map: Dict[str, int] = {}
        funct_counter = 1
        for amp_name, pts in self.amplitudes.items():
            funct_id_map[amp_name] = funct_counter
            lines.append(f'/FUNCT/{funct_counter}')
            lines.append(amp_name)
            for t, v in pts:
                lines.append(f'             {t:.5f}            {v:.5f}')
            funct_counter += 1
        # 固定0関数
        funct_id_map['__zero__'] = funct_counter
        lines.append(f'/FUNCT/{funct_counter}')
        lines.append('Zero_Velocity')
        lines.append('             0.00000            0.00000')
        lines.append('             1.00000            0.00000')
        funct_counter += 1

        # ── 剛体ノード収集 /GRNOD/NODE ────────────────────────────────────────
        # *Boundary で拘束されるノードをリジッドボディとして扱う
        rigid_nodes = sorted({b['node'] for b in self.boundaries})
        impvel_entries: List[dict] = []
        impvel_counter = 1
        dof_label = {1: 'X', 2: 'Y', 3: 'Z'}

        for b in self.boundaries:
            nid  = b['node']
            amp  = b['amplitude']
            val  = b['value']
            gid  = nid * 10  # グループID = ノードID×10

            lines.append(f'/GRNOD/NODE/{gid}')
            lines.append(f'Node_Group_{nid}')
            lines.append(f'{nid:>10d}')

            for dof in range(b['dof1'], b['dof2'] + 1):
                if dof > 3:
                    continue
                dir_label = dof_label.get(dof, 'X')
                if amp and amp in funct_id_map and val != 0.0:
                    fid = funct_id_map[amp]
                else:
                    fid = funct_id_map['__zero__']
                impvel_entries.append({
                    'id': impvel_counter,
                    'label': f'Node{nid}_{dir_label}',
                    'fid': fid,
                    'dir': dir_label,
                    'gid': gid,
                    'scale': val,
                })
                impvel_counter += 1

        # ── /IMPVEL ────────────────────────────────────────────────────────────
        for iv in impvel_entries:
            lines.append(f'/IMPVEL/{iv["id"]}')
            lines.append(iv['label'])
            lines.append(f'#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID'
                         f'     Icoor    Iframe')
            lines.append(f'         {iv["fid"]}         {iv["dir"]}         0'
                         f'         0       {iv["gid"]}         0         0')
            lines.append(f'#             Ascale_x            Fscale_y'
                         f'            Tstart              Tstop')
            lines.append(f'             1.00000             1.00000'
                         f'             0.00000         1.00000E+30')

        # ── /INTER/TYPE25 接触 ────────────────────────────────────────────────
        elset_names = list(self.elements.keys())
        for ci, (slave, master) in enumerate(self.contact_pairs, start=1):
            # サーフェスIDをノード名から推定
            def _surf_id(name: str) -> int:
                for idx, es in enumerate(elset_names):
                    if es.lower() in name.lower() or name.lower() in es.lower():
                        return (idx + 1) * 100 + 200
                return (ci) * 100 + 200

            sid1 = _surf_id(slave)
            sid2 = _surf_id(master)
            lines.append(f'/INTER/TYPE25/{ci}/0')
            lines.append(f'Contact_{ci}')
            lines.append('#  surf_ID1  surf_ID2      Istf      Igap   Irem_i2'
                         '      Idel     Iedge')
            lines.append(f'       {sid1}       {sid2}         4         3'
                         f'         3         1         0')
            lines.append('#  grnd_IDs             Gap_scale           %mesh_size'
                         '              Gap_max_s              Gap_max_m')
            lines.append('         0                   1.0                  0.4'
                         '                 0.15                 0.15')
            lines.append('#                 Stmin                 Stmax     Igap0'
                         '    Ishape               Edge_angle')
            lines.append('                    0.0               1.0E30         0'
                         '         1                  135.0')
            lines.append('#                 Stfac                  Fric'
                         '               Tstart                 Tstop')
            lines.append('               1.0E-4                   0.1'
                         '                  0.0               1.0E30')
            lines.append('#      I_BC     IVIS2    Inacti                  VISs')
            lines.append('         0         0         0                   0.0')
            lines.append('#     Ifric    Ifiltr                 Xfreq   sens_ID'
                         '   fric_ID')
            lines.append('         0         0                   0.0         0         0')

        lines.append('/END')
        return '\n'.join(lines) + '\n'

    def generate_engine(self, title: str = 'Converted from Prepomax') -> str:
        dt_anim = self.step_end_time / 40.0
        lines = []
        lines.append(f'/RUN/{title}/1')
        lines.append(f'             {self.step_end_time:.7f}')
        lines.append('/DT/NODA/CST/0')
        lines.append(f'             0.90000             {self.dt_min:.2E}')
        lines.append('/RFILE/200000')
        lines.append('/ANIM/DT')
        lines.append(f'             0.0000000000         {dt_anim:.5E}')
        lines.append('/ANIM/ELEM/EPSP')
        lines.append('/ANIM/ELEM/VONM')
        lines.append('/ANIM/ELEM/ENER')
        lines.append('/ANIM/ELEM/SIGX')
        lines.append('/ANIM/ELEM/SIGY')
        lines.append('/ANIM/ELEM/SIGZ')
        lines.append('/ANIM/ELEM/SIGXY')
        lines.append('/ANIM/ELEM/SIGYZ')
        lines.append('/ANIM/ELEM/SIGZX')
        lines.append('/ANIM/VECT/DISP')
        lines.append('/ANIM/VECT/VEL')
        lines.append('/END')
        return '\n'.join(lines) + '\n'


def convert(inp_path: str, out_dir: str) -> dict:
    """
    .inp を読み込み、_0000.rad と _0001.rad を out_dir に書き出す。
    戻り値: {'starter': path, 'engine': path, 'warnings': [...]}
    """
    inp_text = Path(inp_path).read_text(encoding='utf-8', errors='replace')
    stem     = Path(inp_path).stem
    today    = __import__('datetime').date.today().strftime('%Y%m%d')
    base     = f'{stem}_{today}'

    conv = InpConverter(inp_text)
    warnings = []

    if not conv.nodes:
        warnings.append('ノードが見つかりません。*Node セクションを確認してください。')
    if not conv.elements:
        warnings.append('要素が見つかりません。C3D4以外の要素は非対応です。')
    if not conv.materials:
        warnings.append('材料が見つかりません。')

    title = f'Converted_{stem}'
    starter_text = conv.generate_starter(title)
    engine_text  = conv.generate_engine(title)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    starter_path = out / f'{base}_0000.rad'
    engine_path  = out / f'{base}_0001.rad'

    starter_path.write_text(starter_text, encoding='utf-8')
    engine_path.write_text(engine_text,   encoding='utf-8')

    return {
        'starter':  str(starter_path),
        'engine':   str(engine_path),
        'base':     base,
        'stats': {
            'nodes':     len(conv.nodes),
            'elements':  sum(len(e) for e in conv.elements.values()),
            'parts':     len(conv.elements),
            'materials': len(conv.materials),
            'contacts':  len(conv.contact_pairs),
            'end_time':  conv.step_end_time,
        },
        'warnings': warnings,
    }
