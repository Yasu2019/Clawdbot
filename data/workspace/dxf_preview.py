#!/usr/bin/env python3
"""
dxf_preview.py - DXFと3DモデルをPNGで可視化してVS Codeで確認できるようにする

Usage (host):
  python3 data/workspace/dxf_preview.py <dxf_file> [--step <step_file>] [--layer <layer>] [--out <output_dir>]

Usage (Docker経由で3Dレンダリング):
  python3 data/workspace/dxf_preview.py <dxf_file> --step <step_file> --docker
"""
import argparse
import math
import sys
from pathlib import Path


def render_dxf_png(dxf_path: Path, out_path: Path, layer: str = ""):
    """ezdxf + matplotlib でDXFを2D PNG出力"""
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.patch.set_facecolor('#1e1e1e')

    # --- 左: 全体ビュー ---
    ax_all = axes[0]
    ax_all.set_facecolor('#1e1e1e')
    ax_all.set_title("全体ビュー (全レイヤー)", color='white', fontsize=11)

    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax_all)
    frontend = Frontend(ctx, backend)
    frontend.draw_layout(msp)

    ax_all.set_aspect('equal')
    ax_all.tick_params(colors='gray')
    ax_all.spines[:].set_color('gray')
    for spine in ax_all.spines.values():
        spine.set_edgecolor('gray')

    # --- 右: 指定レイヤーのみ ---
    ax_layer = axes[1]
    ax_layer.set_facecolor('#1e1e1e')
    layer_title = f"レイヤー '{layer}' のみ" if layer else "全レイヤー"
    ax_layer.set_title(layer_title, color='white', fontsize=11)

    # 手動でエンティティを描画
    colors = {'LINE': '#4FC3F7', 'ARC': '#FFD54F', 'CIRCLE': '#A5D6A7',
              'LWPOLYLINE': '#F48FB1', 'TEXT': '#CE93D8'}

    xs_all, ys_all = [], []
    N_ARC = 64

    for e in msp:
        if layer and e.dxf.layer != layer:
            continue
        t = e.dxftype()
        color = colors.get(t, '#90A4AE')
        lw = 0.7

        try:
            if t == 'LINE':
                x = [e.dxf.start.x, e.dxf.end.x]
                y = [e.dxf.start.y, e.dxf.end.y]
                ax_layer.plot(x, y, color=color, lw=lw)
                xs_all += x; ys_all += y

            elif t == 'CIRCLE':
                cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
                angles = [2 * math.pi * i / N_ARC for i in range(N_ARC + 1)]
                ax_layer.plot([cx + r * math.cos(a) for a in angles],
                              [cy + r * math.sin(a) for a in angles],
                              color=color, lw=lw)
                xs_all += [cx - r, cx + r]; ys_all += [cy - r, cy + r]

            elif t == 'ARC':
                cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
                sa, ea = math.radians(e.dxf.start_angle), math.radians(e.dxf.end_angle)
                if ea < sa:
                    ea += 2 * math.pi
                angles = [sa + (ea - sa) * i / N_ARC for i in range(N_ARC + 1)]
                ax_layer.plot([cx + r * math.cos(a) for a in angles],
                              [cy + r * math.sin(a) for a in angles],
                              color=color, lw=lw)
                xs_all += [cx - r, cx + r]; ys_all += [cy - r, cy + r]

            elif t in ('LWPOLYLINE', 'POLYLINE'):
                pts = list(e.get_points('xy'))
                if pts:
                    xp = [p[0] for p in pts]
                    yp = [p[1] for p in pts]
                    if e.closed:
                        xp.append(xp[0]); yp.append(yp[0])
                    ax_layer.plot(xp, yp, color=color, lw=lw)
                    xs_all += xp; ys_all += yp
        except Exception:
            pass

    ax_layer.set_aspect('equal')
    ax_layer.tick_params(colors='gray')
    for spine in ax_layer.spines.values():
        spine.set_edgecolor('gray')

    if xs_all and ys_all:
        mx, my = (max(xs_all) + min(xs_all)) / 2, (max(ys_all) + min(ys_all)) / 2
        span = max(max(xs_all) - min(xs_all), max(ys_all) - min(ys_all)) * 0.55
        ax_layer.set_xlim(mx - span, mx + span)
        ax_layer.set_ylim(my - span, my + span)

    # 凡例
    legend = [mpatches.Patch(color=c, label=t) for t, c in colors.items()]
    ax_layer.legend(handles=legend, loc='upper right', fontsize=7,
                    facecolor='#2d2d2d', edgecolor='gray', labelcolor='white')

    # 統計テキスト
    from collections import Counter
    cnt = Counter(e.dxftype() for e in msp if not layer or e.dxf.layer == layer)
    stats = "  ".join(f"{t}:{n}" for t, n in cnt.most_common(5))
    fig.text(0.5, 0.02, f"ファイル: {dxf_path.name}  |  {stats}",
             ha='center', color='#aaaaaa', fontsize=9)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(str(out_path), dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close(fig)
    print(f"[DXF PNG] → {out_path}")


def render_3d_png_freecad(step_path: Path, out_path: Path):
    """FreeCAD headless で3D等角投影PNGを生成 (Antigravityコンテナ内で実行)"""
    import subprocess, os, tempfile, importlib.util

    script = f'''
import FreeCAD as App, Part
import math

shape = Part.Shape()
shape.read('{step_path}')
print(f"Faces: {{len(shape.Faces)}}, Volume: {{shape.Volume:.1f}} mm3")

# 等角投影: XYZ方向から45度
import FreeCAD as App
from FreeCAD import Vector

# Bounding box 中心
bb = shape.BoundBox
cx = (bb.XMin + bb.XMax) / 2
cy = (bb.YMin + bb.YMax) / 2
cz = (bb.ZMin + bb.ZMax) / 2

# 各方向に投影 (Front/Top/Isometric)
views = [
    ("正面 (Front XZ)", Vector(0, -1, 0), Vector(0, 0, 1)),
    ("上面 (Top XY)",   Vector(0, 0, -1), Vector(0, 1, 0)),
    ("等角 (ISO)",      Vector(-1, -1, 1).normalize(), Vector(0, 0, 1)),
]

results = []
for name, direction, up in views:
    proj = shape.project([shape], direction)
    edges = proj.Edges
    results.append((name, edges, direction))

# matplotlib でプロット
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

fig = plt.figure(figsize=(18, 6))
fig.patch.set_facecolor('#1e1e1e')

# 3Dビューを3アングルで表示
angles = [
    ("正面", 0, 0),
    ("等角", 30, -45),
    ("上面", 90, -90),
]

# STEPからメッシュを作成
mesh = shape.tessellate(0.5)
verts = [(v.x, v.y, v.z) for v in mesh[0]]
faces_idx = mesh[1]

for idx, (title, elev, azim) in enumerate(angles):
    ax = fig.add_subplot(1, 3, idx + 1, projection='3d')
    ax.set_facecolor('#1e1e1e')
    ax.set_title(title, color='white', fontsize=11)

    if verts and faces_idx:
        tris = [[verts[i] for i in f] for f in faces_idx]
        poly = Poly3DCollection(tris, alpha=0.85, linewidth=0.1)
        poly.set_facecolor('#5B9BD5')
        poly.set_edgecolor('#2E5F8A')
        ax.add_collection3d(poly)

        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        ax.set_xlim(min(xs), max(xs))
        ax.set_ylim(min(ys), max(ys))
        ax.set_zlim(min(zs), max(zs))

    ax.view_init(elev=elev, azim=azim)
    ax.tick_params(colors='gray', labelsize=6)
    ax.set_xlabel('X', color='#FF6B6B', fontsize=8)
    ax.set_ylabel('Y', color='#51CF66', fontsize=8)
    ax.set_zlabel('Z', color='#74C0FC', fontsize=8)
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor('#444444')

bb_info = f"BBox: {bb.XMax-bb.XMin:.1f} x {bb.YMax-bb.YMin:.1f} x {bb.ZMax-bb.ZMin:.1f} mm"
vol_info = f"Volume: {shape.Volume:.0f} mm³  |  Faces: {len(shape.Faces)}"
fig.text(0.5, 0.02, f"{bb_info}  |  {vol_info}", ha='center', color='#aaaaaa', fontsize=9)

plt.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig('{out_path}', dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
plt.close()
print(f"[3D PNG] saved")
'''

    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False, encoding='utf-8') as f:
        f.write(script)
        tmp = f.name

    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'LIBGL_ALWAYS_SOFTWARE': '1'}
    freecadcmd = os.environ.get('FREECADCMD', '/opt/freecad/usr/bin/freecadcmd')
    p = subprocess.run([freecadcmd, tmp],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, env=env, timeout=120)
    os.unlink(tmp)
    for line in p.stdout.split('\n'):
        if any(kw in line for kw in ['Faces', 'Volume', '3D PNG', 'Error', 'error', 'Traceback']):
            print(line)
    if p.returncode != 0:
        raise RuntimeError(f"FreeCAD failed (RC={p.returncode})")
    print(f"[3D PNG] → {out_path}")


