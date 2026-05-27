# Local Vector Database Comparison for Indian Tax Filing Assistant

## 1. Purpose

This document compares multiple local vector database options for the Indian personal income tax filing assistant.

The comparison is based on these requirements:

- Must run locally with no external or cloud API dependency.
- Must run from Docker containers without issues.
- Must work well for the actual product need.
- Must integrate well with Python.
- Must expose an easy-to-use interface.

Current architecture decision already made:

- the primary relational database for V1 is `PostgreSQL`

Important design note:

- A vector database is optional for V1.
- The current product does not need a large-scale RAG platform by default.
- The likely V1 uses for a vector store are:
  - retrieving local tax guidance documents
  - retrieving local ITR templates and related reference snippets
  - matching uploaded documents to known layouts or parser templates
  - assisting the local LLM with focused context retrieval

In this project, the vector database is expected to store a curated internal corpus such as:

- tax guidance documents organized by topic and assessment year
- ITR templates and template fragments organized by ITR form and year
- parser-template support content
- internal help/reference content

Because of that, ease of use and low operational complexity matter more than raw scale.

## 2. Evaluation Criteria

Each option is evaluated on:

1. Local-only deployment viability
2. Docker friendliness
3. Python integration
4. Ease of interface and developer experience
5. Fit for retrieval of tax guidance documents and ITR templates
6. Operational complexity
7. Long-term flexibility

Additional weighting for this product:

- metadata filtering by `assessment_year`, `itr_form`, `template_type`, `section`, and `rule_version`
- predictable retrieval from a relatively small curated corpus
- simple content ingestion and updates from Python

## 3. Candidate Options

## 3.1 Chroma

### What it is

Chroma is an open-source vector database/search system with a Python-friendly API and a simple developer experience.

### Why it is a strong option

Chroma is attractive for this project because it is very easy to start with in Python and has a low-complexity mental model for document collections and retrieval.

### Pros

- Very easy Python-first developer experience
- Simple collection-based interface
- Good fit for small to medium local retrieval workloads
- Easy to prototype with
- Supports local persistence
- Supports client-server mode
- Containerized deployment is available
- Good fit for small curated corpora such as tax guidance documents and ITR template chunks

### Cons

- Less infrastructure maturity than more specialized vector databases like Qdrant
- Some teams find it best for simpler retrieval use cases rather than more demanding production setups
- If retrieval requirements become more complex, it may be outgrown sooner
- Metadata-heavy filtering may feel less robust than in a more dedicated vector database

### Fit for this software

Good fit when:

- the vector store is mainly used for tax guidance retrieval and ITR template retrieval
- fast implementation matters more than advanced indexing features

### Overall assessment

One of the best choices if simplicity is the top priority.

## 3.2 Qdrant

### What it is

Qdrant is a purpose-built vector search database with REST and gRPC APIs, a web UI, and a strong Python client.

### Why it is a strong option

Qdrant is attractive because it is more database-like and operationally mature than lighter developer-first options, while still being easy to run locally in Docker.

### Pros

- Strong local Docker story
- Official Python client
- REST API and gRPC API
- Web UI/dashboard available locally
- Strong metadata filtering support
- Good long-term flexibility if retrieval grows in importance
- Well suited for collections with structured payload metadata
- Strong fit for payload fields like `assessment_year`, `itr_form`, `template_type`, `source_section`, and `rule_version`

### Cons

- Slightly heavier than Chroma for a simple V1 use case
- More infrastructure than you may need if retrieval is only a helper feature

### Fit for this software

Very good fit when:

- retrieval quality and filtering matter
- you want a dedicated vector service
- you want something stronger than a lightweight embedded option
- you expect template and guidance retrieval to rely heavily on metadata filters

### Overall assessment

Best dedicated vector DB option for this project if you want a clear long-term path and a clean service boundary.

## 3.3 pgvector

### What it is

pgvector is a PostgreSQL extension for vector similarity search.

### Why it is a strong option

pgvector is attractive because it keeps structured application data and vector search in the same database.

### Pros

- Works inside PostgreSQL
- Lets you keep metadata and vectors together
- Strong SQL and relational querying support
- Good Python ecosystem through standard PostgreSQL clients
- Good option if PostgreSQL is already selected as the primary app database
- Exact and approximate nearest-neighbor support
- Easy to model rich tax guidance and ITR template metadata in relational tables

