#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "data" / "state" / "dify_email"
STATE_FILE = STATE_DIR / "workflow.json"
EMAIL = "y.suzuki.hk@gmail.com"
APP_NAME = "Email Fast Summary"
API_CONTAINER = "clawstack-unified-dify-api-1"


PY_SNIPPET = r"""
import json
from app import app
from extensions.ext_database import db
from models import Account, TenantAccountJoin
from models.model import ApiToken, App
from services.app_service import AppService
from services.workflow_service import WorkflowService

EMAIL = "y.suzuki.hk@gmail.com"
APP_NAME = "Email Fast Summary"

with app.app_context():
    account = db.session.query(Account).where(Account.email == EMAIL).first()
    if not account:
        raise SystemExit("account_not_found")
    tenant_join = db.session.query(TenantAccountJoin).where(TenantAccountJoin.account_id == account.id).first()
    if not tenant_join:
        raise SystemExit("tenant_join_not_found")
    tenant_id = tenant_join.tenant_id
    account.set_tenant_id(tenant_id)
    app_model = db.session.query(App).where(
        App.tenant_id == tenant_id,
        App.name == APP_NAME,
    ).first()
    if not app_model:
        app_model = AppService().create_app(
            tenant_id=tenant_id,
            args={
                "name": APP_NAME,
                "mode": "workflow",
                "icon_type": "emoji",
                "icon": "📧",
                "icon_background": "#D9F7BE",
            },
            account=account,
        )

    graph = {
        "nodes": [
            {
                "id": "start",
                "position": None,
                "data": {
                    "title": "START",
                    "type": "start",
                    "variables": [
                        {
                            "variable": "query",
                            "label": "Query",
                            "description": "email query",
                            "type": "paragraph",
                            "required": True,
                            "max_length": 400,
                        }
                    ],
                },
            },
            {
                "id": "http_request_1",
                "position": None,
                "data": {
                    "title": "EMAIL HARNESS",
                    "type": "http-request",
                    "method": "post",
                    "url": "http://host.docker.internal:8787/summarize_email",
                    "authorization": {"type": "no-auth"},
                    "headers": "",
                    "params": "",
                    "body": {
                        "type": "json",
                        "data": "{\"query\": \"{{#start.query#}}\", \"limit\": 3}"
                    },
                    "timeout": {"connect": 10, "read": 30, "write": 10},
                    "ssl_verify": False,
                },
            },
            {
                "id": "end",
                "position": None,
                "data": {
                    "title": "END",
                    "type": "end",
                    "outputs": [
                        {"variable": "result", "value_selector": ["http_request_1", "body"]}
                    ],
                },
            },
        ],
        "edges": [
            {"id": "start-http_request_1", "source": "start", "target": "http_request_1"},
            {"id": "http_request_1-end", "source": "http_request_1", "target": "end"},
        ],
    }
    features = {"file_upload": None, "text_to_speech": None, "sensitive_word_avoidance": None}
    workflow_service = WorkflowService()
    existing_draft = workflow_service.get_draft_workflow(app_model=app_model)
    draft = workflow_service.sync_draft_workflow(
        app_model=app_model,
        graph=graph,
        features=features,
        unique_hash=existing_draft.unique_hash if existing_draft else None,
        account=account,
        environment_variables=[],
        conversation_variables=[],
    )
    published = workflow_service.publish_workflow(
        session=db.session,
        app_model=app_model,
        account=account,
        marked_name="email-fast-summary-v1",
        marked_comment="host harness via HTTP request",
    )
    app_model.workflow_id = published.id
    token = db.session.query(ApiToken).where(ApiToken.app_id == app_model.id, ApiToken.type == "app").first()
    if not token:
        token = ApiToken(
            app_id=app_model.id,
            tenant_id=tenant_id,
            type="app",
            token=ApiToken.generate_api_key("app-", 32),
        )
        db.session.add(token)
    db.session.commit()
    print(json.dumps({
        "app_id": app_model.id,
        "workflow_id": published.id,
        "token": token.token,
        "tenant_id": tenant_id,
    }))
"""


def run() -> dict:
    completed = subprocess.run(
        [
            "docker",
            "exec",
            API_CONTAINER,
            "python",
            "-c",
            PY_SNIPPET,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = run()
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
