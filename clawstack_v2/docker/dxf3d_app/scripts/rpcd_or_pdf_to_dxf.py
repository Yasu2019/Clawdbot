"""
rpcd_or_pdf_to_dxf.py — PDF / RPCD -> DXF (vector reconstruction)
=================================================================
Runs inside the dxf3d_app container with the system interpreter:

    python /work/scripts/rpcd_or_pdf_to_dxf.py <input.pdf|input.rpcd> \
        -o <out.dxf> --report-json <report.json> [--no-text]

PDF   : vector drawing operators (PyMuPDF `get_drawings`) are converted to
        DXF LINE / LWPOLYLINE. Bezier curves are flattened.
RPCD  : RootPro CAD documents carry no public geometry format. The only
        supported route is an embedded/companion PDF payload — the file is
        scanned for one (OLE stream or raw `%PDF-` block) and that PDF is
        converted. Native RPCD geometry is NOT parsed.

Geometry lands on layer CONTOUR, text on layer TEXT, so the caller's layer
heuristics pick the contour layer and skip annotations.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import ezdxf
import fitz  # PyMuPDF

PT_TO_MM = 25.4 / 72.0     # PDF user space unit (1/72 inch) -> mm
BEZIER_SEGMENTS = 12       # flattening resolution per cubic segment
MIN_SEG_MM = 0.01          # drop segments shorter than this
GEO_LAYER = "CONTOUR"
TEXT_LAYER = "TEXT"


def _bezier(p0, p1, p2, p3, n=BEZIER_SEGMENTS):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1.0 - t
        pts.append((
            u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
        ))
    return pts


class _Mapper:
    """PDF user space -> DXF model space (mm, y-axis flipped)."""

    def __init__(self, page_height_pt: float):
        self.h = page_height_pt

    def __call__(self, pt):
        x = float(pt[0]) if not hasattr(pt, "x") else float(pt.x)
        y = float(pt[1]) if not hasattr(pt, "y") else float(pt.y)
        return (x * PT_TO_MM, (self.h - y) * PT_TO_MM)


def _emit_polyline(msp, pts, closed: bool, stats: dict):
    clean = []
    for pt in pts:
        if clean and math.hypot(pt[0] - clean[-1][0], pt[1] - clean[-1][1]) < MIN_SEG_MM:
            continue
        clean.append(pt)
    if len(clean) < 2:
        return
    if len(clean) == 2:
        msp.add_line(clean[0], clean[1], dxfattribs={"layer": GEO_LAYER})
        stats["lines"] += 1
        return
    msp.add_lwpolyline(clean, close=closed, dxfattribs={"layer": GEO_LAYER})
    stats["polylines"] += 1


def convert_pdf(pdf_bytes: bytes, out_path: Path, add_text: bool) -> dict:
    doc_out = ezdxf.new("R2010", setup=True)
    doc_out.layers.add(GEO_LAYER)
    doc_out.layers.add(TEXT_LAYER)
    msp = doc_out.modelspace()

    stats = {"lines": 0, "polylines": 0, "curves": 0, "rects": 0, "texts": 0}
    warnings = []
    pages_used = 0

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        n_pages = len(pdf)
        if n_pages > 1:
            warnings.append(
                f"{n_pages} ページ中 1 ページ目のみを変換しました。"
            )
        page = pdf[0]
        pages_used = 1
        to_mm = _Mapper(page.rect.height)

        for drawing in page.get_drawings():
            for item in drawing.get("items", []):
                kind = item[0]
                if kind == "l":                       # line
                    a, b = to_mm(item[1]), to_mm(item[2])
                    if math.hypot(b[0] - a[0], b[1] - a[1]) >= MIN_SEG_MM:
                        msp.add_line(a, b, dxfattribs={"layer": GEO_LAYER})
                        stats["lines"] += 1
                elif kind == "c":                     # cubic bezier
                    p0, p1, p2, p3 = (to_mm(item[i]) for i in (1, 2, 3, 4))
                    _emit_polyline(msp, [p0] + _bezier(p0, p1, p2, p3), False, stats)
                    stats["curves"] += 1
                elif kind == "re":                    # rectangle
                    r = item[1]
                    corners = [
                        to_mm((r.x0, r.y0)), to_mm((r.x1, r.y0)),
                        to_mm((r.x1, r.y1)), to_mm((r.x0, r.y1)),
                    ]
                    _emit_polyline(msp, corners, True, stats)
                    stats["rects"] += 1
                elif kind == "qu":                    # quad
                    q = item[1]
                    corners = [to_mm(p) for p in
                               (q.ul, q.ur, q.lr, q.ll)]
                    _emit_polyline(msp, corners, True, stats)
                    stats["rects"] += 1

        if add_text:
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        content = (span.get("text") or "").strip()
                        if not content:
                            continue
                        origin = to_mm(span.get("origin", (0, 0)))
                        height = max(float(span.get("size", 8.0)) * PT_TO_MM, 0.5)
                        msp.add_text(
                            content,
                            height=height,
                            dxfattribs={"layer": TEXT_LAYER},
                        ).set_placement(origin)
                        stats["texts"] += 1

    doc_out.saveas(str(out_path), encoding="utf-8")

    total_geo = stats["lines"] + stats["polylines"]
    if total_geo == 0:
        warnings.append(
            "ベクタ線が1本も検出されませんでした。スキャン画像PDFの可能性があります "
            "(ラスタPDFは非対応)。"
        )
    return {
        "pages_total": n_pages,
        "pages_converted": pages_used,
        "scale": f"1 pt = {PT_TO_MM:.6f} mm",
        "entities": stats,
        "geometry_entities": total_geo,
        "warnings": warnings,
    }


def extract_pdf_payload(raw: bytes) -> bytes | None:
    """Find a PDF inside a non-PDF container (RPCD): OLE stream or raw block."""
    if raw[:5] == b"%PDF-":
        return raw

    try:
        import olefile
        import io as _io
        if olefile.isOleFile(_io.BytesIO(raw)):
            ole = olefile.OleFileIO(_io.BytesIO(raw))
            try:
                for entry in ole.listdir(streams=True):
                    data = ole.openstream(entry).read()
                    start = data.find(b"%PDF-")
                    if start >= 0:
                        return data[start:]
            finally:
                ole.close()
    except Exception:
        pass

    start = raw.find(b"%PDF-")
    if start >= 0:
        end = raw.rfind(b"%%EOF")
        if end > start:
            return raw[start:end + 5]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF / RPCD -> DXF")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--report-json")
    ap.add_argument("--no-text", action="store_true")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"input not found: {in_path}", file=sys.stderr)
        return 1

    raw = in_path.read_bytes()
    suffix = in_path.suffix.lower()

    if suffix == ".pdf":
        mode = "pdf_vector"
        payload = raw if raw[:5] == b"%PDF-" else extract_pdf_payload(raw)
        if payload is None:
            print("not a valid PDF file", file=sys.stderr)
            return 1
    else:
        payload = extract_pdf_payload(raw)
        if payload is None:
            print(
                "RPCD 内に PDF ペイロードが見つかりませんでした。\n"
                "RootPro CAD から PDF を書き出して、その PDF を入力してください "
                "(RPCD ネイティブ幾何の解析は非対応です)。",
                file=sys.stderr,
            )
            return 1
        mode = "rpcd_embedded_pdf"

    report = convert_pdf(payload, out_path, add_text=not args.no_text)
    report.update({
        "mode": mode,
        "input": in_path.name,
        "output": out_path.name,
        "output_kb": round(out_path.stat().st_size / 1024.0, 1),
    })

    if args.report_json:
        Path(args.report_json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
