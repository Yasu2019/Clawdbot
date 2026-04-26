# Local App Concept

## App name
AI Video Control Desk

## Objective
Provide a local UI to:
- edit structured JSON prompts
- attach start/end frame images
- attach motion reference video
- run generation jobs manually or semi-automatically
- review outputs with QA scores
- store revisions and reusable templates

## Suggested modules
1. Prompt editor
2. Asset manager
3. Revision diff viewer
4. QA scoring panel
5. Template library
6. Export/import ZIP project package

## Suggested stack
- Frontend: Next.js
- Backend: FastAPI
- Storage: SQLite/PostgreSQL
- Media assets: local folder / object storage
- Optional CV: MediaPipe / OpenCV for motion checks
