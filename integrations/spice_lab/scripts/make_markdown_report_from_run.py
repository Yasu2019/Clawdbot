"""Create a simple Markdown report from a run metadata.json file."""
from __future__ import annotations
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    raise SystemExit("Usage: python make_markdown_report_from_run.py path/to/metadata.json")

meta_path = Path(sys.argv[1])
meta = json.loads(meta_path.read_text(encoding='utf-8'))
run_dir = meta_path.parent
log_path = run_dir / 'run.log'
log_tail = ''
if log_path.exists():
    log = log_path.read_text(encoding='utf-8', errors='replace')
    log_tail = log[-4000:]

md = []
md.append(f"# SPICE Simulation Report: {meta.get('name')}")
md.append("")
md.append(f"- Run ID: `{meta.get('run_id')}`")
md.append(f"- Created UTC: `{meta.get('created_at_utc')}`")
md.append(f"- Exit Code: `{meta.get('exit_code')}`")
md.append(f"- Elapsed sec: `{meta.get('elapsed_sec')}`")
md.append("")
md.append("## Measurements")
md.append("")
for k, v in (meta.get('measurements') or {}).items():
    md.append(f"- `{k}`: {v.get('value')}  ")
    md.append(f"  - raw: `{v.get('raw')}`")
if not meta.get('measurements'):
    md.append("No .meas values parsed.")
md.append("")
md.append("## Files")
md.append("")
for k, v in (meta.get('files') or {}).items():
    md.append(f"- `{k}`: `{v}`")
md.append("")
md.append("## Log Tail")
md.append("")
md.append("```text")
md.append(log_tail)
md.append("```")
md.append("")
md.append("## Notes")
md.append("")
md.append("This simulation is a design-support result. Confirm important decisions with physical measurement and model review.")

out = run_dir / 'report.md'
out.write_text("\n".join(md), encoding='utf-8')
print(out)
