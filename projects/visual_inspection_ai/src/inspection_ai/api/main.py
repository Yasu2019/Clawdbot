from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.learning.reference_training import train_reference_challenger
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.pipeline import InspectionPipeline
from inspection_ai.reporting.export import export_reviews_csv
from inspection_ai.review.service import ReviewService
from inspection_ai.schemas import PromoteRequest, ReviewLabelRequest


class Context:
    def __init__(self, config_path: str | None = None):
        self.config = AppConfig(config_path)
        self.db = Database(self.config.paths.database)
        self.registry = ModelRegistry(self.db, self.config.paths.model_registry, self.config.paths.root)
        self.pipeline = InspectionPipeline(self.config, self.db, self.registry)
        self.reviews = ReviewService(self.db)


def _url(path: str) -> str:
    return "/" + path.replace("\\", "/").lstrip("/")


def create_app(config_path: str | None = None) -> FastAPI:
    ctx = Context(config_path)
    app = FastAPI(title="Local Visual Inspection AI", version="0.1.0")
    app.state.ctx = ctx
    root = ctx.config.paths.root
    ctx.config.paths.runtime.mkdir(parents=True, exist_ok=True)
    app.mount("/data/runtime", StaticFiles(directory=ctx.config.paths.runtime), name="runtime")
    app.mount("/ui", StaticFiles(directory=root / "ui"), name="ui")

    @app.get("/")
    def index():
        return FileResponse(root / "ui" / "index.html")

    @app.get("/api/health")
    def health():
        row = ctx.db.query_one("SELECT COUNT(*) AS c FROM models WHERE stage='CHAMPION'")
        return {"status": "ok", "external_api_disabled": ctx.config.disable_external_api, "champion_count": row["c"]}

    @app.post("/api/inspect")
    async def inspect(
        file: Annotated[UploadFile, File(...)],
        product_id: Annotated[str, Form()] = "demo_press_part",
        lot: Annotated[str, Form()] = "",
        equipment: Annotated[str, Form()] = "",
    ):
        suffix = Path(file.filename or "").suffix.lower()
        allowed = set(ctx.config.security.get("allowed_extensions", []))
        if suffix not in allowed:
            raise HTTPException(400, f"許可されていない拡張子です: {suffix}")
        content = await file.read()
        max_bytes = int(ctx.config.security.get("max_upload_mb", 25)) * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(413, "ファイルが大きすぎます")
        try:
            return ctx.pipeline.inspect_bytes(content, file.filename or "upload.png", product_id, lot, equipment)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            ctx.db.audit("INSPECTION_ERROR", "upload", file.filename or "unknown", {"error": repr(exc)})
            raise HTTPException(500, f"検査処理に失敗しました: {exc}") from exc

    @app.get("/api/reviews")
    def reviews(status: str = "PENDING", limit: int = 100):
        rows = ctx.reviews.list(status if status != "ALL" else None, min(max(limit, 1), 500))
        for row in rows:
            row["original_url"] = _url(row["original_path"])
            row["annotated_url"] = _url(row["annotated_path"])
            row["measurements"] = json.loads(row.pop("measurements_json"))
            row["regions"] = json.loads(row.pop("regions_json"))
        return rows

    @app.post("/api/reviews/{review_id}/label")
    def label_review(review_id: str, request: ReviewLabelRequest):
        try:
            ctx.reviews.label(review_id, request)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"status": "updated", "review_id": review_id}

    def _training_job(product_id: str):
        try:
            result = train_reference_challenger(ctx.config, ctx.db, ctx.registry, product_id, promote=False)
            ctx.db.audit("BACKGROUND_TRAINING_DONE", "product", product_id, result)
        except Exception as exc:
            ctx.db.audit("BACKGROUND_TRAINING_FAILED", "product", product_id, {"error": repr(exc)})

    @app.post("/api/learning/reference")
    def start_reference_training(background_tasks: BackgroundTasks, product_id: str = "demo_press_part"):
        background_tasks.add_task(_training_job, product_id)
        return {"status": "queued", "product_id": product_id, "auto_promote": False}

    @app.get("/api/models")
    def models(product_id: str | None = None):
        return ctx.registry.list_models(product_id)

    @app.post("/api/models/{version}/promote")
    def promote(version: str, request: PromoteRequest):
        if not request.confirm:
            raise HTTPException(400, "confirm=trueが必要です")
        try:
            ctx.registry.promote(version, request.approved_by, request.note)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        ctx.pipeline._detectors.clear()
        return {"status": "promoted", "version": version}

    @app.post("/api/models/{version}/rollback")
    def rollback(version: str, product_id: str, request: PromoteRequest):
        if not request.confirm:
            raise HTTPException(400, "confirm=trueが必要です")
        try:
            ctx.registry.rollback(product_id, version, request.approved_by)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        ctx.pipeline._detectors.clear()
        return {"status": "rolled_back", "version": version}

    @app.get("/api/metrics")
    def metrics():
        decisions = ctx.db.query_all("SELECT product_id,decision,COUNT(*) AS count,AVG(anomaly_score) AS avg_score FROM inspections GROUP BY product_id,decision")
        reviews_summary = ctx.db.query_all("SELECT status,COUNT(*) AS count FROM reviews GROUP BY status")
        timing = ctx.db.query_all("SELECT elapsed_json FROM inspections ORDER BY created_at DESC LIMIT 200")
        totals = []
        for row in timing:
            try:
                totals.append(float(json.loads(row["elapsed_json"])["total"]))
            except Exception:
                pass
        totals.sort()
        def pct(p: float):
            if not totals:
                return None
            return totals[min(len(totals) - 1, int((len(totals) - 1) * p))]
        return {"decisions": decisions, "reviews": reviews_summary, "timing_ms": {"count": len(totals), "p50": pct(.5), "p95": pct(.95), "max": max(totals) if totals else None}}

    @app.get("/api/reports/reviews.csv")
    def review_report(status: str | None = None):
        path = export_reviews_csv(ctx.db, ctx.config.paths.reports, status)
        return FileResponse(path, media_type="text/csv", filename=path.name)

    @app.get("/api/audit")
    def audit(limit: int = 100):
        return ctx.db.query_all("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (min(max(limit, 1), 500),))

    return app


app = create_app()
