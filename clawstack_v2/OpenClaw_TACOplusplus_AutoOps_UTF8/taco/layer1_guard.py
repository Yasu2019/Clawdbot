import re
from dataclasses import dataclass

@dataclass
class GuardResult:
    protected_lines: list[str]
    normal_lines: list[str]
    protected_count: int

class Layer1Guard:
    def __init__(self, patterns, before=8, after=16):
        self.patterns = [re.compile(p, re.I) for p in patterns]
        self.before = before
        self.after = after

    def is_critical(self, line: str) -> bool:
        return any(p.search(line or "") for p in self.patterns)

    def split(self, text: str) -> GuardResult:
        lines = text.splitlines()
        keep = set()
        for i, line in enumerate(lines):
            if self.is_critical(line):
                for j in range(max(0, i-self.before), min(len(lines), i+self.after+1)):
                    keep.add(j)
        protected, normal = [], []
        for i, line in enumerate(lines):
            (protected if i in keep else normal).append(line)
        return GuardResult(protected, normal, len(protected))
