#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portal_external_bridge.py

A lightweight, secure external HTTP reverse proxy bridge running on Windows host.
Binds to 0.0.0.0:18088 and forwards all traffic to local Portal Server (127.0.0.1:8088).
This allows other computers on the same company LAN to access the Clawstack Portal safely.

Usage:
  python data/workspace/portal_external_bridge.py
"""

from __future__ import annotations
import sys

# P023: Windows cp932 Encoding protection standard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Set default encoding to protect against Japanese Windows console exceptions
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 28088
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8088

class BridgeProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass # Suppress standard console noise to maintain premium performance

    def _handle_request(self):
        # Extract headers
        headers = {}
        for key, val in self.headers.items():
            if key.lower() == "host":
                # Rewrite Host header to match target destination
                headers["Host"] = f"{TARGET_HOST}:{TARGET_PORT}"
            else:
                headers[key] = val

        # Extract request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Establish connection with local portal container
        conn = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=10)
        try:
            conn.request(self.command, self.path, body, headers)
            resp = conn.getresponse()

            # Send status code back to client
            self.send_response(resp.status, resp.reason)

            # Send headers back to client
            for key, val in resp.getheaders():
                # Prevent caching issues or duplicate headers
                if key.lower() not in ["transfer-encoding"]:
                    self.send_header(key, val)
            self.end_headers()

            # Read response body and write back to client
            resp_body = resp.read()
            self.wfile.write(resp_body)

        except Exception as e:
            # Safe recovery handling
            print(f"[BridgeProxy] Error forwarding request: {e}", file=sys.stderr)
            self.send_response(502, "Bad Gateway")
            self.end_headers()
            self.wfile.write(f"Clawstack Proxy Bridge Error: {e}".encode("utf-8"))
        finally:
            conn.close()

    def do_GET(self): self._handle_request()
    def do_POST(self): self._handle_request()
    def do_PUT(self): self._handle_request()
    def do_DELETE(self): self._handle_request()
    def do_OPTIONS(self): self._handle_request()
    def do_PATCH(self): self._handle_request()
    def do_HEAD(self): self._handle_request()

def main():
    print(f"============================================================")
    print(f" Clawstack Portal External Bridge Active ")
    print(f"============================================================")
    print(f" - Local Target: http://{TARGET_HOST}:{TARGET_PORT}")
    print(f" - External Access: http://0.0.0.0:{LISTEN_PORT}")
    print(f" - Mitui LAN Access: http://192.168.5.172:{LISTEN_PORT}")
    print(f"============================================================")
    
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), BridgeProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Portal External Bridge proxy...")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
