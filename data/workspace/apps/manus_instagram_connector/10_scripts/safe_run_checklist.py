"""
Static safety scanner for this package.

Usage:
  python safe_run_checklist.py <folder>

It scans files for dangerous text patterns.
This is not a full security audit.
"""

from __future__ import annotations

import sys
from pathlib import Path

DANGEROUS = [
    "docker compose down -v",
    "docker volume rm",
    "docker system prune -a --volumes",
    "rm -rf",
    "Remove-Item -Recurse -Force",
    "DROP ",
    "DELETE ",
    "UPDATE ",
    "INSERT ",
    "TRUNCATE ",
    "auto_publish_without_approval=false",
]

ALLOWLIST_FILES = {
    "forbidden_commands_and_actions.md",
    "safety_policy.yaml",
    "safe_run_checklist.py",
    "README.md",
    "00_CLAUDE_README_FIRST.md",
    "05_claude_mini_pc_adoption_prompt.md",
    "rollback_plan.md",
}

def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    issues = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".md", ".py", ".ps1", ".yml", ".yaml", ".json", ".txt"]:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat in DANGEROUS:
                if pat in text and p.name not in ALLOWLIST_FILES:
                    issues.append((str(p), pat))
    print("=== Safety Scan ===")
    if issues:
        print("[CAUTION] Dangerous patterns found outside allowlist:")
        for file, pat in issues:
            print(f" - {file}: {pat}")
        return 1
    print("[OK] No dangerous patterns found outside allowlist.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
