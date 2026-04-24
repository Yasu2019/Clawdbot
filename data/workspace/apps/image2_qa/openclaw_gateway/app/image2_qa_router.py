from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/image2-qa", tags=["image2-qa"])


class Image2QARequest(BaseModel):
    purpose: str = Field(..., description="例: 内部監査教育、不良事例説明、顧客報告")
    process_or_product: str = Field(..., description="工程名または製品名")
    main_message: str = Field(..., description="画像で最も伝えたい結論")
    rag_summary: Optional[str] = Field(default="", description="RAG検索結果の要約。未連携時は手入力可")
    aspect_ratio: str = Field(default="16:9")
    style: str = Field(default="clean Japanese manufacturing QA infographic")
    dry_run: bool = Field(default=True, description="trueなら画像生成せずpromptのみ返す")


class Image2QAResponse(BaseModel):
    status: str
    prompt: str
    output_dir: Optional[str] = None
    image_base64: Optional[str] = None
    notes: List[str] = []


def build_prompt(req: Image2QARequest) -> str:
    return f"""
製造業の品質保証資料として使う、日本語入りの1枚画像を作成してください。

目的: {req.purpose}
対象工程/製品: {req.process_or_product}
伝えたい結論: {req.main_message}
根拠情報: {req.rag_summary or '根拠情報は未接続。一般化した表現に限定すること。'}

画像仕様:
- アスペクト比: {req.aspect_ratio}
- スタイル: {req.style}
- 日本語文字は大きく、読みやすく、誤字を避ける
- 構成: タイトル / 現象 / 原因候補 / 対策 / 確認方法 / 注意書き
- 注意書き: 「寸法・合否判定は正式帳票で確認」と小さく入れる
- 実在顧客名、個人名、秘密情報は入れない
""".strip()


async def call_openai_image_adapter(prompt: str, aspect_ratio: str) -> str:
    """Return base64 image. Requires OpenAI SDK in the real Gateway environment.

    This adapter is intentionally isolated so Codex/Antigravity can replace
    the implementation if OpenClaw already has a shared LLM/Image client.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        result = client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
            prompt=prompt,
            size="1536x864" if aspect_ratio == "16:9" else "1024x1024",
            quality=os.getenv("OPENAI_IMAGE_QUALITY", "high"),
        )
        return result.data[0].b64_json
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc


@router.post("/generate", response_model=Image2QAResponse)
async def generate_image2_qa(req: Image2QARequest) -> Image2QAResponse:
    prompt = build_prompt(req)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(os.getenv("IMAGE2_QA_OUTPUT_DIR", "/data/generated/image2_qa")) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.json").write_text(json.dumps(req.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "final_prompt.txt").write_text(prompt, encoding="utf-8")
    (out_dir / "review_checklist.md").write_text(REVIEW_CHECKLIST, encoding="utf-8")

    if req.dry_run:
        return Image2QAResponse(status="dry_run", prompt=prompt, output_dir=str(out_dir), notes=["画像生成は未実行です。dry_run=falseで実行してください。"])

    image_b64 = await call_openai_image_adapter(prompt, req.aspect_ratio)
    (out_dir / "image.png.b64").write_text(image_b64, encoding="utf-8")
    try:
        (out_dir / "image.png").write_bytes(base64.b64decode(image_b64))
    except Exception:
        pass
    return Image2QAResponse(status="generated", prompt=prompt, output_dir=str(out_dir), image_base64=image_b64)


REVIEW_CHECKLIST = """# QA画像レビュー確認表

- [ ] 画像内の日本語に誤字がない
- [ ] 寸法・公差・合否を断定していない
- [ ] 顧客名・個人名・機密情報が入っていない
- [ ] RAG根拠と矛盾していない
- [ ] 現場教育/監査/顧客説明の目的に合っている
- [ ] 承認者が確認した
"""
