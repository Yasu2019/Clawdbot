# Docker Add-ons Plan

## Goal
Add recommended free self-hosted apps without modifying the core `docker-compose.yml`.

## Scope
- Re-enable `Stirling-PDF` as an external overlay service.
- Add `changedetection.io`.
- Add `Actual Budget`.
- Add `Vikunja`.
- Add `Immich` with its own Redis/Postgres pair.
- Add `ntfy`.
- Add `Dashy`.

## Constraints
- Do not edit `docker-compose.yml`.
- Use a separate compose overlay so the current stack remains stable.
- Prefer named volumes or isolated bind mounts to reduce Windows permission issues.
- Keep existing ports unchanged where already implied by the current stack.

## Implementation
- Add `docker-compose.addons.yml`.
- Add a startup script to create required host folders and launch the add-on services.
- Add a status script to inspect only the add-on services.

## Verification
- Compose config validates with the overlay file.
- Add-on services can be brought up independently of the core stack.
- `docker compose ps` shows the add-on services.
