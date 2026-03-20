#!/usr/bin/env python3
"""
clawstack_mcp_server.py
Clawstack 統合 MCP HTTP サーバー (FastMCP streamable-http)

提供ツール:
  - rag_search    : Qdrant universal_knowledge / iatf_knowledge 検索
  - web_search    : SearXNG 経由 Web 検索

起動: python3 /home/node/clawd/clawstack_mcp_server.py
Port: 9876 (内部ネットワーク)
"""

import os
import sys
import time
import json
import requests
from mcp.server.fastmcp import FastMCP

# tracing ユーティリティ — 利用不可でも起動継続
try:
    sys.path.insert(0, "/home/node/clawd")
    from clawstack_tracing import ClawTrace, _get_client as _lf_client
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

INFINITY_URL  = os.getenv("INFINITY_URL",  "http://infinity:7997")
QDRANT_URL    = os.getenv("QDRANT_URL",    "http://qdrant:6333")
SEARXNG_URL   = os.getenv("SEARXNG_URL",   "http://searxng:8080")
OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://ollama:11434")
TRANSLATE_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")
EMBED_MODEL   = "mxbai-embed-large-v1"
DEFAULT_COLL  = "universal_knowledge"

import logging
logger = logging.getLogger("clawstack_mcp")

mcp = FastMCP("clawstack-tools")


def _translate_query(query: str, collection: str) -> str:
    """
    日本語クエリを英語に翻訳して RAG スコアを向上させる。
    CETOL/FEM コンテンツは英語で取り込まれているため英語クエリが有効。
    失敗時は元のクエリをそのまま返す（本体処理に影響させない）。
    """
    has_japanese = any('\u3040' <= c <= '\u9fff' for c in query)
    if not has_japanese or collection == "iatf_knowledge":
        return query
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": TRANSLATE_MODEL,
                "prompt": (
                    "Translate this Japanese technical query to English. "
                    "Return only the translation, no explanation:\n" + query
                ),
                "stream": False,
                "options": {"num_predict": 80, "temperature": 0.1},
            },
            timeout=15,
        )
        resp.raise_for_status()
        en_query = resp.json().get("response", "").strip()
        if en_query and len(en_query) > 3:
            logger.info(f"[rag] translated: '{query}' → '{en_query}'")
            return en_query
    except Exception as e:
        logger.warning(f"[rag] translation failed: {e}")
    return query


def _embed(text: str) -> tuple[list[float], float]:
    """テキストを Infinity でベクトル化。(vector, ms) を返す。"""
    t0 = time.monotonic()
    resp = requests.post(
        f"{INFINITY_URL}/embeddings",
        json={"model": EMBED_MODEL, "input": [text]},
        timeout=60,
    )
    resp.raise_for_status()
    ms = (time.monotonic() - t0) * 1000
    return resp.json()["data"][0]["embedding"], ms


@mcp.tool()
def rag_search(
    query: str,
    collection: str = "universal_knowledge",
    top_k: int = 5,
) -> str:
    """
    Qdrant ベクトルDBを検索して関連ナレッジを返す。
    技術的な質問（FMEA・公差解析・FEM・IATF等）に必ず使うこと。

    Args:
        query:      検索クエリ（英語または混合推奨）
        collection: "universal_knowledge" (FMEA/CETOL/FEM/5Why) または "iatf_knowledge" (IATF 16949)
        top_k:      取得件数（デフォルト5、最大20）
    """
    top_k = min(int(top_k), 20)
    embed_ms = 0.0
    search_ms = 0.0

    # P3: 日本語クエリを英語に翻訳して CETOL/FEM スコアを向上
    translated_query = _translate_query(query, collection)

    try:
        vector, embed_ms = _embed(translated_query)
    except Exception as e:
        result = f"[ERROR] Embedding失敗: {e}"
        return result

    try:
        t0 = time.monotonic()
        resp = requests.post(
            f"{QDRANT_URL}/collections/{collection}/points/search",
            json={"vector": vector, "limit": top_k, "with_payload": True},
            timeout=30,
        )
        resp.raise_for_status()
        search_ms = (time.monotonic() - t0) * 1000
        results = resp.json().get("result", [])
    except Exception as e:
        result = f"[ERROR] Qdrant検索失敗: {e}"
        return result

    top_score = results[0].get("score", 0.0) if results else 0.0

    if not results:
        result = f"[結果なし] collection={collection} でクエリ '{query}' に一致する文書が見つかりません。クエリを英語に変えて再検索してください。"
    else:
        lines = [f"## RAG検索結果: '{query}' (collection={collection}, {len(results)}件)\n"]
        for i, r in enumerate(results, 1):
            score   = r.get("score", 0)
            payload = r.get("payload", {})
            text    = payload.get("text", "")[:400]
            source  = payload.get("source", "")
            fname   = payload.get("filename", "")
            lines.append(
                f"### [{i}] スコア={score:.3f} | {source} / {fname}\n{text}\n"
            )
        result = "\n".join(lines)

    # Langfuse トレーシング（失敗しても本体継続）
    if TRACING_AVAILABLE:
        try:
            trace = ClawTrace(name="mcp.rag_search").start()
            trace.span_rag(
                query=query,
                result=result,
                collection=collection,
                top_score=top_score,
                embed_ms=embed_ms,
                search_ms=search_ms,
                result_count=len(results),
                translated_query=translated_query if translated_query != query else None,
            )
            trace.end(output=f"top_score={top_score:.3f}, count={len(results)}")
        except Exception:
            pass

    return result


