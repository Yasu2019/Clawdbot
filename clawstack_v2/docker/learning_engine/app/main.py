from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def qdrant_point_id(source_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, source_id))


class Settings(BaseModel):
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "").rstrip("/")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "bge-small-en-v1.5")
    embedding_size: int = int(os.getenv("EMBEDDING_SIZE", "256"))
    memory_top_k: int = int(os.getenv("MEMORY_TOP_K", "8"))
    include_cross_org_default: bool = os.getenv("INCLUDE_CROSS_ORG_DEFAULT", "false").lower() == "true"


settings = Settings()
WORKSPACE_PATH = Path("/workspace")


class CaseIngestRequest(BaseModel):
    case_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="manual")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    title: str
    summary: str = ""
    lot_no: str | None = None
    part_number: str | None = None
    process: str | None = None
    defect_name: str | None = None
    symptom: str | None = None
    containment_action: str | None = None
    suspected_root_cause: str | None = None
    permanent_action: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class QualityIssueIngestRequest(BaseModel):
    issue_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="manual")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    title: str
    summary: str = ""
    lot_no: str | None = None
    part_number: str | None = None
    process: str | None = None
    defect_name: str | None = None
    symptom: str | None = None
    containment_action: str | None = None
    suspected_root_cause: str | None = None
    permanent_action: str | None = None
    due_date: str | None = None
    owner: str | None = None
    verification_result: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ImprovementActivityIngestRequest(BaseModel):
    activity_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="manual")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    title: str
    summary: str = ""
    target_process: str | None = None
    trigger_issue: str | None = None
    before_state: str | None = None
    after_state: str | None = None
    change_type: str | None = None
    expected_effect: str | None = None
    measured_effect: str | None = None
    side_effect: str | None = None
    rollout_scope: str | None = None
    horizontal_deployment: str | None = None
    result_status: str | None = None
    owner: str | None = None
    verification_result: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class EmailMessageIngestRequest(BaseModel):
    message_id: str | None = None
    thread_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="email")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    subject: str
    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    sent_at: str | None = None
    summary: str = ""
    body_excerpt: str | None = None
    extracted_facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    latest_status: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class EmailThreadIngestRequest(BaseModel):
    thread_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="email")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    subject: str
    participants: list[str] = Field(default_factory=list)
    summary: str = ""
    open_questions: list[str] = Field(default_factory=list)
    latest_status: str | None = None
    next_action: str | None = None
    related_case_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class CaeRunIngestRequest(BaseModel):
    run_id: str | None = None
    source_org: str = Field(default="unknown")
    source_type: str = Field(default="cae_log")
    confidentiality: str = Field(default="internal")
    reuse_scope: str = Field(default="same_org_only")
    review_status: str = Field(default="draft")
    tool_name: str
    tool_version: str | None = None
    simulation_type: str | None = None
    project_name: str | None = None
    material: str | None = None
    geometry_type: str | None = None
    mesh_size: str | None = None
    element_type: str | None = None
    contact_type: str | None = None
    friction: str | None = None
    time_step: str | None = None
    solver_settings: str | None = None
    boundary_conditions: str | None = None
    initial_conditions: str | None = None
    result_status: str = Field(default="partial")
    failure_mode: str | None = None
    error_signature: str | None = None
    wall_clock_time: str | None = None
    output_files: list[str] = Field(default_factory=list)
    summary: str = ""
    lesson: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class CompareCaseRequest(BaseModel):
    source_org: str = Field(default="unknown")
    include_cross_org: bool | None = None
    top_k: int | None = None
    title: str
    summary: str = ""
    process: str | None = None
    defect_name: str | None = None
    symptom: str | None = None
    suspected_root_cause: str | None = None
    permanent_action: str | None = None


class CompareEmailThreadRequest(BaseModel):
    source_org: str = Field(default="unknown")
    include_cross_org: bool | None = None
    top_k: int | None = None
    subject: str
    summary: str = ""
    open_questions: list[str] = Field(default_factory=list)
    latest_status: str | None = None
    next_action: str | None = None
    tags: list[str] = Field(default_factory=list)


class CompareCaeRunRequest(BaseModel):
    source_org: str = Field(default="unknown")
    include_cross_org: bool | None = None
    top_k: int | None = None
    tool_name: str
    simulation_type: str | None = None
    result_status: str | None = None
    failure_mode: str | None = None
    error_signature: str | None = None
    summary: str = ""
    lesson: str | None = None
    tags: list[str] = Field(default_factory=list)


