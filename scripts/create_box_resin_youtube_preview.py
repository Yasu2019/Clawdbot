# -*- coding: utf-8 -*-
"""Create a short YouTube-ready simplified resin-molding preview."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Polygon
from matplotlib.path import Path as MplPath


OUT = Path.home() / "Downloads" / "OpenFOAM_Box_Resin_6_Defects_English_Preview.mp4"
FPS = 24
DURATION = 38

BG = "#07111f"
PANEL = "#10243a"
EDGE = "#89a9c7"
RESIN = "#ff7a18"
HOT = "#ffd166"
AIR = "#65d6ff"
BAD = "#ff4567"
TEXT = "#f4f8fc"
MUTED = "#a9bfd2"


def ease(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def cavity(ax) -> None:
    ax.add_patch(FancyBboxPatch(
        (1.2, 1.45), 7.6, 4.1,
        boxstyle="round,pad=0.03,rounding_size=0.18",
        linewidth=3, edgecolor=EDGE, facecolor=PANEL,
    ))
    ax.plot([0.55, 1.2], [3.5, 3.5], color=HOT, lw=12, solid_capstyle="round")
    ax.plot([0.55, 1.2], [3.5, 3.5], color=RESIN, lw=6, solid_capstyle="round")


def heading(ax, title: str, line: str) -> None:
    ax.text(0.5, 0.91, title, transform=ax.transAxes, ha="center", va="center",
            color=TEXT, fontsize=28, weight="bold")
    ax.text(0.5, 0.835, line, transform=ax.transAxes, ha="center", va="center",
            color=MUTED, fontsize=15)


def fill_shape(ax, frac: float, stop: float = 1.0) -> None:
    width = 7.48 * min(frac, stop)
    if width > 0:
        ax.add_patch(FancyBboxPatch(
            (1.26, 1.53), width, 3.94,
            boxstyle="round,pad=0,rounding_size=0.12",
            linewidth=0, facecolor=RESIN, alpha=0.92,
        ))
        front_x = 1.26 + width
        ax.plot([front_x, front_x], [1.7, 5.3], color=HOT, lw=4, alpha=0.85)


def draw_fill(ax, p: float) -> None:
    cavity(ax)
    fill_shape(ax, ease(p))
    heading(ax, "FILLING", "Molten plastic enters the box.")


def draw_void(ax, p: float) -> None:
    cavity(ax)
    fill_shape(ax, 1.0)
    radius = 0.08 + 0.42 * ease(p)
    ax.add_patch(Circle((6.9, 4.05), radius, facecolor=BG, edgecolor=AIR, lw=4))
    ax.annotate("TRAPPED AIR", xy=(6.9, 4.05), xytext=(6.0, 5.95), color=AIR,
                fontsize=12, weight="bold", arrowprops=dict(arrowstyle="->", color=AIR, lw=2))
    heading(ax, "VOID", "Air can remain trapped inside.")


def draw_warpage(ax, p: float) -> None:
    bend = 0.65 * ease(p)
    xs = np.linspace(1.4, 8.6, 80)
    top = 5.1 + bend * np.sin(np.pi * (xs - 1.4) / 7.2)
    bottom = 1.9 + bend * np.sin(np.pi * (xs - 1.4) / 7.2)
    verts = np.vstack([np.c_[xs, bottom], np.c_[xs[::-1], top[::-1]]])
    ax.add_patch(Polygon(verts, closed=True, facecolor=RESIN, edgecolor=HOT, lw=3, alpha=0.92))
    ax.plot([1.4, 8.6], [1.9, 1.9], ls="--", lw=2, color=EDGE, alpha=0.65)
    heading(ax, "WARPAGE", "Uneven cooling can bend the part.")


def draw_sink(ax, p: float) -> None:
    cavity(ax)
    fill_shape(ax, 1.0)
    depth = 0.55 * ease(p)
    verts = [(3.25, 5.47), (4.3, 5.47), (4.65, 5.47-depth),
             (5.0, 5.47), (6.05, 5.47)]
    codes = [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3, MplPath.CURVE3, MplPath.CURVE3]
    ax.add_patch(PathPatch(MplPath(verts, codes), edgecolor=BAD, facecolor="none", lw=7))
    ax.annotate("DENT", xy=(4.65, 5.47-depth), xytext=(4.65, 6.15), ha="center",
                color=BAD, fontsize=12, weight="bold",
                arrowprops=dict(arrowstyle="->", color=BAD, lw=2))
    heading(ax, "SINK MARK", "A thick area can pull the surface inward.")


def draw_weld(ax, p: float) -> None:
    ax.add_patch(FancyBboxPatch((1.2, 1.45), 7.6, 4.1,
                               boxstyle="round,pad=0.03,rounding_size=0.18",
                               linewidth=3, edgecolor=EDGE, facecolor=PANEL))
    q = ease(p)
    w = 3.72 * q
    ax.add_patch(FancyBboxPatch((1.26, 1.53), w, 3.94, boxstyle="round,pad=0",
                               linewidth=0, facecolor=RESIN, alpha=0.92))
    ax.add_patch(FancyBboxPatch((8.74-w, 1.53), w, 3.94, boxstyle="round,pad=0",
                               linewidth=0, facecolor="#ffad32", alpha=0.92))
    if q > 0.88:
        ax.plot([5, 5], [1.68, 5.32], color=BAD, lw=4, ls="--")
        ax.text(5.15, 4.8, "MEETING LINE", color=BAD, fontsize=12, weight="bold")
    heading(ax, "WELD LINE", "Two flow fronts meet and leave a line.")


def draw_short(ax, p: float) -> None:
    cavity(ax)
    fill_shape(ax, ease(p), stop=0.72)
    if p > 0.7:
        ax.text(7.15, 3.5, "UNFILLED", color=AIR, fontsize=14, ha="center", weight="bold")
    heading(ax, "SHORT SHOT", "The plastic stops before the box is full.")


def render(frame: int) -> None:
    ax.clear()
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    t = frame / FPS
    if t < 3:
        ax.text(0.5, 0.57, "PLASTIC FILLING", transform=ax.transAxes, ha="center",
                color=TEXT, fontsize=34, weight="bold")
        ax.text(0.5, 0.45, "6 common molding defects in 38 seconds", transform=ax.transAxes,
                ha="center", color=HOT, fontsize=18)
        ax.text(0.5, 0.35, "OpenFOAM + CalculiX preview", transform=ax.transAxes,
                ha="center", color=MUTED, fontsize=14)
    elif t < 9:
        draw_fill(ax, (t-3)/6)
    elif t < 14:
        draw_void(ax, (t-9)/5)
    elif t < 19:
        draw_warpage(ax, (t-14)/5)
    elif t < 24:
        draw_sink(ax, (t-19)/5)
    elif t < 29:
        draw_weld(ax, (t-24)/5)
    elif t < 34:
        draw_short(ax, (t-29)/5)
    else:
        ax.text(0.5, 0.57, "Which defect should we test next?", transform=ax.transAxes,
                ha="center", color=TEXT, fontsize=27, weight="bold")
        ax.text(0.5, 0.43, "OpenFOAM + CalculiX", transform=ax.transAxes,
                ha="center", color=HOT, fontsize=20)
    ax.text(0.5, 0.035, "SIMPLIFIED ENGINEERING PREVIEW - UNVALIDATED",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=9)


def main() -> int:
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    movie = animation.FuncAnimation(fig, render, frames=DURATION * FPS, interval=1000/FPS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    writer = animation.FFMpegWriter(
        fps=FPS, codec="libx264", bitrate=3500,
        extra_args=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    movie.save(OUT, writer=writer)
    plt.close(fig)
    print(f"VIDEO_OK path={OUT} bytes={OUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
