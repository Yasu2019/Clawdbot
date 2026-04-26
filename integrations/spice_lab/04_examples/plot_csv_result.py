"""Plot ngspice wrdata CSV-like output.
Usage:
  python plot_csv_result.py path/to/file.csv
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    raise SystemExit("Usage: python plot_csv_result.py path/to/file.csv")

path = Path(sys.argv[1])
# ngspice wrdata often writes whitespace-separated columns.
df = pd.read_csv(path, delim_whitespace=True, header=None, comment='*')
print(df.head())

x = df.iloc[:, 0]
for col in range(1, df.shape[1]):
    plt.figure()
    plt.plot(x, df.iloc[:, col])
    plt.xlabel('time or index')
    plt.ylabel(f'column {col}')
    out = path.with_name(f'{path.stem}_col{col}.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'wrote {out}')