class FeedbackJudgementRequest(BaseModel):
    judgement_type: str
    input_case_id: str | None = None
    related_case_ids: list[str] = Field(default_factory=list)
    decision_summary: str
    confidence: float | None = None
    next_action: str | None = None
    human_feedback: str | None = None
    actual_outcome: str | None = None
    source_org: str = Field(default="unknown")
    review_status: str = Field(default="reviewed")


class SearchMemoryRequest(BaseModel):
    query: str
    collections: list[str] = Field(
        default_factory=lambda: [
            "defect_case_memory",
            "email_thread_memory",
            "email_fact_memory",
            "quality_issue_memory",
            "improvement_activity_memory",
            "cae_run_memory",
            "judgement_memory",
        ]
    )
    include_cross_org: bool | None = None
    allowed_reuse_scope: list[str] = Field(default_factory=lambda: ["same_org_only", "analysis_only", "cross_org_anonymized_only"])
    source_org: str | None = None
    top_k: int | None = None


class SimpleEmbedding:
    def __init__(self, size: int) -> None:
        self.size = size

    def _fallback_embed(self, text: str) -> list[float]:
        buckets = [0.0] * self.size
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.size
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            buckets[idx] += sign
        norm = sum(v * v for v in buckets) ** 0.5 or 1.0
        return [v / norm for v in buckets]

    def _normalize_vector_size(self, vector: list[float]) -> list[float]:
        if len(vector) == self.size:
            return vector
        resized = [0.0] * self.size
        if not vector:
            return resized
        for idx, value in enumerate(vector):
            resized[idx % self.size] += float(value)
        norm = sum(v * v for v in resized) ** 0.5 or 1.0
        return [v / norm for v in resized]

    def embed(self, text: str) -> list[float]:
        if settings.embedding_base_url:
            try:
                resp = requests.post(
                    f"{settings.embedding_base_url}/embeddings",
                    json={"input": [text], "model": settings.embedding_model},
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                vec = data["data"][0]["embedding"]
                return self._normalize_vector_size(vec)
            except Exception:
                pass
        return self._fallback_embed(text)


class MemoryStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
        self.embedder = SimpleEmbedding(settings.embedding_size)
        self.collection_sizes = {
            "defect_case_memory": settings.embedding_size,
            "email_thread_memory": settings.embedding_size,
            "email_fact_memory": settings.embedding_size,
            "quality_issue_memory": settings.embedding_size,
            "improvement_activity_memory": settings.embedding_size,
            "cae_run_memory": settings.embedding_size,
            "judgement_memory": settings.embedding_size,
        }

    def ensure_collection(self, name: str) -> None:
        size = self.collection_sizes.get(name, settings.embedding_size)
        try:
            self.client.get_collection(name)
            return
        except Exception:
            pass
        try:
            self.client.create_collection(
                collection_name=name,
                vectors_config=qm.VectorParams(size=size, distance=qm.Distance.COSINE),
            )
        except Exception as exc:
            if "already exists" not in str(exc):
                raise

    def collection_snapshot(self) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for name in self.collection_sizes:
            self.ensure_collection(name)
            info = self.client.get_collection(name)
            snapshots.append(
                {
                    "name": name,
                    "points_count": getattr(info, "points_count", None),
                    "vectors_count": getattr(info, "vectors_count", None),
                    "status": str(getattr(info, "status", "")) or "unknown",
                }
            )
        snapshots.sort(key=lambda item: item["name"])
        return snapshots

    def build_text(self, payload: dict[str, Any]) -> str:
        ordered = []
        for key in [
            "title",
            "subject",
            "summary",
            "body_excerpt",
            "tool_name",
            "tool_version",
            "simulation_type",
            "project_name",
            "material",
            "geometry_type",
            "process",
            "defect_name",
            "symptom",
            "containment_action",
            "suspected_root_cause",
            "permanent_action",
            "mesh_size",
            "element_type",
            "contact_type",
            "friction",
            "time_step",
            "solver_settings",
            "boundary_conditions",
            "initial_conditions",
            "due_date",
            "owner",
            "verification_result",
            "status",
            "target_process",
            "trigger_issue",
            "before_state",
            "after_state",
            "change_type",
            "expected_effect",
            "measured_effect",
            "side_effect",
            "rollout_scope",
            "horizontal_deployment",
            "result_status",
            "failure_mode",
            "error_signature",
            "wall_clock_time",
            "lesson",
            "output_files",
            "sender",
            "participants",
            "open_questions",
            "latest_status",
            "next_action",
            "extracted_facts",
            "decision_summary",
            "human_feedback",
        ]:
            value = payload.get(key)
            if value:
                if isinstance(value, list):
                    ordered.append(f"{key}: {', '.join(str(item) for item in value)}")
                else:
                    ordered.append(f"{key}: {value}")
        tags = payload.get("tags") or []
        if tags:
            ordered.append("tags: " + ", ".join(tags))
        return "\n".join(ordered)

    def upsert_memory(self, collection: str, payload: dict[str, Any], point_id: str | None = None) -> dict[str, Any]:
        self.ensure_collection(collection)
        external_id = point_id or str(uuid.uuid4())
        point_id = qdrant_point_id(external_id)
        payload = dict(payload)
        payload["memory_type"] = collection.removesuffix("_memory")
        payload["created_at"] = payload.get("created_at") or utc_now_iso()
        payload["updated_at"] = utc_now_iso()
        payload["external_id"] = external_id
        embedding_text = self.build_text(payload)
        vector = self.embedder.embed(embedding_text)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.client.upsert(
                    collection_name=collection,
                    points=[
                        qm.PointStruct(
                            id=point_id,
                            vector=vector,
                            payload=payload,
                        )
                    ],
                )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(0.5 * (attempt + 1))
        if last_error is not None:
            raise last_error
        return {"id": point_id, "external_id": external_id, "collection": collection}

    def search(
        self,
        collection: str,
        query_text: str,
        top_k: int,
        include_cross_org: bool,
        source_org: str | None,
        allowed_reuse_scope: list[str],
    ) -> list[dict[str, Any]]:
        self.ensure_collection(collection)
        vector = self.embedder.embed(query_text)
        conditions: list[qm.FieldCondition] = [
            qm.FieldCondition(
                key="review_status",
                match=qm.MatchAny(any=["reviewed", "approved", "draft"]),
            ),
            qm.FieldCondition(
                key="reuse_scope",
                match=qm.MatchAny(any=allowed_reuse_scope),
            ),
        ]
        if not include_cross_org and source_org:
            conditions.append(qm.FieldCondition(key="source_org", match=qm.MatchValue(value=source_org)))
        query_filter = qm.Filter(must=conditions) if conditions else None
        hits = self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
        )
        result = []
        for hit in hits:
            result.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "collection": collection,
                    "payload": hit.payload,
                }
            )
        return result


