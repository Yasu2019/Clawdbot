#!/usr/bin/env python3
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import unescape


JST = timezone(timedelta(hours=9))
USER_AGENT = "Mozilla/5.0 (compatible; ClawdbotTrendScout/1.0; +https://example.invalid)"
GOOGLE_TRENDS_RSS = "https://trends.google.com/trending/rss?geo=JP"
YAHOO_RANKING_NEWS = "https://news.yahoo.co.jp/ranking/access/news"
YAHOO_RANKING_VIDEO = "https://news.yahoo.co.jp/ranking/access/video"

THEMES = {
    "アニメ": "アニメ 人気",
    "アイドル": "アイドル 人気",
    "老後不安": "老後 不安",
    "趣味": "趣味 人気",
    "占い": "占い 人気",
}

PLATFORMS = {
    "YouTube": "site:youtube.com アニメ OR アイドル OR 趣味 OR 占い OR 老後",
    "note": "site:note.com アニメ OR アイドル OR 趣味 OR 占い OR 老後",
    "TikTok": "site:tiktok.com アニメ OR アイドル OR 趣味 OR 占い OR 老後",
    "X": "site:x.com アニメ OR アイドル OR 趣味 OR 占い OR 老後",
    "Instagram": "site:instagram.com アニメ OR アイドル OR 趣味 OR 占い OR 老後",
    "Threads": "site:threads.net アニメ OR アイドル OR 趣味 OR 占い OR 老後",
}


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def open_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_google_trends(limit: int = 8) -> list[str]:
    xml_text = open_text(GOOGLE_TRENDS_RSS)
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item")[:limit]:
        title = clean(item.findtext("title", default=""))
        traffic = clean(item.findtext("{https://trends.google.com/trending/rss}approx_traffic", default=""))
        suffix = f" ({traffic})" if traffic else ""
        if title:
            items.append(f"{title}{suffix}")
    return items


def fetch_google_news_search(query: str, limit: int = 3) -> list[dict]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "ja", "gl": "JP", "ceid": "JP:ja"}
    )
    xml_text = open_text(url)
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item")[:limit]:
        title = clean(item.findtext("title", default=""))
        link = clean(item.findtext("link", default=""))
        if title and link:
            items.append({"title": title, "url": link})
    return items


def fetch_yahoo_ranking(url: str, limit: int = 5) -> list[dict]:
    html = open_text(url)
    results = []
    seen = set()
    pattern = r'<a[^>]+href="(https://news\.yahoo\.co\.jp/articles/[^"]+)"[^>]*>(.*?)</a>'
    for href, title in re.findall(pattern, html, flags=re.I | re.S):
        title = clean(title)
        if not title or href in seen:
            continue
        seen.add(href)
        results.append({"title": title, "url": href})
        if len(results) >= limit:
            break
    return results


def build_monetization_opportunities(theme_hits: dict[str, list[dict]]) -> list[str]:
    ideas = []
    if theme_hits.get("アニメ"):
        ideas.append("アニメ: 新作まとめ、考察、比較、グッズ紹介、初心者向け解説の需要が見込めます。")
    if theme_hits.get("アイドル"):
        ideas.append("アイドル: ライブ日程整理、話題まとめ、SNS反応まとめ、グッズ比較に商機があります。")
    if theme_hits.get("老後不安"):
        ideas.append("老後不安: 家計チェック、制度解説、固定費見直し、Q&A型の情報発信が有望です。")
    if theme_hits.get("趣味"):
        ideas.append("趣味: 始め方、費用感、道具比較、初心者向け体験談が伸びやすい傾向です。")
    if theme_hits.get("占い"):
        ideas.append("占い: 毎日更新、相性診断、テーマ別ランキング、悩み別コンテンツに継続需要があります。")
    return ideas[:3]


def build_message() -> str:
    trends = fetch_google_trends()
    yahoo_news = fetch_yahoo_ranking(YAHOO_RANKING_NEWS)
    yahoo_video = fetch_yahoo_ranking(YAHOO_RANKING_VIDEO)
    theme_hits = {name: fetch_google_news_search(query, limit=2) for name, query in THEMES.items()}
    platform_hits = {name: fetch_google_news_search(query, limit=1) for name, query in PLATFORMS.items()}
    opportunities = build_monetization_opportunities(theme_hits)

    lines = [
        f"トレンド機会日報 ({now_jst()})",
        "",
        "■ Google Trends JP 上位",
    ]
    lines.extend([f"- {item}" for item in trends[:8]])
    lines.extend(["", "■ Yahooニュース アクセス上位"])
    lines.extend([f"- {item['title']}" for item in yahoo_news[:5]])
    lines.extend(["", "■ Yahoo動画 アクセス上位"])
    lines.extend([f"- {item['title']}" for item in yahoo_video[:3]])
    lines.append("")

    for theme, hits in theme_hits.items():
        lines.append(f"■ 関心テーマ: {theme}")
        if hits:
            lines.extend([f"- {item['title']}" for item in hits[:2]])
        else:
            lines.append("- 直近の公開シグナルなし")
        lines.append("")

    lines.append("■ プラットフォーム別 公開シグナル")
    for platform, hits in platform_hits.items():
        if hits:
            lines.append(f"- {platform}: {hits[0]['title']}")
        else:
            lines.append(f"- {platform}: 取得できる公開シグナルなし")
    lines.append("")

    lines.append("■ 稼げるチャンス候補")
    if opportunities:
        lines.extend([f"- {item}" for item in opportunities])
    else:
        lines.append("- 本日は強い機会候補が少ないため、Google Trends 上位から再検討してください。")
    lines.extend(
        [
            "",
            "参照元: Google Trends RSS / Google News RSS / Yahooニュース ランキング",
            "方針: 公開RSS・公開ランキング・公開ニュース検索のみを使用し、Instagram / X / TikTok / Threads の直接スクレイプは行いません。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = json.dumps({"message": build_message()}, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8"))


if __name__ == "__main__":
    main()
