# Phase 3 and Phase 4 Robustness Roadmap

## 1. Purpose

This roadmap defines the work required to make Phase 3 and Phase 4 robust enough for mainstream Indian personal tax filing workflows before Phase 5 begins.

The goal is not only to parse happy-path fixtures, but to reliably handle normal real-world documents, including mixed formats, issuer variations, noisy PDFs, OCR edge cases, and cross-document inconsistencies.

## 2. Why This Exists

The current system now supports:

- filing creation and profile management
- document upload and versioning
- PDF and OCR processing
- structured-file parsing
- first parser support for:
  - `Form 16`
  - `Form 26AS`
  - `AIS`
  - foreign-income-oriented documents
- review items
- overrides and split actions
- basic gap analysis

However, this is not yet sufficient to claim that normal user document sets will parse reliably enough for deterministic tax calculation.

Before Phase 5, the system must become strong in:

- parser breadth
- parser correctness
- OCR resilience
- table extraction
- cross-document reconciliation
- review completeness
- gap-analysis accuracy
- regression test coverage

## 3. Guiding Principles

- Deterministic tax logic remains separate from LLM behavior.
- Low-confidence or conflicting extraction must degrade into review, not silent guesses.
- Every supported document class should have explicit parser expectations.
- Every parser bug should become a permanent regression fixture.
- Phase 5 should only consume reviewed, supported, traceable values.

## 4. Requirements This Roadmap Closes

This roadmap is meant to close the remaining gaps from:

- [requirements-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/requirements/requirements-tax-ai-assistant.md)
- [design-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/design/design-tax-ai-assistant.md)
- [phase-wise-design-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/design/phase-wise-design-tax-ai-assistant.md)

The most important unmet requirements are currently:

- broader first parser set for common personal filing documents
- table extraction robustness
- TDS reconciliation across `Form 16`, `26AS`, and `AIS`
- deduction-proof-aware gap analysis
- user review completeness for uncertain or conflicting items
- document conflict handling
- support for realistic multi-document filing scenarios

## 5. Milestones

### Milestone 1: Core Parser Breadth

Objective:
Expand the first parser set so common non-foreign personal filing documents can be handled reliably.

Target document classes:

- salary slips
- interest certificates
- bank statements
- capital gains statements
- broker statements
- rent receipts
- home loan certificates
- insurance premium proofs
- PPF / ELSS proofs
- donation receipts
- tuition fee receipts
- medical insurance documents

Deliverables:

- document-type adapters for each priority class
- canonical field-name mapping per adapter
- document-specific normalized-item rules
- document-type detection improvements
- fixture set for each supported class

Exit criteria:

- each target class has at least one clean digital fixture and one noisy or variant fixture
- each target class produces expected extracted fields and normalized items
- unsupported or weakly parsed variants degrade into `needs_review`

### Milestone 2: Table Extraction and PDF Robustness

Objective:
Handle the table-heavy and layout-heavy documents that are common in real filing workflows.

Focus areas:

- 26AS row parsing
- AIS section parsing
- broker transaction rows
- capital gains statement rows
- salary breakup tables
- bank statement interest rows

Deliverables:

- row/header detection helpers
- section-aware parsing for repeated blocks
- layout-tolerant PDF text interpretation
- OCR preprocessing improvements
- confidence downgrades for weak tabular extraction

Exit criteria:

- repeated rows are extracted without collapsing into one field
- major columns map into stable canonical names
- malformed or partial tables trigger review instead of false precision

### Milestone 3: Reconciliation Layer

Objective:
Compare overlapping data across documents and surface match, mismatch, duplication, and missing-support conditions.

Required reconciliations:

- salary and TDS across `Form 16`, `26AS`, and `AIS`
- interest income across bank documents, `AIS`, and `26AS`
- dividends across broker statements and `AIS`
- capital gains across broker/capital gains statements and `AIS`
- duplicate evidence across multiple uploads

Deliverables:

- reconciliation service
- conflict markers in stored review state
- document-supported confidence adjustments
- gap rules for unsupported credits or unsupported income claims

Exit criteria:

- matching values reduce ambiguity
- conflicting values are visible in review state
- missing supporting documents trigger targeted gaps

### Milestone 4: Review Workflow Completion

Objective:
Complete the Phase 4 user correction model so normal parsing uncertainty is manageable without manual database cleanup.

Missing capabilities to add:

- reject action
- mark-for-later action
- manual add-item action
- conflict review status
- richer override payloads for document-backed corrections
- explicit resolution pathways for “not applicable” gaps

Deliverables:

- API support for missing review actions
- persistence model updates where needed
- gap-resolution state transitions
- review-state rules that distinguish supported, conflicted, rejected, and deferred items

Exit criteria:

