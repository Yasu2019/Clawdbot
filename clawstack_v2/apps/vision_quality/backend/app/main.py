from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from PIL import Image
import uuid, json, os, datetime, shutil, base64, requests
import numpy as np

APP_NAME = "OpenClaw Vision Quality Inspection"

DATA_DIR = Path("/data")
IMAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", "/data/images"))
AUDIT_DIR = Path(os.getenv("AUDIT_LOG_DIR", "/data/audit"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "/data/results"))
for d in [DATA_DIR, IMAGE_DIR, AUDIT_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LITELLM_URL = os.getenv("LITELLM_URL", "http://host.docker.internal:4001")
VISION_MODEL = os.getenv("VISION_MODEL", "google/gemini-2.5-flash")

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InspectionResult(BaseModel):
    inspection_id: str
    status: str
    judgement: str
    defect_candidates: list[str]
    confidence: float
    reasoning: str
    human_review_required: bool
    saved_image: str
    audit_log: str
    vlm_used: bool

DEFECT_LABELS = [
    "キズ", "バリ", "打痕", "シミムラ", "変形", "付着", "めくれ",
    "アニール打痕", "カスハマリ", "ふくらみ", "エッチング", "その他"
]

LABEL_STR = "、".join(DEFECT_LABELS)

VLM_PROMPT = (
    "あなたは金属プレス部品の外観検査AIです。\n"
    "添付画像を見て、以下の不良種別から該当するものを特定してください。\n"
    f"不良種別: {LABEL_STR}\n\n"
    "以下のJSON形式のみで回答してください（他のテキスト不要）:\n"
    '{\n'
    '  "judgement": "OK" または "NG",\n'
    '  "defect_candidates": ["不良種別1", "不良種別2"],\n'
    '  "confidence": 0.0〜1.0,\n'
    '  "reasoning": "判定根拠（1〜2文）"\n'
    '}\n'
    '不良なし場合: defect_candidates=[]、judgement="OK"'
)


def simple_image_signal(image_path: Path):
    img = Image.open(image_path).convert("L").resize((512, 512))
    arr = np.asarray(img).astype(np.float32)
    mean = float(arr.mean())
    std = float(arr.std())
    edge = float(np.abs(np.diff(arr, axis=0)).mean() + np.abs(np.diff(arr, axis=1)).mean())
    darkness = float((arr < 40).mean())
    brightness = float((arr > 230).mean())
    return {
        "mean": mean,
        "std": std,
        "edge_score": edge,
        "dark_area_ratio": darkness,
        "bright_area_ratio": brightness,
    }


def rule_based_judgement(features: dict):
    candidates = []
    score = 0.0

    if features["edge_score"] > 18:
        candidates.append("キズ")
        score += 0.25
    if features["dark_area_ratio"] > 0.03:
        candidates.append("シミムラ")
        score += 0.20
    if features["bright_area_ratio"] > 0.03:
        candidates.append("付着")
        score += 0.15
    if features["std"] > 55:
        candidates.append("打痕")
        score += 0.20

    if not candidates:
        return "OK候補", [], 0.62

    return "NG候補", list(dict.fromkeys(candidates)), min(0.95, 0.55 + score)


def vlm_inspection(image_path: Path, part_no: str, features: dict):
    """LiteLLM経由でVision LLMによる外観検査を実行する。失敗時はNoneを返す。"""
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        suffix = image_path.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png" if suffix == ".png" else "image/jpeg"

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": VLM_PROMPT + f"\n\n部品番号: {part_no}\n局所特徴量: {json.dumps(features, ensure_ascii=False)}",
                        },
                    ],
                }
            ],
            "max_tokens": 512,
            "temperature": 0.1,
        }

        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # JSON部分を抽出（マークダウンコードブロック対応）
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed = json.loads(content)
        judgement = parsed.get("judgement", "")
        candidates = parsed.get("defect_candidates", [])
        confidence = float(parsed.get("confidence", 0.7))
        reasoning = parsed.get("reasoning", "")

        # 正規化
        judgement_jp = "NG" if judgement.upper() == "NG" else "OK"
        valid_candidates = [c for c in candidates if c in DEFECT_LABELS]

        return {
            "judgement": judgement_jp,
            "defect_candidates": valid_candidates,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    except Exception as e:
        return None


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "vlm_model": VISION_MODEL}


@app.post("/inspect", response_model=InspectionResult)
async def inspect(
    image: UploadFile = File(...),
    part_no: str = Form("UNKNOWN"),
    lot_no: str = Form("UNKNOWN"),
    machine_id: str = Form("UNKNOWN"),
    shot_count: str = Form(""),
    spm: str = Form(""),
    chokotei_count: str = Form(""),
):
    inspection_id = str(uuid.uuid4())
    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    saved = IMAGE_DIR / f"{inspection_id}{suffix}"

    with saved.open("wb") as f:
        shutil.copyfileobj(image.file, f)

    features = simple_image_signal(saved)
    rb_judgement, rb_candidates, rb_confidence = rule_based_judgement(features)

    vlm_result = vlm_inspection(saved, part_no, features)
    vlm_used = vlm_result is not None

    if vlm_used:
        judgement = vlm_result["judgement"]
        candidates = vlm_result["defect_candidates"] or rb_candidates
        confidence = vlm_result["confidence"]
        reasoning = f"[VLM({VISION_MODEL})] {vlm_result['reasoning']} (ルール候補: {rb_judgement})"
    else:
        judgement = rb_judgement
        candidates = rb_candidates
        confidence = rb_confidence
        reasoning = (
            "VLM推論失敗のためローカル特徴量による暫定判定。"
            "edge_score/std/dark_area_ratio/bright_area_ratioを確認。最終判定は人間レビュー必要。"
        )

    human_review_required = (judgement not in ("OK",)) or confidence < 0.80

    record = {
        "inspection_id": inspection_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "part_no": part_no,
        "lot_no": lot_no,
        "machine_id": machine_id,
        "shot_count": shot_count,
        "spm": spm,
        "chokotei_count": chokotei_count,
        "features": features,
        "rule_based": {"judgement": rb_judgement, "candidates": rb_candidates, "confidence": rb_confidence},
        "vlm_used": vlm_used,
        "judgement": judgement,
        "defect_candidates": candidates,
        "confidence": confidence,
        "human_review_required": human_review_required,
        "image_path": str(saved),
        "reasoning": reasoning,
    }

    audit_path = AUDIT_DIR / f"{inspection_id}.json"
    result_path = RESULTS_DIR / f"{inspection_id}.json"
    audit_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    result_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return InspectionResult(
        inspection_id=inspection_id,
        status="completed",
        judgement=judgement,
        defect_candidates=candidates,
        confidence=confidence,
        reasoning=reasoning,
        human_review_required=human_review_required,
        saved_image=str(saved),
        audit_log=str(audit_path),
        vlm_used=vlm_used,
    )


@app.get("/labels")
def labels():
    return {"defect_labels": DEFECT_LABELS}


@app.get("/recent")
def recent(limit: int = 20):
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]
