# File Responsibility Map

Date: 2026-06-12

## Purpose

This document explains what each meaningful project file is responsible for, with extra detail for the backend and worker code under `deployment/backend` and `deployment/worker`.

## How The Application Works

This section is written for someone who is new to the project and wants to understand the system before reading individual files.

### Big Picture

The application is a local tax-document processing system.

At a high level, it does 4 things:

1. stores a filing workspace and taxpayer context
2. accepts and versions uploaded tax documents
3. processes those documents into extracted and normalized tax candidates
4. lets the user review, correct, reconcile, and complete the data before any tax calculation phase

Right now, the application is strongest as a:

- filing workspace
- document understanding pipeline
- review and gap-analysis system

It is not yet the final tax-calculation engine.

### Runtime Components

The running application is made of these main parts:

- `PostgreSQL`
  Stores the application data.
- `backend`
  Exposes the API and contains almost all of the business logic.
- `worker`
  Polls the backend and asks it to run pending processing jobs.
- `LLM container`
  Exists as a local service dependency for future/assistive AI behavior and health checks.
- `frontend`
  User-facing UI container, separate from the backend logic.

### Core Data Flow

The simplest way to understand the application is to follow the data flow from upload to review.

#### 1. A filing is created

The user first creates a filing for an assessment year.

That creates the main workspace record in the database.

The filing becomes the parent container for:

- taxpayer profile
- uploaded documents
- extracted tax items
- review items
- gaps

#### 2. A document is uploaded

The user uploads a document into a filing.

At upload time, the system:

- stores the physical file on disk
- records metadata in PostgreSQL
- creates a document row
- creates a document version row
- computes checksum and size
- may detect duplicates later using the checksum

At this point, the system has stored the file, but it has not yet “understood” it.

#### 3. Processing jobs are created

Once the document is sent into Phase 3 processing, the backend creates a sequence of jobs:

- validate document
- parse document
- extract fields
- normalize tax items

For PDFs with no native text layer, an OCR job may be inserted as well.

These jobs are stored in the database and can be run:

- immediately through the API
- asynchronously by the worker

#### 4. The backend validates the document

The validation stage tries to answer:

- is this file readable?
- does it look tax-related?
- does it match the filing’s year context?
- is it a duplicate?
- does it need OCR?

The result is saved as a `document_validation_result`.

#### 5. The backend parses the file

The parse stage turns the raw file into machine-usable content.

Depending on file type:

- `JSON/XML/CSV/XLSX` go through structured parsing
- text-layer PDFs go through native PDF text extraction
- scanned PDFs go through OCR fallback

The raw parsed output is saved as a `raw_extraction`.

#### 6. Fields are extracted

The extraction stage converts raw parsed content into canonical fields.

Examples:

- `Gross Salary` -> `gross_salary`
- `TDS Deducted` -> `tax_deducted`
- `Interest Paid` -> `interest_income`

This stage also records provenance:

- which extraction the field came from
- source locator such as line, page, row, or column
- snippet/source context

The output is saved as `parsed_fields` plus `field_provenance`.

#### 7. Tax candidates are normalized

The normalization stage turns parsed fields into tax-oriented candidate items.

Examples:

- `gross_salary` -> `salary_income`
- `tax_deducted` -> `tds_credits`
- `premium_paid` -> `deductions`
- `interest_income` -> `interest_income`

These are stored as `normalized_tax_items`.

If the document represents foreign-income activity, supporting `foreign_income_events` may also be created.

#### 8. Review state is created

Phase 4 converts normalized tax items into review items.

A review item is what the user actually works with.

It keeps:

- suggested category
- final category if overridden
- amount
- confidence
- source linkage
- reconciliation state
- review status

This review state is stored in `category_assignments`.

#### 9. Reconciliation is applied

If multiple documents talk about the same thing, the system tries to compare them.

For example:

