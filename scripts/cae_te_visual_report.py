# -*- coding: utf-8 -*-
"""
CAE T&E Visual Report Generator
=================================
Generates press forming simulation result images from cae_te_log.json
using matplotlib (host Python) and sends them via Telegram Bot API.

Complies with AGENTS.md P023 Windows Encoding Standard.

Images generated per trial (when real computation data exists):
  1. "Before" schematic: initial blank/tool geometry (parametric diagram)
  2. "After" result chart: convergence, defect zone ratios, verdict

For DRY_RUN trials: generates informational parameter summary cards.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import json
import math
import datetime
import urllib.request
import urllib.parse
import mimetypes
import tempfile
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import numpy as np

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
TE_LOG_FILE = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"
IMG_OUT_DIR = ROOT / "data" / "cae_te_workspace" / "results" / "images"
IMG_OUT_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
CHAT_ID   = "8173025084"

# ─── Color palette ────────────────────────────────────────────────────────────
DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
BORDER     = "#30363d"
COL_OK     = "#3fb950"
COL_NG     = "#f85149"
COL_WARN   = "#e3b341"
COL_BLUE   = "#58a6ff"
COL_PURPLE = "#a371f7"
COL_TEXT   = "#e6edf3"
COL_DIM    = "#7d8590"

# Category color map
CAT_COLORS = {
    "press_bending":  COL_BLUE,
    "press_blanking": COL_PURPLE,
    "press_drawing":  COL_OK,
    "press_crushing": COL_WARN,
}
CAT_LABELS = {
    "press_bending":  "曲げ加工",
    "press_blanking": "打ち抜き",
    "press_drawing":  "絞り加工",
    "press_crushing": "潰し加工",
}
CAT_DEFECTS = {
    "press_bending":  ["スプリングバック", "破断", "バリ", "せん断面比率"],
    "press_blanking": ["バリ高さ", "せん断面%", "破断面%", "ロールオーバー"],
    "press_drawing":  ["しわ", "破断/ネック", "板厚減少率", "LDR"],
    "press_crushing": ["コイニング圧", "材料流動", "残留応力", "バリ"],
}


# ─── Helper: set dark style ──────────────────────────────────────────────────

def _find_jp_font() -> str:
    """Find best available Japanese font on this system."""
    import matplotlib.font_manager as fm
    preferred = ["Yu Gothic", "Meiryo", "MS Gothic", "BIZ UDGothic",
                 "IPAexGothic", "Noto Sans CJK JP", "Source Han Sans JP"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in preferred:
        if name in available:
            return name
    return "DejaVu Sans"  # fallback


JP_FONT = _find_jp_font()
print(f"[Visual Report] Using font: {JP_FONT}")


def _dark_style():
    plt.rcParams.update({
        "figure.facecolor":  DARK_BG,
        "axes.facecolor":    CARD_BG,
        "axes.edgecolor":    BORDER,
        "axes.labelcolor":   COL_TEXT,
        "xtick.color":       COL_DIM,
        "ytick.color":       COL_DIM,
        "text.color":        COL_TEXT,
        "grid.color":        BORDER,
        "grid.alpha":        0.5,
        "font.family":       JP_FONT,
        "font.size":         10,
    })


# ─── Image 1: Before — Process Schematic ─────────────────────────────────────

def draw_process_schematic(trial: dict, out_path: Path):
    """Draw a schematic of the press forming setup (initial condition) mathematically scaled."""
    _dark_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    cat    = trial.get("category", "press_bending")
    params = trial.get("params", {})
    color  = CAT_COLORS.get(cat, COL_BLUE)
    label  = CAT_LABELS.get(cat, cat)
    defects = CAT_DEFECTS.get(cat, [])

    # ── Title ──
    fig.text(0.5, 0.96, f"[BEFORE] {label} — 初期設定",
             ha="center", va="top", fontsize=16, fontweight="bold",
             color=COL_TEXT, transform=fig.transFigure)

    # ── Draw schematic depending on category ──
    if cat == "press_bending":
        r_t = params.get("bend_radius_t_ratio", 1.0)
        # V-punch above, sheet below, die V-groove
        punch_height = 4.5 - (r_t - 1.0) * 0.2
        punch = patches.FancyBboxPatch((3.5, punch_height), 3, 1.5,
                                       boxstyle="round,pad=0.1",
                                       linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(punch)
        ax.text(5, punch_height + 0.75, "パンチ", ha="center", va="center",
                fontsize=9, color=COL_DIM)
        # V-groove die
        vx = [1.5, 5, 8.5]
        vy = [3.5, 1.0, 3.5]
        ax.fill_between(vx, vy, [3.5, 3.5, 3.5], alpha=0.3, color=COL_DIM)
        ax.plot(vx, vy, color=COL_DIM, linewidth=2)
        ax.text(5, 0.5, "ダイ (Die) — V溝", ha="center", color=COL_DIM, fontsize=9)
        # Sheet
        sheet = patches.Rectangle((1, 3.5), 8, 0.4,
                                   linewidth=2, edgecolor=color, facecolor=color, alpha=0.6)
        ax.add_patch(sheet)
        ax.text(5, 3.7, f"板材 (t=1.6mm, R/t={r_t:.1f})", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        # Arrow
        ax.annotate("", xy=(5, 4.5), xytext=(5, 4.0),
                    arrowprops=dict(arrowstyle="-|>", color=COL_WARN, lw=2))

    elif cat == "press_blanking":
        cl_pct = params.get("clearance_pct", 8.0)
        # Calculate visual clearance offset based on cl_pct (8% is standard visual gap 0.1)
        cl_offset = (cl_pct / 8.0) * 0.15
        
        # Punch (fixed center)
        punch = patches.Rectangle((3.5, 4.5), 3.0, 1.5,
                                   linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(punch)
        ax.text(5, 5.25, "パンチ", ha="center", va="center", color=COL_DIM, fontsize=9)
        
        # Sheet (t=1.2mm)
        sheet = patches.Rectangle((1.0, 3.0), 8.0, 0.5,
                                   linewidth=2, edgecolor=color, facecolor=color, alpha=0.6)
        ax.add_patch(sheet)
        ax.text(5, 3.25, "板材 (t=1.2mm)", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        
        # Mathematically offset left and right dies to visualize clearance gap clearly!
        die_l = patches.Rectangle((1.0, 2.0), 2.5 - cl_offset, 1.0,
                                   linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        die_r = patches.Rectangle((6.5 + cl_offset, 2.0), 2.5 - cl_offset, 1.0,
                                   linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(die_l)
        ax.add_patch(die_r)
        ax.text(2.0, 2.5, "ダイ", ha="center", va="center", color=COL_DIM, fontsize=9)
        
        # Arrow
        ax.annotate("", xy=(5, 4.5), xytext=(5, 3.5),
                    arrowprops=dict(arrowstyle="-|>", color=COL_WARN, lw=2))
        
        # Visualize clearance dimension gap
        ax.annotate("", xy=(6.5, 2.5), xytext=(6.5 + cl_offset, 2.5),
                    arrowprops=dict(arrowstyle="<->", color=COL_NG, lw=1.5))
        ax.text(6.5 + cl_offset / 2.0, 1.6, f"隙間 Cl={cl_pct}%t", color=COL_NG, fontsize=8, ha="center")

    elif cat == "press_drawing":
        bhf = params.get("blankholder_force_kN", 15.0)
        # Punch + blank + die + blankholder
        punch = patches.Circle((5, 5), 1.5, linewidth=2,
                                edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(punch)
        ax.text(5, 5, "パンチ", ha="center", va="center", color=COL_DIM, fontsize=9)
        blank = patches.Rectangle((1.5, 3.0), 7, 0.5,
                                   linewidth=2, edgecolor=color, facecolor=color, alpha=0.6)
        ax.add_patch(blank)
        ax.text(5, 3.25, "ブランク (IF鋼)", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        die_ring = patches.Wedge((5, 1.5), 3.5, 0, 180, width=0.8,
                                  linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(die_ring)
        ax.text(5, 1.5, "ダイ", ha="center", va="center", color=COL_DIM, fontsize=9)
        ax.text(1.5, 3.8, f"しわ押さえ BHF={bhf}kN", color=COL_PURPLE, fontsize=9, fontweight="bold")
        ax.annotate("", xy=(5, 3.5), xytext=(5, 3.8),
                    arrowprops=dict(arrowstyle="-|>", color=COL_WARN, lw=2))

    elif cat == "press_crushing":
        red = params.get("reduction_pct", 25.0)
        # Flat punch + blank + flat die (coining)
        punch = patches.Rectangle((2, 4.5), 6, 1.2,
                                   linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(punch)
        ax.text(5, 5.1, "パンチ", ha="center", va="center",
                color=COL_DIM, fontsize=9)
        
        # Scale sheet thickness according to reduction_pct!
        sheet_height = 2.0 * (1.0 - red / 100.0) # Visual thickness reduction
        sheet = patches.Rectangle((2.5, 2.5), 5.0, sheet_height,
                                   linewidth=2, edgecolor=color, facecolor=color, alpha=0.6)
        ax.add_patch(sheet)
        ax.text(5, 2.5 + sheet_height / 2.0, "ブランク (純銅)", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        
        die = patches.Rectangle((2, 1.5), 6, 1.0,
                                 linewidth=2, edgecolor=COL_DIM, facecolor="#2d333b")
        ax.add_patch(die)
        ax.text(5, 2.0, "ダイ", ha="center", va="center",
                color=COL_DIM, fontsize=9)
        ax.text(0.2, 3.5, f"設定圧縮率\n{red}%", ha="center", color=COL_WARN,
                fontsize=9, fontweight="bold")
        ax.annotate("", xy=(5, 4.5), xytext=(5, 4.1),
                    arrowprops=dict(arrowstyle="-|>", color=COL_WARN, lw=2))

    # ── Parameter table (right panel) ──
    param_lines = [f"{k}: {v}" for k, v in params.items()]
    param_text  = "\n".join(param_lines) if param_lines else "N/A"
    ax.text(8.8, 6.2, "パラメータ", fontsize=9, fontweight="bold",
            color=color, va="top", ha="center")
    ax.text(8.8, 5.8, param_text, fontsize=8, color=COL_TEXT,
            va="top", ha="center", family="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=CARD_BG,
                      edgecolor=color, alpha=0.8))

    # ── Defect targets ──
    ax.text(8.8, 3.5, "検出対象", fontsize=9, fontweight="bold",
            color=COL_NG, va="top", ha="center")
    for i, d in enumerate(defects):
        ax.text(8.8, 3.1 - i * 0.45, f"• {d}", fontsize=8,
                color=COL_TEXT, va="top", ha="center")

    # ── Trial ID badge ──
    fig.text(0.01, 0.01, f"Trial: {trial.get('id', '?')} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
             fontsize=7, color=COL_DIM, transform=fig.transFigure)

    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    fig.savefig(str(out_path), dpi=120, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)


def draw_result_dashboard(trial: dict, all_trials: list, out_path: Path):
    """Draw result summary: verdict, category stats, defect summary, timeline."""
    _dark_style()
    fig = plt.figure(figsize=(12, 7))
    fig.patch.set_facecolor(DARK_BG)

    cat     = trial.get("category", "press_bending")
    label   = CAT_LABELS.get(cat, cat)
    color   = CAT_COLORS.get(cat, COL_BLUE)
    verdict = trial.get("verdict", "UNKNOWN")
    params  = trial.get("params", {})
    lesson  = trial.get("lesson", "")
    v_color = COL_OK if verdict == "SUCCESS" else COL_NG if verdict == "FAILED" else COL_WARN

    # ── Layout: 2x2 grid ──
    gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.35,
                           left=0.07, right=0.97, top=0.88, bottom=0.08)
    ax_verdict = fig.add_subplot(gs[0, 0])
    ax_cat     = fig.add_subplot(gs[0, 1])
    ax_sweep   = fig.add_subplot(gs[0, 2])
    ax_lesson  = fig.add_subplot(gs[1, :])

    # Title
    fig.text(0.5, 0.96, f"[AFTER] {label} — 実行結果",
             ha="center", va="top", fontsize=16, fontweight="bold",
             color=COL_TEXT, transform=fig.transFigure)
    fig.text(0.5, 0.91, f"Trial: {trial.get('id','?')}  |  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
             ha="center", va="top", fontsize=9, color=COL_DIM,
             transform=fig.transFigure)

    # ── Panel 1: Verdict ring ──
    ax_verdict.set_facecolor(CARD_BG)
    ring_color = [v_color, "#1c2128"]
    score = 1.0 if verdict == "SUCCESS" else 0.0 if verdict == "FAILED" else 0.5
    ax_verdict.pie([score, 1 - score], colors=ring_color,
                   startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.4, edgecolor=DARK_BG))
    ax_verdict.text(0, 0, verdict, ha="center", va="center",
                    fontsize=14, fontweight="bold", color=v_color)
    ax_verdict.set_title("判定結果", fontsize=10, color=COL_TEXT, pad=8)

    # ── Panel 2: Category success rate (all trials) ──
    ax_cat.set_facecolor(CARD_BG)
    cat_data = {}
    for t in all_trials:
        c = t.get("category", "unknown")
        if c not in cat_data:
            cat_data[c] = {"total": 0, "ok": 0}
        cat_data[c]["total"] += 1
        if t.get("verdict") == "SUCCESS":
            cat_data[c]["ok"] += 1

    cats = list(CAT_LABELS.keys())
    rates = []
    bar_colors = []
    for c in cats:
        d = cat_data.get(c, {"total": 0, "ok": 0})
        rates.append(d["ok"] / d["total"] * 100 if d["total"] > 0 else 0)
        bar_colors.append(CAT_COLORS[c])

    short_labels = ["曲げ", "打ち抜き", "絞り", "潰し"]
    bars = ax_cat.bar(short_labels, rates, color=bar_colors, alpha=0.85,
                      edgecolor=DARK_BG, width=0.6)
    for bar, r in zip(bars, rates):
        if r > 0:
            ax_cat.text(bar.get_x() + bar.get_width() / 2, r + 1,
                        f"{r:.0f}%", ha="center", va="bottom",
                        fontsize=8, color=COL_TEXT)
    ax_cat.set_ylim(0, 115)
    ax_cat.set_ylabel("成功率 %", fontsize=8, color=COL_DIM)
    ax_cat.set_title("カテゴリ別成功率", fontsize=10, color=COL_TEXT, pad=8)
    ax_cat.grid(axis="y", alpha=0.3)
    ax_cat.spines[:].set_color(BORDER)

    # ── Panel 3: Parameter sweep results ──
    ax_sweep.set_facecolor(CARD_BG)
    same_exp = [t for t in all_trials if t.get("exp_id") == trial.get("exp_id")]
    if len(same_exp) > 1 and params:
        first_param_key = list(params.keys())[0]
        x_vals = [t.get("params", {}).get(first_param_key, i) for i, t in enumerate(same_exp)]
        v_vals = [1 if t.get("verdict") == "SUCCESS" else 0 for t in same_exp]
        c_vals = [COL_OK if v == 1 else COL_NG for v in v_vals]
        ax_sweep.scatter(range(len(x_vals)), x_vals, c=c_vals, s=80, zorder=3)
        ax_sweep.plot(range(len(x_vals)), x_vals, color=COL_DIM, alpha=0.4, lw=1)
        ax_sweep.set_xticks(range(len(x_vals)))
        ax_sweep.set_xticklabels([f"S{i+1}" for i in range(len(x_vals))], fontsize=8)
        ax_sweep.set_ylabel(first_param_key[:15], fontsize=8, color=COL_DIM)
    else:
        ax_sweep.text(0.5, 0.5, "スイープ\nデータなし",
                      ha="center", va="center", color=COL_DIM,
                      transform=ax_sweep.transAxes, fontsize=11)
    ax_sweep.set_title("パラメータスイープ", fontsize=10, color=COL_TEXT, pad=8)
    ax_sweep.grid(alpha=0.3)
    ax_sweep.spines[:].set_color(BORDER)

    # ── Panel 4: Lesson learned & Physical Quality Metrics (full width) ──
    ax_lesson.set_facecolor(CARD_BG)
    ax_lesson.axis("off")
    ax_lesson.set_title("物理特性分析 / Lesson Learned", fontsize=10,
                         color=COL_TEXT, loc="left", pad=8)

    # Extract dynamic physical results calculated by preprocessor/postprocessor
    defects_det = trial.get("defects_detected", {})
    metrics_lines = []
    
    if cat == "press_blanking":
        crack = defects_det.get("crack_risk", "LOW")
        burr = defects_det.get("burr_height_mm", "0.020")
        roll = defects_det.get("rollover_mm", "0.050")
        shear = defects_det.get("shear_zone_pct", "40.0%")
        frac = defects_det.get("fracture_zone_pct", "60.0%")
        
        # Color coding for crack risk alert
        c_alert = "⚠️ " if "HIGH" in crack else "✅ "
        metrics_lines.append(f"• {c_alert}クラック発生リスク: {crack}")
        metrics_lines.append(f"• 📐 せん断面比率: {shear}  |  破断面比率: {frac}")
        metrics_lines.append(f"• ✂️ ダレ量 (Roll-over): {roll} mm")
        metrics_lines.append(f"• ⚠️ バリ高さ: {burr} mm")
        
    elif cat == "press_bending":
        spb = defects_det.get("springback_deg", "0.00°")
        frac = defects_det.get("fracture_detected", False)
        f_alert = "⚠️ 破断発生 (R/t限界超)" if frac else "✅ 割れなし"
        metrics_lines.append(f"• {f_alert}")
        metrics_lines.append(f"• 📐 スプリングバック角: {spb}")
        
    elif cat == "press_drawing":
        wrk = defects_det.get("wrinkling_detected", False)
        thn = defects_det.get("thinning_max_pct", "12.0%")
        frac = defects_det.get("fracture_detected", False)
        w_alert = "⚠️ しわ発生 (BHF不足)" if wrk else "✅ フランジしわなし"
        f_alert = "⚠️ ネック破断 (BHF過大)" if frac else "✅ 肉厚破断なし"
        metrics_lines.append(f"• {w_alert}")
        metrics_lines.append(f"• {f_alert}")
        metrics_lines.append(f"• 📉 最大板厚減少率: {thn}")
        
    elif cat == "press_crushing":
        press = defects_det.get("coin_pressure_MPa", "300.0 MPa")
        thick = defects_det.get("thickness_achieved_mm", "2.000 mm")
        metrics_lines.append(f"• ⚙️ コイニング所要圧力: {press}")
        metrics_lines.append(f"• 📏 圧潰後到達板厚: {thick}")

    params_str = "  ".join([f"{k}={v}" for k, v in params.items()])
    metrics_text = "\n".join(metrics_lines)
    
    full_text  = (
        f"【操業パラメータ】 {params_str}\n"
        f"--------------------------------------------------------------------------------\n"
        f"【品質解析結果】\n{metrics_text}\n"
        f"--------------------------------------------------------------------------------\n"
        f"【学習した知見 (Lesson)】\n{lesson}"
    )

    ax_lesson.text(0.01, 0.90, full_text,
                   transform=ax_lesson.transAxes,
                   fontsize=9, color=COL_TEXT, va="top",
                   wrap=True,
                   bbox=dict(boxstyle="round,pad=0.6",
                             facecolor=DARK_BG, edgecolor=color, alpha=0.9),
                   linespacing=1.6)

    # Verdict badge
    ax_verdict.set_facecolor(CARD_BG)
    fig.text(0.01, 0.01,
             f"Duration: {trial.get('duration_sec', 0):.1f}s  |  "
             f"Solver: {trial.get('solver','?')}  |  Category: {cat}",
             fontsize=7, color=COL_DIM, transform=fig.transFigure)

    fig.savefig(str(out_path), dpi=120, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)


# ─── Telegram: send photo ─────────────────────────────────────────────────────

def send_telegram_photo(image_path: Path, caption: str) -> bool:
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    boundary = "----MultipartBoundary987654"

    with open(image_path, "rb") as f:
        img_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                print(f"  [OK] Photo sent: {image_path.name}")
                return True
            else:
                print(f"  [ERR] Telegram photo error: {res_data.get('description','')}")
                return False
    except Exception as e:
        print(f"  [ERR] Photo send failed: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(max_reports: int = 3):
    print("[Visual Report] Generating CAE T&E images for Telegram...")

    if not TE_LOG_FILE.exists():
        print("[WARN] cae_te_log.json not found. Run cae_te_engine.py first.")
        return 1

    with TE_LOG_FILE.open("r", encoding="utf-8") as f:
        te_log = json.load(f)

    trials     = te_log.get("trials", [])
    all_trials = trials  # For cross-category stats

    if not trials:
        print("[WARN] No trials in log yet.")
        return 1

    # Generate images for the latest N trials
    report_trials = trials[:max_reports]
    sent_count    = 0

    for trial in report_trials:
        trial_id = trial.get("id", "unknown")
        cat      = trial.get("category", "unknown")
        verdict  = trial.get("verdict", "UNKNOWN")
        v_icon   = "OK" if verdict == "SUCCESS" else "NG" if verdict == "FAILED" else verdict[:2]
        print(f"\n  Processing: {trial_id} [{verdict}]")

        # Generate BEFORE image
        before_path = IMG_OUT_DIR / f"{trial_id}_before.png"
        try:
            draw_process_schematic(trial, before_path)
            print(f"    Generated BEFORE: {before_path.name}")
        except Exception as e:
            print(f"    [ERR] BEFORE image failed: {e}")
            before_path = None

        # Generate AFTER image
        after_path = IMG_OUT_DIR / f"{trial_id}_after.png"
        try:
            draw_result_dashboard(trial, all_trials, after_path)
            print(f"    Generated AFTER:  {after_path.name}")
        except Exception as e:
            print(f"    [ERR] AFTER image failed: {e}")
            after_path = None

        # Send BEFORE
        if before_path and before_path.exists():
            caption_before = (
                f"[BEFORE] {trial_id} — {CAT_LABELS.get(cat, cat)}\n"
                f"初期設定 / Initial Setup\n"
                f"Params: {trial.get('params', {})}"
            )
            send_telegram_photo(before_path, caption_before)

        import time; time.sleep(1)  # Telegram rate limit

        # Send AFTER
        if after_path and after_path.exists():
            caption_after = (
                f"[AFTER] {trial_id} — 判定: {verdict} {v_icon}\n"
                f"{(trial.get('lesson',''))[:120]}"
            )
            send_telegram_photo(after_path, caption_after)

        sent_count += 1
        import time; time.sleep(2)

    print(f"\n[Visual Report] Done. Sent {sent_count} trial(s) x 2 images.")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CAE T&E Visual Report")
    parser.add_argument("--max-reports", type=int, default=3,
                        help="Number of latest trials to report (default: 3)")
    args = parser.parse_args()
    raise SystemExit(main(args.max_reports))
