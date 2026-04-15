from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime
from skill_registry import SkillRegistry, Skill

LOG_DIR = Path("/logs")

def extract_candidate_from_summary(summary: dict) -> Skill | None:
    # デモ用の単純な規則:
    # review になったタスクがあれば、安定化用スキル候補を提案
    if summary.get("result_label") == "review":
        task_id = summary["task_id"]
        return Skill(
            skill_id=f"PROP_{task_id}",
            name=f"stability_guard_for_{task_id}",
            description=f"Task {task_id} needs output normalization or stricter template.",
            source_task_id=task_id,
            status="proposed",
        )
    return None

def main() -> None:
    registry = SkillRegistry()
    created = []

    for p in LOG_DIR.glob("*_summary.json"):
        if p.name == "all_tasks_summary.json":
            continue
        summary = json.loads(p.read_text(encoding="utf-8"))
        skill = extract_candidate_from_summary(summary)
        if skill:
            registry.add_proposal(skill)
            created.append({
                "skill_id": skill.skill_id,
                "task_id": skill.source_task_id,
                "created_at": datetime.utcnow().isoformat() + "Z"
            })

    out = LOG_DIR / "skill_proposals.json"
    out.write_text(json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Hermes learning loop demo completed.")
    print(json.dumps(created, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
