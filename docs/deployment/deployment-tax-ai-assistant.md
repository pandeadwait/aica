# Deployment Document: AI Assistant for Indian Personal Income Tax Filing

## 1. Purpose

This document defines the deployment approach for the Indian personal income tax filing assistant.

It covers:

- deployment structure
- reasons for the chosen structure
- step-by-step deployment plan
- environment and infrastructure considerations
- operational and maintenance guidance

This deployment design is based on the current product decisions:

- local-first architecture
- single-user V1
- web-based frontend
- Python backend
- local LLM: `Qwen2.5 Instruct (14B)`
- relational database: `PostgreSQL`
- vector database: `pgvector`
- all services containerized

## 2. Deployment Goals

The deployment approach should satisfy these goals:

- all data stays local
- no dependency on cloud services
- easy local setup for development and V1 usage
- isolated services for maintainability
- reproducible environment through containers
- easy upgrades and re-deployments
- clear separation of application, database, model runtime, and storage concerns

## 3. Deployment Model

## 3.1 Chosen Model

The project should be deployed as a local multi-container application using `Docker Compose`.

This means:

- each major service runs in its own container
- containers communicate over a local Docker network
- persistent volumes are used for data that must survive restart
- the full stack can be started and stopped with a single command

## 3.2 Why This Model Was Chosen

This structure was chosen because it is the best fit for the product’s requirements:

- local-first operation
- single-user deployment
- multiple infrastructure components
- strong need for reproducibility
- clean separation between application and infrastructure

Compared with installing everything directly on the host machine, a containerized deployment gives:

- simpler dependency management
- more predictable local environments
- cleaner upgrades
- fewer conflicts between Python, database, OCR, and model runtime dependencies

Compared with a monolithic single-container deployment, a multi-container structure gives:

- better service isolation
- easier debugging
- cleaner persistence boundaries
- easier component replacement later

## 4. Detailed Deployment Structure

## 4.1 High-Level Service Layout

The deployment should include these containers:

1. `frontend`
2. `backend`
3. `worker`
4. `postgres`
5. `llm`
6. optional `reverse-proxy` if needed later

Notes:

- `pgvector` runs inside the `postgres` container as a PostgreSQL extension, not as a separate service.
- OCR can initially live inside the `backend` and `worker` images unless operational complexity justifies breaking it out later.

## 4.2 Service Responsibilities

### `frontend`

Purpose:

- serves the web UI
- interacts with the backend API
- provides workflow screens for document upload, review, calculation review, and historical access

Likely runtime:

- Node-based frontend build output served through a lightweight web server or frontend dev server in development

### `backend`

Purpose:

- main Python API service
- business logic orchestration
- filing management
- document intake
- validation coordination
- tax rules orchestration
- calculation APIs
- XML generation APIs
- assistant APIs

Likely runtime:

- Python application server such as `uvicorn` with `FastAPI`

### `worker`

Purpose:

- executes long-running tasks asynchronously
- OCR
- parsing
- extraction
- categorization support
- gap analysis refresh
- calculation-heavy background jobs
- artifact generation jobs where useful

Reason for separate worker:

- avoids blocking API requests
- gives better fault isolation for long-running processing

### `postgres`

Purpose:

- authoritative relational data store
- stores workflow state, structured extracted data, historical records, and retrieval corpus metadata
- hosts `pgvector` for semantic retrieval over tax guidance and ITR template content

### `llm`

Purpose:

- hosts `Qwen2.5 Instruct (14B)` locally
- serves model inference to backend and worker

Likely runtime:

- `Ollama` in V1, unless replaced later by another local serving stack

### `reverse-proxy` (optional later)

Purpose:

- route frontend and backend traffic through a single local endpoint
- simplify local TLS or path-based routing if needed later

Not required for the earliest V1 unless the deployment UX benefits from it.

## 4.3 Network Structure

All containers should run on an internal Docker network.

Suggested communication pattern:

- `frontend` -> `backend`
- `backend` -> `postgres`
- `backend` -> `llm`
- `backend` -> local file volumes
- `worker` -> `postgres`
- `worker` -> `llm`
- `worker` -> local file volumes

The `postgres` and `llm` services should not be exposed publicly by default unless needed for local development access.

## 4.4 Persistent Volumes

Persistent storage should be separated by purpose.

Suggested volumes:

- `postgres_data`
- `documents_data`
- `artifacts_data`
- `llm_model_data`
- `app_temp_data`

### `postgres_data`

Stores:

- relational database files
- `pgvector` extension data

### `documents_data`

Stores:

- uploaded PDFs
- structured uploaded files
- intermediate parser inputs

### `artifacts_data`

