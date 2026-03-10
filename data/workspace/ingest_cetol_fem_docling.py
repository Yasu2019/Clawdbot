#!/usr/bin/env python3
"""
ingest_cetol_fem_docling.py
ハイブリッドOCR+VLM再インジェスト（RAG品質修正）

戦略:
  - テキスト多ページ (>= 80文字): Tesseract OCR → 実テキストとして取得
  - グラフ・図解ページ (<  80文字): minicpm-v VLM → 技術的な図解説明を生成
  → 「The image shows...」問題を解消しつつ、グラフの内容も捕捉

実行方法:
  docker exec -d clawstack-unified-clawdbot-gateway-1 \
    python3 /home/node/clawd/ingest_cetol_fem_docling.py

ログ: /home/node/clawd/ingest_cetol_fem_docling.log
"""

import os
import requests
import json
import uuid
import time
import subprocess
import tempfile
import base64
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "PyMuPDF", "-q"])
    import fitz

# --- Config ---
OLLAMA_URL    = "http://ollama:11434"
VLM_MODEL     = "minicpm-v:latest"
INFINITY_URL  = "http://infinity:7997"
QDRANT_URL    = "http://qdrant:6333"
COLLECTION    = "universal_knowledge"
EMBED_MODEL   = "mxbai-embed-large-v1"
LOG_FILE      = "/home/node/clawd/ingest_cetol_fem_docling.log"
STATE_FILE    = "/home/node/clawd/ingest_cetol_fem_docling_state.json"

CHUNK_SIZE         = 900
CHUNK_OVERLAP      = 150
BATCH_EMBED        = 16
UPSERT_BATCH       = 80
OCR_DPI            = 200
OCR_LANG           = "jpn+eng"
# このchar数未満のページはVLMで図解説明を生成
IMAGE_PAGE_THRESHOLD = 80

PDF_TARGETS = [
    ("/home/node/clawd/paperless_consume/cetol6sigma", "cetol6sigma"),
    ("/home/node/clawd/paperless_consume/FEM_CAE",     "fem_cae"),
]

# VLM用の技術的プロンプト（単なる「image shows...」を防ぐ）
VLM_PROMPT = """あなたは機械設計・公差解析・有限要素法（FEM）の専門エンジニアです。
このページの技術的内容を日本語で詳細に説明してください：

1. **図・グラフの種類**: ベクトルループ図/公差連鎖図/感度解析グラフ/フローチャート/ソフトウェア画面など
2. **表示されている全テキスト**: 数値・ラベル・軸タイトル・凡例・数式を正確に転写
3. **技術的意味**: この図が示す公差解析の概念・手法・結論
4. **数値データ**: グラフの値域・公差値・確率・σ値など具体的な数値

「The image shows」のような一般的な表現は避け、エンジニアリングの専門用語で説明してください。"""

# --- Logging ---
def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# --- State (再開対応) ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"done_files": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# --- ページをPNGに変換 ---
def page_to_png(page, tmpdir, page_num):
    mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
    pix = page.get_pixmap(matrix=mat)
    png_path = os.path.join(tmpdir, f"page_{page_num:04d}.png")
    pix.save(png_path)
    return png_path

# --- Tesseract OCR ---
def ocr_page(png_path: str) -> str:
    result = subprocess.run(
        ["tesseract", png_path, "stdout", "-l", OCR_LANG, "--psm", "3"],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

# --- minicpm-v VLM（図解説明） ---
def vlm_describe_page(png_path: str) -> str:
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    for attempt in range(2):  # 最大2回試行
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": VLM_MODEL,
                    "prompt": VLM_PROMPT,
                    "images": [b64],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 400},
                },
                timeout=300,  # 5分（モデルロード時間含む）
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            log(f"    VLMタイムアウト (試行{attempt+1}/2)")
            if attempt == 0:
                time.sleep(5)
        except Exception as e:
            log(f"    VLMエラー: {e}")
            break
    return ""

# --- PDF全ページ処理（ハイブリッド） ---
def process_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_text_parts = []
    ocr_pages = 0
    vlm_pages = 0

    log(f"  処理開始: {Path(pdf_path).name} ({total_pages}ページ)")

    with tempfile.TemporaryDirectory() as tmpdir:
        for page_num in range(total_pages):
            page = doc[page_num]
            png_path = page_to_png(page, tmpdir, page_num)

            # まずTesseract OCR
            ocr_text = ocr_page(png_path)

            if len(ocr_text) >= IMAGE_PAGE_THRESHOLD:
                # テキスト多ページ → OCRテキストそのまま使用
                all_text_parts.append(f"[p{page_num+1}]\n{ocr_text}")
                ocr_pages += 1
            else:
                # グラフ・図解ページ → VLMで技術説明
                vlm_text = vlm_describe_page(png_path)
                if vlm_text:
                    all_text_parts.append(
                        f"[p{page_num+1} 図解]\n{vlm_text}"
                        + (f"\n[OCRラベル: {ocr_text}]" if ocr_text else "")
                    )
                    vlm_pages += 1
                elif ocr_text:
                    all_text_parts.append(f"[p{page_num+1}]\n{ocr_text}")

            if (page_num + 1) % 10 == 0 or page_num == total_pages - 1:
                log(f"  進捗: {page_num+1}/{total_pages}p "
                    f"(OCR:{ocr_pages} VLM:{vlm_pages})")

    doc.close()
    full_text = "\n\n".join(all_text_parts)
    log(f"  完了: {len(full_text)}文字 (OCR:{ocr_pages}p / VLM:{vlm_pages}p)")
    return full_text

