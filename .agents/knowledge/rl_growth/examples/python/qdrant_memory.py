"""
Qdrantへメモリ保存・検索する最小例
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


COLLECTION_NAME = "task_memories"


def get_qdrant() -> QdrantClient:
    return QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
    )


def get_openai_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("LITELLM_BASE_URL"),
        api_key=os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
    )


def embed_text(text: str) -> list[float]:
    client = get_openai_client()
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def ensure_collection(dim: int) -> None:
    qdrant = get_qdrant()
    exists = qdrant.collection_exists(COLLECTION_NAME)
    if not exists:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def make_memory_text(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"task_type: {payload.get('task_type', '')}",
            f"input_summary: {payload.get('input_summary', '')}",
            f"user_goal: {payload.get('user_goal', '')}",
            f"final_answer: {payload.get('final_answer', '')}",
            f"failure_tags: {payload.get('review', {}).get('failure_tags', [])}",
            f"success_tags: {payload.get('review', {}).get('success_tags', [])}",
        ]
    )


def store_memory(payload: dict[str, Any]) -> str:
    text = make_memory_text(payload)
    vector = embed_text(text)
    ensure_collection(len(vector))
    qdrant = get_qdrant()
    point_id = str(uuid.uuid4())
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )
    return point_id


def search_similar(query_text: str, limit: int = 5) -> list[Any]:
    qdrant = get_qdrant()
    vector = embed_text(query_text)
    return qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
    ).points