- salary across `Form 16` and `AIS`
- TDS across `Form 16`, `26AS`, and `AIS`
- interest across bank docs, `26AS`, and `AIS`

The item is then marked as:

- `supported`
- `conflicted`
- `unsupported`
- `unverified`

That result is stored directly on the review item so the API and gap logic can use it.

#### 10. Gap analysis runs

The backend then asks:

- what important data is still missing?
- which claims are unsupported?
- which review items are unresolved?
- which documents are missing?
- are there year mismatches or conflicts?

The answers become `gap_items`.

These are what tell the user what still needs attention before later phases.

### Worker Flow

The worker is intentionally thin.

It does not contain the parser rules itself.

Instead, it:

- wakes up on a fixed interval
- checks database and LLM reachability
- calls the backend internal endpoint for “run next pending job”

The backend then does the actual job execution.

So the worker is best thought of as:

- a poller
- a trigger
- a lightweight orchestrator

not the place where business logic lives.

### Database Schema Shape

The database is PostgreSQL, and the application tables live in the `app` schema.

The schema is easiest to understand as a few groups.

#### Filing and profile group

These tables define the filing workspace:

- filings
- taxpayer profile related tables
- supporting profile detail tables such as bank account and residency data

These tables answer:

- who is filing?
- for which year?
- what profile data is known?

#### Document intake group

These tables store uploaded document information:

- documents
- document_versions
- document_storage_refs
- document_upload_events

These tables answer:

- what was uploaded?
- where is the file stored?
- what version is current?
- what changed over time?

#### Phase 3 processing group

These tables represent document understanding:

- processing_jobs
- document_validation_results
- raw_extractions
- parsed_fields
- field_provenance
- normalized_tax_items
- foreign_income_events

These tables answer:

- what happened during processing?
- what did we extract?
- where did it come from?
- what tax-relevant candidates did we derive?

#### Phase 4 review group

These tables represent user-facing review state:

- category_assignments
- manual_overrides
- review_sessions
- gap_items
- gap_resolutions

These tables answer:

- what does the system think this item is?
- what did the user accept or change?
- is the item supported or conflicted?
- what is still missing?

### Modularity

The application is intentionally split into layers, and each layer has a different job.

#### 1. Routes

The route files expose HTTP endpoints.

They should mainly:

- validate incoming API requests
- load DB session dependencies
- call service functions
- return response models

They are the API boundary, not the core logic layer.

#### 2. Schemas

The schema files define API request and response contracts.

They protect the API layer from leaking raw ORM objects or random dict structures.

#### 3. Models

The model files define the database schema in ORM form.

They explain what the system stores and how the stored entities relate to each other.

#### 4. Services

The service files are where most real behavior lives.

In this codebase:

- `storage.py` handles file persistence concerns
- `processing.py` handles document understanding
- `review.py` handles review, reconciliation, and gaps

This is the most important modular split in the current backend.

#### 5. Worker

The worker stays separate from backend services so processing can be run asynchronously without putting long-running loops inside the API process.

### Why This Modularity Matters

This modular structure makes the app easier to evolve because:

- file storage logic is separate from parsing logic
- parsing logic is separate from review logic
- review logic is separate from API transport
- worker orchestration is separate from business logic
- database structure is separate from request/response structure

That means future work can happen with less accidental coupling.

Examples:

- a new document parser usually belongs in `services/processing.py`
- a new review action usually belongs in `services/review.py` plus `api/routes/review.py`
- a new persisted state often means changing a model and a migration
- a new endpoint usually means touching route + schema + service, not everything

### Best Mental Model For A New Team Member

If you are new, the easiest mental model is:

1. `filing` is the workspace
2. `document` is the uploaded evidence
3. `processing` turns evidence into extracted machine-readable candidate data
4. `review` turns candidate data into human-correctable filing state
5. `gaps` describe what is still missing or risky
6. `worker` just keeps the pipeline moving

If you keep that model in mind, the rest of the file structure becomes much easier to understand.