### Cons

- Not a standalone vector database
- Ties the vector decision to a PostgreSQL decision
- Less appealing if the primary app DB is SQLite
- More setup than a purely embedded Python-first option if Postgres is otherwise unnecessary

### Fit for this software

Very good fit when:

- PostgreSQL is the main application database
- you want fewer moving parts
- retrieval is useful but not important enough to justify a separate vector service
- you want SQL-first control over guidance/template metadata and retrieval rules

### Overall assessment

One of the strongest options for this project now that `PostgreSQL` is the selected relational database.

## 3.4 Milvus

### What it is

Milvus is a full vector database platform that supports both embedded-style local development and Docker deployment for larger setups.

### Why it is a strong option

Milvus is attractive when you expect retrieval and vector operations to become more central over time.

### Pros

- Strong vector-database feature set
- Good Python client support
- Supports local development and Docker deployment
- Good long-term scale potential

### Cons

- More infrastructure weight than the likely V1 needs
- More complexity than necessary for simple ITR template retrieval or tax guidance retrieval
- Best value appears when scale or advanced retrieval needs are higher

### Fit for this software

Reasonable fit when:

- you expect the product to evolve into a more retrieval-heavy platform
- you want a more dedicated vector platform from the beginning
- you expect the guidance/template corpus to grow significantly over time

### Overall assessment

Capable, but likely more than V1 needs.

## 3.5 FAISS

### What it is

FAISS is a vector similarity library rather than a full database.

### Why it is worth comparing

FAISS is important to consider because it is powerful, local, and Python-friendly, but it is not really a database product with persistence and service semantics in the same way as Chroma, Qdrant, or Milvus.

### Pros

- Very strong vector search performance
- Excellent Python support
- Fully local
- Great if you want full control over indexing behavior

### Cons

- Not a full vector database
- No built-in application-level metadata store
- No built-in service model or dashboard by default
- You must build more of the persistence and retrieval management yourself
- You must also build your own metadata filtering flow for year/form/template retrieval

### Fit for this software

Good fit only when:

- you intentionally want a lower-level retrieval library
- your team wants to build its own storage and retrieval layer

### Overall assessment

Very strong library, but not the best default choice for this product if the goal is an easy-to-use vector DB.

## 4. Comparative Summary

| Option | Local-Only Fit | Docker Fit | Python Fit | Ease of Use | Best For | Main Drawback |
|---|---|---|---|---|---|---|
| Chroma | Excellent | Good | Excellent | Excellent | simple retrieval of tax guidance and ITR template chunks | may be outgrown sooner |
| Qdrant | Excellent | Excellent | Excellent | Very good | metadata-rich guidance/template retrieval | slightly more infrastructure |
| pgvector | Excellent | Excellent | Excellent | Good | SQL-friendly guidance/template retrieval inside PostgreSQL | somewhat less specialized than a dedicated vector DB |
| Milvus | Excellent | Excellent | Excellent | Good | larger long-term vector workloads | more complex than needed for V1 |
| FAISS | Excellent | N/A as a DB service | Excellent | Moderate | low-level custom retrieval | not a full DB |

## 5. Match Against Your Requirements

## Requirement 1: Local only, no cloud API

All listed options can satisfy this.

Best fit:

- Chroma
- Qdrant
- pgvector
- Milvus
- FAISS

## Requirement 2: Docker support

Strongest options:

- Qdrant
- pgvector
- Milvus
- Chroma

Notes:

- Qdrant has a very straightforward local Docker flow.
- pgvector works well if PostgreSQL is already being containerized.
- Milvus supports Docker, but is heavier.
- Chroma supports client-server mode and container deployment, though its simplest usage is often more Python-centric.

## Requirement 3: Good fit for the product need

The product’s specific retrieval need is:

- retrieve local tax guidance documents
- retrieve ITR templates and related template snippets
- filter by metadata such as assessment year, ITR form, and template category

The product does not need large-scale RAG infrastructure in V1.

Best fit:

- Chroma if simplicity is the priority and the corpus remains curated and moderate in size
- Qdrant if you want a stronger dedicated vector service with better filtering
- pgvector because PostgreSQL is already chosen and SQL-centric metadata control is likely valuable here

Less ideal:

- Milvus if you want the lightest stack
- FAISS if you want a database rather than a library