Stores:

- generated XML files
- generated summaries
- parser output artifacts if retained

### `llm_model_data`

Stores:

- downloaded local model files
- model cache

### `app_temp_data`

Stores:

- temporary processing files
- OCR intermediate outputs
- task scratch files

## 4.5 Filesystem Layout Recommendation

Recommended mounted directory structure inside the backend/worker containers:

```text
/app
/app/data/documents
/app/data/artifacts
/app/data/temp
/app/config
```

Recommended volume mapping on host:

```text
./volumes/postgres
./volumes/documents
./volumes/artifacts
./volumes/llm
./volumes/temp
```

## 5. Why This Structure Was Chosen

## 5.1 Separation of Concerns

This structure separates:

- UI serving
- synchronous API logic
- background processing
- relational persistence
- LLM inference

This makes the system easier to:

- debug
- scale later
- replace components in
- reason about operationally

## 5.2 Local-First Privacy

The structure ensures all sensitive user data remains local because:

- database is local
- documents are local
- model inference is local
- retrieval is local
- no cloud services are required

## 5.3 Better Handling of Long-Running Tasks

OCR, parsing, and LLM-assisted extraction can be slow. Separating the worker prevents:

- frontend timeouts
- blocked API requests
- poor user experience

## 5.4 Clean PostgreSQL + pgvector Integration

Because `pgvector` runs inside PostgreSQL, we avoid introducing an extra vector service.

Benefits:

- fewer moving parts
- simpler deployment
- one place for relational and retrieval metadata
- cleaner Python integration

## 5.5 Clean LLM Isolation

Keeping the LLM in its own container is useful because:

- model runtime dependencies are separate from application dependencies
- model upgrades are easier
- resource allocation is clearer
- inference runtime can be swapped later without redesigning the backend container

## 6. Detailed Deployment Flow

## 6.1 Boot Sequence

Recommended startup order:

1. start `postgres`
2. initialize DB extensions and schema
3. start `llm`
4. preload/pull `Qwen2.5 Instruct (14B)` if not already available
5. start `backend`
6. start `worker`
7. start `frontend`

Why this order:

- backend depends on DB and LLM availability
- worker depends on DB and LLM availability
- frontend depends on backend availability

## 6.2 Runtime Request Flow

Typical request path:

1. user opens frontend
2. frontend calls backend
3. backend reads/writes PostgreSQL
4. backend stores documents in local volume
5. backend creates background job
6. worker processes job
7. worker uses PostgreSQL, file storage, and LLM as needed
8. frontend polls or fetches updated status from backend

## 7. Environment Configuration

## 7.1 Required Configuration Areas

The deployment should use environment variables or config files for:

- database connection string
- PostgreSQL credentials
- LLM service URL
- model name
- data directory paths
- document storage paths
- artifact storage paths
- temp storage paths
- app port bindings
- logging levels

## 7.2 Recommended Configuration Files

Suggested files:

- `.env`
- `docker-compose.yml`
- `docker-compose.override.yml` for local development
- backend app config file if needed

## 8. Step-by-Step Deployment Plan

## 8.1 Phase 1: Prepare the Repository

1. Create container definitions for:
   - frontend
   - backend
   - worker
   - postgres
   - llm
2. Create a shared `docker-compose.yml`
3. Define persistent volumes
4. Define Docker network
5. Add `.env.example` with required configuration keys

## 8.2 Phase 2: Prepare PostgreSQL

1. Use an official PostgreSQL image as the base
2. Enable the `pgvector` extension
3. Create database initialization scripts
4. Add schema migration support
5. Define health checks for DB readiness

Expected result:

- local PostgreSQL starts reliably
- schema can be created or migrated automatically
- `pgvector` is available at startup

## 8.3 Phase 3: Prepare the LLM Service

1. Create the `llm` container configuration
2. Choose serving runtime, likely `Ollama`
3. Mount persistent model storage
4. Configure model pull/load for `Qwen2.5 Instruct (14B)`
5. Add health checks
6. Confirm API access from backend and worker

Expected result:

- backend and worker can call the local LLM service reliably

## 8.4 Phase 4: Prepare the Backend Service

1. Create backend Dockerfile
2. Install Python dependencies
3. Install OCR and PDF-processing dependencies required by backend/worker image
4. Configure database connectivity
5. Configure local storage paths
6. Configure LLM endpoint access
7. Add health endpoint
8. Add startup migration step if appropriate

Expected result:

- backend starts and can connect to PostgreSQL and the LLM service

## 8.5 Phase 5: Prepare the Worker Service

1. Create worker Dockerfile or reuse backend image with different command
2. Configure job execution entrypoint
3. Ensure access to:
   - PostgreSQL
   - local file volumes
   - LLM service
