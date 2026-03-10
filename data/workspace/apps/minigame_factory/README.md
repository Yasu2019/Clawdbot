# MiniGame Factory v1.1 (RQ + Godot Builder + Single-HTML Builder)

## What you get
- API (FastAPI): create project, submit spec, enqueue build
- Worker (RQ): runs build jobs
- Godot Builder (HTTP): exports Android debug APK (release AAB optional later)
- Node Builder (HTTP): generates Single-HTML web build
- UI (Next.js): minimal buttons to trigger flow

## Quick start
```bash
cp .env.example .env
mkdir -p projects output secrets
docker compose up --build
```

Open:
- UI: http://localhost:3000
- API: http://localhost:8000/docs

## Minimal API flow (curl)
```bash
# 1) create project
curl -X POST http://localhost:8000/projects

# 2) submit spec (replace PROJECT_ID)
curl -X POST http://localhost:8000/projects/PROJECT_ID/spec \
  -H "Content-Type: application/json" \
  -d @example_spec.json

# 3) check status
curl http://localhost:8000/projects/PROJECT_ID
```

Artifacts appear under:
- ./output/PROJECT_ID/android/...
- ./output/PROJECT_ID/web_singlehtml/index.html
