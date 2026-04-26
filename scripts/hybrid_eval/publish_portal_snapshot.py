import argparse
import csv
import json
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def now_iso_local() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_text(value: str | None) -> str:
    return (value or "").replace("\r\n", "\n").strip()


def find_latest_phase0(phase0_root: Path) -> Path | None:
    if not phase0_root.exists():
        return None
    candidates = [p for p in phase0_root.iterdir() if p.is_dir()]
    candidates.sort(key=lambda p: p.name, reverse=True)
    for p in candidates:
        if (p / "compare_results.csv").exists():
            return p
    for p in candidates:
        if (p / "suite_results.csv").exists():
            return p
    return None


def load_compare_rows(compare_csv: Path) -> list[dict]:
    with compare_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_suite_rows(suite_csv: Path) -> list[dict]:
    with suite_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_case_texts(run_dir: Path) -> tuple[str, str, str]:
    err = ""
    ollama_text = ""
    foundry_text = ""

    o = run_dir / "ollama_raw.json"
    f = run_dir / "foundry_raw.json"

    if o.exists():
        obj = read_json(o)
        if isinstance(obj, dict) and obj.get("error"):
            err = f"ollama: {obj.get('error')}"
        ollama_text = safe_text(str(obj.get("response") or ""))
        if not ollama_text and obj.get("thinking"):
            ollama_text = safe_text(str(obj.get("thinking") or ""))
    else:
        err = (err + " / missing ollama_raw.json").strip(" /")

    if f.exists():
        obj = read_json(f)
        if isinstance(obj, dict) and obj.get("error"):
            err = (err + f" / foundry: {obj.get('error')}").strip(" /")
        foundry_text = safe_text(str(obj.get("stdout") or ""))
    else:
        # suite-only runs won't have foundry
        pass

    return ollama_text, foundry_text, err


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish hybrid eval snapshot into Portal app folder.")
    parser.add_argument("--phase0-root", default="tmp/foundrylocal_phase0")
    parser.add_argument("--phase0-dir", default="", help="Use a specific phase0 dir (overrides auto latest).")
    parser.add_argument("--app-dir", default="data/workspace/apps/hybrid_eval_compare")
    args = parser.parse_args()

    phase0_root = (REPO_ROOT / args.phase0_root).resolve()
    # data/workspace can be a junction outside repo root; don't assume subpath
    app_dir = (REPO_ROOT / args.app_dir).resolve()
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    if args.phase0_dir:
        phase0_dir = (REPO_ROOT / args.phase0_dir).resolve()
    else:
        phase0_dir = find_latest_phase0(phase0_root)

    if not phase0_dir or not phase0_dir.exists():
        raise SystemExit(f"Phase0 dir not found under: {phase0_root}")

    compare_csv = phase0_dir / "compare_results.csv"
    suite_csv = phase0_dir / "suite_results.csv"

    def _rel_if_possible(p: Path, base: Path) -> str:
        try:
            return str(p.relative_to(base)).replace("\\", "/")
        except Exception:
            return str(p).replace("\\", "/")

    snapshot: dict = {
        "generated_at": now_iso_local(),
        "source_phase0_dir": _rel_if_possible(phase0_dir, REPO_ROOT),
        "rows": [],
    }

    if compare_csv.exists():
        rows = load_compare_rows(compare_csv)
        # also publish the raw artifacts for user download
        (data_dir / "compare_results.csv").write_bytes(compare_csv.read_bytes())
        md = phase0_dir / "compare_outputs.md"
        if md.exists():
            (data_dir / "compare_outputs.md").write_bytes(md.read_bytes())

        for r in rows:
            run_dir = REPO_ROOT / (r.get("run_dir") or "")
            ollama_text, foundry_text, err = load_case_texts(run_dir) if run_dir.exists() else ("", "", "missing run_dir")
            snapshot["rows"].append(
                {
                    "case_no": int(r.get("case_no") or 0) or None,
                    "date": r.get("date"),
                    "prompt_file": r.get("prompt_file"),
                    "elapsed_sec": float(r.get("elapsed_sec") or 0) or None,
                    "ollama_model": r.get("ollama_model"),
                    "foundry": r.get("foundry"),
                    "ollama_chars": int(r.get("ollama_chars") or 0),
                    "foundry_chars": int(r.get("foundry_chars") or 0),
                    "run_dir": r.get("run_dir"),
                    "ollama_text": ollama_text,
                    "foundry_text": foundry_text,
                    "error": err or r.get("error") or "",
                }
            )

    elif suite_csv.exists():
        rows = load_suite_rows(suite_csv)
        (data_dir / "suite_results.csv").write_bytes(suite_csv.read_bytes())
        for r in rows:
            run_dir = REPO_ROOT / (r.get("run_dir") or "")
            ollama_text, _, err = load_case_texts(run_dir) if run_dir.exists() else ("", "", "missing run_dir")
            snapshot["rows"].append(
                {
                    "case_no": int(r.get("case_no") or 0) or None,
                    "date": r.get("date"),
                    "prompt_file": r.get("prompt_template"),
                    "elapsed_sec": float(r.get("elapsed_sec") or 0) or None,
                    "ollama_model": r.get("model"),
                    "foundry": "",
                    "ollama_chars": int(r.get("output_chars") or 0),
                    "foundry_chars": 0,
                    "run_dir": r.get("run_dir"),
                    "ollama_text": ollama_text,
                    "foundry_text": "",
                    "error": err or r.get("error") or "",
                }
            )
    else:
        raise SystemExit(f"No compare_results.csv or suite_results.csv in: {phase0_dir}")

    latest_path = data_dir / "latest.json"
    latest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_rel_if_possible(latest_path, REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
