"""photo_bg_compositor.py — 写真APIから都市背景を取得してZakuと合成する。

Pexels / Pixabay から横長の都市写真を検索・DLし、
Blender 2パスのアルファマスクを使って Zaku を写真上に配置する。
24h キャッシュあり。
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV = ROOT / ".env"
USER_AGENT = "CityCharacterPipeline/1.0 (local research workflow)"


# ══════════════════════════════════════════════════════════════
# .env ローダー
# ══════════════════════════════════════════════════════════════

def _read_env(path: Path) -> dict:
    env: dict = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


# ══════════════════════════════════════════════════════════════
# HTTP ユーティリティ
# ══════════════════════════════════════════════════════════════

def _request_json(url: str, headers: Optional[dict] = None, timeout: int = 30) -> dict:
    req_headers: dict = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download_image(url: str, output_path: Path, timeout: int = 60) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        output_path.write_bytes(resp.read())


# ══════════════════════════════════════════════════════════════
# API 検索
# ══════════════════════════════════════════════════════════════

def _search_pexels(query: str, api_key: str, limit: int = 5) -> list:
    params = {"query": query, "per_page": str(limit), "orientation": "landscape"}
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(params)
    data = _request_json(url, headers={"Authorization": api_key})
    results = []
    for photo in data.get("photos", []):
        src = photo.get("src") or {}
        results.append({
            "source": "pexels",
            "id": str(photo.get("id", "")),
            "image_url": src.get("large2x") or src.get("large") or src.get("original", ""),
            "width": photo.get("width", 0),
            "height": photo.get("height", 0),
            "author": photo.get("photographer", ""),
            "page_url": photo.get("url", ""),
        })
    return results


def _search_pixabay(query: str, api_key: str, limit: int = 5) -> list:
    params = {
        "key": api_key,
        "q": query,
        "per_page": str(max(3, limit)),
        "image_type": "photo",
        "orientation": "horizontal",
        "safesearch": "true",
    }
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(params)
    data = _request_json(url)
    results = []
    for photo in data.get("hits", [])[:limit]:
        results.append({
            "source": "pixabay",
            "id": str(photo.get("id", "")),
            "image_url": photo.get("largeImageURL") or photo.get("webformatURL", ""),
            "width": photo.get("imageWidth", 0),
            "height": photo.get("imageHeight", 0),
            "author": photo.get("user", ""),
            "page_url": photo.get("pageURL", ""),
        })
    return results


# ══════════════════════════════════════════════════════════════
# 公開 API
# ══════════════════════════════════════════════════════════════

def fetch_city_photo(
    query: str,
    output_dir: Path,
    sources: str = "pexels,pixabay",
    env_path: Path = DEFAULT_ENV,
    cache_hours: int = 24,
) -> Optional[Path]:
    """都市写真を検索・ダウンロードしてローカルパスを返す。

    24h キャッシュあり（同クエリなら再 DL しない）。
    失敗時は None を返す（後処理をスキップするだけ）。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_meta = output_dir / "photo_bg_cache.json"

    # キャッシュ確認
    if cache_meta.exists():
        try:
            meta = json.loads(cache_meta.read_text(encoding="utf-8"))
            cached_path = Path(meta.get("local_path", ""))
            age_hours = (time.time() - meta.get("downloaded_at", 0)) / 3600
            if cached_path.exists() and age_hours < cache_hours and meta.get("query") == query:
                print(f"[PhotoBg] Cache hit ({age_hours:.1f}h old): {cached_path.name}", flush=True)
                return cached_path
        except Exception:
            pass

    env = _read_env(env_path)
    pexels_key  = env.get("PEXELS_API_KEY", "")
    pixabay_key = env.get("PIXABAY_API_KEY", "")

    source_list = [s.strip().lower() for s in sources.split(",") if s.strip()]
    candidates: list = []

    for source in source_list:
        try:
            if source == "pexels" and pexels_key:
                found = _search_pexels(query, pexels_key)
                candidates.extend(found)
                print(f"[PhotoBg] Pexels: {len(found)} hits", flush=True)
            elif source == "pixabay" and pixabay_key:
                found = _search_pixabay(query, pixabay_key)
                candidates.extend(found)
                print(f"[PhotoBg] Pixabay: {len(found)} hits", flush=True)
        except Exception as e:
            print(f"[PhotoBg] {source} search error: {e}", flush=True)

    if not candidates:
        print("[PhotoBg] No candidates found — photo composite skipped", flush=True)
        return None

    # 横長かつ最大解像度の写真を選択
    def _score(item: dict) -> float:
        w, h = item.get("width", 0), item.get("height", 0)
        if h == 0:
            return 0.0
        ratio = w / h
        if ratio < 1.2:
            return 0.0  # 縦長除外
        return float(w * h)

    best = max(candidates, key=_score)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{best['source']}_{best['id']}")[:80]
    local_path = output_dir / f"photo_bg_{slug}.jpg"

    print(f"[PhotoBg] Downloading: {best['source']} id={best['id']} {best.get('width')}x{best.get('height')}", flush=True)
    try:
        _download_image(best["image_url"], local_path)
    except Exception as e:
        print(f"[PhotoBg] Download failed: {e}", flush=True)
        return None

    cache_meta.write_text(json.dumps({
        "query": query,
        "local_path": str(local_path),
        "source": best["source"],
        "id": best["id"],
        "author": best.get("author", ""),
        "page_url": best.get("page_url", ""),
        "downloaded_at": time.time(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[PhotoBg] Saved: {local_path.name}", flush=True)
    return local_path


def composite_zaku_on_photo(
    bg_path: Path,
    full_path: Path,
    photo_path: Path,
) -> Image.Image:
    """実写写真の上に Blender レンダーの Zaku を合成する。

    bg_path:    Pass A RGBA (Zaku=alpha 0, 背景=alpha 255)
    full_path:  Pass B RGB  (Zaku込み通常レンダー)
    photo_path: 実写都市写真 (RGB)

    戻り値: RGB — 背景=実写写真 / Zaku=Blender レンダー由来
    """
    bg_rgba  = Image.open(bg_path).convert("RGBA")
    full_rgb = Image.open(full_path).convert("RGB")
    photo    = Image.open(photo_path).convert("RGB")

    target_size = bg_rgba.size  # Blender レンダー解像度に合わせる

    # 写真をレンダー解像度にリサイズ（クロップして比率維持）
    photo = _fit_cover(photo, target_size)
    if full_rgb.size != target_size:
        full_rgb = full_rgb.resize(target_size, Image.LANCZOS)

    alpha_mask = bg_rgba.split()[3]  # 255=背景, 0=Zaku

    # composite(img1, img2, mask): mask=255→img1, mask=0→img2
    composite = Image.composite(photo, full_rgb, alpha_mask)
    print(
        f"[PhotoBg] Composite OK: {target_size[0]}x{target_size[1]} (photo={photo_path.name})",
        flush=True,
    )
    return composite


def _fit_cover(img: Image.Image, target: tuple) -> Image.Image:
    """アスペクト比を維持したまま target サイズにクロップフィットする。"""
    tw, th = target
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top  = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))
