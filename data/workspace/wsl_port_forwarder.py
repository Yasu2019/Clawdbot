#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import socket
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def pump(client: socket.socket, upstream: socket.socket) -> None:
    sockets = [client, upstream]
    try:
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 5.0)
            if exceptional:
                break
            if not readable:
                continue
            for sock in readable:
                data = sock.recv(65536)
                if not data:
                    return
                other = upstream if sock is client else client
                other.sendall(data)
    finally:
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward localhost TCP to a WSL service")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, required=True)
    parser.add_argument("--status-path", required=True)
    args = parser.parse_args()

    status_path = Path(args.status_path)
    status = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "state": "starting",
        "listen": f"{args.listen_host}:{args.listen_port}",
        "target": f"{args.target_host}:{args.target_port}",
        "pid": os.getpid(),
        "acceptedConnections": 0,
    }
    write_status(status_path, status)

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.listen_host, args.listen_port))
        server.listen(20)
        status["state"] = "running"
        status["updatedAt"] = now_jst_text()
        write_status(status_path, status)

        while True:
            client, addr = server.accept()
            status["acceptedConnections"] += 1
            status["lastClient"] = f"{addr[0]}:{addr[1]}"
            status["updatedAt"] = now_jst_text()
            write_status(status_path, status)
            try:
                upstream = socket.create_connection((args.target_host, args.target_port), timeout=10)
            except Exception as exc:
                status["lastError"] = str(exc)
                status["updatedAt"] = now_jst_text()
                write_status(status_path, status)
                try:
                    client.close()
                except Exception:
                    pass
                continue
            thread = threading.Thread(target=pump, args=(client, upstream), daemon=True)
            thread.start()


if __name__ == "__main__":
    raise SystemExit(main())
