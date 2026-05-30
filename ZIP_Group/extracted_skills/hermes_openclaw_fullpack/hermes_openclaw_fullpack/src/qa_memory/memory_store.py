from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import os
import uuid

MEMORY_FILE = Path(os.getenv("HERMES_MEMORY_FILE", "/workspace/hermes_sandbox/qa_memory.jsonl"))

@dataclass
class MemoryItem:
    id: str
    created_at: str
    category: str
    title: str
    body: str
    source: str

class MemoryStore:
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def add(self, category: str, title: str, body: str, source: str = "manual") -> dict:
        item = MemoryItem(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(timespec="seconds"),
            category=category,
            title=title,
            body=body,
            source=source,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return asdict(item)

    def search(self, q: str, limit: int = 10) -> list[dict]:
        q_lower = q.lower()
        hits = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                haystack = f"{obj.get('category','')} {obj.get('title','')} {obj.get('body','')}".lower()
                if q_lower in haystack:
                    hits.append(obj)
        return hits[-limit:][::-1]