def render_3d_png_via_docker(step_path_host: Path, out_path_host: Path,
                             container: str = "clawstack-unified-antigravity-1"):
    """Docker Antigravityコンテナ内でFreeCAD tessellate → PNG (ホストから呼び出し)"""
    import subprocess, os, tempfile

    # ホストパスをコンテナ内パスに変換 (/work マウント)
    work_host = Path("D:/Clawdbot_Docker_20260125/clawstack_v2/data/work")
    try:
        step_rel = step_path_host.resolve().relative_to(work_host.resolve())
        step_container = f"/work/{step_rel.as_posix()}"
        out_rel = out_path_host.resolve().relative_to(work_host.resolve())
        out_container = f"/work/{out_rel.as_posix()}"
    except ValueError:
        # /work マウント外の場合は docker cp で転送
        step_container = "/tmp/preview_input.step"
        out_container = "/tmp/preview_output.png"
        subprocess.run(["docker", "cp", str(step_path_host),
                        f"{container}:{step_container}"], check=True)

    # Note: use simple string replace to substitute only STEP/OUT paths (avoids {} conflicts)
    script = ("""
import FreeCAD as App, Part
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

shape = Part.Shape()
shape.read('__STEP__')
bb = shape.BoundBox
mesh = shape.tessellate(1.0)
verts = [(v.x, v.y, v.z) for v in mesh[0]]
faces_idx = mesh[1]
tris = [[verts[i] for i in f] for f in faces_idx] if faces_idx else []

fig = plt.figure(figsize=(18, 7))
fig.patch.set_facecolor("#1a1a2e")
views = [("Front", 5, -90), ("ISO", 25, -50), ("Top", 88, -90)]

for idx, (title, elev, azim) in enumerate(views):
    ax = fig.add_subplot(1, 3, idx+1, projection="3d")
    ax.set_facecolor("#1a1a2e")
    ax.set_title(title, color="white", fontsize=13, fontweight="bold")
    if tris:
        poly = Poly3DCollection(tris, alpha=0.9, linewidth=0.05)
        poly.set_facecolor("#3a86ff")
        poly.set_edgecolor("#1d3a8a")
        ax.add_collection3d(poly)
        m = 5
        ax.set_xlim(bb.XMin-m, bb.XMax+m)
        ax.set_ylim(bb.YMin-m, bb.YMax+m)
        ax.set_zlim(bb.ZMin-1, bb.ZMax+1)
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("X", color="#ff6b6b", fontsize=9)
    ax.set_ylabel("Y", color="#51cf66", fontsize=9)
    ax.set_zlabel("Z", color="#74c0fc", fontsize=9)
    ax.tick_params(colors="gray", labelsize=6)
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor("#333355")

w = bb.XMax-bb.XMin; h = bb.YMax-bb.YMin; d = bb.ZMax-bb.ZMin
info = f"{w:.1f} x {h:.1f} x {d:.1f} mm  Faces:{len(shape.Faces)}  Vol:{shape.Volume:.0f} mm3"
fig.text(0.5, 0.02, info, ha="center", color="#aaaacc", fontsize=10)
plt.tight_layout(rect=[0, 0.06, 1, 0.97])
fig.savefig('__OUT__', dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
plt.close()
print("3D render done")
""").replace('__STEP__', step_container).replace('__OUT__', out_container)
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False,
                                     encoding='utf-8') as f:
        f.write(script)
        tmp_host = f.name

    tmp_container = f"/tmp/render3d_{os.getpid()}.py"
    subprocess.run(["docker", "cp", tmp_host, f"{container}:{tmp_container}"], check=True)
    os.unlink(tmp_host)

    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'LIBGL_ALWAYS_SOFTWARE': '1'}
    r = subprocess.run(
        ["docker", "exec", "-e", "QT_QPA_PLATFORM=offscreen", "-e", "LIBGL_ALWAYS_SOFTWARE=1",
         container, "/opt/freecad/usr/bin/freecadcmd", tmp_container],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    subprocess.run(["docker", "exec", container, "rm", "-f", tmp_container])

    for line in r.stdout.split('\n'):
        if any(kw in line for kw in ['BBox', 'Faces', 'done', 'Error', 'error', 'rror']):
            print(f"  [FreeCAD] {line}")

    # out_container が /tmp の場合はコピーして戻す
    if out_container.startswith('/tmp/'):
        subprocess.run(["docker", "cp", f"{container}:{out_container}", str(out_path_host)], check=True)

    print(f"[3D PNG] -> {out_path_host}")


def render_3d_png_matplotlib(step_path: Path, loops_json: Path, out_path: Path, height: float = 5.0):
    """ezdxf ループデータからmatplotlib 3Dで簡易レンダリング (FreeCAD不要)"""
    import json
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    with open(loops_json) as f:
        loops = json.load(f)['loops']

    fig = plt.figure(figsize=(18, 6))
    fig.patch.set_facecolor('#1e1e1e')

    angles_cfg = [("正面 (Front)", 0, -90), ("等角 (ISO)", 30, -60), ("上面 (Top)", 88, -90)]

    # ループから簡易ポリゴンを作り3D押し出し表現
    for idx, (title, elev, azim) in enumerate(angles_cfg):
        ax = fig.add_subplot(1, 3, idx + 1, projection='3d')
        ax.set_facecolor('#1e1e1e')
        ax.set_title(title, color='white', fontsize=11)

        # 各ループを上面・底面・側面として描画
        for loop in loops:
            n = len(loop)
            if n < 3:
                continue
            xs = [p[0] for p in loop]
            ys = [p[1] for p in loop]

            # 上面 (z=height)
            ax.plot(xs + [xs[0]], ys + [ys[0]], [height] * (n + 1),
                    color='#5B9BD5', lw=0.4, alpha=0.8)
            # 底面 (z=0)
            ax.plot(xs + [xs[0]], ys + [ys[0]], [0] * (n + 1),
                    color='#5B9BD5', lw=0.4, alpha=0.5)
            # 側面エッジ (点の間引き)
            step = max(1, n // 8)
            for i in range(0, n, step):
                ax.plot([xs[i], xs[i]], [ys[i], ys[i]], [0, height],
                        color='#2E5F8A', lw=0.3, alpha=0.4)

        ax.view_init(elev=elev, azim=azim)
        ax.tick_params(colors='gray', labelsize=6)
        ax.set_xlabel('X', color='#FF6B6B', fontsize=8)
        ax.set_ylabel('Y', color='#51CF66', fontsize=8)
        ax.set_zlabel('Z', color='#74C0FC', fontsize=8)
        for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
            pane.fill = False
            pane.set_edgecolor('#444444')

    n_loops = len(loops)
    fig.text(0.5, 0.02, f"ループ数: {n_loops}  |  押し出し高さ: {height}mm  |  {step_path.name}",
             ha='center', color='#aaaaaa', fontsize=9)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(str(out_path), dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close(fig)
    print(f"[3D PNG] → {out_path}")


def main():
    ap = argparse.ArgumentParser(description="DXF/STEP PNG preview generator")
    ap.add_argument("dxf", type=Path, help="DXF file path")
    ap.add_argument("--step", type=Path, help="STEP file path (optional)")
    ap.add_argument("--loops-json", type=Path, help="ezdxf loops JSON (fast 3D preview)")
    ap.add_argument("--layer", default="", help="Layer name to highlight")
    ap.add_argument("--height", type=float, default=5.0, help="Extrusion height (mm)")
    ap.add_argument("--out", type=Path, help="Output directory (default: same as DXF)")
    ap.add_argument("--docker", action="store_true", help="Use Docker Antigravity for FreeCAD render")
    args = ap.parse_args()

    out_dir = args.out or args.dxf.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = args.dxf.stem

    # 1. DXF → PNG
    dxf_png = out_dir / f"{stem}_dxf_preview.png"
    render_dxf_png(args.dxf, dxf_png, layer=args.layer)

    # 2. 3D → PNG
    model_png = None
    if args.step and args.step.exists():
        model_png = out_dir / f"{stem}_3d_preview.png"
        if args.docker:
            # FreeCAD tessellate via Antigravity Docker (high quality)
            try:
                render_3d_png_via_docker(args.step, model_png)
            except Exception as e:
                print(f"[WARN] Docker render failed: {e}", file=sys.stderr)
                if args.loops_json and args.loops_json.exists():
                    render_3d_png_matplotlib(args.step, args.loops_json, model_png, args.height)
        elif args.loops_json and args.loops_json.exists():
            # Wireframe from ezdxf loops (fast, no FreeCAD)
            render_3d_png_matplotlib(args.step, args.loops_json, model_png, args.height)
        else:
            # FreeCAD local
            try:
                render_3d_png_freecad(args.step, model_png)
            except Exception as e:
                print(f"[WARN] FreeCAD render failed: {e}", file=sys.stderr)
                print("[INFO] Use --docker or --loops-json for 3D rendering")

    print(f"\nDone. Open in VS Code:")
    print(f"  code \"{dxf_png}\"")
    if model_png:
        print(f"  code \"{model_png}\"")


if __name__ == "__main__":
    main()
