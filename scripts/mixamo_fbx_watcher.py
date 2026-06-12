#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mixamo FBX 自動リネーム・分類ウォッチャー
C:/Users/yasu/Downloads を監視し、UUID名FBXをアニメーション名にリネームして motion_lab へ移動。
Usage:
  python scripts/mixamo_fbx_watcher.py           # 60分間監視（10秒ごと）
  python scripts/mixamo_fbx_watcher.py --once    # 1回だけスキャン
  python scripts/mixamo_fbx_watcher.py --duration 7200  # 2時間監視
"""
from __future__ import annotations
import re, shutil, time, json, struct
from pathlib import Path
from datetime import datetime

WATCH_DIR  = Path("C:/Users/yasu/Downloads")
REPO_ROOT  = Path(__file__).resolve().parent.parent
MOTION_LAB = REPO_ROOT / "data/workspace/apps/motion_lab/assets"
CHAR_DIR   = MOTION_LAB / "characters/raw"
MOTION_DIR = MOTION_LAB / "motions/raw/mixamo"

FBX_MAGIC            = b"Kaydara FBX Binary"
UUID_RE              = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MOTION_SIZE_THRESHOLD = 10 * 1024 * 1024   # 10 MB: 未満 → モーション, 以上 → キャラクター
MANIFEST_PATH        = MOTION_DIR / "_manifest.json"

GENERIC_TAKES = {"mixamo.com", "take 001", "take001", "default", "scene", "armature"}


# ── FBX パーサー ────────────────────────────────────────────────────
def _is_fbx(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(18) == FBX_MAGIC
    except Exception:
        return False


def _read_take_name(path: Path) -> str:
    """FBXバイナリからアニメーション名（Take/AnimStack名）を抽出。"""
    try:
        data = path.read_bytes()

        # ASCII FBX
        if FBX_MAGIC not in data[:20]:
            for line in data.decode("utf-8", errors="ignore").splitlines():
                s = line.strip()
                if s.startswith("Take:"):
                    name = s[5:].strip().strip('"')
                    if name.lower() not in GENERIC_TAKES:
                        return name
            return ""

        # Binary FBX: "AnimStack::<name>" パターンを探す
        pos = 0
        while True:
            idx = data.find(b"AnimStack::", pos)
            if idx == -1:
                break
            name_start = idx + 11
            buf = bytearray()
            for i in range(name_start, min(name_start + 80, len(data))):
                b = data[i]
                if b == 0 or b < 32:
                    break
                buf.append(b)
            if buf:
                name = buf.decode("utf-8", errors="ignore")
                if name.lower() not in GENERIC_TAKES and any(c.isalpha() for c in name):
                    return name
            pos = idx + 1

        # フォールバック: "Takes" ノードの直後にある文字列を探す
        takes_idx = data.find(b"\x05Takes")
        if takes_idx > 0:
            for i in range(takes_idx + 6, min(takes_idx + 300, len(data))):
                slen = data[i]
                if 4 <= slen <= 80:
                    chunk = data[i + 1 : i + 1 + slen]
                    try:
                        s = chunk.decode("ascii")
                        if (
                            all(32 <= ord(c) < 128 for c in s)
                            and any(c.isalpha() for c in s)
                            and s.lower() not in GENERIC_TAKES | {"Takes", "AnimStack"}
                        ):
                            return s
                    except Exception:
                        pass

    except Exception:
        pass
    return ""


# ── リネーム・移動 ──────────────────────────────────────────────────
def _sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60]


def _dest_dir(path: Path) -> tuple[Path, str]:
    """(保存先ディレクトリ, カテゴリ名)"""
    size = path.stat().st_size
    if size >= MOTION_SIZE_THRESHOLD:
        return CHAR_DIR, "character"
    return MOTION_DIR, "motion"


def _unique_dest(dest_dir: Path, base_name: str) -> Path:
    dest = dest_dir / base_name
    if not dest.exists():
        return dest
    stem, suffix = Path(base_name).stem, Path(base_name).suffix
    for i in range(2, 100):
        dest = dest_dir / f"{stem}_{i}{suffix}"
        if not dest.exists():
            return dest
    return dest_dir / base_name  # fallback（上書き）


def process_file(path: Path, manifest: list[dict]) -> bool:
    """1ファイル処理。FBXでなければ False を返す。"""
    if not _is_fbx(path):
        return False

    take_name = _read_take_name(path)
    dest_dir, category = _dest_dir(path)
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d_%H%M%S")

    if take_name and take_name.lower() not in GENERIC_TAKES:
        base_name = _sanitize(take_name) + ".fbx"
    else:
        # UUID先頭8文字 + タイムスタンプ
        base_name = f"mixamo_{ts}_{path.stem[:8]}.fbx"

    dest = _unique_dest(dest_dir, base_name)
    shutil.copy2(path, dest)

    entry = {
        "original": path.name,
        "renamed": dest.name,
        "take_name": take_name or "(unknown)",
        "category": category,
        "size_kb": path.stat().st_size // 1024,
        "dest": str(dest),
        "processed_at": datetime.now().isoformat(),
    }
    manifest.append(entry)
    print(f"  [{category:9s}] {path.name[:36]:36s} → {dest.name}")
    return True


# ── ウォッチャー ─────────────────────────────────────────────────────
def _load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_manifest(manifest: list[dict]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def scan_once(seen: set[Path], manifest: list[dict]) -> int:
    count = 0
    for f in WATCH_DIR.iterdir():
        if not f.is_file() or f in seen:
            continue
        if f.suffix.lower() == ".crdownload":
            continue  # ダウンロード中はスキップ

        is_uuid = UUID_RE.match(f.stem) and f.suffix == ""
        is_fbx  = f.suffix.lower() == ".fbx"
        if not (is_uuid or is_fbx):
            continue

        seen.add(f)
        if process_file(f, manifest):
            count += 1

    return count


def run(interval: int = 10, duration: int = 3600) -> None:
    MOTION_DIR.mkdir(parents=True, exist_ok=True)
    CHAR_DIR.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    already_done = {e["original"] for e in manifest}

    # 既処理ファイルを seen に登録（重複処理防止）
    seen: set[Path] = set()
    for f in WATCH_DIR.iterdir():
        if f.is_file() and f.name in already_done:
            seen.add(f)

    print(f"[Watcher] 監視開始: {WATCH_DIR}")
    print(f"  モーション保存先: {MOTION_DIR}")
    print(f"  キャラ保存先:     {CHAR_DIR}")
    print(f"  間隔={interval}s  最大={duration}s  既処理={len(already_done)}件")

    start = time.time()
    while time.time() - start < duration:
        n = scan_once(seen, manifest)
        if n:
            _save_manifest(manifest)
            print(f"  → {n}件追加  合計{len(manifest)}件  マニフェスト保存済み")
        time.sleep(interval)

    print(f"\n[Watcher] 終了。累計処理: {len(manifest)}件")
    if manifest:
        print(f"  マニフェスト: {MANIFEST_PATH}")


# ── エントリポイント ─────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Mixamo FBX watcher")
    ap.add_argument("--interval", type=int, default=10, help="スキャン間隔(秒)")
    ap.add_argument("--duration", type=int, default=3600, help="監視時間(秒)")
    ap.add_argument("--once", action="store_true", help="1回だけスキャン")
    args = ap.parse_args()

    if args.once:
        manifest = _load_manifest()
        seen: set[Path] = set()
        n = scan_once(seen, manifest)
        if n:
            _save_manifest(manifest)
        print(f"[一回スキャン] {n}件処理")
    else:
        run(args.interval, args.duration)
