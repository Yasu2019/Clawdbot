#!/usr/bin/env python3
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape


USER_AGENT = "Mozilla/5.0 (compatible; ClawdbotAI/1.0; +https://example.invalid)"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_results(results: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in results:
        key = (item.get("title", ""), item.get("url", ""))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def extract_homepage_links(url: str, link_pattern: str | None = None, limit: int = 3) -> list[dict]:
    html = fetch_text(url)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    page_title = clean_text(title_match.group(1)) if title_match else url
    results = [{"title": page_title, "url": url}]

    hrefs = re.findall(r'href="([^"]+)"', html, flags=re.I)
    for href in hrefs:
        if href.startswith("/"):
            base = url.rstrip("/")
            href = base + href
        if not href.startswith("http"):
            continue
        if link_pattern and not re.search(link_pattern, href, flags=re.I):
            continue
        if any(token in href for token in ["static", "assets", "fonts", "mailto:", "x.com", "twitter.com"]):
            continue
        results.append({"title": href.rsplit("/", 1)[-1] or href, "url": href})
        if len(results) >= limit + 1:
            break
    return unique_results(results)[:limit + 1]


def extract_rss(url: str, limit: int = 3) -> list[dict]:
    raw = fetch_text(url)
    root = ET.fromstring(raw)
    results = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(item.findtext("title", default=""))
        link = clean_text(item.findtext("link", default=""))
        if title and link:
            results.append({"title": title, "url": link})
    return unique_results(results)


def main() -> None:
    payload = {
        "sources": [
            {
                "category": "公式サイト / ニュースレター",
                "source": "Rowan Cheung / The Rundown AI",
                "results": extract_homepage_links(
                    "https://rowancheung.com/",
                    link_pattern=r"rowancheung\\.com|rundown\\.ai|therundown\\.ai",
                ),
            },
            {
                "category": "公式サイト / ニュースレター",
                "source": "Ethan Mollick / One Useful Thing",
                "results": extract_homepage_links(
                    "https://www.oneusefulthing.org/",
                    link_pattern=r"oneusefulthing\\.org",
                ),
            },
            {
                "category": "公式プロフィール / ブログ",
                "source": "Allie K. Miller",
                "results": extract_homepage_links(
                    "https://www.alliekmiller.com/",
                    link_pattern=r"alliekmiller\\.com/(resources|courses|home|$)|youtube\\.com/@AKMofficial",
                ),
            },
            {
                "category": "公式プロフィール / ブログ",
                "source": "Logan Kilpatrick / Google Blog",
                "results": extract_rss("https://blog.google/authors/logan-kilpatrick/rss/"),
            },
        ]
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
