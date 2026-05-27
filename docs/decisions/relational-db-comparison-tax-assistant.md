# Local Relational Database Comparison for Indian Tax Filing Assistant

## 1. Purpose

This document compares relational database options for the Indian personal income tax filing assistant.

The comparison is based on these requirements:

- Must run locally with no external or cloud API dependency.
- Must run from Docker containers without issues where applicable.
- Must work well for the product requirements.
- Must integrate well with Python.
- Must expose an easy-to-use interface.

This product needs the relational database to store:

- filing records
- taxpayer profile data
- workflow states
- uploaded document metadata
- parsed and normalized structured data
- category assignments
- gap analysis results
- calculation snapshots
- generated artifacts
- historical filings

Important design context:

- V1 is single-user.
- V1 is local-first.
- V1 has meaningful structured workflow state, not just analytics.
- The database is the authoritative source of business data.

Because of that, correctness, simplicity, and transactional reliability matter more than scale.

## 2. Evaluation Criteria

Each option is evaluated on:

1. Local-only deployment viability
2. Docker friendliness
3. Python integration
4. Ease of interface and developer experience
5. Fit for a single-user transactional application
6. Operational complexity
7. Long-term flexibility

## 3. Candidate Options

## 3.1 SQLite

### What it is

SQLite is an embedded relational database stored in a local file. In Python, it is available through the standard library `sqlite3` module.

### Why it is a strong option

SQLite is a natural candidate because this product is:

- local-first
- single-user
- transactional
- relatively modest in concurrency needs

It offers the simplest possible deployment model while still giving strong relational behavior for application state.

### Pros

- Extremely simple to use
- No separate DB server required
- Built into Python via `sqlite3`
- Very low operational complexity
- Good fit for local single-user applications
- Easy file-based persistence
- Excellent choice for rapid V1 development

### Cons

- Less suitable for higher write concurrency
- Fewer advanced operational capabilities than PostgreSQL
- Less ideal if the architecture later grows into a multi-user or more concurrent system
- Some advanced DB patterns will need more care than in a server database

### Fit for this software

Very strong fit when:

- the product remains single-user
- local-first simplicity is a priority
- the worker/API concurrency remains moderate

### Overall assessment

Best default V1 choice for a local single-user tax application.

## 3.2 PostgreSQL

### What it is

PostgreSQL is a full-featured server-based relational database with strong transactional guarantees and excellent ecosystem support.

### Why it is a strong option

PostgreSQL is attractive because it is the most robust general-purpose relational option among the candidates and offers the cleanest path if the system grows in complexity later.

### Pros

- Strong transactional reliability
- Excellent schema and query capabilities
- Mature tooling and migration ecosystem
- Strong Python ecosystem
- Excellent Docker support through the official image
- Good fit for background workers plus API concurrency
- Strong future path if the product grows

### Cons

- More operational complexity than SQLite
- Requires a separate running DB service
- Heavier than necessary for the simplest possible V1

### Fit for this software

Very strong fit when:

- you want a future-ready foundation
- you expect more complex workflows, indexing, or background processing
- you prefer a server database from the start

### Overall assessment

Best long-term relational database option, but heavier than needed for the simplest V1.

## 3.3 DuckDB

### What it is

DuckDB is an embedded database designed primarily for analytical workloads. It can persist to a local file and has strong Python support.

### Why it is worth comparing

DuckDB is attractive in local Python applications, but its primary strength is analytics, not application-state-heavy transactional workflows.

### Pros

- Very strong Python integration
- Easy local file-based persistence
- Excellent analytical query capabilities
- Simple local setup

### Cons

- Better suited to analytics than OLTP-style application state
- Global/shared connection usage needs care in Python
- Less natural fit for workflow-driven transactional application data than SQLite or PostgreSQL

### Fit for this software

Reasonable only if:

- analytical exploration becomes unusually important
- you are intentionally optimizing for local analytics over standard app-database patterns

### Overall assessment

Interesting technically, but not a strong primary database choice for this product.

## 3.4 MariaDB

### What it is

MariaDB is a server-based relational database compatible with the MySQL ecosystem and supported by an official Python connector.

### Why it is worth comparing

MariaDB is a valid relational database choice, but it offers fewer specific advantages than PostgreSQL for this product.

### Pros

- Mature relational database
- Official Python connector
- Docker-friendly deployment
- Familiar operational model

### Cons

- Less compelling than PostgreSQL for structured, evolving application data
- Fewer obvious advantages for this product than either SQLite or PostgreSQL
- Adds server-database complexity without a clear benefit over PostgreSQL

### Fit for this software

Acceptable fit when:

- the team already prefers MariaDB/MySQL operationally

