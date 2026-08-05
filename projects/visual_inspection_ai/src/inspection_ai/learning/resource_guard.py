from __future__ import annotations

import csv
import io
import subprocess
from dataclasses import dataclass

import psutil


@dataclass
class ResourceState:
    cpu_percent: float
    memory_percent: float
    gpu_util_percent: float | None
    gpu_free_mb: float | None
    gpu_temperature_c: float | None


def nvidia_state() -> tuple[float | None, float | None, float | None]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=utilization.gpu,memory.free,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=True)
        first = next(csv.reader(io.StringIO(result.stdout)))
        return float(first[0]), float(first[1]), float(first[2])
    except Exception:
        return None, None, None


def current_resources() -> ResourceState:
    gpu_u, gpu_free, gpu_temp = nvidia_state()
    return ResourceState(
        cpu_percent=float(psutil.cpu_percent(interval=0.5)),
        memory_percent=float(psutil.virtual_memory().percent),
        gpu_util_percent=gpu_u,
        gpu_free_mb=gpu_free,
        gpu_temperature_c=gpu_temp,
    )


def gpu_lease_blocker() -> str | None:
    """GPU時分割調停(scripts/gpu_arbiter.py)のリース保持者を返す。

    空きVRAMの確認だけでは、2つのジョブが同時に判定を通過して衝突しうる。
    リースを見ることで「他が使うと宣言している」状態を検出する。
    arbiterが無い環境ではNone(=阻害なし)。
    """
    try:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[5]
        sys.path.insert(0, str(root / "scripts"))
        import gpu_arbiter

        lease = gpu_arbiter.read_lease()
        if gpu_arbiter.lease_is_live(lease):
            return f"{lease.get('owner')} (期限 {lease.get('expires_at')})"
    except Exception:
        return None
    return None


def may_train(config_learning: dict) -> tuple[bool, ResourceState, list[str]]:
    state = current_resources()
    reasons=[]
    holder = gpu_lease_blocker()
    if holder:
        reasons.append(f"GPUリースを他が保持中: {holder}")
    if state.cpu_percent > float(config_learning.get("idle_cpu_max_percent",35)):
        reasons.append("CPU使用率が高い")
    if state.memory_percent > 88:
        reasons.append("メモリ使用率が高い")
    if state.gpu_util_percent is not None and state.gpu_util_percent > float(config_learning.get("idle_gpu_max_percent",30)):
        reasons.append("GPU使用率が高い")
    if state.gpu_free_mb is not None and state.gpu_free_mb < float(config_learning.get("min_free_gpu_mb",5000)):
        reasons.append("GPU空きメモリが少ない")
    return not reasons, state, reasons
