from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from storage_cleanup_candidates import OUTPUT_PATH, ROOTS, scan


ARCHIVE_ROOT = Path(r"E:\ClawstackData\CleanupArchives")


def load_candidates() -> dict:
    if not OUTPUT_PATH.exists():
        return scan()
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def in_allowed_roots(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in ROOTS:
        if not root.exists():
            continue
        try:
            if str(resolved).lower().startswith(str(root.resolve()).lower()):
                return True
        except OSError:
            continue
    return False


def candidate_paths() -> set[str]:
    data = load_candidates()
    return {str(Path(row["path"]).resolve()).lower() for row in data.get("candidates", []) if Path(row["path"]).exists()}


def archive_path(src: Path) -> Path:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ARCHIVE_ROOT / f"{src.name}_{stamp}.zip"


def archive_item(src: Path) -> Path:
    dst = archive_path(src)
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            zf.write(src, arcname=src.name)
        else:
            for child in src.rglob("*"):
                if child.is_file():
                    zf.write(child, arcname=str(child.relative_to(src.parent)))
    return dst


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send({"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/status":
            self._send(load_candidates())
            return
        self._send({"ok": False, "error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or "{}")

        if parsed.path == "/scan":
            self._send(scan())
            return

        path_value = data.get("path", "")
        src = Path(path_value)
        if not path_value or not src.exists():
            self._send({"ok": False, "error": "path_not_found"}, 400)
            return
        if not in_allowed_roots(src):
            self._send({"ok": False, "error": "path_not_allowed"}, 403)
            return
        resolved_key = str(src.resolve()).lower()
        if resolved_key not in candidate_paths():
            self._send({"ok": False, "error": "path_not_in_current_candidates"}, 409)
            return

        try:
            if parsed.path == "/archive_delete":
                archive = archive_item(src)
                if src.is_dir():
                    shutil.rmtree(src)
                else:
                    src.unlink()
                result = {"ok": True, "action": "archive_delete", "archive": str(archive), "path": str(src)}
                scan()
                self._send(result)
                return
            if parsed.path == "/delete":
                if src.is_dir():
                    shutil.rmtree(src)
                else:
                    src.unlink()
                result = {"ok": True, "action": "delete", "path": str(src)}
                scan()
                self._send(result)
                return
        except Exception as exc:  # noqa: BLE001
            self._send({"ok": False, "error": str(exc)}, 500)
            return

        self._send({"ok": False, "error": "not_found"}, 404)


def main() -> int:
    scan()
    server = ThreadingHTTPServer(("127.0.0.1", 8097), Handler)
    print("storage_cleanup_api listening on 127.0.0.1:8097", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
