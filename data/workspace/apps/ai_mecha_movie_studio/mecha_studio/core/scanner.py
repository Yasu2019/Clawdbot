# -*- coding: utf-8 -*-
from __future__ import annotations
import glob
import os
import platform
import shutil
import string
import subprocess
import urllib.request
from pathlib import Path
from typing import Iterable

# 稼働中サービスの疎通先。Docker等でフォルダが見つからなくても実体があることを検出する。
SERVICE_PROBES = {
    "comfyui_api": "http://127.0.0.1:8188/system_stats",
    "ollama_api": "http://127.0.0.1:11434/api/tags",
}

COMMON_NAMES = {
    "comfyui": ["ComfyUI", "comfyui"],
    "open3dstudio": ["Open3DStudio", "open3dstudio"],
    "3daigc_api": ["3DAIGC-API", "3daigc-api", "3DAIGC_API"],
    "remotion": ["remotion", "Remotion"],
}

# ドライブ直下 / <drive>:/AI / <drive>:/Tools を候補にする相対パターン
DRIVE_RELATIVE_CANDIDATES = {
    "comfyui": ["ComfyUI", "AI/ComfyUI", "Tools/ComfyUI", "ComfyUI_windows_portable/ComfyUI"],
    "open3dstudio": ["Open3DStudio", "AI/Open3DStudio", "Tools/Open3DStudio"],
    "3daigc_api": ["3DAIGC-API", "AI/3DAIGC-API", "Tools/3DAIGC-API"],
    "remotion": ["Remotion", "AI/Remotion", "Tools/Remotion"],
}

# PATHに無い場合のみ探す実行ファイルの既知インストール先（新しい版を優先するため降順ソート）
TOOL_FALLBACK_GLOBS = {
    "blender": [
        "C:/Program Files/Blender Foundation/*/blender.exe",
        "C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe",
        "*:/Blender*/blender.exe",
        "*:/Program Files/Blender Foundation/*/blender.exe",
    ],
    "ffmpeg": [
        "C:/Users/*/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe",
        "C:/ffmpeg/bin/ffmpeg.exe",
        "*:/ffmpeg/bin/ffmpeg.exe",
    ],
    "ffprobe": [
        "C:/Users/*/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffprobe.exe",
        "C:/ffmpeg/bin/ffprobe.exe",
        "*:/ffmpeg/bin/ffprobe.exe",
    ],
    "ollama": [
        "C:/Users/*/AppData/Local/Programs/Ollama/ollama.exe",
    ],
}

SKIP_DIRS = {"Windows", "$Recycle.Bin", "System Volume Information", "node_modules", ".git", "site-packages"}


def _fixed_drives():
    """存在する固定ドライブのルートを返す。ネットワークドライブの走査待ちを避けるため
    Windowsでは GetDriveTypeW == DRIVE_FIXED のみを採用する。"""
    if os.name != "nt":
        return ["/"]
    drives = []
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for letter in string.ascii_uppercase:
            root = f"{letter}:/"
            # 3 == DRIVE_FIXED
            if kernel32.GetDriveTypeW(f"{letter}:\\") == 3:
                drives.append(root)
    except Exception:
        for letter in string.ascii_uppercase:
            root = f"{letter}:/"
            if Path(root).exists():
                drives.append(root)
    return drives


def _expand_drive_glob(pattern: str):
    """先頭が '*:' のパターンを固定ドライブ分に展開する。"""
    if not pattern.startswith("*:"):
        return [pattern]
    return [d.rstrip("/") + pattern[2:] for d in _fixed_drives()]


def resolve_tool(cmd: str):
    """PATHを最優先し、見つからなければ既知インストール先を探す。
    Blenderのように既定でPATHに入らないツールを取りこぼさないための処理。"""
    found = shutil.which(cmd)
    if found:
        return found
    for raw in TOOL_FALLBACK_GLOBS.get(cmd, []):
        for pattern in _expand_drive_glob(raw):
            try:
                matches = sorted(glob.glob(pattern), reverse=True)
            except OSError:
                continue
            for m in matches:
                if Path(m).is_file():
                    return str(Path(m))
    return None


def _candidate_roots(extra_roots: Iterable[str] = ()):
    roots = []
    envs = [os.environ.get("USERPROFILE"), os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")]
    env_extra = os.environ.get("MECHA_STUDIO_EXTRA_ROOTS", "")
    env_list = [x.strip() for x in env_extra.split(";") if x.strip()]
    defaults = []
    for drive in _fixed_drives():
        defaults += [drive + "AI", drive + "Tools"]
    for p in list(extra_roots) + env_list + [e for e in envs if e] + defaults:
        try:
            q = Path(p).expanduser()
            if q.exists() and q not in roots:
                roots.append(q)
        except Exception:
            pass
    return roots


def _drive_candidates(key: str):
    out = []
    for drive in _fixed_drives():
        for rel in DRIVE_RELATIVE_CANDIDATES.get(key, []):
            p = drive + rel
            if Path(p).is_dir():
                out.append(str(Path(p)))
    return out


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


def _probe_services(timeout=3):
    """localhostで動いているサービスを読み取り専用で確認する。
    ComfyUIがDockerや別パスで動いている場合、フォルダ検出では見つからないため。"""
    out = {}
    for key, url in SERVICE_PROBES.items():
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                out[key] = r.status == 200
        except Exception:
            out[key] = False
    return out


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
    tools_off_path = []
    for cmd in ["python", "py", "ffmpeg", "ffprobe", "blender", "node", "npm", "npx", "git", "ollama", "nvidia-smi", "nvcc"]:
        on_path = shutil.which(cmd)
        resolved = on_path or resolve_tool(cmd)
        tools[cmd] = resolved
        if resolved and not on_path:
            tools_off_path.append(cmd)

    dirs = {}
    for key, names in COMMON_NAMES.items():
        found = _drive_candidates(key)
        found += _find_named_dirs(roots, names)[:12]
        dirs[key] = list(dict.fromkeys(found))[:12]

    services = _probe_services()

    notes = [
        "検出は読み取り専用です。既存システムは変更していません。",
        "システムドライブ全体の深掘りは避け、ユーザーフォルダと代表的AI/Toolsフォルダを最大3階層だけ確認します。",
        "固定ドライブのみを対象にします（ネットワークドライブは走査しません）。",
        "環境変数 MECHA_STUDIO_EXTRA_ROOTS（;区切り）で探索ルートを追加できます。",
    ]
    if tools_off_path:
        notes.append("PATH外で発見したツール: " + ", ".join(tools_off_path) + "（実行時は検出した絶対パスを使用します）")
    if services.get("comfyui_api") and not dirs.get("comfyui"):
        notes.append("ComfyUIのフォルダは見つかりませんでしたが、APIは応答しています（Docker等で稼働中の可能性）。")

    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "gpu": _gpu_info(tools.get("nvidia-smi")),
        "tools": tools,
        "tools_off_path": tools_off_path,
        "services": services,
        "directories": dirs,
        "roots_scanned": [str(x) for x in roots],
        "notes": notes,
    }
    return report
