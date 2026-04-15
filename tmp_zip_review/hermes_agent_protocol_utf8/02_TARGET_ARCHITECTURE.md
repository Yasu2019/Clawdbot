# Target Architecture

## Functional layers

### Layer 1: Runtime agent
Responsible for:
- planning
- tool use
- result synthesis

Candidate:
- OpenClaw or equivalent orchestrator

### Layer 2: Model routing
Responsible for:
- selecting cloud or local model
- fallback handling
- price and latency control

Candidate:
- LiteLLM

### Layer 3: Knowledge RAG
Responsible for:
- document search
- file retrieval
- knowledge grounding

Candidates:
- Qdrant
- Paperless
- Docling
- SearXNG for web search if enabled

### Layer 4: Experience memory
Responsible for:
- storing task outcomes
- storing lessons learned
- storing failure recovery recipes
- storing user- or environment-specific operational constraints

Candidate:
- Qdrant separate collection(s) for experience memory

### Layer 5: Reflection engine
Responsible for:
- turning traces into reusable lessons
- extracting success/failure reasons
- creating structured memory entries

Candidates:
- local Ollama model for cheap batch reflection
- cloud model for difficult reflection jobs

### Layer 6: Observability
Responsible for:
- trace capture
- latency/cost visibility
- debugging
- regression detection

Candidate:
- Langfuse

## Recommended separation of data
Do not mix document RAG chunks and experience memory in one undifferentiated collection.
Keep them logically separate.

Recommended logical stores:
- docs_knowledge
- agent_experience
- tool_playbooks
- environment_constraints

## Retrieval order for a new task
1. environment constraints
2. relevant playbooks
3. past similar experiences
4. raw knowledge RAG
5. live tool calls

## Why this order works
It prevents the system from repeating old mistakes before it even starts general retrieval.
