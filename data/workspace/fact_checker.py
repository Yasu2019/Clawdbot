#!/usr/bin/env python3
"""
Fact Checker — SearXNG照合ツール
主要な事実的主張をSearXNGで検索し、裏付け・反証を返す。

使い方:
  python3 fact_checker.py "東京の人口は約1400万人である"
  python3 fact_checker.py --batch claims.txt
  echo "claim text" | python3 fact_checker.py -
"""
import sys, os, json, re, urllib.request, urllib.parse, argparse
from datetime import datetime, timezone

SEARXNG_URL = "http://searxng:8081"  # Docker内部。ホストからは http://localhost:8081

def searxng_search(query: str, num_results: int = 5) -> list[dict]:
    """SearXNGで検索し、結果リストを返す"""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "language": "ja-JP",
        "categories": "general",
    })
    url = f"{SEARXNG_URL}/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        return data.get("results", [])[:num_results]
    except Exception as e:
        return [{"error": str(e)}]


def extract_claims(text: str) -> list[str]:
    """テキストから事実的主張を抽出（数値・固有名詞・断定文を優先）"""
    sentences = re.split(r"[。．\.\!\?！？\n]", text)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        # 数値・パーセント・年号・固有名詞を含む文を優先
        if re.search(r'\d+|[A-Z]{2,}|(?:年|月|GB|MB|TB|km|kg|%)', s):
            claims.append(s)
        elif len(s) > 20:
            claims.append(s)
    return claims[:5]  # 最大5件


def check_claim(claim: str) -> dict:
    """1つの主張をSearXNGで照合"""
    results = searxng_search(claim)

    if results and "error" in results[0]:
        return {
            "claim": claim,
            "status": "error",
            "reason": results[0]["error"],
            "sources": [],
        }

    # 結果からサポート/矛盾の判定（簡易: タイトル+スニペットに主張のキーワードが含まれるか）
    keywords = [w for w in re.split(r'[\s、。,]', claim) if len(w) >= 3]
    supporting = []
    for r in results:
        title = r.get("title", "")
        snippet = r.get("content", "")
        combined = (title + snippet).lower()
        hit = sum(1 for kw in keywords if kw.lower() in combined)
        if hit >= max(1, len(keywords) // 2):
            supporting.append({
                "title": title[:80],
                "url": r.get("url", ""),
                "snippet": snippet[:150],
            })

    status = "supported" if supporting else "unverified"
    return {
        "claim": claim,
        "status": status,
        "supporting_sources": supporting[:3],
        "total_results": len(results),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def fact_check(text: str, verbose: bool = True) -> list[dict]:
    """テキスト全体をファクトチェック"""
    claims = extract_claims(text)
    if not claims:
        claims = [text[:300]]  # 短文はそのままチェック

    results = []
    for i, claim in enumerate(claims, 1):
        if verbose:
            print(f"[{i}/{len(claims)}] 照合中: {claim[:60]}...")
        result = check_claim(claim)
        results.append(result)
        if verbose:
            icon = "✅" if result["status"] == "supported" else ("❌" if result["status"] == "error" else "⚠️")
            print(f"  {icon} {result['status']} ({result.get('total_results', 0)}件の検索結果)")
            for s in result.get("supporting_sources", [])[:2]:
                print(f"    → {s['title']}")
    return results


def main():
    global SEARXNG_URL
    parser = argparse.ArgumentParser(description="SearXNG Fact Checker")
    parser.add_argument("text", nargs="?", help="チェックするテキスト（'-'でstdin）")
    parser.add_argument("--batch", metavar="FILE", help="1行1主張のテキストファイル")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--url", default=SEARXNG_URL, help=f"SearXNG URL (default: {SEARXNG_URL})")
    args = parser.parse_args()

    SEARXNG_URL = args.url

    if args.batch:
        with open(args.batch) as f:
            texts = [l.strip() for l in f if l.strip()]
    elif args.text == "-":
        texts = [sys.stdin.read()]
    elif args.text:
        texts = [args.text]
    else:
        parser.print_help()
        sys.exit(1)

    all_results = []
    for text in texts:
        results = fact_check(text, verbose=not args.json)
        all_results.extend(results)

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== ファクトチェック完了 ===")
        supported = sum(1 for r in all_results if r["status"] == "supported")
        unverified = sum(1 for r in all_results if r["status"] == "unverified")
        errors = sum(1 for r in all_results if r["status"] == "error")
        print(f"✅ 裏付けあり: {supported}件 / ⚠️ 未確認: {unverified}件 / ❌ エラー: {errors}件")


if __name__ == "__main__":
    main()
