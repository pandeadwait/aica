# Vector Database Evaluation Decision: pgvector

## 1. Purpose

This document records the vector database decision for V1 of the Indian personal income tax filing assistant.

It is based on the broader comparison in [vector-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/vector-db-comparison-tax-assistant.md) and captures:

- the selected vector database technology
- why it was chosen
- why other options were not chosen as the primary V1 vector solution
- implementation implications
- evaluation points to validate during integration

## 2. Selected Vector Database Technology

The selected V1 local vector database technology is:

- `pgvector`

This means vector retrieval will run inside the selected relational database:

- `PostgreSQL`

## 3. Why pgvector Was Chosen

`pgvector` was selected because it offers the best balance of:

- local-only deployment
- Docker compatibility
- Python integration
- low architectural sprawl
- strong metadata handling through PostgreSQL
- a clean fit for the actual retrieval use case

The current vector retrieval use case is:

- retrieving local tax guidance documents
- retrieving ITR templates and template fragments
- filtering by metadata such as:
  - assessment year
  - ITR form
  - template type
  - rule version

Because the corpus is expected to be curated and moderate in size, the simplicity of keeping vectors and metadata in the same PostgreSQL database is a major advantage.

## 4. Decision Summary Against Requirements

## Requirement 1: Local only

Decision:

- Satisfied

Why:

- `pgvector` runs entirely inside local `PostgreSQL`.

## Requirement 2: Docker compatible

Decision:

- Satisfied

Why:

- The solution runs inside the containerized PostgreSQL stack.

## Requirement 3: Must work well for the actual product need

Decision:

- Satisfied

Why:

- The product needs retrieval over a curated corpus of tax guidance documents and ITR template content.
- Metadata-based filtering is important.
- `pgvector` works well because PostgreSQL can manage both the structured metadata and the vector search layer.

## Requirement 4: Python integration

Decision:

- Satisfied

Why:

- Python can access vector retrieval through normal PostgreSQL drivers and query layers.

## Requirement 5: Easy-to-use interface

Decision:

- Satisfied

Why:

- The main advantage of `pgvector` is architectural simplicity: no separate vector service is required.

## 5. Why pgvector Instead of Chroma

`Chroma` was the simplest pure vector-database experience, but `pgvector` was chosen because:

- `PostgreSQL` is already selected as the relational database
- keeping metadata and vectors together reduces moving parts
- tax guidance and ITR template retrieval is likely to depend heavily on metadata filters
- a single-DB architecture is easier to reason about for this product

Tradeoff:

- `Chroma` may feel more vector-first and simpler for some retrieval-only developer workflows

This tradeoff is acceptable because the overall system becomes cleaner with `pgvector`.

## 6. Why pgvector Instead of Qdrant

`Qdrant` was the strongest dedicated vector DB candidate, but `pgvector` was chosen because:

- the current retrieval workload is moderate
- a separate vector service is not clearly necessary
- PostgreSQL already provides the required metadata model
- the product benefits from fewer moving parts in V1

Tradeoff:

- `Qdrant` may become more attractive if retrieval becomes a much larger standalone capability

## 7. Why Other Options Were Not Selected

## Chroma

Why it was not chosen as primary:

- Very strong simplicity option, but it adds another distinct retrieval layer when PostgreSQL already exists.

Why it still matters:

- It remains a viable fallback if a lighter vector-first developer experience is later preferred.

## Qdrant

Why it was not chosen as primary:

- Strong dedicated vector service, but heavier than needed for the current retrieval scope.

Why it still matters:

- It remains the best alternate if retrieval requirements become much richer or more independent.

## Milvus

Why it was not chosen as primary:

- Too heavy for the current V1 use case.

Why it still matters:

- It could become relevant only if the retrieval layer grows substantially beyond the current design.

## FAISS

Why it was not chosen as primary:

- It is a library, not a full vector database solution.

Why it still matters:

- It remains useful only for highly custom retrieval-engine work, which is not the current goal.

## 8. Expected Role of pgvector in the System

`pgvector` should be used for:

- semantic retrieval of tax guidance snippets
- semantic retrieval of ITR templates and template fragments
- retrieval assisted by relational filters such as year, ITR form, template category, or rule version

`pgvector` should not be used as:

- the primary storage system for authoritative business data
- a replacement for relational schema design

The likely pattern is:

1. store guidance/template chunks in PostgreSQL tables
2. store embeddings in vector columns
3. filter candidate rows using metadata
4. apply vector similarity search within the filtered scope

## 9. Risks of This Choice

## Risk 1: Retrieval needs may outgrow a PostgreSQL-native vector approach

Impact:

- future vector-specific tuning may become harder

Mitigation:

- keep the retrieval layer abstracted in Python
- make it possible to swap to Qdrant later if needed

## Risk 2: Embedding/query design may matter more than the DB choice

Impact:

- poor retrieval quality if chunking and metadata design are weak

Mitigation:

- design guidance/template chunking carefully
- include strong metadata fields from the beginning

## Risk 3: Mixing business and retrieval data in one DB can create coupling

Impact:

- schema design becomes more important

Mitigation:

- isolate retrieval tables clearly
- keep ingestion and query logic modular

## 10. Validation Checklist for Integration

Before finalizing implementation, validate that:

1. Tax guidance chunks can be filtered cleanly by assessment year and topic
2. ITR template chunks can be filtered cleanly by ITR form and year
3. Retrieval quality is acceptable for the curated corpus size
4. Python integration remains simple through PostgreSQL access libraries
5. Query latency is acceptable for local interactive use
6. The retrieval layer can be abstracted enough to swap out later if required

## 11. Final Decision

The V1 project will proceed with:

- `pgvector` as the local vector database technology

This is the best choice because it offers the strongest balance of:

- local deployability
- Docker compatibility
- Python integration
- metadata-aware retrieval
- architectural simplicity
- alignment with the already selected PostgreSQL stack

## 12. Related Documents

- Requirements: [requirements-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/requirements/requirements-tax-ai-assistant.md)
- Relational DB comparison: [relational-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/relational-db-comparison-tax-assistant.md)
- Vector DB comparison: [vector-db-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/vector-db-comparison-tax-assistant.md)
