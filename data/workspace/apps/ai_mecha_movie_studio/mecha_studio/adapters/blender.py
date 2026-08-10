# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess
from pathlib import Path
from ..core.paths import ROOT
from ..core.scanner import resolve_tool


def available():
    """PATHに無くても Program Files 等の既知インストール先から探す。"""
    return resolve_tool("blender")


def _run(cmd, output_dir: Path, pattern="*.png", what="Blenderレンダ"):
    """Blenderを実行し、実出力の有無で成否を判定する。

    Blenderは --python 内でPython例外が出ても終了コード0を返すため、
    returncodeだけを見ると『成功したのに出力ゼロ』を見逃す。
    """
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    produced = sorted(output_dir.rglob(pattern))
    if p.returncode != 0 or not produced:
        log = (p.stderr or "") + "\n" + (p.stdout or "")
        detail = log[-4000:].strip() or "(Blenderの出力なし)"
        raise RuntimeError(
            f"{what}に失敗しました (exit={p.returncode}, 出力{len(produced)}件)\n{detail}"
        )
    return produced, p.stdout or ""


def render_walk_animation(model_path: Path, motion_path: Path, output_dir: Path,
                          views="side", step=1, resolution=640):
    """リグ付きメカFBXへ別FBXのモーションを移植して連番PNGをレンダする。

    ボーン名が一致するリグ同士（Mixamo系など）が前提。
    """
    exe = available()
    if not exe:
        raise RuntimeError("blender が見つかりません（PATHにも既知インストール先にもありません）")
    for p in (Path(model_path), Path(motion_path)):
        if not p.exists():
            raise RuntimeError(f"ファイルが見つかりません: {p}")
    script = ROOT / "mecha_studio" / "blender" / "render_walk_animation.py"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--background", "--python", str(script), "--",
           str(model_path), str(motion_path), str(output_dir),
           str(views), str(step), str(resolution)]
    produced, log = _run(cmd, output_dir, what="歩行モーションのレンダ")
    for line in log.splitlines():
        if line.startswith("[walk]"):
            print(line)
    return [str(x) for x in produced]


def render_reference_views(model_path: Path, output_dir: Path):
    exe = available()
    if not exe:
        raise RuntimeError("blender が見つかりません（PATHにも既知インストール先にもありません）")
    script = ROOT / "mecha_studio" / "blender" / "render_reference_views.py"
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--background", "--python", str(script), "--", str(model_path), str(output_dir)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    # Blenderは --python 内でPython例外が出ても終了コード0を返す。
    # returncodeだけを見ると「成功したのに出力ゼロ」を見逃すため、実出力で判定する。
    produced = sorted(output_dir.glob("*.png"))
    if p.returncode != 0 or not produced:
        log = (p.stderr or "") + "\n" + (p.stdout or "")
        detail = log[-4000:].strip() or "(Blenderの出力なし)"
        raise RuntimeError(
            f"Blenderレンダに失敗しました (exit={p.returncode}, 出力{len(produced)}件)\n{detail}"
        )
    return [str(x) for x in produced]