4. Add worker health monitoring if needed

Expected result:

- background jobs can run independently from the API server

## 8.6 Phase 6: Prepare the Frontend Service

1. Create frontend Dockerfile
2. Configure API base URL
3. Build production frontend assets
4. Serve the app from container
5. Add frontend health check if useful

Expected result:

- UI starts and can talk to backend

## 8.7 Phase 7: Add Initialization and Health Checks

1. Add health checks for:
   - PostgreSQL
   - backend
   - llm
   - optionally frontend
2. Ensure backend waits for required dependencies
3. Ensure worker starts only after DB readiness
4. Validate volume mounts

Expected result:

- deployment becomes reliable and repeatable

## 8.8 Phase 8: First End-to-End Deployment Test

1. Start the full stack
2. Open frontend
3. Create a filing
4. Upload a sample document
5. Run parsing workflow
6. Verify DB writes
7. Verify local artifact generation
8. Verify LLM-assisted workflow path

Expected result:

- the complete local workflow functions end to end

## 9. Health Checks and Operational Readiness

## 9.1 Minimum Health Checks

### PostgreSQL

- accepts connections
- extension availability check for `pgvector`

### Backend

- process alive
- DB reachable
- storage paths writable

### Worker

- process alive
- DB reachable
- queue/task table accessible

### LLM

- API reachable
- selected model available

### Frontend

- UI served successfully

## 9.2 Operational Readiness Checks

Before considering deployment usable, verify:

- PostgreSQL schema migration succeeds
- `pgvector` extension is installed
- `Qwen2.5 Instruct (14B)` is loaded or available
- document and artifact volumes are writable
- end-to-end upload and parse flow works
- XML generation can persist artifacts

## 10. Security and Local Access Considerations

Even though V1 is local-first, the deployment should still follow basic controls:

- do not expose DB externally by default
- do not expose LLM externally by default
- bind only required application ports
- keep secrets in environment configuration, not hardcoded in images
- restrict volume mounts to required directories

## 11. Logging and Diagnostics

The deployment should include:

- container logs for each service
- backend application logs
- worker processing logs
- migration logs
- LLM runtime logs

Logs should avoid storing unnecessary sensitive tax content wherever possible.

## 12. Update and Upgrade Strategy

Recommended upgrade approach:

1. stop the stack
2. back up volumes if operationally desired
3. pull updated images or rebuild local images
4. run DB migrations
5. restart services in dependency order
6. verify health checks

Important rule:

- schema migrations must be versioned and repeatable

## 13. Failure and Recovery Considerations

Expected recoverable failures:

- backend restart
- worker restart
- frontend restart
- temporary LLM unavailability

Important persistence protections:

- documents remain on persistent volumes
- PostgreSQL retains workflow state
- generated artifacts remain on persistent volumes
- model files remain cached in persistent storage

## 14. Recommended Initial Deployment Shape

For V1, the recommended deployment shape is:

- `frontend` container
- `backend` container
- `worker` container
- `postgres` container with `pgvector`
- `llm` container using local model serving
- shared Docker network
- persistent local volumes

This is the best fit because it keeps:

- the architecture local
- the infrastructure understandable
- the deployment reproducible
- the service boundaries clean

## 15. Suggested Deliverables for Deployment Setup

The project should eventually include:

- `docker-compose.yml`
- `.env.example`
- `Dockerfile` for backend
- `Dockerfile` for frontend
- optional worker-specific Dockerfile or command override
- DB init scripts
- migration scripts
- deployment README
- health-check endpoints

## 16. Final Recommendation

The project should be deployed as a local multi-container stack using `Docker Compose`, with:

- `PostgreSQL` + `pgvector` as the persistent data and retrieval layer
- a separate local LLM container for `Qwen2.5 Instruct (14B)`
- separate backend and worker services
- persistent volumes for database, documents, artifacts, temp data, and model storage

This deployment structure was chosen because it gives the strongest balance of:

- privacy
- reproducibility
- maintainability
- local operability
- clean service isolation
- future extensibility

## 17. Related Documents

- Requirements: [requirements-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/requirements/requirements-tax-ai-assistant.md)
- Design: [design-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/design/design-tax-ai-assistant.md)
- LLM evaluation: [llm-evaluation-qwen2.5-14b.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/llm-evaluation-qwen2.5-14b.md)
- Relational DB evaluation: [relational-db-evaluation-postgresql.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/relational-db-evaluation-postgresql.md)
- Vector DB evaluation: [vector-db-evaluation-pgvector.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/vector-db-evaluation-pgvector.md)
