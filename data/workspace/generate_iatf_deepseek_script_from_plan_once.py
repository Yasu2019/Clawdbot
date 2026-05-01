"""Generate a constrained scene script from approved DeepSeek IATF plan.

This keeps the LLM calls small by asking for one scene at a time.  The output
is a script JSON with visual_action and evidence_on_screen fields, suitable for
the next slide/video preflight step.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data/workspace/iatf_deepseek_scene_script_status.json"


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def find_design_dir() -> Path:
    candidates = [
        path
        for path in (ROOT / "data/iatf_videos").iterdir()
        if path.is_dir() and path.name.endswith("_design_pilot")
    ]
    if not candidates:
        raise RuntimeError("No *_design_pilot directory found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def call_deepseek_scene(scene_prompt: dict, out_raw: Path) -> dict:
    endpoint = os.environ["OPENCODE_GO_API_BASE"].rstrip("/") + "/chat/completions"
    messages = [
        {
            "role": "system",
            "content": (
                "Return valid JSON only. No markdown. "
                "Use the exact output schema. Keep it compact."
            ),
        },
        {"role": "user", "content": json.dumps(scene_prompt, ensure_ascii=False)},
    ]
    errors: list[str] = []
    for model in ["deepseek-v4-flash", "deepseek-v4-pro", "kimi-k2.6"]:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": "Bearer " + os.environ["OPENCODE_GO_API_KEY"],
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.15,
                "max_tokens": 2200,
            },
            timeout=240,
        )
        raw_model_path = out_raw.with_name(f"{out_raw.stem}_{model.replace('/', '_')}{out_raw.suffix}")
        if response.status_code >= 400:
            raw_model_path.write_text(response.text, encoding="utf-8")
            errors.append(f"{model}:http_{response.status_code}")
            continue
        content = (response.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
        raw_model_path.write_text(content, encoding="utf-8")
        clean = content.strip()
        if not clean:
            errors.append(f"{model}:empty")
            continue
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
        try:
            parsed = json.loads(clean.strip())
            out_raw.write_text(content, encoding="utf-8")
            parsed["model_used"] = f"direct/{model}"
            return parsed
        except json.JSONDecodeError as exc:
            errors.append(f"{model}:json:{exc}")
    raise RuntimeError("All scene models failed: " + "; ".join(errors))


def local_scene_fallback(scene: dict, slide: dict, render_plan: dict, intent: dict) -> dict:
    scene_id = scene.get("scene_id", "")
    evidence = slide.get("visual_evidence") or render_plan.get("foreground_evidence") or scene.get("must_show", [])
    evidence_text = "、".join(evidence[:5]) or "現場証拠"
    must_match = slide.get("must_match") or scene.get("purpose", scene_id)
    camera = render_plan.get("camera", "audit evidence close-up")

    templates = {
        "opening": [
            ("bulma", f"本日はIATF 16949 箇条{intent.get('clause')}「{intent.get('topic')}」の内部監査教材です。今回は、資料を読むだけでなく、現場で何を証拠として見るかを確認します。"),
            ("goku", f"最初に確認する観点は「{must_match}」です。画面には、今回の監査で使う証拠一覧を表示します。"),
        ],
        "requirements_to_evidence": [
            ("roshi", f"要求事項は、現場で確認できる証拠に置き換えて考えるのじゃ。今回の証拠は、{evidence_text} じゃ。"),
            ("bulma", "つまり、要求文を覚えるだけではなく、どの記録や表示で適合を判断するかを確認するのね。"),
        ],
        "on_site_observation": [
            ("goku", f"梱包工程を確認します。作業カード、QMI、箱の40個/50個表示、FIFOラベルを順に見せてください。"),
            ("gohan", "はい。QMIで梱包指示を確認できますが、現場の作業カードが最新かどうかは、今ここで照合します。"),
            ("goku", "顧客別の梱包数量が違う場合、現場で迷わず判断できる状態でなければ、不適合候補になります。"),
        ],
        "finding_risk": [
            ("android17", f"不適合候補は、{must_match} です。証拠が現場で確認できない場合、要求事項とのズレとして扱います。"),
            ("android18", "特に、梱包指示書が現場にない、40個/50個の区別が曖昧、FIFOや旧品管理が見えない状態はリスクです。"),
        ],
        "corrective_action": [
            ("android18", "是正処置として、改訂版作業カードを現場に配置し、QMIとの整合を確認します。さらに、ポカヨケや点検記録で再発防止を残します。"),
            ("gohan", "責任者、期限、有効性確認の方法を記録し、次回監査で追跡できるようにします。"),
        ],
        "closing_review": [
            ("roshi", "最後に、監査質問、確認証拠、不適合候補を3点ずつ整理するのじゃ。"),
            ("bulma", f"今回のポイントは、{evidence_text} を使って、箇条{intent.get('clause')}の要求に適合しているかを証拠で判断することです。"),
        ],
    }
    lines = []
    for character, text in templates.get(scene_id, templates["closing_review"]):
        lines.append(
            {
                "character": character,
                "text": text,
                "visual_action": f"{camera}; evidence focus: {evidence_text}",
                "evidence_on_screen": evidence[:8],
                "emotion": "explain",
                "pose": "point",
            }
        )
    return {
        "scene_id": scene_id,
        "scene_name": scene.get("purpose", scene_id),
        "model_used": "local/plan_constrained_fallback",
        "lines": lines,
    }


def main() -> int:
    load_env()
    if not os.environ.get("OPENCODE_GO_API_KEY") or not os.environ.get("OPENCODE_GO_API_BASE"):
        raise RuntimeError("OPENCODE_GO_API_KEY / OPENCODE_GO_API_BASE are required")

    design_dir = find_design_dir()
    approval = design_dir / "deepseek_plan_check_slides/codex_visual_approval.json"
    if not approval.exists():
        raise RuntimeError(f"Plan slides are not visually approved yet: {approval}")

    intent = json.loads((design_dir / "intent_map.json").read_text(encoding="utf-8"))
    storyboard = json.loads((design_dir / "storyboard.json").read_text(encoding="utf-8"))
    compact_plan = json.loads((design_dir / "deepseek_compact_video_plan.json").read_text(encoding="utf-8"))

    render_by_scene = {item.get("scene_id"): item for item in compact_plan.get("render_plan", [])}
    slide_by_scene = {item.get("scene_id"): item for item in compact_plan.get("slide_plan", [])}

    raw_dir = design_dir / "deepseek_scene_script_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    scenes_out: list[dict] = []

    for index, scene in enumerate(storyboard.get("scenes", []), start=1):
        scene_id = scene.get("scene_id")
        prompt = {
            "task": "Generate one compact IATF training-video scene script.",
            "source_clause": intent.get("clause"),
            "topic": intent.get("topic"),
            "scene": scene,
            "slide_checkpoint": slide_by_scene.get(scene_id, {}),
            "render_plan": render_by_scene.get(scene_id, {}),
            "global_constraints": compact_plan.get("script_constraints", []),
            "rules": [
                "Use audit dialogue and evidence-based wording.",
                "Every line must include visual_action and evidence_on_screen.",
                "Do not invent confidential customer names.",
                "Keep each scene to 2 or 3 lines.",
                "Characters must be one of: bulma, goku, gohan, android17, android18, roshi, trunks.",
            ],
            "output_schema": {
                "scene_id": scene_id,
                "scene_name": "",
                "lines": [
                    {
                        "character": "goku",
                        "text": "",
                        "visual_action": "",
                        "evidence_on_screen": [""],
                        "emotion": "normal",
                        "pose": "neutral",
                    }
                ],
            },
        }
        write_status("request_scene", scene_id=scene_id, index=index)
        try:
            scene_result = call_deepseek_scene(prompt, raw_dir / f"{index:02d}_{scene_id}.txt")
        except Exception as exc:
            write_status("scene_fallback", scene_id=scene_id, reason=str(exc)[:300])
            scene_result = local_scene_fallback(
                scene=scene,
                slide=slide_by_scene.get(scene_id, {}),
                render_plan=render_by_scene.get(scene_id, {}),
                intent=intent,
            )
        scene_result.setdefault("scene_id", scene_id)
        scene_result.setdefault("scene_name", scene.get("purpose", scene_id))
        scenes_out.append(scene_result)

    script = {
        "source_pdf": intent.get("source_pdf"),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "model_used": "direct/deepseek-v4-flash",
        "generation_mode": "intent_map_storyboard_deepseek_plan",
        "clause": intent.get("clause"),
        "topic": intent.get("topic"),
        "scenes": scenes_out,
        "quality_requirements": intent.get("quality_gates", []),
    }
    out_path = design_dir / "deepseek_scene_script.json"
    out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    write_status("done", ok=True, script=str(out_path), scenes=len(scenes_out))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
