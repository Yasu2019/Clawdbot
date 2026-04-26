import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
import sys
import traceback

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
    try:
        html = fetch_text(url)
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
        page_title = clean_text(title_match.group(1)) if title_match else url
        results = [{"title": page_title, "url": url}]

        hrefs = re.findall(r'href="([^"]+)"', html, flags=re.I)
        for href in hrefs:
            if href.startswith("/"):
                # Handle base URL reconstruction
                parts = url.split("//")
                if len(parts) > 1:
                    base = parts[0] + "//" + parts[1].split("/")[0]
                    href = base + href
            if not href.startswith("http"):
                continue
            if link_pattern and not re.search(link_pattern, href, flags=re.I):
                continue
            if any(token in href for token in ["static", "assets", "fonts", "mailto:", "x.com", "twitter.com", "facebook.com", "linkedin.com"]):
                continue
            results.append({"title": href.rsplit("/", 1)[-1] or href, "url": href})
            if len(results) >= limit + 1:
                break
        return unique_results(results)[:limit + 1]
    except:
        return []

def extract_rss(url: str, limit: int = 3) -> list[dict]:
    try:
        raw = fetch_text(url)
        root = ET.fromstring(raw)
        results = []
        # Support RSS <item> and Atom <entry>
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for item in items[:limit]:
            title_node = item.find("title") or item.find("{http://www.w3.org/2005/Atom}title")
            link_node = item.find("link") or item.find("{http://www.w3.org/2005/Atom}link")
            
            title = clean_text(title_node.text) if title_node is not None else ""
            link = ""
            if link_node is not None:
                link = link_node.text or link_node.get("href") or ""
            
            if title and link:
                results.append({"title": title, "url": link})
        return unique_results(results)
    except:
        return []

def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

    sources_to_check = [
        # --- AI Corporate Intel ---
        {"category": "Global Corporate Intel (US)", "source": "OpenAI / News", "url": "https://openai.com/news", "pattern": r"openai\.com/index/", "type": "links"},
        {"category": "Global Corporate Intel (US)", "source": "Anthropic / News", "url": "https://www.anthropic.com/news", "pattern": r"anthropic\.com/news/", "type": "links"},
        {"category": "Global Corporate Intel (US)", "source": "DeepMind / Blog", "url": "https://deepmind.google/discover/blog/", "pattern": r"deepmind\.google/discover/blog/", "type": "links"},
        {"category": "Asia-Pacific AI Trends", "source": "Sakana AI / News", "url": "https://sakana.ai/blog/", "pattern": r"sakana\.ai/blog/", "type": "links"},
        
        # --- Global FEM & Simulation Intel ---
        {"category": "Global FEM & Simulation Intel", "source": "OpenFOAM News", "url": "https://www.openfoam.com/news", "pattern": r"openfoam\.com/news/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "FEniCS Project", "url": "https://fenicsproject.org/news/", "pattern": r"fenicsproject\.org/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "MFEM News", "url": "https://mfem.org/news/", "pattern": r"mfem\.org/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "deal.II News", "url": "https://www.dealii.org/news.html", "pattern": r"dealii\.org/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "SU2 Foundation", "url": "https://su2foundation.org/news/", "pattern": r"su2foundation\.org/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "OpenRadioss Releases", "url": "https://github.com/OpenRadioss/OpenRadioss/releases.atom", "type": "rss"},
        {"category": "Global FEM & Simulation Intel", "source": "PrePoMax News", "url": "https://prepomax.fs.um.si/news/", "pattern": r"prepomax\.fs\.um\.si/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "Code_Aster", "url": "https://www.code-aster.org/", "pattern": r"code-aster\.org/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "CalculiX", "url": "http://www.calculix.de/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "Elmer FEM", "url": "https://www.csc.fi/web/elmer", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "MOOSE Framework", "url": "https://mooseframework.inl.gov/news.html", "pattern": r"mooseframework\.inl\.gov/", "type": "links"},
        {"category": "Global FEM & Simulation Intel", "source": "SimScale Blog", "url": "https://www.simscale.com/blog/", "type": "links"},
    ]

    results_payload = []
    for s in sources_to_check:
        items = []
        try:
            if s["type"] == "links":
                items = extract_homepage_links(s["url"], link_pattern=s.get("pattern"))
            else:
                items = extract_rss(s["url"])
        except:
            pass
        results_payload.append({"category": s["category"], "source": s["source"], "results": items})

    print(json.dumps({"sources": results_payload}, ensure_ascii=False))

if __name__ == "__main__":
    main()