# --- テキストチャンク分割 ---
def chunk_text(text: str) -> list:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > CHUNK_SIZE:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_SIZE:
                for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                    chunk = para[i:i+CHUNK_SIZE]
                    if chunk.strip():
                        chunks.append(chunk)
                current = ""
            else:
                current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c.strip()) > 30]

# --- Infinity embedding ---
def embed_batch(texts: list) -> list:
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{INFINITY_URL}/embeddings",
                json={"model": EMBED_MODEL, "input": texts},
                timeout=120,
            )
            resp.raise_for_status()
            return [item["embedding"] for item in resp.json()["data"]]
        except requests.exceptions.Timeout:
            log(f"    Infinityタイムアウト (試行{attempt+1}/3)、待機後リトライ...")
            time.sleep(10)
    raise RuntimeError("Infinity embed 3回失敗")

# --- Qdrant操作 ---
def delete_old_points(source_tag: str):
    resp = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/delete",
        json={"filter": {"must": [{"key": "source", "match": {"value": source_tag}}]}},
        timeout=30,
    )
    log(f"  旧ポイント削除 ({source_tag}): HTTP {resp.status_code}")

def upsert_points(points: list):
    resp = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": points},
        timeout=60,
    )
    resp.raise_for_status()

def get_collection_count():
    resp = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=10)
    return resp.json().get("result", {}).get("points_count", 0)

# --- メイン ---
def main():
    log("=" * 60)
    log("CETOL/FEM ハイブリッドOCR+VLM 再インジェスト開始")
    log(f"  OCR DPI:{OCR_DPI}  言語:{OCR_LANG}  VLM閾値:<{IMAGE_PAGE_THRESHOLD}文字")
    log("=" * 60)

    state = load_state()
    done_files = set(state.get("done_files", []))
    total_ingested = 0

    for pdf_dir, source_tag in PDF_TARGETS:
        pdf_dir_path = Path(pdf_dir)
        if not pdf_dir_path.exists():
            log(f"[SKIP] ディレクトリ不在: {pdf_dir}")
            continue

        pdf_files = sorted(pdf_dir_path.glob("*.pdf"))
        if not pdf_files:
            log(f"[SKIP] PDFなし: {pdf_dir}")
            continue

        log(f"\n=== {source_tag}: {len(pdf_files)}件 ===")

        if not any(str(f) in done_files for f in pdf_files):
            delete_old_points(source_tag)

        count_before = get_collection_count()
        log(f"  Qdrant現在: {count_before}ポイント")

        all_points = []

        for pdf_path in pdf_files:
            key = str(pdf_path)
            if key in done_files:
                log(f"  [スキップ済] {pdf_path.name}")
                continue

            log(f"\n  ▶ {pdf_path.name}")
            try:
                full_text = process_pdf(str(pdf_path))

                if not full_text.strip():
                    log(f"  [警告] テキストなし: {pdf_path.name}")
                    done_files.add(key)
                    save_state({"done_files": list(done_files)})
                    continue

                chunks = chunk_text(full_text)
                log(f"  チャンク: {len(chunks)}件")

                for i in range(0, len(chunks), BATCH_EMBED):
                    batch_chunks = chunks[i:i+BATCH_EMBED]
                    embeddings = embed_batch(batch_chunks)
                    for j, (chunk, emb) in enumerate(zip(batch_chunks, embeddings)):
                        all_points.append({
                            "id": str(uuid.uuid4()),
                            "vector": emb,
                            "payload": {
                                "text": chunk,
                                "source": source_tag,
                                "filename": pdf_path.name,
                                "chunk_index": i + j,
                                "ingested_by": "hybrid_ocr_vlm",
                            },
                        })
                    if len(all_points) >= UPSERT_BATCH:
                        upsert_points(all_points)
                        log(f"  upsert: {len(all_points)}件")
                        total_ingested += len(all_points)
                        all_points = []
                    time.sleep(0.2)

                done_files.add(key)
                save_state({"done_files": list(done_files)})
                log(f"  ✓ {pdf_path.name} 完了")

            except Exception as e:
                log(f"  [ERROR] {pdf_path.name}: {e}")
                import traceback; traceback.print_exc()

        if all_points:
            upsert_points(all_points)
            log(f"  最終upsert: {len(all_points)}件")
            total_ingested += len(all_points)

        count_after = get_collection_count()
        log(f"  {source_tag}: +{count_after - count_before}件 (総計: {count_after})")

    log("\n" + "=" * 60)
    log(f"✅ 完了: 合計{total_ingested}件追加 / Qdrant総計:{get_collection_count()}")
    log("=" * 60)

if __name__ == "__main__":
    main()
