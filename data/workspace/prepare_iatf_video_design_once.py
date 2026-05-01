"""Prepare intent/storyboard materials for one IATF training video.

The purpose of this pilot is to add a design gate before DeepSeek/video
generation.  It turns one PDF into:

- intent_map.json: what the document is trying to teach
- storyboard.json: what each video scene must show
- deepseek_handoff_prompt.md: constrained prompt for script/video generation
- storyboard_check_slides/: human/AI review slides before rendering
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "clawstack_v2/apps/iatf_video_factory"
STATUS_PATH = ROOT / "data/workspace/iatf_video_design_status.json"
sys.path.insert(0, str(APP_DIR))

import run_host  # noqa: E402


SLIDE_SIZE = (1280, 720)


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def lines_from_pdf_text(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = normalize_space(raw)
        if len(line) >= 3:
            lines.append(line)
    return lines


def find_lines(lines: list[str], patterns: list[str], limit: int = 8) -> list[str]:
    hits: list[str] = []
    for line in lines:
        if any(pattern in line for pattern in patterns):
            hits.append(line)
        if len(hits) >= limit:
            break
    return hits


def clause_topic(pdf_path: Path) -> tuple[str, str]:
    stem = pdf_path.stem
    parts = stem.replace("箇条", "").split("_")
    clause = parts[1].strip() if len(parts) > 1 else "?"
    topic = parts[2].strip() if len(parts) > 2 else stem
    return clause, topic


def infer_intent_map(pdf_path: Path, pdf_text: str) -> dict:
    clause, topic = clause_topic(pdf_path)
    lines = lines_from_pdf_text(pdf_text)

    requirement_lines = find_lines(
        lines,
        ["要求事項", "しなければならない", "確実に実施", "文書化", "管理", "保存", "顧客要求"],
        limit=16,
    )
    evidence_lines = find_lines(
        lines,
        [
            "記録", "証拠", "指示書", "標準", "作業カード", "QMI", "ラベル",
            "識別", "箱", "容器", "保管", "FIFO", "先入先出", "40個", "50個",
            "顧客", "梱包",
        ],
        limit=16,
    )
    risk_lines = find_lines(
        lines,
        ["リスク", "不適合", "クレーム", "問題", "誤", "欠落", "不足", "混入", "汚染", "旧品"],
        limit=16,
    )
    audit_question_lines = find_lines(
        lines,
        ["確認", "質問", "監査", "どのよう", "なぜ", "誰が", "いつ", "どこ", "手順"],
        limit=12,
    )

    show_evidence = []
    for keyword in [
        "梱包指示書", "作業指示書", "作業カード", "QMI", "ラベル", "箱",
        "容器", "40個", "50個", "保管棚", "FIFO", "旧品", "不適合品",
        "顧客仕様", "顧客要求",
    ]:
        if keyword in pdf_text:
            show_evidence.append(keyword)
    if not show_evidence:
        show_evidence = ["該当工程の作業標準", "現場記録", "識別表示", "保管状態"]

    return {
        "source_pdf": str(pdf_path),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "clause": clause,
        "topic": topic,
        "document_intent": {
            "primary_lesson": f"箇条{clause}「{topic}」について、内部監査で何を確認し、どの証拠で判断するかを理解する。",
            "learner_outcome": "受講者が、現場で要求事項に対する証拠・リスク・不適合候補を説明できる。",
            "video_must_not_do": [
                "PDF本文を単に読み上げるだけにしない",
                "キャラクターだけを映し続けない",
                "証拠物や監査判断ポイントがない抽象的な会話にしない",
            ],
        },
        "source_backed_points": {
            "requirements": requirement_lines,
            "evidence_candidates": evidence_lines,
            "risk_or_nonconformity_candidates": risk_lines,
            "audit_question_candidates": audit_question_lines,
        },
        "must_show_evidence": show_evidence,
        "known_scenario_signals": {
            "customer_specific_pack_count": ["40個", "50個"] if "40個" in pdf_text or "50個" in pdf_text else [],
            "document_access_issue": ["梱包指示書が現場になくQMI参照"] if "QMI" in pdf_text else [],
            "audit_story_hook": "顧客別の梱包数量・梱包指示の現場利用性を、監査員が証拠で確認する。",
        },
        "quality_gates": [
            "各シーンに、資料由来の根拠または監査証拠が最低1つある",
            "前半・中盤・後半チェック用スライドで、台本と場面意図が一致している",
            "動画フレームに人物だけでなく、確認対象の証拠物または現場状態が映っている",
            "Visual QAで静止・極端な寄り・背面のみ・低情報量を検出したらMP4化しない",
        ],
    }


def storyboard_from_intent(intent: dict) -> dict:
    clause = intent["clause"]
    topic = intent["topic"]
    evidence = intent.get("must_show_evidence", [])
    reqs = intent["source_backed_points"].get("requirements", [])
    risks = intent["source_backed_points"].get("risk_or_nonconformity_candidates", [])
    questions = intent["source_backed_points"].get("audit_question_candidates", [])

    scenes = [
        {
            "scene_id": "opening",
            "purpose": "受講者に箇条と監査テーマを明示する",
            "must_show": [f"箇条{clause}", topic, "今回確認する証拠一覧"],
            "audit_focus": reqs[:3],
            "deepseek_instruction": "MCは要求事項を羅列するだけでなく、現場で何を確認する教材かを宣言する。",
        },
        {
            "scene_id": "requirements_to_evidence",
            "purpose": "要求事項を現場証拠へ変換する",
            "must_show": evidence[:5],
            "audit_focus": reqs[:6],
            "deepseek_instruction": "要求文を、監査員が見る証拠物・記録・表示に変換して説明する。",
        },
        {
            "scene_id": "on_site_observation",
            "purpose": "現場観察で、良い状態と怪しい状態を見分ける",
            "must_show": evidence,
            "audit_focus": questions[:5],
            "deepseek_instruction": "監査員の質問、被監査者の回答、現場証拠の照合を対話で進める。",
        },
        {
            "scene_id": "finding_risk",
            "purpose": "不適合候補・リスクを特定する",
            "must_show": ["不適合候補の一覧", "要求事項とのズレ", "影響範囲"],
            "audit_focus": risks[:6],
            "deepseek_instruction": "何が要求事項とズレているのかを、感想ではなく証拠ベースで指摘する。",
        },
        {
            "scene_id": "corrective_action",
            "purpose": "是正処置・再発防止・監査証跡を示す",
            "must_show": ["是正処置案", "再発防止策", "更新すべき記録"],
            "audit_focus": reqs[3:9],
            "deepseek_instruction": "対応策は、責任者・記録・確認頻度・有効性確認まで含める。",
        },
        {
            "scene_id": "closing_review",
            "purpose": "受講者が判断できる状態に整理する",
            "must_show": ["監査質問3点", "証拠3点", "不適合候補3点"],
            "audit_focus": reqs[:4] + risks[:4],
            "deepseek_instruction": "最後に、受講者が現場で使えるチェック観点としてまとめる。",
        },
    ]
    return {
        "source_pdf": intent["source_pdf"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "clause": clause,
        "topic": topic,
        "scenes": scenes,
        "rendering_constraints": {
            "primary_visual_subject": "監査証拠物と現場状態",
            "characters_are": "説明と対話の補助",
            "forbidden_visuals": ["人物の背面だけ", "衣服や体の一部だけの極端な寄り", "証拠物がない抽象背景"],
        },
    }


def deepseek_prompt(intent: dict, storyboard: dict) -> str:
    return f"""# DeepSeek Pro Handoff: IATF Training Video

