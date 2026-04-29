#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import pandas as pd

def detect(csv_path: Path):
    df = pd.read_csv(csv_path)
    findings = []
    for col in df.columns:
        lc = col.lower()
        if lc in ["spm", "shot", "chokotei", "jyotai"] or any(k in lc for k in ["spm", "shot", "チョコ", "停止"]):
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s) >= 10:
                mean, std = s.mean(), s.std(ddof=1)
                if std and std > 0:
                    outliers = df[pd.to_numeric(df[col], errors="coerce").sub(mean).abs() > 3*std]
                    if len(outliers):
                        findings.append({"column": col, "type": "3sigma_outlier", "count": int(len(outliers)), "mean": float(mean), "std": float(std)})
    return findings

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    print(json.dumps(detect(Path(args.csv)), ensure_ascii=False, indent=2))
