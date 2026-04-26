from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import List

@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    source_task_id: str
    status: str  # proposed / approved / rejected / disabled

class SkillRegistry:
    def __init__(self, path: str = "/skills/registry.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> List[Skill]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [Skill(**item) for item in data]

    def save(self, skills: List[Skill]) -> None:
        self.path.write_text(
            json.dumps([asdict(s) for s in skills], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add_proposal(self, skill: Skill) -> None:
        skills = self.load()
        skills.append(skill)
        self.save(skills)

if __name__ == "__main__":
    registry = SkillRegistry()
    registry.add_proposal(Skill(
        skill_id="SK001",
        name="email_politeness_guard",
        description="Supplier email politeness and action-item formatting rule",
        source_task_id="T002",
        status="proposed"
    ))
    print("Proposed skill added.")
