#!/usr/bin/env python3
from __future__ import annotations

import atexit
import os
from pathlib import Path


LOCK_PATH = Path(__file__).resolve().parent / "email_search_ops.lock"


class EmailDbLock:
    def __init__(self, owner: str):
        self.owner = owner
        self.acquired = False

    def acquire(self) -> bool:
        payload = f"{self.owner}|pid={os.getpid()}\n"
        self._clear_stale_lock()
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            atexit.register(self.release)
            self.acquired = True
            return True
        except FileExistsError:
            return False

    def _clear_stale_lock(self) -> None:
        owner = read_lock_owner()
        pid = parse_lock_pid(owner)
        if pid is None:
            return
        if process_exists(pid):
            return
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            LOCK_PATH.unlink(missing_ok=True)
        finally:
            self.acquired = False


def read_lock_owner() -> str:
    try:
        return LOCK_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def parse_lock_pid(owner: str) -> int | None:
    marker = "pid="
    if marker not in owner:
        return None
    tail = owner.split(marker, 1)[1].strip()
    digits = "".join(ch for ch in tail if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return False
    return True
