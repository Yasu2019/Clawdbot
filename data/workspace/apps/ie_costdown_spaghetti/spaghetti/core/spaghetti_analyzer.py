#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spaghetti Diagram Analyzer

X/Y時系列CSVから、歩行距離、ゾーン滞在、往復回数、ムダ動線候補を分析します。
既存MOST/サーブリッグ法コードとは独立した追加モジュールです。

入力CSV:
timestamp,tag_id,x,y[,z,quality,source]

レイアウトJSON:
{
  "width": 8.0,
  "height": 5.0,
  "zones": [
    {"id":"INSPECT","name":"検査机","x_min":1,"y_min":1,"x_max":2,"y_max":2}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


@dataclass
class Zone:
    id: str
    name: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    type: str = "zone"

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)


def load_layout(path: str | Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def zones_from_layout(layout: Dict) -> List[Zone]:
    zones = []
    for z in layout.get("zones", []):
        zones.append(
            Zone(
                id=z["id"],
                name=z.get("name", z["id"]),
                type=z.get("type", "zone"),
                x_min=float(z["x_min"]),
                y_min=float(z["y_min"]),
                x_max=float(z["x_max"]),
                y_max=float(z["y_max"]),
            )
        )
    return zones


def load_trace(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"timestamp", "tag_id", "x", "y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "x", "y"]).copy()
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["x", "y"]).sort_values(["tag_id", "timestamp"]).reset_index(drop=True)
    if "quality" in df.columns:
        df["quality"] = pd.to_numeric(df["quality"], errors="coerce")
    else:
        df["quality"] = np.nan
    return df


def assign_zones(df: pd.DataFrame, zones: List[Zone]) -> pd.DataFrame:
    def find_zone(row):
        x, y = row["x"], row["y"]
        for z in zones:
            if z.contains(x, y):
                return z.id
        return "OUTSIDE"
    out = df.copy()
    out["zone_id"] = out.apply(find_zone, axis=1)
    return out


def add_motion_features(df: pd.DataFrame) -> pd.DataFrame:
    chunks = []
    for tag_id, g in df.groupby("tag_id", sort=False):
        g = g.sort_values("timestamp").copy()
        g["dt_sec"] = g["timestamp"].diff().dt.total_seconds().fillna(0)
        g.loc[g["dt_sec"] < 0, "dt_sec"] = 0
        g["dx"] = g["x"].diff().fillna(0)
        g["dy"] = g["y"].diff().fillna(0)
        g["step_distance_m"] = np.sqrt(g["dx"] ** 2 + g["dy"] ** 2)
        g["speed_m_s"] = np.where(g["dt_sec"] > 0, g["step_distance_m"] / g["dt_sec"], 0)
        # 現場測位の外れ値対策：速度が大きすぎる点をフラグ
        g["outlier_speed"] = g["speed_m_s"] > 3.0
        chunks.append(g)
    return pd.concat(chunks, ignore_index=True)


def summarize_by_tag(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tag_id, g in df.groupby("tag_id", sort=False):
        clean = g[~g.get("outlier_speed", False)].copy()
        total_time = (g["timestamp"].max() - g["timestamp"].min()).total_seconds()
        rows.append({
            "tag_id": tag_id,
            "start": g["timestamp"].min(),
            "end": g["timestamp"].max(),
            "duration_sec": round(total_time, 2),
            "samples": len(g),
            "distance_m": round(clean["step_distance_m"].sum(), 3),
            "avg_speed_m_s": round(clean["speed_m_s"].replace([np.inf, -np.inf], np.nan).dropna().mean(), 3),
            "max_speed_m_s": round(clean["speed_m_s"].replace([np.inf, -np.inf], np.nan).dropna().max(), 3),
            "outlier_count": int(g["outlier_speed"].sum()),
        })
    return pd.DataFrame(rows)


def zone_dwell_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (tag_id, zone_id), g in df.groupby(["tag_id", "zone_id"], sort=False):
        rows.append({
            "tag_id": tag_id,
            "zone_id": zone_id,
            "dwell_sec": round(g["dt_sec"].sum(), 2),
            "samples": len(g),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        total = out.groupby("tag_id")["dwell_sec"].transform("sum")
        out["dwell_ratio"] = np.where(total > 0, out["dwell_sec"] / total, 0)
        out = out.sort_values(["tag_id", "dwell_sec"], ascending=[True, False])
    return out


def transition_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tag_id, g in df.groupby("tag_id", sort=False):
        g = g.sort_values("timestamp").copy()
        prev = g["zone_id"].shift(1)
        changed = g[(g["zone_id"] != prev) & prev.notna()].copy()
        for _, row in changed.iterrows():
            rows.append({
                "tag_id": tag_id,
                "from_zone": prev.loc[row.name],
                "to_zone": row["zone_id"],
                "timestamp": row["timestamp"],
            })
    trans = pd.DataFrame(rows)
    if trans.empty:
        return pd.DataFrame(columns=["tag_id","from_zone","to_zone","count"])
    return trans.groupby(["tag_id", "from_zone", "to_zone"]).size().reset_index(name="count").sort_values("count", ascending=False)


def detect_waste_patterns(df: pd.DataFrame, zones: List[Zone]) -> pd.DataFrame:
    """
    簡易ムダ候補検出:
    - A-B-A往復
    - OUTSIDE経由が多い
    - 長距離移動
    - 高速外れ値
    """
    rows = []
    zone_name = {z.id: z.name for z in zones}
    for tag_id, g in df.groupby("tag_id", sort=False):
        g = g.sort_values("timestamp").copy()
        seq = g.loc[g["zone_id"] != g["zone_id"].shift(1), ["timestamp", "zone_id"]].reset_index(drop=True)

        # A-B-A detection
        for i in range(len(seq) - 2):
            a, b, c = seq.loc[i, "zone_id"], seq.loc[i+1, "zone_id"], seq.loc[i+2, "zone_id"]
            if a == c and a != b and a != "OUTSIDE" and b != "OUTSIDE":
                rows.append({
                    "tag_id": tag_id,
                    "pattern": "A-B-A往復",
                    "severity": "medium",
                    "timestamp": str(seq.loc[i+1, "timestamp"]),
                    "detail": f"{zone_name.get(a,a)} → {zone_name.get(b,b)} → {zone_name.get(c,c)}",
                    "suggestion": "置き場の手元化、外段取り化、補充頻度見直しを確認する"
                })

        # Long movement
        long_steps = g[g["step_distance_m"] > 1.0]
        for _, row in long_steps.head(20).iterrows():
            rows.append({
                "tag_id": tag_id,
                "pattern": "長距離ジャンプ/移動",
                "severity": "low",
                "timestamp": str(row["timestamp"]),
                "detail": f"step_distance={row['step_distance_m']:.2f}m, speed={row['speed_m_s']:.2f}m/s",
                "suggestion": "測位外れ値または長距離歩行の可能性。生データと現場動画を確認する"
            })

        # Outlier speed
        outliers = g[g["outlier_speed"]]
        if len(outliers) > 0:
            rows.append({
                "tag_id": tag_id,
                "pattern": "測位外れ値候補",
                "severity": "data_quality",
                "timestamp": str(outliers["timestamp"].min()),
                "detail": f"速度3m/s超の点が{len(outliers)}件",
                "suggestion": "UWBアンカー配置、NLOS、フィルタ設定、quality閾値を確認する"
            })

        # Outside dwell
        outside_sec = g.loc[g["zone_id"] == "OUTSIDE", "dt_sec"].sum()
        if outside_sec > 30:
            rows.append({
                "tag_id": tag_id,
                "pattern": "レイアウト外滞在が多い",
                "severity": "medium",
                "timestamp": str(g["timestamp"].min()),
                "detail": f"OUTSIDE dwell={outside_sec:.1f}sec",
                "suggestion": "レイアウトゾーン定義不足、または作業範囲外への移動を確認する"
            })

    return pd.DataFrame(rows)


def plot_spaghetti(df: pd.DataFrame, layout: Dict, zones: List[Zone], output_png: str | Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    width = layout.get("width", max(df["x"].max(), 1))
    height = layout.get("height", max(df["y"].max(), 1))

    # Zones
    for z in zones:
        rect = plt.Rectangle((z.x_min, z.y_min), z.x_max - z.x_min, z.y_max - z.y_min, fill=False, linewidth=1.5)
        ax.add_patch(rect)
        cx, cy = z.center
        ax.text(cx, cy, z.name, ha="center", va="center", fontsize=8)

    # Tracks per tag
    for tag_id, g in df.groupby("tag_id", sort=False):
        g = g.sort_values("timestamp")
        ax.plot(g["x"], g["y"], linewidth=1.2, alpha=0.85, label=str(tag_id))
        ax.scatter(g["x"].iloc[0], g["y"].iloc[0], marker="o", s=50)
        ax.scatter(g["x"].iloc[-1], g["y"].iloc[-1], marker="x", s=60)

    # Anchors
    for a in layout.get("anchors", []):
        ax.scatter([a["x"]], [a["y"]], marker="^", s=60)
        ax.text(a["x"], a["y"], a.get("id", "A"), fontsize=8, ha="left", va="bottom")

    ax.set_title("Spaghetti Diagram")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", linewidth=0.4)
    ax.legend(loc="upper right")
    fig.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=160)
    plt.close(fig)


def plot_heatmap(df: pd.DataFrame, layout: Dict, output_png: str | Path, bins: int = 40) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    width = layout.get("width", max(df["x"].max(), 1))
    height = layout.get("height", max(df["y"].max(), 1))
    h = ax.hist2d(df["x"], df["y"], bins=bins, range=[[0, width], [0, height]])
    fig.colorbar(h[3], ax=ax, label="samples")
    ax.set_title("Dwell Heatmap")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=160)
    plt.close(fig)


def write_report(output_dir: Path, tag_summary: pd.DataFrame, dwell: pd.DataFrame, transitions: pd.DataFrame, patterns: pd.DataFrame) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    tag_summary.to_csv(output_dir / "tag_summary.csv", index=False, encoding="utf-8-sig")
    dwell.to_csv(output_dir / "zone_dwell_summary.csv", index=False, encoding="utf-8-sig")
    transitions.to_csv(output_dir / "transition_summary.csv", index=False, encoding="utf-8-sig")
    patterns.to_csv(output_dir / "waste_patterns.csv", index=False, encoding="utf-8-sig")

    md = ["# スパゲッティ図 分析レポート", ""]
    md.append("## 1. タグ別サマリー")
    md.append(tag_summary.to_markdown(index=False) if not tag_summary.empty else "データなし")
    md.append("")
    md.append("## 2. ゾーン滞在時間")
    md.append(dwell.to_markdown(index=False) if not dwell.empty else "データなし")
    md.append("")
    md.append("## 3. ゾーン遷移")
    md.append(transitions.head(30).to_markdown(index=False) if not transitions.empty else "データなし")
    md.append("")
    md.append("## 4. ムダ動線候補")
    md.append(patterns.to_markdown(index=False) if not patterns.empty else "検出なし")
    md.append("")
    md.append("## 5. 改善確認の見方")
    md.append("- A-B-A往復が多い場合：置き場の手元化、外段取り化、補充方法の見直し")
    md.append("- ラベル/箱/治具置場への往復が多い場合：3定5Sとミズスマシ化を検討")
    md.append("- OUTSIDEが多い場合：ゾーン定義不足、または想定外動線を確認")
    md.append("- 速度外れ値が多い場合：UWB NLOS、アンカー配置、フィルタ設定を確認")
    (output_dir / "report.md").write_text("\n".join(md), encoding="utf-8")


def analyze(input_csv: str | Path, layout_json: str | Path, output_dir: str | Path) -> Dict[str, str]:
    output_dir = Path(output_dir)
    layout = load_layout(layout_json)
    zones = zones_from_layout(layout)
    df = load_trace(input_csv)
    df = assign_zones(df, zones)
    df = add_motion_features(df)

    tag_summary = summarize_by_tag(df)
    dwell = zone_dwell_summary(df)
    transitions = transition_summary(df)
    patterns = detect_waste_patterns(df, zones)

    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "trace_enriched.csv", index=False, encoding="utf-8-sig")
    plot_spaghetti(df, layout, zones, output_dir / "spaghetti.png")
    plot_heatmap(df, layout, output_dir / "heatmap.png")
    write_report(output_dir, tag_summary, dwell, transitions, patterns)

    return {
        "trace_enriched": str(output_dir / "trace_enriched.csv"),
        "spaghetti": str(output_dir / "spaghetti.png"),
        "heatmap": str(output_dir / "heatmap.png"),
        "report": str(output_dir / "report.md"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="X/Y trace CSV")
    parser.add_argument("--layout", required=True, help="layout JSON")
    parser.add_argument("--output", required=True, help="output directory")
    args = parser.parse_args()
    results = analyze(args.input, args.layout, args.output)
    for k, v in results.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
