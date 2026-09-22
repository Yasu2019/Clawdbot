# -*- coding: utf-8 -*-
"""INC-188レポート用: ダイ・ストリッパー・パンチ(矩形/トリム/丸)・材料(ブランク)の
アイソメトリック配置図。t=0(未変形)フレームの実メッシュ境界面をパーツ別に色分けして描く。
使い方: python render_tooling_isometric.py <f01.vtk> <out.png>

注記: 最終デックではPART=4に3つのパンチ形状が全て入っている(build_panel4mm_3d_blanking.py
の"通し番号へ詰め替え"処理でtag情報が失われるため)。ここでは各要素のz最小値が、標準順番
(矩形zmin=1.8mm/トリム=2.4mm/丸=3.0mm)のどれに近いかで判別する。この図はP1r7(標準順番)の
t=0フレームで使うこと(順番を入れ替えたRunでは判別が狂う)。
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Noto Sans JP"
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\scripts\inc188_analysis")
from render_mesh_faces import load, boundary_faces  # noqa: E402

path, out = sys.argv[1], sys.argv[2]
pts, cells, part, ero, vm, tens, t = load(path)

PART_COLOR = {1: "#6d6d6d", 2: "#c8b98a", 3: "#4a7fb5"}
PART_LABEL = {1: "ダイ", 2: "材料(ブランク)", 3: "ストリッパー"}
PART_ALPHA = {1: 0.55, 2: 0.9, 3: 0.35}
PUNCH_COLOR = {"rect": "#c0392b", "trim": "#e67e22", "round": "#8e44ad"}
PUNCH_LABEL = {"rect": "矩形パンチ", "trim": "トリムパンチ", "round": "丸パンチ"}
PUNCH_ZMIN_REF = {"rect": 1.8e-3, "trim": 2.4e-3, "round": 3.0e-3}

# matplotlibの3D半透明面は奥行きの前後判定が不完全で、Z位置が近い部品が埋没して見えなくなる。
# 各部品をZ方向に一定量ずらして重なりを避ける「展開図(分解アイソメ)」にする(位置関係はスケール外)。
EXPLODE = 1.2e-3
fig = plt.figure(figsize=(14.0, 12.0), dpi=160)
ax = fig.add_subplot(111, projection="3d")
xs_all, ys_all, zs_all = [], [], []


def add(idxs, color, alpha, zshift):
    if not idxs:
        return
    faces = boundary_faces(cells, idxs)
    tris = np.array([[pts[n] for n in tri] for _, tri in faces])
    tris = tris.copy(); tris[:, :, 2] += zshift
    pc = Poly3DCollection(tris, facecolors=[color] * len(tris), edgecolor="none", alpha=alpha, shade=True)
    ax.add_collection3d(pc)
    xs_all.append(tris[:, :, 0].ravel())
    ys_all.append(tris[:, :, 1].ravel())
    zs_all.append(tris[:, :, 2].ravel())


add([i for i, p in enumerate(part) if p == 1], PART_COLOR[1], PART_ALPHA[1], 0.0)
add([i for i, p in enumerate(part) if p == 3], PART_COLOR[3], PART_ALPHA[3], EXPLODE)
add([i for i, p in enumerate(part) if p == 2], PART_COLOR[2], PART_ALPHA[2], 2 * EXPLODE)

punch_idx = [i for i, p in enumerate(part) if p == 4]
bucket = {"rect": [], "trim": [], "round": []}
TIP_TOL = 0.15e-3  # 各パンチ先端(zmin近傍)だけを描く。中腹は3形状のZ範囲が重なり誤分類するため
for i in punch_idx:
    zmin_i = min(pts[n][2] for n in cells[i])
    for shape, ref in PUNCH_ZMIN_REF.items():
        if abs(zmin_i - ref) < TIP_TOL:
            bucket[shape].append(i)
            break
for k, shape in enumerate(("rect", "trim", "round")):
    add(bucket[shape], PUNCH_COLOR[shape], 0.9, (3 + k) * EXPLODE)

xs = np.concatenate(xs_all); ys = np.concatenate(ys_all); zs = np.concatenate(zs_all)
ax.set_xlim(xs.min(), xs.max()); ax.set_ylim(ys.min(), ys.max()); ax.set_zlim(zs.min(), zs.max())
ax.view_init(elev=22.0, azim=-50.0)
ax.set_box_aspect((xs.max() - xs.min(), ys.max() - ys.min(), (zs.max() - zs.min())))
ax.set_title("INC-188 PANEL4MM  工具配置(分解アイソメ図、t=0未変形、Z方向は視認性のため展開表示)", fontsize=15)
ax.set_xlabel("x [m]", fontsize=11); ax.set_ylabel("y [m]", fontsize=11); ax.set_zlabel("z [m]", fontsize=11)
ax.tick_params(labelsize=9)

order = [(1, PART_COLOR[1], PART_LABEL[1], PART_ALPHA[1]),
         (3, PART_COLOR[3], PART_LABEL[3], PART_ALPHA[3]),
         ("rect", PUNCH_COLOR["rect"], PUNCH_LABEL["rect"], 0.9),
         ("trim", PUNCH_COLOR["trim"], PUNCH_LABEL["trim"], 0.9),
         ("round", PUNCH_COLOR["round"], PUNCH_LABEL["round"], 0.9),
         (2, PART_COLOR[2], PART_LABEL[2], PART_ALPHA[2])]
handles = [plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=14, alpha=a) for _, c, _, a in order]
labels = [lbl for _, _, lbl, _ in order]
ax.legend(handles, labels, loc="upper left", fontsize=12, framealpha=0.9)

fig.savefig(out, dpi=160)
print("saved", out)
