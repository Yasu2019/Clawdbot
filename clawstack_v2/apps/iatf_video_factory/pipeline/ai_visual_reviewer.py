"""AI Visual Reviewer -- checklist-driven multimodal gate (OpenCodeGo / Qwen2-VL)."""
import json
import os
import re
import sys
from pathlib import Path

import base64
import time
import requests

try:
    from dotenv import load_dotenv as _load_dotenv
    # Walk up from this script's location and load all .env files found
    _here = Path(__file__).resolve()
    for _parent in [_here.parent] + list(_here.parents):
        _env_candidate = _parent / ".env"
        if _env_candidate.exists():
            _load_dotenv(dotenv_path=str(_env_candidate), override=False)
except ImportError:
    pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_prompt(request: dict) -> str:
    visual_mode = request.get("visual_mode", request.get("mode", "render"))
    checks = request.get("vision_checks") or []
    schema = request.get("ai_output_schema") or {}

    lines = [
        "You are an IATF training video quality inspector.",
        "Inspect the contact sheet image. Use ONLY visible evidence.",
        "If uncertain about any item, set pass=false (fail closed).",
        "",
        "Output ONLY one JSON object, no markdown:",
        json.dumps(
            {
                "approved": "boolean -- true only if ALL checks pass",
                "mode": visual_mode,
                "checks": [
                    {"id": "V01_...", "pass": True, "evidence": "one short sentence"}
                ],
                "reason": "summary if approved is false",
            },
            ensure_ascii=False,
        ),
        "",
        "Vision checklist (evaluate EVERY id):",
    ]
    for chk in checks:
        cid = chk.get("id", "?")
        q = chk.get("question", "")
        fail = chk.get("fail_answer", "fail")
        lines.append(f"- {cid}: {q}")
        lines.append(f"  Set pass=false if: {fail}")
    if request.get("deterministic_failed"):
        lines.append("")
        lines.append(
            "Note: deterministic checks already failed: "
            + ", ".join(request["deterministic_failed"])
        )
    if schema:
        lines.append("")
        lines.append(f"Checklist version: {request.get('checklist_version', '?')}")
    return "\n".join(lines)


def _parse_ai_json(content: str) -> dict | None:
    # Strip markdown fences
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", content)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # Use raw_decode to extract first JSON object (handles trailing text)
    start = content.find("{")
    if start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(content, start)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return None


def _normalize_payload(raw: dict, vision_checks: list[dict]) -> dict:
    checks_out = []
    by_id = {c.get("id"): c for c in raw.get("checks", []) if c.get("id")}
    all_pass = True
    for chk in vision_checks:
        cid = chk["id"]
        item = by_id.get(cid, {})
        passed = bool(item.get("pass", False))
        if not passed:
            all_pass = False
        checks_out.append(
            {
                "id": cid,
                "pass": passed,
                "evidence": str(item.get("evidence", ""))[:240],
            }
        )
    approved = bool(raw.get("approved", False)) and all_pass
    if not all_pass:
        approved = False
    reason = raw.get("reason") or (
        "vision checklist item(s) failed"
        if not all_pass
        else "ok"
    )
    return {
        "approved": approved,
        "mode": raw.get("mode"),
        "checks": checks_out,
        "reason": reason,
    }


_GEMINI_DIRECT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
_GEMINI_VISION_MODEL = "gemini-2.5-flash"


def _call_gemini_vision(prompt: str, base64_image: str, image_mime: str = "image/jpeg") -> str | None:
    """Fallback: call Gemini Vision API directly when OpenCodeGo fails. Returns raw content string."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        return None
    payload = {
        "model": _GEMINI_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_mime};base64,{base64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    for attempt in range(3):
        resp = requests.post(
            _GEMINI_DIRECT_URL,
            headers={"Authorization": f"Bearer {gemini_key}"},
            json=payload,
            timeout=120,
        )
        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    return None  # all retries exhausted


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"approved": False, "reason": "missing request path"}))
        return

    request_path = Path(sys.argv[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    contact_sheet = Path(request.get("contact_sheet", ""))
    visual_mode = request.get("visual_mode", request.get("mode", "slide"))
    vision_checks = request.get("vision_checks") or []

    if not contact_sheet.exists():
        print(json.dumps({"approved": False, "reason": "contact_sheet missing"}))
        return

    prompt = _build_prompt(request)
    image_mime = "image/jpeg" if str(contact_sheet).lower().endswith(".jpg") else "image/png"

    api_key = os.getenv("OPENCODE_GO_API_KEY") or os.getenv("OpenCode_Go")
    url = os.getenv("OPENCODE_GO_API_BASE", "https://opencode.ai/zen/go/v1") + "/chat/completions"
    model = "qwen2-vl-72b" if visual_mode == "render" else "kimi-k2-5"

    content = None
    try:
        base64_image = encode_image(str(contact_sheet))

        if api_key:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{image_mime};base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=60,
            )
            if resp.status_code == 401:
                pass  # fall through to Gemini fallback
            else:
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]

        if content is None:
            content = _call_gemini_vision(prompt, base64_image, image_mime)

        if content is None:
            print(json.dumps({"approved": False, "reason": "no vision API available (OpenCodeGo 401, GEMINI_API_KEY not set)", "checks": []}))
            return

        raw = _parse_ai_json(content)
        if not raw:
            # Non-JSON response: look for explicit rejection keywords first
            lower = content.lower()
            rejected = any(w in lower for w in ("not approved", "reject", "fail", "false", "no pass", "不合格", "不承認"))
            approved = (not rejected) and any(w in lower for w in ("readable", "ok", "yes", "good", "pass", "承認", "合格"))
            print(json.dumps({
                "approved": approved,
                "mode": visual_mode,
                "checks": [],
                "reason": content[:500],
                "_model": "gemini-2.5-flash-vision",
            }, ensure_ascii=False))
            return

        out = _normalize_payload(raw, vision_checks)
        print(json.dumps(out, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"approved": False, "reason": str(e), "checks": []}))


if __name__ == "__main__":
    main()