- all expected user actions from the Phase 4 design are available
- unresolved critical review states can block later phases
- users can complete review without direct data surgery

### Milestone 5: Regression Fixtures and Golden Tests

Objective:
Convert parser behavior into a repeatable, trusted contract.

Fixture matrix required per supported document type:

- clean digital source
- scanned/OCR source
- issuer/layout variant
- missing-field variant
- wrong-year variant
- duplicate variant
- conflict variant where applicable

Golden assertions should cover:

- detected document type
- validation state
- year match outcome
- parsed field count and key fields
- normalized item categories
- gap outcomes
- review-state shape

Exit criteria:

- every supported document class has golden tests
- every bug fixed in parsing or review adds a permanent regression fixture
- CI-level parser confidence exists before Phase 5

## 6. Priority Order

Recommended implementation order:

1. salary slips
2. interest certificates and bank statements
3. deduction-proof document classes
4. broker and capital gains statement parsing
5. reconciliation between `Form 16`, `26AS`, and `AIS`
6. review workflow completion
7. full regression fixture library

Rationale:

- salary, TDS, and bank-interest flows are central to mainstream ITR-1 and ITR-2 workflows
- deduction-proof support is necessary for realistic tax-saving scenarios
- reconciliation is essential before deterministic tax calculation can be trusted

## 7. Technical Workstreams

### 7.1 Parser Adapter Workstream

Build parser modules or helper branches for each supported document class.

Each adapter should define:

- detection hints
- expected canonical fields
- required fields
- optional fields
- extraction strategy
- normalization strategy
- fallback behavior

### 7.2 Canonical Schema Workstream

Stabilize the normalized item model around mainstream Indian filing data.

This includes:

- salary components
- TDS credits
- interest income
- dividend income
- capital gains support rows
- proof-backed deductions
- supporting metadata used by gap analysis

### 7.3 OCR Hardening Workstream

Improve scan handling through:

- preprocessing
- better image scaling/contrast assumptions
- OCR failure classification
- page quality indicators
- explicit low-confidence review routing

### 7.4 Reconciliation Workstream

Add comparison rules and conflict persistence for multi-document filings.

### 7.5 Review and Gap Workstream

Complete the user workflow so every ambiguous or unsupported state has a clear path forward.

## 8. Test Strategy

### 8.1 Fixture Policy

Every supported document type must have:

- at least 2 happy-path fixtures
- at least 2 variant or degraded fixtures
- expected output notes kept beside the fixture or in test definitions

### 8.2 Golden Test Policy

Golden tests should verify:

- validation summary
- inferred document type
- extracted core fields
- normalized categories
- gap outcomes
- review-item states after typical actions

### 8.3 Manual QA Checklist

For every major parser addition:

- upload file
- confirm document type detection
- confirm key extracted fields
- confirm normalized items
- confirm review display shape
- confirm expected gaps
- confirm no irrelevant items are created

## 9. Phase 5 Readiness Gate

Phase 5 should not begin until all of the following are true:

- `Form 16`, `26AS`, and `AIS` are stable across multiple fixture variants
- salary slips, interest documents, and deduction proofs are supported
- major table-heavy documents parse with acceptable reliability
- reconciliation across salary/TDS/interest core documents exists
- review supports accept, override, split, reject, and mark-for-later flows
- gap analysis is document-aware for mainstream filing scenarios
- supported document classes have regression fixtures and golden tests
- unsupported or ambiguous scenarios degrade safely into review

## 10. Suggested Immediate Sprint Plan

### Sprint A

- add salary slip parser
- add bank statement and interest certificate parser
- add proof-backed deduction document parsers
- add fixtures and golden tests for these classes

### Sprint B

- add `Form 16` / `26AS` / `AIS` reconciliation
- add conflict persistence and review surfacing
- refine TDS and salary support gap logic

### Sprint C

- add reject and mark-for-later review actions
- add manual item creation
- improve gap-resolution flows

### Sprint D

- add broker/capital gains table extraction
- add noisy PDF and OCR regression suite
- complete Phase 5 readiness checklist

## 11. Step-by-Step Implementation Structure

This section translates the roadmap into an execution order that can be followed directly during implementation.

### Step 1: Freeze the Canonical Parsing Contract

Before adding more document support, define the canonical field names and normalized item expectations for each target document family.

Work to do:

- list required canonical fields for salary documents
- list required canonical fields for interest documents
- list required canonical fields for deduction-proof documents
- define which normalized categories each field can produce
- define which fields are informational only and should not become tax items

Output:

- documented canonical field map
- parser expectations per document class

Completion check:

- all new parsers target the same canonical names
- normalization rules no longer depend on arbitrary source wording

### Step 2: Add Salary Slip Support

