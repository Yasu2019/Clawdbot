from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import csv
import json
from pathlib import Path

# backend/app をimportできるようにする
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import ContentIdea  # noqa: E402
from app.scorer import ContentFiveForcesScorer  # noqa: E402


def evaluate_json(path: Path, output: Path | None) -> None:
    scorer = ContentFiveForcesScorer(config_dir=ROOT / "configs")
    data = json.loads(path.read_text(encoding="utf-8"))
    result = scorer.evaluate(ContentIdea(**data))
    text = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
    if output:
        output.write_text(text, encoding="utf-8")
    print(text)


def evaluate_csv(path: Path, output: Path | None) -> None:
    scorer = ContentFiveForcesScorer(config_dir=ROOT / "configs")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    out_rows = []
    for row in rows:
        idea = ContentIdea(
            title=row.get("title", ""),
            target_audience=row.get("target_audience", ""),
            pain=row.get("pain", ""),
            proof=row.get("proof", ""),
            unique_angle=row.get("unique_angle", ""),
            preferred_platform=row.get("preferred_platform", "auto") or "auto",
        )
        result = scorer.evaluate(idea)
        out_rows.append(
            {
                "title": result.title,
                "total_score": result.total_score,
                "decision": result.decision,
                "recommended_platform": result.recommended_platform,
                "risks": " / ".join(result.risks),
                "next_actions": " / ".join(result.next_actions),
            }
        )

    fieldnames = [
        "title",
        "total_score",
        "decision",
        "recommended_platform",
        "risks",
        "next_actions",
    ]

    if output:
        # Excelで開いても文字化けしにくい utf-8-sig
        with output.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"saved: {output}")
    else:
        for row in out_rows:
            print(json.dumps(row, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Content 5-Forces Gate CLI")
    parser.add_argument("--json", type=Path, help="JSON入力ファイル")
    parser.add_argument("--csv", type=Path, help="CSV入力ファイル")
    parser.add_argument("--output", type=Path, help="出力ファイル")
    args = parser.parse_args()

    if args.json:
        evaluate_json(args.json, args.output)
    elif args.csv:
        evaluate_csv(args.csv, args.output)
    else:
        parser.error("--json または --csv を指定してください。")


if __name__ == "__main__":
    main()
