from pathlib import Path
import json

class Corpus2SkillEngine:
    def run(self, query: str) -> str:
        path = Path("data/structure.json")
        if not path.exists():
            return "[Corpus2Skill] structure.json が未作成です。まず文書を階層化してください。"
        structure = json.loads(path.read_text(encoding="utf-8"))
        sections = list(structure.keys())
        return f"[Corpus2Skill探索] query={query} / top_sections={sections}"