Salary slips are the next most common salary-support document after `Form 16`.

Work to do:

- detect salary slip documents
- parse common salary-slip fields such as employer name, employee name, period, gross salary, basic salary, deductions, and net pay
- normalize salary-related monetary fields
- distinguish proof/support fields from direct tax-calculation candidates where needed
- add fixtures for at least:
  - clean digital salary slip
  - variant layout salary slip
  - scanned salary slip

Output:

- salary slip parsing support
- salary slip fixtures
- salary slip regression tests

Completion check:

- salary slips produce stable review items
- noisy salary slips degrade safely to review when needed

### Step 3: Add Interest Certificate and Bank Statement Support

These are central for interest-income scenarios in ITR-1 and ITR-2.

Work to do:

- detect interest certificates and bank statements
- extract account/source name, interest period, and interest totals
- support repeated row or section parsing where interest appears multiple times
- normalize interest-income candidates
- add fixtures for:
  - bank interest certificate
  - bank statement with identifiable interest rows
  - variant/noisy statement sample

Output:

- interest parsing support
- bank-statement interest extraction support
- tests for interest normalization and gap behavior

Completion check:

- interest documents produce `interest_income` candidates
- missing-support gaps disappear when valid interest support is uploaded

### Step 4: Add Deduction Proof Support

This closes a major review and gap-analysis requirement for mainstream filings.

Work to do:

- add detection for:
  - insurance premium proof
  - PPF / ELSS proof
  - donation receipt
  - tuition fee receipt
  - medical insurance document
  - rent receipt
  - home loan certificate
- extract proof-specific metadata and amount fields
- normalize proof-backed deduction items where appropriate
- keep unsupported proofs reviewable rather than silently ignored

Output:

- deduction-proof parser set
- proof-aware normalized deduction candidates
- gap rules that check for actual supporting documents

Completion check:

- deduction-related uploads suppress the relevant missing-proof gaps
- non-proof deductions like standard deduction do not trigger proof gaps

### Step 5: Improve Table Extraction

Once the next parser set exists, strengthen table handling across supported documents.

Work to do:

- add row and header helpers
- add repeated-section extraction
- handle statements with tabular layouts
- make column-name matching tolerant to format variation

Output:

- reusable table extraction helpers
- cleaner parsing for 26AS, AIS, broker, and bank statement rows

Completion check:

- repeated entries are extracted as distinct rows
- important numeric columns map correctly

### Step 6: Add Reconciliation Across Core Sources

At this point, the system should begin comparing overlapping values instead of treating each document independently.

Work to do:

- compare salary and TDS across `Form 16`, `26AS`, and `AIS`
- compare interest across bank documents, `AIS`, and `26AS`
- compare deduction support against claimed deduction review items
- persist match, mismatch, and missing-support states

Output:

- reconciliation layer
- conflict-aware review metadata
- support-aware gap decisions

Completion check:

- the system can identify agreement, conflict, and unsupported claims
- users can see which values are corroborated by multiple sources

### Step 7: Complete the Review Workflow

Once more documents are supported, the review state model must be made complete.

Work to do:

- add reject action
- add mark-for-later action
- add manual add-item action
- support conflict-specific review states
- support “not applicable” gap resolution flow

Output:

- full Phase 4 correction workflow
- richer audit history for review decisions

Completion check:

- all expected review actions exist in the API and persistence model
- users can fully resolve realistic ambiguous scenarios

### Step 8: Build the Regression Fixture Matrix

Now lock the behavior down with durable tests.

Work to do:

- create fixture families per supported document type
- add happy-path, variant, wrong-year, duplicate, and noisy cases
- define golden expectations
- automate parser and gap assertions

Output:

- regression fixture library
- golden parser tests
- confidence in parser stability over future changes

Completion check:

- every supported document type has automated coverage
- every fixed bug becomes a permanent regression test

### Step 9: Run the Phase 5 Readiness Review

Only after the previous steps are complete should the system be considered ready to begin tax calculation work.

Work to do:

- verify parser coverage against requirements
- verify gap rules against mainstream filing scenarios
- verify review completeness
- verify reconciliation behavior
- verify regression test health

Output:

- explicit sign-off that Phase 3 and Phase 4 are robust enough

Completion check:

- the readiness gate in this document is fully satisfied

## 12. Definition of Done For Robustness

Phase 3 and Phase 4 should be considered robust enough for Phase 5 only when:

- a normal salaried filing with common supporting documents can be uploaded and reviewed successfully
- a mixed filing with salary, bank interest, TDS, and deductions can be processed without hidden parser failures
- the system correctly identifies missing support documents instead of silently assuming completeness
- conflicts across major source documents are visible and reviewable
- regression coverage exists for the supported document set
