from __future__ import annotations
from pathlib import Path
from .process_runner import run_process

def first_path(discovery: dict, key: str) -> str:
    paths = discovery["executables"].get(key) or []
    if not paths:
        raise RuntimeError(f"Moldflow utility not discovered: {key}")
    return paths[0]

def run_study(discovery: dict, study: Path, timeout: int, dry_run: bool):
    exe = first_path(discovery, "runstudy")
    return run_process([exe, str(study)], study.parent, timeout, dry_run)

def export_log(discovery: dict, study: Path, output: Path, timeout: int, dry_run: bool):
    exe = first_path(discovery, "studyrlt")
    argv = [exe, str(study), "-exportoutput", "-output", str(output), "-unit", "Metric"]
    return run_process(argv, study.parent, timeout, dry_run)

def modify_study(discovery: dict, source: Path, target: Path, modifier_xml: Path,
                 timeout: int, dry_run: bool):
    exe = first_path(discovery, "studymod")
    argv = [exe, str(source), str(target), str(modifier_xml)]
    return run_process(argv, source.parent, timeout, dry_run)