## Requirement 4: Python integration

All options work with Python, but the easiest are:

- Chroma
- Qdrant
- pgvector through standard Postgres drivers and ORMs
- Milvus via `pymilvus`

## Requirement 5: Easy-to-use interface

Best fit:

- Chroma for the simplest Python developer experience
- Qdrant for the best balance of usability and dedicated-service maturity
- pgvector for the simplest overall architecture if you want to avoid a separate vector service

## 6. Recommended Shortlist

## Option 1: Best Simple V1 Choice

### Chroma

Why:

- easiest to start with
- Python-first
- low operational overhead
- good fit for modest retrieval needs
- good fit for curated tax guidance and ITR template retrieval

Choose this if:

- vector retrieval is a helper feature, not a core platform capability

## Option 2: Best Dedicated Vector DB Choice

### Qdrant

Why:

- strongest dedicated vector-service option for this project
- excellent local Docker support
- strong Python client
- better long-term flexibility than Chroma
- especially strong when guidance/template retrieval depends on metadata filters

Choose this if:

- you want a cleaner long-term service boundary
- you want strong metadata filtering and dedicated vector operations

## Option 3: Best PostgreSQL-Native Choice

### pgvector

Why:

- no extra vector service needed
- keeps vectors and relational metadata together
- operationally elegant if PostgreSQL is already in the stack
- a good fit if guidance/template content is heavily versioned and richly described

Choose this if:

- you want to reuse the already selected PostgreSQL stack
- you want vector retrieval and metadata filtering in one database

## Option 4: Best If You Expect Heavy Retrieval Growth

### Milvus

Why:

- strongest “future scale” option among the compared full DBs

Choose this if:

- retrieval is expected to become much more central than it appears today

## 7. Recommendation for This Software

For this tax assistant, my recommendation is:

1. Do not force a vector database into the earliest V1 unless retrieval clearly improves document-template matching or tax-guidance assistance.
2. If you want the simplest overall architecture now that `PostgreSQL` is already selected, `pgvector` is a strong first choice.
3. Choose `Chroma` if you want the easiest developer experience and do not mind a separate vector component style.
4. Choose `Qdrant` instead if you want a more robust dedicated vector service from the beginning.

Reason:

- The current use case is likely modest:
  - retrieve local tax guidance documents
  - retrieve ITR templates and template fragments
  - help the assistant ground explanations
- The relational database is already fixed as `PostgreSQL`, which makes `pgvector` materially more attractive than before.
- That does not automatically justify a heavier vector platform.
- Simplicity matters because the core product complexity is already high in parsing, tax rules, and workflow.

## 8. Suggested Decision

If you want a practical V1 decision today:

- choose `pgvector` if you want the cleanest fit with the already selected `PostgreSQL` stack
- choose `Chroma` if you want the easiest developer experience for a curated local guidance/template corpus
- choose `Qdrant` if you want the strongest dedicated vector DB for metadata-rich guidance/template retrieval

My default recommendation:

- `pgvector` as the most architecture-aligned default now that `PostgreSQL` is selected

My long-term recommendation:

- `Qdrant` if retrieval becomes a meaningful standalone part of the architecture or if dedicated vector-service features become important early

## 9. Sources

- Chroma README and Python usage: [github.com/chroma-core/chroma](https://github.com/chroma-core/chroma)
- Chroma docs/reference home: [docs.trychroma.com/reference](https://docs.trychroma.com/reference)
- Qdrant local quickstart: [qdrant.tech/documentation/quick-start](https://qdrant.tech/documentation/quick-start/)
- Qdrant Docker image: [hub.docker.com/r/qdrant/qdrant](https://hub.docker.com/r/qdrant/qdrant)
- Qdrant API reference: [api.qdrant.tech](https://api.qdrant.tech/)
- pgvector official repository: [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
- Milvus quickstart: [milvus.io/docs/quickstart.md](https://milvus.io/docs/quickstart.md)
- Milvus install overview: [milvus.io/docs/install-overview.md](https://milvus.io/docs/install-overview.md)
- FAISS repository: [github.com/facebookresearch/faiss](https://github.com/facebookresearch/faiss)
- FAISS getting started: [github.com/facebookresearch/faiss/wiki/Getting-started](https://github.com/facebookresearch/faiss/wiki/Getting-started)