あなたはIATF 16949内部監査教育動画の台本・動画設計担当です。
以下の `intent_map` と `storyboard` は、ChatGPT/Codex側でPDF資料から抽出した拘束条件です。
この拘束条件を破らずに、台本・チェック用スライド・動画レンダー指示を生成してください。

## 絶対ルール
- PDF本文の単なる読み上げにしない。
- 各シーンに監査証拠物または現場状態を入れる。
- キャラクターは補助であり、主役は「監査で確認する証拠」。
- 前半・中盤・後半の確認スライドで意図と台本が一致しない場合、動画生成へ進まない。
- 動画では人物の背面だけ、衣服だけ、静止画に近い映像を禁止する。

## Required Output JSON
```json
{{
  "script": {{
    "scenes": [
      {{
        "scene_id": "opening",
        "lines": [
          {{"character": "bulma", "text": "...", "visual_action": "...", "evidence_on_screen": ["..."]}}
        ]
      }}
    ]
  }},
  "slide_plan": [
    {{"checkpoint": "front", "scene_id": "...", "must_match": "..."}}
  ],
  "render_plan": [
    {{"scene_id": "...", "camera": "...", "foreground_evidence": ["..."], "forbidden": ["..."]}}
  ]
}}
```

## intent_map
```json
{json.dumps(intent, ensure_ascii=False, indent=2)}
```

