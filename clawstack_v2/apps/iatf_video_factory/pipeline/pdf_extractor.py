"""PDF全文抽出 — 省略なし。pdfplumber優先、Doclingフォールバック。"""
import pdfplumber, requests, json
from pathlib import Path

DOCLING_URL = "http://localhost:8087"
PDF_DIR = Path("d:/Clawdbot_Docker_20260125/iatf_system/db/documents")


def extract_with_pdfplumber(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            tables = page.extract_tables()
            for tbl in tables:
                for row in tbl:
                    text += "\n" + " | ".join(c or "" for c in row if c)
            pages.append(f"--- Page {i+1} ---\n{text.strip()}")
    return "\n\n".join(pages)


def extract_with_docling(pdf_path: Path) -> str:
    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                f"{DOCLING_URL}/convert/file",
                files={"file": (pdf_path.name, f, "application/pdf")},
                data={"to_formats": '["md"]'},
                timeout=120,
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("document", {}).get("md_content", "")
    except Exception as e:
        return ""


def extract_pdf(pdf_path: Path) -> str:
    text = extract_with_pdfplumber(pdf_path)
    if len(text.strip()) < 100:
        text = extract_with_docling(pdf_path)
    return text


def list_audit_pdfs() -> list[Path]:
    return sorted(
        p for p in PDF_DIR.glob("IATF 16949 内部監査資料*.pdf")
        if p.is_file()
    )


if __name__ == "__main__":
    pdfs = list_audit_pdfs()
    print(f"Found {len(pdfs)} IATF audit PDFs")
    if pdfs:
        text = extract_pdf(pdfs[0])
        print(f"First PDF: {pdfs[0].name}")
        print(f"Chars extracted: {len(text)}")
        print(text[:500])
