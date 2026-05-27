# Deployment Files

This folder contains the project deployment scaffold aligned with the deployment design document.

It includes:

- a full `docker-compose` layout
- environment configuration examples
- PostgreSQL with `pgvector`
- local LLM service using `Ollama`
- a Phase 0 backend foundation service
- a Phase 0 worker foundation service
- a placeholder frontend service

Important notes:

- These files have been created only for structure and understanding.
- Nothing has been executed.
- The frontend is still a placeholder.
- The backend and worker now implement the Phase 0 foundation needed for later phases.

## Layout

- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `docker-compose.override.yml`
- `postgres/`
- `llm/`
- `backend/`
- `worker/`
- `frontend/`

## What is production-intent vs placeholder

Production-intent infrastructure:

- PostgreSQL container
- `pgvector` extension initialization
- Ollama-based LLM container
- volume layout
- container network and health checks
- backend config, health endpoints, and runtime dependency checks
- Alembic migration framework
- worker connectivity and heartbeat foundation

Placeholder services:

- frontend

The frontend placeholder exists so the deployment structure matches the planned architecture before the real UI is built.

The backend and worker are not final application implementations yet, but they are no longer empty placeholders. They now provide:

- backend startup and health endpoints
- DB and LLM runtime checks
- migration bootstrap
- worker startup checks and heartbeat loop

## Expected future flow

Later, the frontend placeholder will be replaced with the real UI, and the backend/worker foundation will be expanded into the full application implementation. The `postgres`, `llm`, volumes, env structure, and compose layout can stay largely the same.
