# Relational Database Evaluation Decision: PostgreSQL

## 1. Purpose

This document records the relational database decision for V1 of the Indian personal income tax filing assistant.

It is based on the broader comparison in [relational-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/relational-db-comparison-tax-assistant.md) and captures:

- the selected relational database
- why it was chosen
- why other options were not chosen as the primary V1 database
- implementation implications
- evaluation points to validate during integration

## 2. Selected Database

The selected V1 local relational database is:

- `PostgreSQL`

## 3. Why PostgreSQL Was Chosen

`PostgreSQL` was selected because it provides the best balance of:

- transactional reliability
- structured data modeling
- support for evolving schema complexity
- strong Docker support
- strong Python ecosystem
- compatibility with future architecture growth

This product needs the database to store authoritative structured state for:

- filings
- taxpayer profile data
- workflow and status transitions
- document metadata
- parsed structured records
- reviewed and corrected values
- calculation snapshots
- generated artifacts
- historical filings

`PostgreSQL` is a very strong fit for this style of application.

## 4. Decision Summary Against Requirements

## Requirement 1: Local only

Decision:

- Satisfied

Why:

- `PostgreSQL` can run fully locally with no cloud dependency.

## Requirement 2: Docker compatible

Decision:

- Satisfied

Why:

- `PostgreSQL` has a very strong official Docker story and is easy to run in a local containerized stack.

## Requirement 3: Must work well for the product requirements

Decision:

- Satisfied

Why:

- The product requires reliable transactional persistence and well-structured schema design.
- `PostgreSQL` handles this better than lighter or analytics-oriented alternatives.

## Requirement 4: Python integration

Decision:

- Satisfied

Why:

- `PostgreSQL` has mature Python support through drivers, ORMs, and migration tools.

## Requirement 5: Easy-to-use interface

Decision:

- Satisfied

Why:

- While not as lightweight as SQLite, `PostgreSQL` is still easy to work with due to excellent tooling and broad familiarity.

## 5. Why PostgreSQL Instead of SQLite

`SQLite` was the strongest simplicity-first option, but `PostgreSQL` was chosen because:

- the product already has meaningful workflow complexity
- background processing and API activity may overlap
- structured tax and document data will likely grow over time
- future evolution is easier with a server-based database
- `pgvector` becomes available as a clean vector-search option in the same stack

Tradeoff:

- more infrastructure than SQLite
- slightly more setup and operational overhead

This tradeoff is acceptable because it gives a stronger foundation for the product.

## 6. Why Other Options Were Not Selected

## SQLite

Why it was not chosen as primary:

- Best for the simplest possible single-user V1, but less attractive once you want a more extensible server-style architecture.

Why it still matters:

- It remains the best fallback if deployment simplicity becomes the dominant concern.

## DuckDB

Why it was not chosen as primary:

- It is more naturally suited to analytics-heavy workloads than workflow-heavy transactional application state.

Why it still matters:

- It could be useful later for analytical reporting or offline exploration, but not as the main application DB.

## MariaDB

Why it was not chosen as primary:

- It is viable, but it does not offer a stronger fit than `PostgreSQL` for this product.

Why it still matters:

- It would only become relevant if there were strong external ecosystem or team preferences.

## 7. Expected Role of PostgreSQL in the System

`PostgreSQL` will be the authoritative system of record for:

- filing metadata
- user-entered profile data
- document metadata
- extracted and normalized tax data
- category assignments
- user overrides
- gap analysis state
- calculation snapshots
- generated artifact references
- submission status

It should not store the original uploaded documents themselves as the primary storage mechanism. Those should remain in local file storage, with `PostgreSQL` storing references and metadata.

## 8. Risks of This Choice

## Risk 1: More operational complexity than SQLite

Impact:

- slightly heavier local deployment
- more configuration and maintenance work

Mitigation:

- use a simple Docker Compose setup
- keep the DB configuration minimal for local V1

## Risk 2: Over-engineering the first version

Impact:

- longer setup compared to a file-based embedded database

Mitigation:

- keep the schema lean
- avoid adding infrastructure-heavy extras unless justified

## Risk 3: Schema growth complexity

Impact:

- tax workflow evolution may create schema churn

Mitigation:

- use proper migrations from the start
- version domain rules cleanly by assessment year

## 9. Validation Checklist for Integration

Before finalizing implementation, validate that:

1. Filing creation, update, and locking flows work cleanly
2. Background worker writes do not create avoidable contention
3. Document metadata and parsed item storage patterns are efficient
4. Historical filing retrieval is simple and performant
5. Schema migrations are easy to run in Dockerized local environments
6. `pgvector` integration remains straightforward if enabled in the same DB

## 10. Final Decision

The V1 project will proceed with:

- `PostgreSQL` as the local relational database

This is the best choice because it offers the strongest balance of:

- local deployability
- Docker compatibility
- Python integration
- transactional reliability
- schema flexibility
- long-term architectural strength

## 11. Related Documents

- Requirements: [requirements-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/requirements/requirements-tax-ai-assistant.md)
- Relational DB comparison: [relational-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/relational-db-comparison-tax-assistant.md)
- Vector DB comparison: [vector-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/vector-db-comparison-tax-assistant.md)