### Overall assessment

Viable, but not a top recommendation for this project.

## 4. Comparative Summary

| Option | Local-Only Fit | Docker Fit | Python Fit | Ease of Use | Best For | Main Drawback |
|---|---|---|---|---|---|---|
| SQLite | Excellent | N/A as separate server DB | Excellent | Excellent | simplest single-user local app state | limited concurrency and server-style features |
| PostgreSQL | Excellent | Excellent | Excellent | Very good | robust app database with future flexibility | more operational complexity |
| DuckDB | Excellent | Optional but not central | Excellent | Good | local analytics-heavy workflows | weaker fit for transactional app state |
| MariaDB | Excellent | Excellent | Good | Good | teams already aligned on MySQL/MariaDB | less compelling than PostgreSQL here |

## 5. Match Against Your Requirements

## Requirement 1: Local only, no cloud API

All listed options can satisfy this.

Best fit:

- SQLite
- PostgreSQL
- DuckDB
- MariaDB

## Requirement 2: Docker support

Strongest options:

- PostgreSQL
- MariaDB

Notes:

- PostgreSQL has a well-supported official Docker image.
- MariaDB also has a straightforward server-container model.
- SQLite does not need a dedicated DB container because it is embedded and file-based, but it can still be used inside the backend container.
- DuckDB is also embedded rather than typically run as a dedicated DB service.

## Requirement 3: Good fit for the product need

The product needs a reliable transactional database for:

- filing workflow state
- structured records
- user corrections
- historical data
- calculation snapshots

Best fit:

- SQLite if simplicity is the priority
- PostgreSQL if future flexibility is the priority

Less ideal:

- DuckDB because the workload is application-state-centric, not analytics-centric
- MariaDB because it does not offer a stronger fit than PostgreSQL here

## Requirement 4: Python integration

Best fit:

- SQLite through Python standard library `sqlite3`
- PostgreSQL through mature Python drivers and ORMs
- DuckDB through its official Python client

## Requirement 5: Easy-to-use interface

Best fit:

- SQLite for the simplest developer experience
- PostgreSQL for the best balance between ease and production-style robustness

## 6. Recommended Shortlist

## Option 1: Best Simple V1 Choice

### SQLite

Why:

- easiest local-first setup
- built into Python
- ideal for single-user local applications
- minimal operational burden

Choose this if:

- you want the simplest path to a solid V1

## Option 2: Best Future-Ready Choice

### PostgreSQL

Why:

- strongest long-term relational foundation
- clean server-database model
- excellent Docker support
- strong fit for richer future architecture

Choose this if:

- you want to invest in a more scalable DB foundation from day one

## Option 3: Not Recommended as Primary Choice

### DuckDB

Why:

- good database technology, but better for analytics than workflow-heavy app state

Choose this only if:

- you have an unusual need to optimize for analytical workflows first

## Option 4: Acceptable but Lower Priority

### MariaDB

Why:

- viable relational DB, but not stronger than PostgreSQL for this use case

Choose this only if:

- your team already strongly prefers MariaDB/MySQL

## 7. Recommendation for This Software

For this tax assistant, my recommendation is:

1. Choose `SQLite` if you want the best V1 fit for a single-user local-first application.
2. Choose `PostgreSQL` if you want a heavier but more future-ready relational foundation.
3. Do not choose `DuckDB` as the primary app database.
4. Do not choose `MariaDB` unless there is a strong external reason.

Reason:

- The product is currently single-user and local-first.
- The main DB workload is structured transactional application state.
- Simplicity matters because the system already has complexity in OCR, LLM orchestration, tax rules, and document workflows.

## 8. Suggested Decision

If you want a practical V1 decision today:

- choose `SQLite` for the simplest and strongest V1 fit
- choose `PostgreSQL` only if you intentionally want more infrastructure from the start

My default recommendation:

- `SQLite`

My long-term recommendation:

- `PostgreSQL` only if future product scope expands significantly

## 9. Sources

- Python `sqlite3` docs: [docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)
- PostgreSQL Docker official image: [hub.docker.com/_/postgres](https://hub.docker.com/_/postgres)
- Docker PostgreSQL guide: [docs.docker.com/guides/postgresql](https://docs.docker.com/guides/postgresql/)
- DuckDB Python docs: [duckdb.org/docs/current/clients/python/overview](https://duckdb.org/docs/current/clients/python/overview)
- DuckDB docs home: [duckdb.org/docs/current](https://duckdb.org/docs/current/)
- MariaDB Connector/Python docs: [mariadb.com/docs/connectors/mariadb-connector-python](https://mariadb.com/docs/connectors/mariadb-connector-python)