## storyboard
```json
{json.dumps(storyboard, ensure_ascii=False, indent=2)}
```
"""


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font_obj)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def render_storyboard_slides(storyboard: dict, out_dir: Path) -> Path:
    slides_dir = out_dir / "storyboard_check_slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    title_font = font(34, bold=True)
    body_font = font(24)
    small_font = font(18)

    slide_paths = []
    for index, scene in enumerate(storyboard["scenes"], start=1):
        image = Image.new("RGB", SLIDE_SIZE, "#f8fafc")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1280, 78), fill="#11314f")
        draw.text((44, 22), f"Storyboard Check {index}/{len(storyboard['scenes'])}", fill="white", font=title_font)
        y = 108
        blocks = [
            ("Scene", f"{scene['scene_id']} / {scene['purpose']}"),
            ("Must Show", " / ".join(scene.get("must_show", []))),
            ("Audit Focus", " / ".join(scene.get("audit_focus", [])[:4])),
            ("DeepSeek Instruction", scene.get("deepseek_instruction", "")),
        ]
        for label, text in blocks:
            draw.text((48, y), label, fill="#0f172a", font=small_font)
            y += 28
            for line in wrap(draw, text, body_font, 1120)[:4]:
                draw.text((72, y), line, fill="#1e293b", font=body_font)
                y += 34
            y += 16
        slide_path = slides_dir / f"storyboard_{index:02d}.jpg"
        image.save(slide_path, quality=92)
        slide_paths.append(slide_path)

    sheet = Image.new("RGB", (960, 642), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(slide_paths):
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((320, 180))
        x = (idx % 3) * 320
        y = (idx // 3) * 214
        sheet.paste(thumb, (x, y))
        draw.text((x + 8, y + 184), path.name, fill="#111827", font=small_font)
    contact_sheet = slides_dir / "contact_sheet.jpg"
    sheet.save(contact_sheet, quality=92)
    return contact_sheet


def main() -> int:
    pdfs = run_host.list_pending(1)
    if not pdfs:
        raise RuntimeError("No pending IATF PDFs found")
    pdf_path = pdfs[0]
    out_dir = run_host.OUTPUT_DIR / f"{pdf_path.stem}_design_pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_status("extract_pdf", pdf=str(pdf_path), output_dir=str(out_dir))
    pdf_text = run_host.extract_pdf(pdf_path)
    (out_dir / "source_excerpt.txt").write_text(pdf_text[:12000], encoding="utf-8")

    write_status("build_intent_map", chars=len(pdf_text))
    intent = infer_intent_map(pdf_path, pdf_text)
    (out_dir / "intent_map.json").write_text(json.dumps(intent, ensure_ascii=False, indent=2), encoding="utf-8")

    write_status("build_storyboard")
    storyboard = storyboard_from_intent(intent)
    (out_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    write_status("write_deepseek_handoff")
    prompt = deepseek_prompt(intent, storyboard)
    (out_dir / "deepseek_handoff_prompt.md").write_text(prompt, encoding="utf-8")

    write_status("render_storyboard_slides")
    contact_sheet = render_storyboard_slides(storyboard, out_dir)

    result = {
        "ok": True,
        "pdf": str(pdf_path),
        "output_dir": str(out_dir),
        "intent_map": str(out_dir / "intent_map.json"),
        "storyboard": str(out_dir / "storyboard.json"),
        "deepseek_handoff_prompt": str(out_dir / "deepseek_handoff_prompt.md"),
        "storyboard_contact_sheet": str(contact_sheet),
    }
    (out_dir / "design_pilot_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_status("done", **result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
