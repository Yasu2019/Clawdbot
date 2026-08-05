"""GPU時分割調停 (single RTX 5060 Ti 16GB / MIG非対応)。

同一GPUを RL学習・FEM・ComfyUI・Blender が同時に掴むと VRAM が枯渇して落ちる
(trouble_history: resume中の RuntimeError: bad allocation)。GeForce系はMIGで分割
できないため、"同時実行"ではなく"リースによる時分割"で調停する。

設計:
  - リースは1本 (data/state/gpu_leases/gpu0.lease.json)。取得は O_CREAT|O_EXCL で原子的。
  - 保持者が死んだ / TTL切れのリースは自動回収する(ゾンビ対策。プロセス残留でVRAMが
    解放されなかった事例があるため必須)。
  - preemptible な保持者は yield_url を持つ。横取り時に yield_url を叩いてVRAMを
    解放させる。ComfyUI は POST /free {"unload_models":true,"free_memory":true} で
    プロセスを殺さずにVRAMを手放せるため preemptible。
  - RL学習/FEM は途中停止の損失が大きいため nonpreemptible。ComfyUI 側が待つ。

優先度 (小さいほど強い):
  0  = 学習・CAEソルバ等の長時間ジョブ (nonpreemptible)
  10 = ComfyUI 対話生成 (preemptible)
  20 = バッチレンダ等 (preemptible)

CLI:
  python scripts/gpu_arbiter.py status
  python scripts/gpu_arbiter.py acquire --owner rl_train --priority 0 --vram 10000 --ttl 21600 --nonpreemptible
  python scripts/gpu_arbiter.py release --owner rl_train
  python scripts/gpu_arbiter.py renew   --owner rl_train --ttl 21600
  python scripts/gpu_arbiter.py reap
  python scripts/gpu_arbiter.py yield-comfyui        # リース無しで居座るComfyUIのVRAMを解放

Python:
  from gpu_arbiter import gpu_lease
  with gpu_lease("rl_train", priority=0, est_vram_mb=10000, ttl_sec=21600,
                 preemptible=False, wait_sec=600):
      train()
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(__file__).resolve().parents[1]
LEASE_DIR = ROOT / "data" / "state" / "gpu_leases"
LEASE_PATH = LEASE_DIR / "gpu0.lease.json"
LOCK_PATH = LEASE_DIR / "gpu0.lock"
LOCK_STALE_SEC = 30
DEFAULT_COMFY_FREE_URL = "http://127.0.0.1:8188/free"
# /free 後にVRAMが戻るまでの待ち時間。実測で60秒では戻らないことがあるため長めに取る。
DEFAULT_YIELD_WAIT_SEC = 180.0

PRIORITY_LONG_JOB = 0
PRIORITY_INTERACTIVE = 10
PRIORITY_BATCH = 20


# ---------------------------------------------------------------- utilities

def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def pid_alive(pid: int) -> bool:
    """保持者プロセスの生存確認。psutil非依存(system pythonに未導入のため)。"""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def gpu_memory() -> tuple[int | None, int | None]:
    """(free_mb, total_mb)。取得できなければ (None, None)。"""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total",
             "--format=csv,noheader,nounits"],
            text=True, timeout=15, stderr=subprocess.STDOUT,
        ).strip().splitlines()[0]
        free, total = (int(x.strip()) for x in out.split(","))
        return free, total
    except Exception:
        return None, None


def compute_apps() -> list[str]:
    """GPUを掴んでいるプロセス一覧。WSL2/Docker越しは
    [Insufficient Permissions] としか出ないため、これだけに頼らない。"""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory,name",
             "--format=csv,noheader"],
            text=True, timeout=15, stderr=subprocess.STDOUT,
        ).strip()
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


# ------------------------------------------------------------ mutation lock

@contextlib.contextmanager
def _mutation_lock(timeout_sec: float = 20.0):
    """リース更新の排他。リース本体とは別の短命ロック。"""
    LEASE_DIR.mkdir(parents=True, exist_ok=True)
    deadline = _now() + timeout_sec
    while True:
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {_now()}".encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                age = _now() - LOCK_PATH.stat().st_mtime
            except OSError:
                age = 0.0
            if age > LOCK_STALE_SEC:
                LOCK_PATH.unlink(missing_ok=True)
                continue
            if _now() > deadline:
                raise TimeoutError(f"GPUリースのロックを取得できません: {LOCK_PATH}")
            time.sleep(0.2)
    try:
        yield
    finally:
        LOCK_PATH.unlink(missing_ok=True)


# ----------------------------------------------------------------- lease io

def read_lease() -> dict | None:
    try:
        return json.loads(LEASE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lease_is_live(lease: dict | None) -> bool:
    if not lease:
        return False
    if lease.get("expires_at_epoch", 0) < _now():
        return False
    pid = int(lease.get("pid", 0))
    # pid=0 は「プロセスに紐づかないリース」(手動取得)。TTLだけで判定する。
    return True if pid == 0 else pid_alive(pid)


def _write_lease(lease: dict) -> None:
    tmp = LEASE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(lease, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, LEASE_PATH)


def _clear_lease() -> None:
    LEASE_PATH.unlink(missing_ok=True)


# ------------------------------------------------------------------- yield

def _post_free(url: str) -> bool:
    body = json.dumps({"unload_models": True, "free_memory": True}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except Exception as exc:
        print(f"[gpu_arbiter] /free 要求に失敗: {exc}")
        return False


def _wait_release(before_free_mb: int | None, wait_sec: float, margin_mb: int = 500) -> bool:
    if before_free_mb is None:
        return False
    deadline = _now() + wait_sec
    while _now() < deadline:
        time.sleep(3)
        free, _ = gpu_memory()
        if free is None:
            return False
        if free > before_free_mb + margin_mb:
            print(f"[gpu_arbiter] VRAM解放を確認: {before_free_mb} MB -> {free} MB "
                  f"({int(wait_sec - (deadline - _now()))}秒)")
            return True
    return False


def terminate_pid(pid: int) -> bool:
    """保持者プロセスを終了させる。ComfyUI(comfy_aimdo)はプロセス終了でVRAMを全解放する。"""
    if pid <= 0 or not pid_alive(pid):
        return False
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            os.kill(pid, 15)
        return True
    except Exception as exc:
        print(f"[gpu_arbiter] プロセス終了に失敗: pid={pid} {exc}")
        return False


def request_yield(lease: dict, wait_sec: float | None = None) -> bool:
    """preemptibleな保持者にVRAM解放を要求する。

    実測(2026-08-06 K10): ComfyUIの POST /free はVRAMを解放するが即時ではなく、
    60秒以内には戻らないことがある(comfy_aimdo のVRAMバッファは vrambuf_destroy
    まで保持されるため)。プロセス終了なら即時に全解放される。
    そこで「/free で待つ → 期限内に戻らなければプロセス終了」の二段構えにする。
    """
    mode = lease.get("yield_mode", "http_free+terminate")
    if mode == "none":
        return False
    wait_sec = float(lease.get("yield_wait_sec", DEFAULT_YIELD_WAIT_SEC)
                     if wait_sec is None else wait_sec)
    before, _ = gpu_memory()

    if mode.startswith("http_free"):
        url = lease.get("yield_url")
        if url and _post_free(url):
            print(f"[gpu_arbiter] /free を送信。最大{int(wait_sec)}秒待機します: {url}")
            if _wait_release(before, wait_sec):
                return True
            print("[gpu_arbiter] 期限内にVRAMが戻りませんでした")

    if "terminate" in mode:
        pid = int(lease.get("pid", 0))
        if terminate_pid(pid):
            print(f"[gpu_arbiter] 保持者プロセスを終了しました: pid={pid}")
            if _wait_release(before, 30.0):
                return True
            free, _ = gpu_memory()
            print(f"[gpu_arbiter] 終了後のVRAM空き: {free} MB")
            return True
        print("[gpu_arbiter] 終了できるPIDがありません(pid=0 で登録された可能性)")
    return False


def yield_comfyui(url: str = DEFAULT_COMFY_FREE_URL, wait_sec: float = DEFAULT_YIELD_WAIT_SEC) -> bool:
    """リースの有無に関係なくComfyUIにVRAMを手放させる安全弁(/freeのみ、プロセスは殺さない)。"""
    return request_yield({"yield_url": url, "yield_mode": "http_free"}, wait_sec=wait_sec)


# ----------------------------------------------------------------- core api

def acquire(owner: str, priority: int = PRIORITY_INTERACTIVE, est_vram_mb: int = 0,
            ttl_sec: int = 3600, preemptible: bool = True, wait_sec: float = 0.0,
            yield_url: str | None = None, pid: int | None = None,
            note: str = "", force: bool = False) -> tuple[bool, dict | None]:
    """リースを取得する。戻り値 (取得できたか, 現保持者)。"""
    deadline = _now() + max(wait_sec, 0.0)
    while True:
        with _mutation_lock():
            cur = read_lease()
            live = lease_is_live(cur)
            if cur and not live:
                print(f"[gpu_arbiter] 失効リースを回収: owner={cur.get('owner')} pid={cur.get('pid')}")
                _clear_lease()
                cur = None

            if cur and cur.get("owner") == owner:
                cur["expires_at_epoch"] = _now() + ttl_sec
                cur["expires_at"] = _iso(cur["expires_at_epoch"])
                _write_lease(cur)
                return True, cur

            if cur:
                can_take = force or (
                    cur.get("preemptible", False) and priority < int(cur.get("priority", 99))
                )
                if can_take and (force or request_yield(cur)):
                    print(f"[gpu_arbiter] 横取り: {cur.get('owner')} -> {owner}")
                    _clear_lease()
                    cur = None

            if cur:
                if _now() >= deadline:
                    return False, cur
            else:
                lease = {
                    "gpu_index": 0,
                    "owner": owner,
                    "pid": os.getpid() if pid is None else pid,
                    "priority": priority,
                    "preemptible": preemptible,
                    "yield_url": yield_url,
                    "est_vram_mb": est_vram_mb,
                    "note": note,
                    "acquired_at": _iso(_now()),
                    "ttl_sec": ttl_sec,
                    "expires_at_epoch": _now() + ttl_sec,
                    "expires_at": _iso(_now() + ttl_sec),
                }
                _write_lease(lease)
                return True, lease
        time.sleep(3)


def release(owner: str) -> bool:
    with _mutation_lock():
        cur = read_lease()
        if not cur:
            return False
        if cur.get("owner") != owner:
            print(f"[gpu_arbiter] 保持者が違うため解放しません: 現保持者={cur.get('owner')}")
            return False
        _clear_lease()
        return True


def renew(owner: str, ttl_sec: int = 3600) -> bool:
    with _mutation_lock():
        cur = read_lease()
        if not cur or cur.get("owner") != owner:
            return False
        cur["expires_at_epoch"] = _now() + ttl_sec
        cur["expires_at"] = _iso(cur["expires_at_epoch"])
        cur["ttl_sec"] = ttl_sec
        _write_lease(cur)
        return True


def reap() -> bool:
    """死んだ保持者・TTL切れのリースを回収する。回収したらTrue。"""
    with _mutation_lock():
        cur = read_lease()
        if cur and not lease_is_live(cur):
            _clear_lease()
            return True
        return False


def status() -> dict:
    cur = read_lease()
    free, total = gpu_memory()
    return {
        "lease": cur,
        "lease_live": lease_is_live(cur),
        "gpu_free_mb": free,
        "gpu_total_mb": total,
        "compute_apps": compute_apps(),
        "checked_at": _iso(_now()),
    }


def available_for(est_vram_mb: int, priority: int = PRIORITY_LONG_JOB) -> tuple[bool, str]:
    """起動前判定。リースを取らずに「今なら通るか」だけを見る。"""
    cur = read_lease()
    if lease_is_live(cur) and cur.get("owner"):
        if not (cur.get("preemptible") and priority < int(cur.get("priority", 99))):
            return False, f"GPUリースを {cur['owner']} が保持中 (期限 {cur.get('expires_at')})"
    free, _ = gpu_memory()
    if free is not None and est_vram_mb and free < est_vram_mb:
        return False, f"GPU空きVRAM不足: {free} MB < 要求 {est_vram_mb} MB"
    return True, "ok"


@contextlib.contextmanager
def gpu_lease(owner: str, **kwargs):
    ok, holder = acquire(owner, **kwargs)
    if not ok:
        raise RuntimeError(
            f"GPUリースを取得できません。現保持者={holder.get('owner') if holder else '不明'}"
        )
    try:
        yield
    finally:
        release(owner)


# ---------------------------------------------------------------------- cli

def main() -> int:
    p = argparse.ArgumentParser(description="GPU時分割調停")
    sub = p.add_subparsers(dest="action", required=True)

    sub.add_parser("status")
    sub.add_parser("reap")
    y = sub.add_parser("yield-comfyui")
    y.add_argument("--url", default=DEFAULT_COMFY_FREE_URL)

    a = sub.add_parser("acquire")
    a.add_argument("--owner", required=True)
    a.add_argument("--priority", type=int, default=PRIORITY_INTERACTIVE)
    a.add_argument("--vram", type=int, default=0, help="想定VRAM使用量(MB)")
    a.add_argument("--ttl", type=int, default=3600)
    a.add_argument("--wait", type=float, default=0.0, help="取得待ち秒数")
    a.add_argument("--nonpreemptible", action="store_true", help="横取りを許さない(学習/CAE)")
    a.add_argument("--yield-url", default=None)
    a.add_argument("--pid", type=int, default=0, help="0=このプロセスに紐づけない")
    a.add_argument("--note", default="")
    a.add_argument("--force", action="store_true", help="強制的に奪う(最終手段)")

    r = sub.add_parser("release")
    r.add_argument("--owner", required=True)

    n = sub.add_parser("renew")
    n.add_argument("--owner", required=True)
    n.add_argument("--ttl", type=int, default=3600)

    args = p.parse_args()

    if args.action == "status":
        st = status()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0
    if args.action == "reap":
        print("回収しました" if reap() else "回収対象はありません")
        return 0
    if args.action == "yield-comfyui":
        return 0 if yield_comfyui(args.url) else 1
    if args.action == "acquire":
        ok, holder = acquire(
            args.owner, priority=args.priority, est_vram_mb=args.vram, ttl_sec=args.ttl,
            preemptible=not args.nonpreemptible, wait_sec=args.wait,
            yield_url=args.yield_url, pid=args.pid, note=args.note, force=args.force,
        )
        if ok:
            print(f"取得: owner={args.owner} 期限={holder['expires_at']}")
            return 0
        print(f"取得失敗。現保持者={holder.get('owner') if holder else '不明'} "
              f"期限={holder.get('expires_at') if holder else '-'}")
        return 1
    if args.action == "release":
        print("解放しました" if release(args.owner) else "解放できませんでした")
        return 0
    if args.action == "renew":
        print("更新しました" if renew(args.owner, args.ttl) else "更新できませんでした")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
