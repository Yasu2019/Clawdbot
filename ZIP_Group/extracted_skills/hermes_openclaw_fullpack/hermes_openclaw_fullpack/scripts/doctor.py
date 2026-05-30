import os
import socket

checks = []

def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False

checks.append(("Bridge API 8791", port_open("127.0.0.1", 8791)))
checks.append(("Qdrant 6633", port_open("127.0.0.1", 6633)))
checks.append(("Postgres 55432", port_open("127.0.0.1", 55432)))
checks.append((".env exists", os.path.exists(".env")))

for name, ok in checks:
    print(f"{name}: {'OK' if ok else 'NG'}")
