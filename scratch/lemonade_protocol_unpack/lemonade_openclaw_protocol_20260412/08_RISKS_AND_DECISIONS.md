# Risks and Decisions

## Main risks
### 1. Feature overlap
Lemonade may overlap with functions already served by Ollama, Open WebUI, or other tools.

### 2. Operational sprawl
Another service adds logs, ports, configs, restart logic, and maintenance burden.

### 3. False replacement assumption
A lightweight binary is not automatically a full replacement for a mature text-serving path.

### 4. Endpoint mismatch
Even with OpenAI compatibility claims, exact endpoint behavior may differ.

### 5. Observability gaps
If traces and logs do not flow into the existing observability system, troubleshooting becomes harder.

## Decision framework
### Adopt if:
- multimodal value is real now
- API unification reduces complexity
- operational burden stays contained

### Do not adopt if:
- it mostly duplicates current services
- it weakens reliability
- the actual tested value is only theoretical
