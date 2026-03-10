#!/usr/bin/env python3
"""
clawstack_tracing.py
Langfuse v3 トレーシング ユーティリティ (Clawstack 統合)

Langfuse SDK v3.x API:
  lf.start_span(name, input)           → LangfuseSpan (root span = new trace)
  span.start_span(name, input, output, metadata) → child LangfuseSpan
  span.end()                            → close span (no args)
  span.update(output=..., metadata=...) → set output/metadata before end
  span.score(name, value, comment)      → score on this span's trace
  lf.flush()                            → batch送信

注意: Langfuse 初回利用前に http://localhost:3001 でサインアップし API キーを
      環境変数 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY に設定してください。
"""

import os
import uuid
import logging

logger = logging.getLogger("clawstack_tracing")

LANGFUSE_HOST       = os.getenv("LANGFUSE_HOST",       "http://langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-07926c92-5480-4fb5-ae97-39e35a0a0ce5")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-9b4e86b1-ec3b-4826-aca7-b20bd68b1bd8")

_langfuse_client = None


def _get_client():
    """Langfuse v3 クライアントをシングルトンで返す。失敗時は None。"""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
    except Exception as e:
        logger.warning(f"[tracing] Langfuse unavailable: {e}")
    return _langfuse_client


class ClawTrace:
    """
    Langfuse v3 root span ラッパー。各 MCP ツール呼び出しの親。

    使い方 (context manager):
        with ClawTrace("rag_session", request_id="req-123") as t:
            t.span_rag(query="...", result="...", top_score=0.8)

    または手動:
        t = ClawTrace("rag_session").start()
        t.span_rag(...)
        t.end()
    """

    def __init__(
        self,
        name: str = "clawstack_session",
        metadata: dict = None,
        request_id: str = None,
        session_id: str = None,
        user_id: str = "openclaw",
    ):
        self.name       = name
        self.metadata   = metadata or {}
        self.request_id = request_id or str(uuid.uuid4())
        self.session_id = session_id
        self.user_id    = user_id
        self._lf        = None
        self._root      = None   # root LangfuseSpan

    def start(self):
        self._lf = _get_client()
        if self._lf is None:
            return self
        try:
            combined_input = {
                **self.metadata,
                "request_id": self.request_id,
                "user_id":    self.user_id,
            }
            if self.session_id:
                combined_input["session_id"] = self.session_id
            self._root = self._lf.start_span(
                name=self.name,
                input=combined_input,
            )
        except Exception as e:
            logger.warning(f"[tracing] start_span failed: {e}")
            self._root = None
        return self

    def end(self, output: str = None):
        if self._root is not None:
            try:
                if output:
                    self._root.update(output=output)
                self._root.end()
                self._lf.flush()
            except Exception as e:
                logger.warning(f"[tracing] span.end failed: {e}")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(output="ERROR" if exc_type else "SUCCESS")
        return False

    # ---- child span helpers ----------------------------------------

    def span_rag(
        self,
        query: str,
        result: str,
        collection: str = "universal_knowledge",
        top_score: float = 0.0,
        embed_ms: float = 0.0,
        search_ms: float = 0.0,
        result_count: int = 0,
        translated_query: str = None,
    ):
        """RAG 検索 child span を記録する。"""
        if self._root is None:
            return
        try:
            meta = {
                "top_score":    round(top_score, 4),
                "embed_ms":     round(embed_ms, 1),
                "search_ms":    round(search_ms, 1),
                "embed_model":  "mxbai-embed-large-v1",
                "request_id":   self.request_id,
            }
            if translated_query and translated_query != query:
                meta["translated_query"] = translated_query
            child = self._root.start_span(
                name="mcp.rag_search",
                input={"query": query, "collection": collection},
                output={"result_count": result_count, "preview": result[:200]},
                metadata=meta,
            )
            child.end()
            if top_score > 0:
                self._root.score(
                    name="rag_relevance",
                    value=round(top_score, 4),
                    comment=f"collection={collection} query={query[:60]}",
                )
        except Exception as e:
            logger.warning(f"[tracing] span_rag failed: {e}")

    def span_web_search(
        self,
        query: str,
        result: str,
        engines: str = "",
        result_count: int = 0,
        latency_ms: float = 0.0,
    ):
        """Web 検索 child span を記録する。"""
        if self._root is None:
            return
        try:
            child = self._root.start_span(
                name="mcp.web_search",
                input={"query": query, "engines": engines},
                output={"result_count": result_count, "preview": result[:200]},
                metadata={"latency_ms": round(latency_ms, 1), "request_id": self.request_id},
            )
            child.end()
        except Exception as e:
            logger.warning(f"[tracing] span_web_search failed: {e}")

    def span_n8n(
        self,
        workflow_id: str,
        payload: dict,
        result: str,
        status: str = "success",
        latency_ms: float = 0.0,
    ):
        """n8n ワークフロー実行 child span を記録する。"""
        if self._root is None:
            return
        try:
            child = self._root.start_span(
                name="n8n.execute_workflow",
                input={"workflow_id": workflow_id, "payload_keys": list(payload.keys())},
                output={"status": status, "preview": str(result)[:200]},
                metadata={"latency_ms": round(latency_ms, 1), "request_id": self.request_id},
            )
            child.end()
        except Exception as e:
            logger.warning(f"[tracing] span_n8n failed: {e}")


# ---- standalone functions ----------------------------------------

def record_rag_quality(query: str, top_score: float, collection: str = "universal_knowledge"):
    """RAG 品質スコアを Langfuse に単体で記録する。"""
    lf = _get_client()
    if lf is None:
        return
    try:
        span = lf.start_span(name="rag_quality_check", input={"query": query})
        span.score(name="rag_relevance", value=round(top_score, 4),
                   comment=f"collection={collection}")
        span.update(output={"top_score": top_score})
        span.end()
        lf.flush()
    except Exception as e:
        logger.warning(f"[tracing] record_rag_quality failed: {e}")


def health_check() -> dict:
    """Langfuse への接続状態を返す。"""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{LANGFUSE_HOST}/api/public/health", timeout=3) as r:
            body = r.read().decode()
        return {"status": "ok", "host": LANGFUSE_HOST, "response": body[:100]}
    except Exception as e:
        return {"status": "error", "host": LANGFUSE_HOST, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    print("[test] health check:", health_check())
    req_id = str(uuid.uuid4())
    print(f"[test] request_id: {req_id}")
    with ClawTrace(name="selftest", request_id=req_id, session_id="test-session") as t:
        t.span_rag(query="CETOL 6sigma tolerance stackup", result="test", top_score=0.75,
                   embed_ms=50, search_ms=10, result_count=3, translated_query="CETOL 6sigma")
        t.span_web_search(query="IATF 16949", result="test", engines="google",
                          result_count=2, latency_ms=280)
    print("[test] done — check Langfuse UI at http://localhost:3001")
