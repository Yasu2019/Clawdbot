#!/usr/bin/env python3
from __future__ import annotations

import atexit
import ctypes
import os
import time
from pathlib import Path


LOCK_PATH = Path(__file__).resolve().parent / "email_search_ops.lock"

# ロックファイルの所有者情報が壊れている(pid解析不能)場合、この秒数より
# 古ければ孤立ロックとみなして削除する。通常のロック保持時間(数分オーダー)
# より十分長く取り、誤って稼働中のロックを消さないようにする。
STALE_UNPARSEABLE_LOCK_SECONDS = 30 * 60


class EmailDbLock:
    def __init__(self, owner: str, path: Path | None = None):
        self.owner = owner
        self.path = path or LOCK_PATH
        self.acquired = False
        self.payload = ""

    def acquire(self) -> bool:
        payload = f"{self.owner}|pid={os.getpid()}\n"
        self._clear_stale_lock()
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            atexit.register(self.release)
            self.acquired = True
            self.payload = payload.strip()
            return True
        except FileExistsError:
            return False

    def _clear_stale_lock(self) -> None:
        if not self.path.exists():
            return
        owner = read_lock_owner(self.path)
        pid = parse_lock_pid(owner)
        if pid is None:
            # 所有者情報が破損/不明な形式(例: NULLバイト埋めなど)で
            # pidを読み取れないケース。以前はここで無条件に諦めて
            # おり、壊れたロックが永久に残るバグがあった。
            # ファイルが十分古ければ孤立ロックとみなして削除する。
            if self._lock_age_seconds() >= STALE_UNPARSEABLE_LOCK_SECONDS:
                self._unlink_lock()
            return
        if process_exists(pid):
            return
        self._unlink_lock()

    def _lock_age_seconds(self) -> float:
        try:
            return time.time() - self.path.stat().st_mtime
        except Exception:
            # stat に失敗する = 実体がないなど。古いものとして扱い削除対象にする。
            return STALE_UNPARSEABLE_LOCK_SECONDS

    def _unlink_lock(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            if read_lock_owner(self.path) == self.payload:
                self.path.unlink(missing_ok=True)
        finally:
            self.acquired = False
            self.payload = ""


def read_lock_owner(path: Path = LOCK_PATH) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
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
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        return _windows_process_exists(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return False
    return True


def _windows_process_exists(pid: int) -> bool:
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        process_query_limited_information, False, pid
    )
    if not handle:
        return False
    ctypes.windll.kernel32.CloseHandle(handle)
    return True