## Top-Level Project Areas

### `/docs`

- `docs/requirements/requirements-tax-ai-assistant.md`
  Defines the product requirements and the intended end-user behavior.
- `docs/design/design-tax-ai-assistant.md`
  Describes the main system architecture and end-to-end design.
- `docs/design/phase-wise-design-tax-ai-assistant.md`
  Breaks the build into project phases.
- `docs/design/canonical-parsing-contract.md`
  Freezes the canonical extracted-field vocabulary used by parsers and normalization.
- `docs/design/phase3-phase4-robustness-roadmap.md`
  Tracks the hardening plan before Phase 5.
- `docs/design/phase5-readiness-review.md`
  Records the formal Phase 5 readiness decision and remaining blockers.
- `docs/design/file-responsibility-map.md`
  This file. It is the codebase file guide.
- `docs/deployment/deployment-tax-ai-assistant.md`
  Explains deployment setup and local runtime assumptions.
- `docs/decisions/*.md`
  Architectural decision records for the LLM, relational DB, and vector DB choices.

### `/deployment`

- `deployment/docker-compose.yml`
  Brings up the local stack: Postgres, LLM, backend, worker, and frontend.
- `deployment/test-fixtures/*`
  Input samples and regression fixtures used to validate document parsing, review, gaps, reconciliation, and edge cases.
- `deployment/phase4_api_smoke_test.sh`
  Manual API smoke test for Phase 4 review/gap flows.
- `deployment/phase34_golden_test.py`
  Golden regression runner for the implemented Phase 3 and Phase 4 document scenarios.

## Backend Overview

The backend is a FastAPI application that:

- stores filings and uploaded documents
- parses and validates documents
- normalizes extracted data into tax candidates
- manages review state and gap analysis
- exposes APIs for the frontend, worker, and test scripts

## Backend Runtime Files

### `deployment/backend/Dockerfile`

- Builds the backend container image.
- Installs Python dependencies and OCR/PDF-related system packages.
- Copies the backend code and startup script into the container.

### `deployment/backend/requirements.txt`

- Python dependency list for the backend.
- Includes FastAPI, SQLAlchemy, Alembic, HTTP client support, OCR/PDF libraries, and multipart upload support.

### `deployment/backend/start.sh`

- Container startup entrypoint for the backend.
- Runs migrations and then starts the FastAPI server process.

### `deployment/backend/alembic.ini`

- Alembic configuration file used by migration commands.

## Backend Migrations

### `deployment/backend/alembic/env.py`

- Connects Alembic to the app’s SQLAlchemy metadata and migration environment.

### `deployment/backend/alembic/script.py.mako`

- Template Alembic uses when generating new migration files.

### `deployment/backend/alembic/versions/20260525_01_phase0_foundation.py`

- Phase 0 schema foundation.
- Creates base application schema and extension-level DB setup required at project start.

### `deployment/backend/alembic/versions/20260525_02_phase1_filing_workspace.py`

- Phase 1 schema.
- Adds filing workspace tables and taxpayer-profile-related data structures.

### `deployment/backend/alembic/versions/20260526_01_phase2_document_intake.py`

- Phase 2 schema.
- Adds document storage, document versions, upload event tracking, and related intake structures.

### `deployment/backend/alembic/versions/20260609_01_phase3_parsing_extraction_normalization.py`

- Phase 3 schema.
- Adds processing jobs, validation results, raw extractions, parsed fields, provenance, normalized tax items, and foreign-income event storage.

### `deployment/backend/alembic/versions/20260609_02_phase4_review_gap_analysis.py`

- Phase 4 schema.
- Adds review sessions, category assignments, manual overrides, gap items, and gap resolutions.

### `deployment/backend/alembic/versions/20260612_01_phase4_reconciliation_state.py`

- Step 6 schema extension.
- Adds reconciliation status and reconciliation context fields to review items.

## Backend App Package