@mcp.tool()
def web_search(
    query: str,
    num_results: int = 5,
    engines: str = "google,bing,duckduckgo",
) -> str:
    """
    SearXNG 経由でプライベートWeb検索を実行する。
    RAGに含まれない最新情報・製品情報・英語技術文書の発見に使う。
    RAG検索で情報が不足した場合の補完として使うこと。

    Args:
        query:       検索クエリ
        num_results: 取得件数（デフォルト5）
        engines:     使用する検索エンジン（カンマ区切り）
    """
    t0 = time.monotonic()
    try:
        resp = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "engines": engines},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])[:num_results]
        latency_ms = (time.monotonic() - t0) * 1000
    except Exception as e:
        return f"[ERROR] SearXNG検索失敗: {e}"

    if not results:
        result = f"[結果なし] '{query}' に一致するWeb検索結果がありません。"
    else:
        lines = [f"## Web検索結果: '{query}' ({len(results)}件)\n"]
        for i, r in enumerate(results, 1):
            title   = r.get("title", "")
            url     = r.get("url", "")
            content = r.get("content", "")[:200]
            lines.append(f"### [{i}] {title}\nURL: {url}\n{content}\n")
        result = "\n".join(lines)
        latency_ms = (time.monotonic() - t0) * 1000

    # Langfuse トレーシング
    if TRACING_AVAILABLE:
        try:
            trace = ClawTrace(name="mcp.web_search").start()
            trace.span_web_search(
                query=query,
                result=result,
                engines=engines,
                result_count=len(results),
                latency_ms=latency_ms,
            )
            trace.end(output=f"count={len(results)}")
        except Exception:
            pass

    return result


@mcp.tool()
def email_search(
    query: str,
    limit: int = 5,
) -> str:
    """
    Local email_search.db (EML + Gmail) を検索して関連メール文脈を返す。
    """
    import sqlite3

    db_path = os.getenv("EMAIL_SEARCH_DB", "/home/node/clawd/email_search.db")
    limit = min(max(int(limit), 1), 10)
    con = None
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        rows = []
        try:
            rows = con.execute(
                """
                SELECT
                    e.source,
                    e.subject,
                    e.sender,
                    e.email_date,
                    e.snippet,
                    bm25(emails_fts) AS score
                FROM emails_fts
                JOIN emails e ON e.rowid = emails_fts.rowid
                WHERE emails_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            terms = [t for t in query.split() if t] or [query]
            clauses = []
            params = []
            for term in terms:
                clauses.append("(subject LIKE ? OR sender LIKE ? OR body_text LIKE ?)")
                needle = f"%{term}%"
                params.extend([needle, needle, needle])
            params.append(limit)
            rows = con.execute(
                f"""
                SELECT
                    source,
                    subject,
                    sender,
                    email_date,
                    snippet,
                    0.0 AS score
                FROM emails
                WHERE {' AND '.join(clauses)}
                ORDER BY internal_ts DESC, indexed_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        if not rows:
            rows = con.execute(
                """
                SELECT
                    source,
                    subject,
                    sender,
                    email_date,
                    snippet,
                    0.0 AS score
                FROM emails
                ORDER BY internal_ts DESC, indexed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        lines = [f"## Email search: '{query}' ({len(rows)} results)\n"]
        for idx, row in enumerate(rows, 1):
            snippet = " ".join((row["snippet"] or "").split())
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            lines.append(
                f"### [{idx}] {row['email_date']} | {row['source']} | from={row['sender']} | subject={row['subject']}\n{snippet}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] email_search failed: {e}"
    finally:
        if con is not None:
            con.close()


@mcp.tool()
def email_tasks(
    query: str,
    limit: int = 5,
) -> str:
    """
    Local email_search.db の tasks テーブルを検索して、期限・依頼事項・回答状況を返す。
    """
    import sqlite3
    import subprocess

    limit = min(max(int(limit), 1), 10)
    db_path = os.getenv("EMAIL_SEARCH_DB", "/home/node/clawd/email_search.db")
    script_path = os.getenv("EMAIL_SEARCH_QUERY", "/home/node/clawd/email_search_query.py")
    try:
        proc = subprocess.run(
            ["python3", script_path, "--db", db_path, "tasks-context", query, "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        payload = json.loads(proc.stdout or "{}")
        summary = payload.get("summary") or "該当する依頼事項は見つかりませんでした。"
        context = payload.get("context") or ""
        if context:
            return f"{summary}\n\n{context}"
        return summary
    except subprocess.CalledProcessError as e:
        return f"[ERROR] email_tasks failed: {e.stderr or e.stdout or e}"
    except Exception as e:
        return f"[ERROR] email_tasks failed: {e}"


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "9876"))
    print(f"[clawstack-mcp] Starting streamable-http on 127.0.0.1:{port}", flush=True)
    print(f"[clawstack-mcp] Tracing: {'enabled' if TRACING_AVAILABLE else 'disabled'}", flush=True)
    # FastMCP 1.26.0: host/port set in constructor settings
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
