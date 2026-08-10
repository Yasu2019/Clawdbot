# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

COMMON_NAMES = {
    "comfyui": ["ComfyUI", "comfyui"],
    "open3dstudio": ["Open3DStudio", "open3dstudio"],
    "3daigc_api": ["3DAIGC-API", "3daigc-api", "3DAIGC_API"],
    "remotion": ["remotion", "Remotion"],
}

GLOBAL_CANDIDATES = {
    "comfyui": ["C:/ComfyUI", "D:/ComfyUI", "C:/AI/ComfyUI", "D:/AI/ComfyUI"],
    "open3dstudio": ["C:/Open3DStudio", "D:/Open3DStudio", "C:/AI/Open3DStudio", "D:/AI/Open3DStudio"],
    "3daigc_api": ["C:/3DAIGC-API", "D:/3DAIGC-API", "C:/AI/3DAIGC-API", "D:/AI/3DAIGC-API"],
    "remotion": ["C:/Remotion", "D:/Remotion", "C:/AI/Remotion", "D:/AI/Remotion"],
}

SKIP_DIRS = {"Windows", "$Recycle.Bin", "System Volume Information", "node_modules", ".git", "site-packages"}


def _candidate_roots(extra_roots: Iterable[str] = ()):
    roots = []
    envs = [os.environ.get("USERPROFILE"), os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")]
    defaults = ["C:/AI", "C:/Tools", "D:/AI", "D:/Tools"]
    for p in list(extra_roots) + [e for e in envs if e] + defaults:
        try:
            q = Path(p).expanduser()
            if q.exists() and q not in roots:
                roots.append(q)
        except Exception:
            pass
    return roots


def _find_named_dirs(roots, names, max_depth=3):
    found = []
    targets = {n.lower() for n in names}
    for root in roots:
        try:
            for name in names:
                p = root / name
                if p.is_dir():
                    found.append(str(p))
            base_depth = len(root.parts)
            for cur, dirs, _files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                depth = len(Path(cur).parts) - base_depth
                if depth >= max_depth:
                    dirs[:] = []
                    continue
                for d in list(dirs):
                    if d.lower() in targets:
                        found.append(str(Path(cur) / d))
        except (PermissionError, OSError):
            continue
    return list(dict.fromkeys(found))


def _gpu_info(nvidia_smi):
    if not nvidia_smi:
        return []
    cmd = [nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
        if p.returncode != 0:
            return []
        out = []
        for line in p.stdout.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 3:
                out.append({"name": parts[0], "vram_mb": int(float(parts[1])), "driver": parts[2]})
        return out
    except Exception:
        return []


def scan(extra_roots=()):
    roots = _candidate_roots(extra_roots)
    tools = {}
    for cmd in ["python", "py", "ffmpeg", "ffprobe", "blender", "node", "npm", "npx", "git", "ollama", "nvidia-smi", "nvcc"]:
        tools[cmd] = shutil.which(cmd)

    dirs = {}
    for key, names in COMMON_NAMES.items():
        found = [p for p in GLOBAL_CANDIDATES.get(key, []) if Path(p).is_dir()]
        found += _find_named_dirs(roots, names)[:12]
        dirs[key] = list(dict.fromkeys(found))[:12]

    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "gpu": _gpu_info(tools.get("nvidia-smi")),
        "tools": tools,
        "directories": dirs,
        "roots_scanned": [str(x) for x in roots],
        "notes": [
            "検出は読み取り専用です。既存システムは変更していません。",
            "システムドライブ全体の深掘りは避け、ユーザーフォルダと代表的AI/Toolsフォルダを最大3階層だけ確認します。"
        ]
    }
    return report
