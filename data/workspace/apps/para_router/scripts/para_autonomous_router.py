#!/usr/bin/env python3
import argparse, csv, json, os, re, shutil, time
from pathlib import Path

DEFAULT_MAP = {
    "10_Projects": ["iatf", "audit", "esp32", "mqtt", "node-red", "nodered", "leveler", "openfoam", "anomaly", "gd&t", "gdt"],
    "20_Areas": ["quality", "qa", "press", "molding", "plating", "reflow", "ai_operations", "maintenance"],
    "30_Resources": ["manual", "standard", "paper", "datasheet", "sds", "reference", "spec"],
    "40_Archives": ["past", "trouble", "failure", "old", "backup", "incident", "error", "archive"],
}

def classify(name: str) -> tuple[str, float, str]:
    s = name.lower()
    scores = {k: sum(1 for w in ws if w in s) for k, ws in DEFAULT_MAP.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        if re.search(r"\.(csv|log|jsonl)$", s):
            return "40_Archives", 0.55, "log-like data; archive/learning candidate"
        return "30_Resources", 0.45, "default reference classification"
    conf = min(0.95, 0.55 + scores[best] * 0.12)
    return best, conf, f"matched keywords: {scores}"

def safe_name(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()

def route(base: Path, apply: bool):
    inbox = base / "02_PARA_Vault" / "90_Inbox"
    report_dir = base / "04_Autonomous_Agent" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in inbox.rglob("*"):
        if not p.is_file():
            continue
        category, conf, reason = classify(p.name)
        dst_dir = base / "02_PARA_Vault" / category / time.strftime("%Y%m")
        dst = dst_dir / safe_name(p.name)
        rows.append({"source": str(p), "target": str(dst), "category": category, "confidence": conf, "reason": reason, "applied": apply})
        if apply:
            dst_dir.mkdir(parents=True, exist_ok=True)
            final = dst
            i = 1
            while final.exists():
                final = dst.with_name(f"{dst.stem}_{i}{dst.suffix}")
                i += 1
            shutil.move(str(p), str(final))
    out = report_dir / f"para_route_report_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["source","target","category","confidence","reason","applied"])
        w.writeheader(); w.writerows(rows)
    print(json.dumps({"count": len(rows), "report": str(out), "applied": apply}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    route(Path(args.base), args.apply)
