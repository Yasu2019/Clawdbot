# -*- coding: utf-8 -*-
"""Skill Request API (S1受付) — Mecha Motion Lab ダッシュボードの依頼フォーム受け口。

- POST /requests {"text": "階段を登る"} -> skill_requests.json に追記(status: queued)
- GET  /requests -> 依頼キュー全件
依頼はスキル獲得パイプライン(S2以降: 解釈→探索→取得→人間ライセンスゲート→学習)の
入力キューとなる。処理自体はまだ手動/半自動(HANDOVER §4.4 / skill_acquisition_pipeline.md)。

起動: python skill_request_api.py   (127.0.0.1:8118, ポートはT008ルールで空き確認済み 2026-07-04)
"""
import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer

STORE = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\skill_requests.json"
PORT = 8118


def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return {"schema": "clawstack.skill_requests.v1", "requests": []}


def save(d):
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


class H(BaseHTTPRequestHandler):
    def _hdr(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")   # 8088(静的portal)からのフォーム用
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._hdr(204)

    def do_GET(self):
        if self.path.startswith("/requests"):
            self._hdr()
            self.wfile.write(json.dumps(load(), ensure_ascii=False).encode())
        else:
            self._hdr(404)
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        # U3: 人間ライセンスゲート/検収 — /requests/<id>/approve | /reject
        import re as _re
        m = _re.match(r"^/requests/([^/]+)/(approve|reject)$", self.path)
        if m:
            rid, act = m.group(1), m.group(2)
            # ボディ無しPOST対応: Content-Lengthちょうどだけ読む(過剰readはブロックする)
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n)) if n else {}
            except Exception:
                body = {}
            d = load()
            req = next((r for r in d["requests"] if r["id"] == rid), None)
            if req is None:
                self._hdr(404); self.wfile.write(b'{"error":"unknown id"}'); return
            if act == "approve":
                if req.get("status") != "license_pending":
                    self._hdr(409)
                    self.wfile.write(json.dumps({"error": f"approve requires license_pending, got {req.get('status')}"}).encode())
                    return
                req["status"] = "retarget_ready"
            else:
                if req.get("status") in ("training", "learned"):
                    self._hdr(409); self.wfile.write(b'{"error":"cannot reject active/finished"}'); return
                req["status"] = "rejected"
            req["gate_decision"] = {"action": act, "by": str(body.get("by", "human")),
                                    "note": str(body.get("note", ""))[:200],
                                    "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save(d)
            self._hdr()
            self.wfile.write(json.dumps({"ok": True, "request": req}, ensure_ascii=False).encode())
            return
        if not self.path.startswith("/requests"):
            self._hdr(404); self.wfile.write(b'{"error":"not found"}'); return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            text = str(body.get("text", "")).strip()[:300]
            assert text, "empty"
        except Exception:
            self._hdr(400); self.wfile.write(b'{"error":"bad request"}'); return
        d = load()
        req = {"id": f"req_{int(time.time())}", "text": text,
               "status": "queued",   # queued -> interpreting -> acquiring -> license_pending -> training -> done/rejected
               "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "notes": None}
        d["requests"].append(req)
        save(d)
        self._hdr()
        self.wfile.write(json.dumps({"ok": True, "request": req}, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == "__main__":
    print(f"skill request API on 127.0.0.1:{PORT}, store={STORE}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
