#!/usr/bin/env python3
"""
IATFアプリ用 ネットワークプロキシ
外部IP(0.0.0.0:3004) から localhost:3004 へ中継する
"""
import socket
import threading
import sys

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 3004
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 3004


def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass


def handle_client(client_sock):
    try:
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.connect((TARGET_HOST, TARGET_PORT))
        t1 = threading.Thread(target=forward, args=(client_sock, target_sock), daemon=True)
        t2 = threading.Thread(target=forward, args=(target_sock, client_sock), daemon=True)
        t1.start()
        t2.start()
    except Exception as e:
        print(f"[ERROR] {e}")
        client_sock.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((LISTEN_HOST, LISTEN_PORT))
    except OSError as e:
        print(f"[ERROR] ポート {LISTEN_PORT} のバインドに失敗しました: {e}")
        print("→ 別のポート (例: 3099) で試みます...")
        LISTEN_PORT_ALT = 3099
        srv.bind((LISTEN_HOST, LISTEN_PORT_ALT))
        print(f"[INFO] 代替ポート {LISTEN_PORT_ALT} でリッスン中...")
        print(f"[INFO] アクセスURL: http://192.168.5.172:{LISTEN_PORT_ALT}/users/sign_in")
        srv.listen(50)
        while True:
            c, _ = srv.accept()
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()
        return

    print(f"[INFO] IATF Proxy 起動: 0.0.0.0:{LISTEN_PORT} → localhost:{TARGET_PORT}")
    print(f"[INFO] 他のパソコンからは: http://192.168.5.172:{LISTEN_PORT}/users/sign_in")
    print("[INFO] 停止するには Ctrl+C を押してください")
    srv.listen(50)
    try:
        while True:
            c, addr = srv.accept()
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[INFO] プロキシを停止しました")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