### `deployment/backend/app/__init__.py`

- Marks `app` as a Python package.

### `deployment/backend/app/main.py`

- FastAPI application entrypoint.
- Registers all API routers.
- Runs startup-time storage creation and health checks for DB and LLM.

### `deployment/backend/app/config.py`

- Backend settings loader.
- Reads environment variables for DB, LLM, and local storage paths.

## Backend API Layer

### `deployment/backend/app/api/__init__.py`

- Marks the API package.

### `deployment/backend/app/api/routes/__init__.py`

- Marks the route package.

### `deployment/backend/app/api/routes/health.py`

- Health and readiness endpoints.
- Reports backend, database, and LLM status.

### `deployment/backend/app/api/routes/filings.py`

- Filing workspace endpoints.
- Handles creating, listing, fetching, duplicating, and submitting filings.
- Handles taxpayer profile create/update flows tied to a filing.

### `deployment/backend/app/api/routes/documents.py`

- Document intake endpoints.
- Handles upload, replacement/versioning, listing documents for a filing, and fetching individual documents.

### `deployment/backend/app/api/routes/processing.py`

- Phase 3 processing endpoints.
- Lets callers enqueue processing, run processing immediately, inspect jobs, and fetch Phase 3 outputs.
- Also exposes the internal worker-facing endpoint that runs the next pending job.

### `deployment/backend/app/api/routes/review.py`

- Phase 4 review and gap endpoints.
- Handles listing review items and gaps.
- Handles review actions such as accept, override, split, reject, mark-for-later, and manual add-item.
- Handles gap-resolution actions.

## Backend DB Layer

### `deployment/backend/app/db/__init__.py`

- Marks the DB package.

### `deployment/backend/app/db/base.py`

- Declares the SQLAlchemy declarative `Base`.
- Central anchor for ORM metadata used by migrations and models.

### `deployment/backend/app/db/session.py`

- Creates the SQLAlchemy engine and session factory.
- Exposes the request-scoped database session dependency used by API routes.

## Backend Model Layer

### `deployment/backend/app/models/__init__.py`

- Exports the backend’s ORM models and enums from one place.
- Used by the rest of the backend and by Alembic metadata loading.

### `deployment/backend/app/models/filing.py`

- Filing domain model.
- Defines filing lifecycle/status, filing year context, and relationships to profile and downstream artifacts.

### `deployment/backend/app/models/taxpayer_profile.py`

- Taxpayer profile model.
- Stores PAN and personal filing-profile information.

### `deployment/backend/app/models/bank_account.py`

- Stores bank account data associated with the taxpayer/profile domain.

### `deployment/backend/app/models/residency_detail.py`

- Stores residency-related details used by the tax profile domain.

### `deployment/backend/app/models/document.py`

- Document intake/storage model.
- Defines documents, document versions, storage references, upload events, and document processing status fields.

### `deployment/backend/app/models/processing.py`

- Phase 3 processing data model.
- Defines processing jobs, validation results, raw extractions, parsed fields, provenance, normalized tax items, and foreign-income events.

### `deployment/backend/app/models/review.py`

- Phase 4 review model.
- Defines review item status, reconciliation status, category assignments, manual overrides, review sessions, gap items, and gap resolutions.

## Backend Schema Layer

These files define the FastAPI/Pydantic request and response shapes.

### `deployment/backend/app/schemas/__init__.py`

- Marks the schema package.

### `deployment/backend/app/schemas/filing.py`

- API payloads for filing creation, profile updates, filing reads, and related filing views.

### `deployment/backend/app/schemas/document.py`

- API payloads for document upload, document reads, and document version responses.

### `deployment/backend/app/schemas/processing.py`

- API payloads for Phase 3 processing summaries, jobs, validation results, parsed fields, normalized items, and foreign-income events.

### `deployment/backend/app/schemas/review.py`

- API payloads for Phase 4 review items, review actions, reconciliation fields, gaps, and gap-resolution requests.

