# -*- coding: utf-8 -*-
"""moldflow_cae_studio_api._parse_multipart の単体テスト (STEP2: cgi脱却の回帰防止)。

実行: cd data/workspace && python -m unittest tests.test_moldflow_studio_api_multipart -v
"""
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "moldflow_cae_studio_api", ROOT / "scripts" / "moldflow_cae_studio_api.py")
mapi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mapi)

BOUNDARY = "BOUND123"


def make_body(parts, boundary=BOUNDARY):
    b = b""
    for name, fn, content in parts:
        b += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'.encode()
        if fn is not None:
            b += f'; filename="{fn}"'.encode()
        b += b"\r\nContent-Type: application/octet-stream\r\n\r\n" + content + b"\r\n"
    return b + f"--{boundary}--\r\n".encode()


def hdr(body, ctype=f"multipart/form-data; boundary={BOUNDARY}"):
    return {"Content-Type": ctype, "Content-Length": str(len(body))}


class TestParseMultipart(unittest.TestCase):
    def test_binary_content_exact(self):
        payload = b"ISO-10303-21;\r\nHEADER;\x00\xff binary \r\n bytes"
        body = make_body([("file", "part.step", payload), ("note", None, b"hello")])
        f = mapi._parse_multipart(hdr(body), io.BytesIO(body))
        self.assertEqual(f["file"], ("part.step", payload))
        self.assertEqual(f["note"], ("", b"hello"))

    def test_quoted_boundary(self):
        body = make_body([("file", "a.step", b"DATA")])
        f = mapi._parse_multipart(
            hdr(body, f'multipart/form-data; boundary="{BOUNDARY}"'), io.BytesIO(body))
        self.assertEqual(f["file"][1], b"DATA")

    def test_missing_boundary_raises(self):
        with self.assertRaises(ValueError):
            mapi._parse_multipart(
                {"Content-Type": "multipart/form-data", "Content-Length": "3"},
                io.BytesIO(b"xxx"))

    def test_empty_body_raises(self):
        body = make_body([("file", "a.step", b"D")])
        h = hdr(body); h["Content-Length"] = "0"
        with self.assertRaises(ValueError):
            mapi._parse_multipart(h, io.BytesIO(b""))

    def test_oversize_raises(self):
        body = make_body([("file", "a.step", b"D")])
        h = hdr(body); h["Content-Length"] = str(mapi.MAX_UPLOAD_BYTES + 1)
        with self.assertRaises(ValueError):
            mapi._parse_multipart(h, io.BytesIO(b""))

    def test_empty_file_content(self):
        body = make_body([("file", "e.step", b"")])
        f = mapi._parse_multipart(hdr(body), io.BytesIO(body))
        self.assertEqual(f["file"], ("e.step", b""))

    def test_no_cgi_import(self):
        src = (ROOT / "scripts" / "moldflow_cae_studio_api.py").read_text(encoding="utf-8")
        self.assertNotIn("import cgi", src)
        self.assertNotIn("cgi.FieldStorage", src)



class TestMaturityAndGoldenTrend(unittest.TestCase):
    """STEP3新設エンドポイントのスナップショット関数テスト。"""

    def test_maturity_snapshot_shape(self):
        snap = mapi._load_maturity_snapshot()
        self.assertIn("available", snap)
        self.assertIn("product", snap)
        if snap["available"]:
            self.assertIn("MOLDFLOW", str(snap["product"]["product_id"]).upper())
            self.assertIsInstance(snap["product"].get("categories"), list)

    def test_golden_trend_missing_file_safe(self):
        import tempfile
        from pathlib import Path as P
        orig = mapi.GOLDEN_ERROR_LOG
        try:
            mapi.GOLDEN_ERROR_LOG = P(tempfile.mkdtemp()) / "nonexistent.jsonl"
            tr = mapi._load_golden_error_trend()
            self.assertFalse(tr["available"])
            self.assertEqual(tr["records"], [])
        finally:
            mapi.GOLDEN_ERROR_LOG = orig

    def test_golden_trend_broken_lines_and_limit(self):
        import json as _json
        import tempfile
        from pathlib import Path as P
        orig = mapi.GOLDEN_ERROR_LOG
        try:
            tmp = P(tempfile.mkdtemp()) / "g.jsonl"
            lines = [_json.dumps({"max_err_pct": 10 - i}) for i in range(5)] + ['{"broken', ""]
            tmp.write_text("\n".join(lines), encoding="utf-8")
            mapi.GOLDEN_ERROR_LOG = tmp
            tr = mapi._load_golden_error_trend(limit=3)
            self.assertTrue(tr["available"])
            self.assertEqual(tr["count_total"], 5)
            self.assertEqual(len(tr["records"]), 3)
            self.assertEqual(tr["records"][-1]["max_err_pct"], 6)
        finally:
            mapi.GOLDEN_ERROR_LOG = orig


if __name__ == "__main__":
    unittest.main()