store = MemoryStore()
app = FastAPI(title="OpenClaw Learning Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_workspace_json(name: str) -> dict[str, Any]:
    path = WORKSPACE_PATH / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        collections = store.client.get_collections().collections
        snapshots = store.collection_snapshot()
        return {
            "status": "ok",
            "qdrant": "ok",
            "collections": [c.name for c in collections],
            "collection_details": snapshots,
            "workspace_sync": {
                "email_learning": read_workspace_json("email_learning_memory_sync_status.json"),
                "cae_learning": read_workspace_json("cae_learning_memory_sync_status.json"),
                "idle_maintenance": read_workspace_json("idle_ingest_maintenance_status.json"),
            },
            "settings": {
                "embedding_model": settings.embedding_model,
                "embedding_size": settings.embedding_size,
                "memory_top_k": settings.memory_top_k,
                "include_cross_org_default": settings.include_cross_org_default,
            },
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "qdrant": "error",
            "detail": str(exc),
        }


@app.post("/ingest/case")
def ingest_case(req: CaseIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    case_id = payload.pop("case_id", None) or f"case-{uuid.uuid4()}"
    payload["case_id"] = case_id
    record = store.upsert_memory("defect_case_memory", payload=payload, point_id=case_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/ingest/quality-issue")
def ingest_quality_issue(req: QualityIssueIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    issue_id = payload.pop("issue_id", None) or f"quality-issue-{uuid.uuid4()}"
    payload["issue_id"] = issue_id
    record = store.upsert_memory("quality_issue_memory", payload=payload, point_id=issue_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/ingest/improvement-activity")
def ingest_improvement_activity(req: ImprovementActivityIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    activity_id = payload.pop("activity_id", None) or f"improvement-activity-{uuid.uuid4()}"
    payload["activity_id"] = activity_id
    record = store.upsert_memory("improvement_activity_memory", payload=payload, point_id=activity_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/ingest/email-message")
def ingest_email_message(req: EmailMessageIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    message_id = payload.pop("message_id", None) or f"email-message-{uuid.uuid4()}"
    payload["message_id"] = message_id
    payload["thread_id"] = payload.get("thread_id") or f"thread-{uuid.uuid4()}"
    record = store.upsert_memory("email_fact_memory", payload=payload, point_id=message_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/ingest/email-thread")
def ingest_email_thread(req: EmailThreadIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    thread_id = payload.pop("thread_id", None) or f"email-thread-{uuid.uuid4()}"
    payload["thread_id"] = thread_id
    record = store.upsert_memory("email_thread_memory", payload=payload, point_id=thread_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/ingest/cae-run")
def ingest_cae_run(req: CaeRunIngestRequest) -> dict[str, Any]:
    payload = req.model_dump()
    run_id = payload.pop("run_id", None) or f"cae-run-{uuid.uuid4()}"
    payload["run_id"] = run_id
    record = store.upsert_memory("cae_run_memory", payload=payload, point_id=run_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/compare/case")
def compare_case(req: CompareCaseRequest) -> dict[str, Any]:
    payload = req.model_dump()
    top_k = payload.pop("top_k", None) or settings.memory_top_k
    include_cross_org = payload.pop("include_cross_org", None)
    if include_cross_org is None:
        include_cross_org = settings.include_cross_org_default
    query_text = store.build_text(payload)
    hits = store.search(
        collection="defect_case_memory",
        query_text=query_text,
        top_k=top_k,
        include_cross_org=include_cross_org,
        source_org=req.source_org,
        allowed_reuse_scope=["same_org_only", "analysis_only"],
    )
    return {
        "status": "ok",
        "query_summary": {
            "title": req.title,
            "source_org": req.source_org,
            "include_cross_org": include_cross_org,
            "top_k": top_k,
        },
        "similar_cases": hits,
    }


@app.post("/compare/email-thread")
def compare_email_thread(req: CompareEmailThreadRequest) -> dict[str, Any]:
    payload = req.model_dump()
    top_k = payload.pop("top_k", None) or settings.memory_top_k
    include_cross_org = payload.pop("include_cross_org", None)
    if include_cross_org is None:
        include_cross_org = settings.include_cross_org_default
    query_text = store.build_text(payload)
    hits = store.search(
        collection="email_thread_memory",
        query_text=query_text,
        top_k=top_k,
        include_cross_org=include_cross_org,
        source_org=req.source_org,
        allowed_reuse_scope=["same_org_only", "analysis_only"],
    )
    return {
        "status": "ok",
        "query_summary": {
            "subject": req.subject,
            "source_org": req.source_org,
            "include_cross_org": include_cross_org,
            "top_k": top_k,
        },
        "similar_threads": hits,
    }


@app.post("/compare/cae-run")
def compare_cae_run(req: CompareCaeRunRequest) -> dict[str, Any]:
    payload = req.model_dump()
    top_k = payload.pop("top_k", None) or settings.memory_top_k
    include_cross_org = payload.pop("include_cross_org", None)
    if include_cross_org is None:
        include_cross_org = settings.include_cross_org_default
    query_text = store.build_text(payload)
    hits = store.search(
        collection="cae_run_memory",
        query_text=query_text,
        top_k=top_k,
        include_cross_org=include_cross_org,
        source_org=req.source_org,
        allowed_reuse_scope=["same_org_only", "analysis_only"],
    )
    return {
        "status": "ok",
        "query_summary": {
            "tool_name": req.tool_name,
            "source_org": req.source_org,
            "include_cross_org": include_cross_org,
            "top_k": top_k,
        },
        "similar_runs": hits,
    }


@app.post("/feedback/judgement")
def feedback_judgement(req: FeedbackJudgementRequest) -> dict[str, Any]:
    payload = req.model_dump()
    judgement_id = f"judgement-{uuid.uuid4()}"
    payload["trace_id"] = judgement_id
    record = store.upsert_memory("judgement_memory", payload=payload, point_id=judgement_id)
    return {
        "status": "ok",
        "record": record,
    }


@app.post("/search/memory")
def search_memory(req: SearchMemoryRequest) -> dict[str, Any]:
    include_cross_org = req.include_cross_org
    if include_cross_org is None:
        include_cross_org = settings.include_cross_org_default

    results: list[dict[str, Any]] = []
    for collection in req.collections:
        try:
            results.extend(
                store.search(
                    collection=collection,
                    query_text=req.query,
                    top_k=req.top_k or settings.memory_top_k,
                    include_cross_org=include_cross_org,
                    source_org=req.source_org,
                    allowed_reuse_scope=req.allowed_reuse_scope,
                )
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"search failed in {collection}: {exc}") from exc

    results.sort(key=lambda item: item["score"], reverse=True)
    return {
        "status": "ok",
        "query": req.query,
        "results": results[: req.top_k or settings.memory_top_k],
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "learning_engine",
        "version": app.version,
        "routes": [
            "/health",
            "/ingest/case",
            "/ingest/quality-issue",
            "/ingest/improvement-activity",
            "/ingest/email-message",
            "/ingest/email-thread",
            "/ingest/cae-run",
            "/compare/case",
            "/compare/email-thread",
            "/compare/cae-run",
            "/feedback/judgement",
            "/search/memory",
        ],
    }
