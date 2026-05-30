import re
from dataclasses import dataclass, asdict

BLOCK_PATTERNS = [
    r"\brm\s+-rf\s+(/|~|\*)",
    r"\bdel\s+/s\s+/q\s+[A-Z]:\\",
    r"\bformat\s+[A-Z]:",
    r"\bdocker\s+(system\s+prune|volume\s+rm|rm\s+-f)",
    r"\bgit\s+reset\s+--hard",
    r"\bgit\s+clean\s+-fdx",
    r"\bdrop\s+database\b",
    r"\btruncate\s+table\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bmkfs\b",
]

WARN_PATTERNS = [
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bdocker\s+compose\s+down\b",
    r"\bchmod\s+777\b",
    r"\bcurl\b.*\|\s*(sh|bash)",
    r"\bInvoke-WebRequest\b.*\|",
]

@dataclass
class GuardResult:
    allowed: bool
    level: str
    message: str
    matched_pattern: str | None = None


def validate_command(command: str) -> dict:
    normalized = command.strip()
    for pat in BLOCK_PATTERNS:
        if re.search(pat, normalized, flags=re.IGNORECASE):
            return asdict(GuardResult(False, "block", "破壊的または高リスクのため実行禁止", pat))
    for pat in WARN_PATTERNS:
        if re.search(pat, normalized, flags=re.IGNORECASE):
            return asdict(GuardResult(False, "review", "人間レビュー後のみ実行可", pat))
    return asdict(GuardResult(True, "allow", "検証用sandbox内で実行可", None))
