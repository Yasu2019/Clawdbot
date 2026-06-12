from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def discover_repo_root() -> Path:
    for candidate in [
        Path.cwd(),
        Path("D:/Clawdbot_Docker_20260125"),
        Path("E:/ClawstackData"),
    ]:
        resolved = candidate.resolve()
        if (resolved / "AGENTS.md").exists() and (resolved / "data" / "state").exists():
            return resolved
    raise FileNotFoundError("Could not locate repository root.")


ROOT = discover_repo_root()
STATE_DIR = ROOT / "data" / "state"
WORKSPACE_DIR = ROOT / "data" / "workspace"
TEMPLATE_PATH = STATE_DIR / "litellm_config.gemma4.experimental.yaml"
RENDERED_PATH = STATE_DIR / "litellm_config.gemma4.ready.yaml"
STATUS_PATH = WORKSPACE_DIR / "gemma4_activation_status.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Gemma 4 LiteLLM overlay once exact Ollama tags are known.")
    parser.add_argument("--small-tag", required=True, help="Exact Ollama tag for the small Gemma 4 route.")
    parser.add_argument("--main-tag", required=True, help="Exact Ollama tag for the main Gemma 4 route.")
    args = parser.parse_args()

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = (
        template.replace("REPLACE_WITH_GEMMA4_SMALL_TAG", args.small_tag)
        .replace("REPLACE_WITH_GEMMA4_MAIN_TAG", args.main_tag)
    )
    if "gemma4" in args.main_tag.lower():
        lines: list[str] = []
        after_main_model = False
        for line in rendered.splitlines():
            if f"openai/{args.main_tag}" in line:
                after_main_model = True
            if after_main_model and "api_base: http://ollama:11434/v1" in line:
                line = line.replace(
                    "http://ollama:11434/v1",
                    "http://host.docker.internal:11435/v1",
                )
                after_main_model = False
            lines.append(line)
        rendered = "\n".join(lines) + "\n"
    RENDERED_PATH.write_text(rendered, encoding="utf-8")

    status = {
        "updatedAt": iso_now(),
        "templatePath": str(TEMPLATE_PATH),
        "renderedPath": str(RENDERED_PATH),
        "smallTag": args.small_tag,
        "mainTag": args.main_tag,
        "status": "rendered",
        "nextStep": "Review litellm_config.gemma4.ready.yaml, then merge or mount it intentionally before restarting LiteLLM.",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