## Backend Service Layer

### `deployment/backend/app/services/__init__.py`

- Marks the service package.

### `deployment/backend/app/services/runtime_checks.py`

- Shared runtime health checks.
- Tests database connectivity and local LLM reachability.

### `deployment/backend/app/services/storage.py`

- Document storage helper layer.
- Creates storage directories, writes uploaded files, computes metadata/checksums, and handles document replacement/version creation.

### `deployment/backend/app/services/processing.py`

- The core Phase 3 engine.
- Responsible for:
  - enqueueing and running document processing jobs
  - validation logic
  - document type inference
  - OCR and native PDF extraction
  - structured file parsing for `JSON/XML/CSV/XLSX`
  - row-aware table extraction
  - extracted-field canonicalization
  - provenance creation
  - normalized tax-item generation
  - foreign-income event creation

This is the main “document understanding” file in the backend.

### `deployment/backend/app/services/review.py`

- The core Phase 4 engine.
- Responsible for:
  - creating review items from normalized tax items
  - accept/override/split/reject/mark-for-later/manual-add review actions
  - reconciliation across `Form 16`, `26AS`, `AIS`, salary/interest/deduction-support documents
  - review session tracking
  - document-aware gap computation
  - gap refresh and resolution support

This is the main “review, reconciliation, and gap analysis” file in the backend.

## Worker Overview

The worker is a lightweight polling process. It does not contain the parser logic itself. Instead, it:

- checks DB and LLM availability
- calls the backend’s internal processing endpoint
- lets the backend run the next pending job
- emits heartbeat/process logs

## Worker Runtime Files

### `deployment/worker/Dockerfile`

- Builds the worker container.
- Installs worker Python dependencies and copies worker code into the image.

### `deployment/worker/requirements.txt`

- Python dependency list for the worker.
- Includes the HTTP client and runtime support needed for backend polling and checks.

## Worker App Package

### `deployment/worker/app/__init__.py`

- Marks the worker app as a Python package.

### `deployment/worker/app/config.py`

- Worker settings loader.
- Reads environment variables for DB, LLM, backend URL, and poll interval.
- Includes fallback/default handling for blank poll-interval values.

### `deployment/worker/app/runtime_checks.py`

- Worker-side runtime health checks for database and LLM connectivity.

### `deployment/worker/app/worker.py`

- Worker entrypoint.
- Loops forever, heartbeat-checks DB and LLM, and calls the backend internal endpoint to process the next pending job.

## Practical Backend/Worker Mental Model

If you want the shortest accurate picture of how the code is organized:

- `main.py`
  Boots the backend.
- `routes/*.py`
  Define the public and internal API endpoints.
- `models/*.py`
  Define what gets stored in the database.
- `schemas/*.py`
  Define what the API accepts and returns.
- `services/storage.py`
  Handles file storage.
- `services/processing.py`
  Understands documents.
- `services/review.py`
  Turns extracted data into reviewable filing state.
- `worker.py`
  Keeps asking the backend to process the next queued job.

## Most Important Files For Ongoing Development

If you are changing behavior, these are usually the first files to inspect:

- [deployment/backend/app/services/processing.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/services/processing.py)
- [deployment/backend/app/services/review.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/services/review.py)
- [deployment/backend/app/api/routes/processing.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/api/routes/processing.py)
- [deployment/backend/app/api/routes/review.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/api/routes/review.py)
- [deployment/backend/app/models/processing.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/models/processing.py)
- [deployment/backend/app/models/review.py](/Users/vikrampande/AI%20CA%20Agent/deployment/backend/app/models/review.py)
- [deployment/worker/app/worker.py](/Users/vikrampande/AI%20CA%20Agent/deployment/worker/app/worker.py)

## Files Intentionally Not Covered In Detail

The following are not meaningful business-logic sources:

- `__pycache__/*`
- `.DS_Store`

They can be ignored for normal development and review.
