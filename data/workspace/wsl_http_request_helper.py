#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import http.client
import json
import sys
from urllib.parse import urlsplit


HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--headers-json", default="{}")
    parser.add_argument("--body-base64", default="")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    parts = urlsplit(args.url)
    headers = json.loads(args.headers_json or "{}")
    filtered_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}
    body = base64.b64decode(args.body_base64.encode("ascii")) if args.body_base64 else None
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    conn = http.client.HTTPConnection(parts.hostname or "127.0.0.1", parts.port or 80, timeout=args.timeout)
    try:
        conn.request(args.method.upper(), path, body=body, headers=filtered_headers)
        response = conn.getresponse()
        resp_headers = [
            [key, value]
            for key, value in response.getheaders()
            if key.lower() not in HOP_BY_HOP
        ]
        payload = {
            "status": response.status,
            "reason": response.reason,
            "headers": resp_headers,
            "body_base64": base64.b64encode(response.read()).decode("ascii"),
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
