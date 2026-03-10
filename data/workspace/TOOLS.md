# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## RAG Knowledge Search

→ 詳細は **PORTAL_APPS.md の「★ 知識検索（RAG）」セクション** を参照（正典はそちら）。

```bash
python3 /home/node/clawd/rag_search.py "CETOL 6sigma tolerance stackup"
python3 /home/node/clawd/rag_search.py "質問文" --collection iatf_knowledge
```

---

## Web Search（SearXNG）

内部ネットワークの SearXNG でプライバシー保護済みの Web 検索が可能。

```bash
# Web検索（JSON形式）
curl -s "http://searxng:8080/search?q=YOUR+QUERY&format=json" \
  | python3 -c "import sys,json; [print(r['title'],r['url'],r.get('content','')[:100]) for r in json.load(sys.stdin).get('results',[])]"

# 例: IATF最新情報を検索
curl -s "http://searxng:8080/search?q=IATF+16949+2024+update&format=json&engines=google,bing" \
  | python3 -c "import sys,json; [print(r['title'],r['url']) for r in json.load(sys.stdin).get('results',[])[:5]]"
```

**用途**: RAG に含まれていない最新情報・製品情報・英語技術文書の発見。RAG 検索後に追加情報が必要な場合に使う。

---

## LLM観測（Langfuse）

全 LLM 呼び出しのトレース → `http://localhost:3001` で確認可能。
LiteLLM を経由した呼び出しは自動記録される（SDK: `pk-lf-clawstack-2026`）。

---

Add whatever helps you do your job. This is your cheat sheet.
