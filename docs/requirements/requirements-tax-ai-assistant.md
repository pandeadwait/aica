# AI Assistant for Indian Personal Income Tax Filing

## 1. Document Purpose

This document defines the detailed product, functional, technical, security, and operational requirements for a local-first, web-based AI assistant that helps individuals prepare and manage Indian personal income tax returns.

The system is intended to:

- Assist users in collecting, validating, and organizing tax-related documents.
- Detect missing information and guide the user to complete the filing.
- Determine the appropriate Income Tax Return (ITR) form.
- Calculate tax liability or refund for a selected assessment year.
- Support Indian tax treatment of eligible foreign income and foreign assets relevant to personal filing, including RSUs, ESOPs, and dividends.
- Generate the final ITR XML for download.
- Preserve completed filings for historical reference while ensuring submitted filings become read-only.

This system is for personal income tax filing under the Indian tax system and must operate entirely on the user’s local environment.

## 2. Product Vision

Build a trustworthy, private, local-first AI tax assistant that behaves like a knowledgeable filing companion:

- Easy for non-experts to use.
- Transparent in its reasoning and calculations.
- Strict about validation and auditability.
- Flexible enough to support multiple filing sessions and historical records.
- Safe by design so no personal financial data leaves the local system.

## 3. Scope

## In Scope

- Indian personal income tax filing workflow.
- Web-based UI.
- Local backend processing in Python.
- Upload and parsing of user tax documents.
- AI-assisted document relevance validation and categorization.
- User review and correction of extracted and categorized data.
- Gap analysis for missing documents and information.
- ITR form identification.
- Tax calculation.
- ITR XML generation for download.
- Support for foreign asset/income related personal filing workflows within the supported ITR forms.
- Filing lifecycle management: new, in-progress, submitted, read-only historical filings.
- Local storage of documents, extracted data, calculations, and filing history.
- Containerized deployment of all services.
- Use of local LLM and local vector database where beneficial.

## Out of Scope for Initial Version

- Direct submission of returns to the government portal.
- E-verification with Aadhaar OTP, net banking, or Demat.
- Support for corporate, LLP, partnership, trust, or GST filings.
- CA workflow management for multiple clients as a first-class feature.
- Integration with external cloud OCR/LLM APIs.
- Mobile native applications.

## 4. Primary Users

- Individual salaried taxpayers.
- Individual taxpayers with multiple income sources.
- Users filing for themselves with limited tax knowledge.
- Advanced users who want full transparency and manual override.

## 5. Key User Goals

- Start a tax filing for a chosen assessment year.
- Upload all relevant documents securely.
- Let the assistant extract and organize tax data.
- Review and correct extracted categories and values.
- Know what is missing before filing.
- See how tax is calculated.
- Download the final ITR XML.
- Reopen previous filings later.
- Prevent accidental edits after submission.

## 6. Filing Lifecycle

Each filing shall move through the following states:

1. Draft
2. Collecting Documents
3. Awaiting User Clarification
4. Ready for Calculation
5. Calculation Reviewed
6. XML Generated
7. Submitted / Done
8. Archived

Rules:

- A new filing starts in `Draft`.
- A filing in `Submitted / Done` becomes read-only.
- A read-only filing may be duplicated to create a new editable filing.
- Historical filings must remain viewable.
- Editing a previously submitted filing should require creating a duplicate working copy, while the original submitted filing remains read-only.

## 7. Functional Requirements

## 7.1 Filing Management

The system shall provide options to:

- Start a new filing.
- Select assessment year.
- Enter basic taxpayer profile data.
- Save a filing as draft.
- Resume an in-progress filing.
- Edit a previous non-submitted filing.
- Open a submitted filing in read-only mode.
- Duplicate a prior filing to reduce repeated data entry.
- Mark a filing as submitted/done.
- Lock the filing after submission.

The system should support:

- Multiple filings across different assessment years.
- Multiple revisions of the same assessment year.
- Clear status indicators for each filing.

## 7.2 Taxpayer Profile Capture

The system shall capture and store taxpayer master information, including:

- Full name
- PAN
- Date of birth
- Residential status inputs needed for filing
- Aadhaar presence indicator if needed for validation workflow
- Contact details
- Employer details where relevant
- Bank account details needed for refund-related reporting
- Filing preference inputs such as old regime vs new regime, where applicable

The system shall:

- Validate format-sensitive fields like PAN and dates.
- Reuse profile data from previous filings with user approval.
- Keep profile history versioned per filing.

## 7.3 Document Intake

The system shall allow users to upload documents through the web UI.

Supported input types should include:

- PDF
- Structured files if available, such as CSV, XLSX, JSON, XML

The system should support common tax-related document classes, including:

- Form 16
- Form 26AS
- AIS
- TIS
- Salary slips
- Interest certificates
- Bank statements
- Capital gains statements
- Broker statements
- Dividend statements
- Foreign broker statements
- RSU / ESOP grant, vesting, and sale statements
- Foreign dividend statements
- Foreign tax credit support documents where applicable
- Rent receipts
- Home loan certificates
- Insurance premium proofs
- PPF / ELSS / tax-saving investment proofs
- Donation receipts
- Tuition fee receipts
- Medical insurance documents
- Foreign asset/income supporting documents where applicable
- Previous return data import artifacts if available

The system shall:

- Store original uploaded files locally.
- Associate each document with one filing.
- Track upload timestamp, file type, checksum, source, and processing status.
- Allow document preview.
- Allow replacing a document while preserving version history.
- Reject unsupported standalone image uploads such as JPG, JPEG, and PNG with a clear message.

## 7.4 Document Validation

For each uploaded document, the system shall validate:

1. Whether the document is relevant for tax calculation.
2. Whether the document pertains to the selected assessment year / financial year.
3. Whether the document is machine-readable or parseable.
4. Whether the document is complete enough for reliable extraction.
5. Whether the document appears duplicated.
6. Whether the document conflicts with information already extracted from other sources.

The system shall classify each document into one of these states:

- Relevant
- Possibly Relevant
- Not Relevant
- Unsupported
- Duplicate
- Corrupted / Unreadable
- Needs User Review

The system shall explain in plain language why a document was flagged.

Examples:

- Wrong assessment year
- Not a tax document
- Password-protected PDF
- Missing pages
- Statement date range does not match filing year
- Unsupported image-only upload format

## 7.5 Document Parsing and Extraction

The system shall parse relevant uploaded documents locally.

Parsing pipeline should support:

- OCR for scanned images/PDFs
- Native PDF text extraction
- Table extraction
- Structured file parsing
- AI-assisted field interpretation using local LLM

For each parsed document, the system shall extract:

- Document type
- Document issuer/source
- Relevant period/date range
- Key entities such as employer, bank, broker, landlord, insurer
- Monetary values
- Currency code where applicable
- Transaction/vesting/sale dates for foreign assets where applicable
- Tax deducted at source details
- Foreign tax withholding details where applicable
- Income/expense/deduction metadata
- Confidence score per extracted field where feasible

The system shall normalize extracted data into a common tax data model.

For foreign asset or foreign income documents, the system shall additionally support:

- Extraction of grant, vesting, holding, sale, and dividend events where applicable.
- Capture of source country, broker/platform, and security/instrument identifiers where available.
- Preservation of both source-currency values and INR-converted values.

## 7.6 Credit / Category Classification

The system shall categorize extracted items into tax-relevant buckets.

Examples include:

- Salary income
- House property income
- Business or professional income support data
- Capital gains
- Interest income
- Dividend income
- Foreign dividend income
- Foreign asset income such as RSU/ESOP related taxable events within supported personal filing scope
- Other sources
- Exempt income
- Deductions under relevant sections
- TDS credits
- Advance tax
- Self-assessment tax
- Refund-related items

The system shall:

- Auto-suggest categories.
- Display the source document and extracted line items.
- Allow the user to review each classification.
- Allow the user to reassign category.
- Allow the user to split one extracted item into multiple categories if needed.
- Preserve both raw extracted value and user-corrected value.
- Store reason/audit metadata for user overrides.

## 7.7 User Validation Workflow

The system shall provide UI for the user to:

- Review uploaded documents.
- Review extracted fields.
- Review suggested categorizations.
- Accept, reject, or edit extracted values.
- Change categories.
- Add missing values manually.
- Mark uncertain items for later review.

The system shall:

- Clearly show confidence and warnings.
- Show the source document snippet or page where a value came from.
- Require explicit confirmation before final calculation.
- Autosave user validation progress locally.

## 7.8 Data Persistence

After user validation, the system shall store relevant data locally in a database or local file-backed storage.

Persisted data shall include:

- Filing metadata
- Taxpayer profile snapshot
- Uploaded document metadata
- Extracted structured data
- User-reviewed corrections
- Gap analysis outcomes
- Calculation results
- Generated XML artifacts
- Submission status
- Audit log

The system shall:

- Store enough metadata to reconstruct how a final value was derived.
- Support reprocessing with version history rather than destructive overwrite.

## 7.9 Gap Analysis

After document upload and initial parsing, the system shall identify missing documents, missing fields, and inconsistencies.

The system shall detect gaps such as:

- Missing Form 16 when salary income is indicated.
- Missing TDS support where credits are claimed.
- Missing bank interest support.
- Missing capital gains statement when broker activity is inferred.
- Missing deduction proof.
- Missing home loan certificate.
- Missing asset/liability details when required.
- Missing bank account information needed for refund reporting.
- Missing residency or foreign asset information where applicable.

The system shall:

- Ask the user for additional documents or information.
- Explain why the information is required.
- Allow the user to mark a gap as “not applicable”.
- Re-run gap analysis after new uploads or manual entries.
- Prevent finalization while critical gaps remain unresolved.

The gap analysis should also detect foreign-income-related gaps such as:

- Missing RSU / ESOP vesting or sale details.
- Missing foreign dividend statements.
- Missing foreign tax withholding details where relief or credit may be relevant.
- Missing exchange-rate basis for foreign currency conversion.

## 7.10 Conversational Assistance

The assistant shall communicate in natural, easy-to-understand language.

The assistant shall:

- Ask focused follow-up questions.
- Avoid excessive tax jargon unless needed.
- Explain calculations and warnings simply.
- Offer guided next steps when information is missing.
- Clarify when it is making an assumption.
- Ask for confirmation before applying non-obvious interpretations.

The assistant should support:

- English in initial release.
- Future localization for Indian users, such as Hindi and other regional languages.

## 7.11 ITR Form Determination

Once sufficient information is available, the system shall identify the appropriate ITR form.

The determination engine shall consider:

- Type of taxpayer
- Residential status
- Sources of income
- Capital gains presence
- Foreign assets/income
- Business/professional income indicators
- Presumptive taxation applicability
- Number of house properties
- Agricultural income thresholds where relevant
- Director/shareholding or other disclosures where relevant

The system shall:

- Present the recommended ITR form.
- Explain why that form was chosen.
- Flag edge cases where manual review is recommended.

For V1, the system shall support only:

- ITR-1
- ITR-2

The system shall:

- Restrict the filing workflow to scenarios compatible with ITR-1 or ITR-2.
- Clearly explain when a user scenario falls outside supported ITR forms.

## 7.12 Tax Calculation Engine

The system shall calculate taxes locally after all critical gaps are resolved.

The engine shall support:

- Income aggregation by head
- Deduction computation
- Exemption treatment as applicable
- Regime comparison where applicable
- Rebate calculation where applicable
- Surcharge
- Health and education cess
- Interest calculations where applicable
- Set-off and carry-forward rules as supported by scope
- TDS, advance tax, and self-assessment tax adjustments
- Refund or payable computation

For foreign income and foreign asset related computations, the engine shall support within V1 scope:

- Conversion of foreign-currency-denominated values into INR for tax calculation.
- Storage of exchange rate used, conversion date, and conversion basis.
- Separate display of source currency amount and INR amount.
- Handling of foreign dividend and supported foreign asset income items relevant to ITR-2 scenarios.

The system shall:

- Show intermediate steps.
- Display assumptions.
- Highlight exceptions and unresolved uncertainties.
- Support recalculation after edits.

## 7.13 Calculation Review

Before XML generation, the system shall present the calculations to the user for verification.

The UI shall display:

- Income summary
- Deduction summary
- Tax credit summary
- Tax payable / refund summary
- Chosen regime and alternatives if calculated
- Selected ITR form
- Warnings, assumptions, and unresolved low-confidence items

The user shall be able to:

- Approve the calculations
- Return to edit data
- Export a human-readable summary

## 7.14 ITR XML Generation

After user approval, the system shall generate an ITR XML file for download.

The XML generator shall:

- Produce schema-valid XML for the selected ITR type and assessment year.
- Use the correct government format for that year.
- Validate required fields before file generation.
- Prevent generation if mandatory data is missing.
- Save generated XML locally with versioning.

The system should also generate:

- A user-readable filing summary report.
- A manifest linking XML output to the source filing dataset and version.

## 7.15 Submission Completion and Read-Only Locking

The system shall allow the user to mark the filing as done/submitted.

After marking as submitted:

- The filing becomes read-only.
- Documents, extracted data, and calculations cannot be edited.
- Notes may be allowed only if explicitly designed as append-only.
- The system stores submission date and completion status.

The system should support:

- Recording acknowledgement/reference number manually if the user wants.
- Marking whether XML was only generated or actually submitted.

## 7.16 Historical Filing Access

The system shall allow users to:

- View historical filings.
- Open submitted filings in read-only mode.
- Reuse prior-year profile and recurring details.
- Compare key values across years.

The system should support:

- Search and filtering by assessment year, status, and taxpayer name/profile.

## 8. Additional Requirements Relevant to Personal Tax Filing

The system should also include the following capabilities because they are highly relevant to a practical personal income tax filing workflow:

- Assessment year and financial year mapping with clear display.
- Tax rule engine versioning by assessment year.
- Support for old vs new tax regime comparison where applicable.
- Support for carry-forward loss tracking where applicable and in scope.
- Support for capital gains holding period classification where applicable.
- Support for TDS reconciliation across Form 26AS, AIS, and uploaded documents.
- Detection of mismatches between user documents and tax credit statements.
- Manual entry forms for cases where documents are unavailable.
- Validation rules for PAN, IFSC, account number formats, dates, and numeric ranges.
- Versioning of generated outputs and recalculations.
- Configurable retention and secure deletion policy for sensitive documents.
- Readiness checks before final XML generation.
- System health checks for local AI/OCR dependencies.
- Exchange-rate reference and conversion-rule versioning for foreign income calculations.

## 9. Non-Functional Requirements

## 9.1 Privacy and Data Residency

The system must ensure that:

- No user tax data leaves the local machine or local private environment.
- No cloud API is required for core functionality.
- All parsing, OCR, embeddings, vector search, reasoning, and calculations run locally.
- Telemetry is disabled by default.
- Any optional diagnostic logs exclude sensitive document contents unless user explicitly opts in.

## 9.2 Accuracy and Explainability

The system shall:

- Show confidence or certainty indicators for extracted data.
- Separate extracted facts from inferred interpretations.
- Provide explanation traces for categorization and calculation decisions.
- Flag low-confidence interpretations for mandatory user review.

The system should never silently finalize tax positions without user visibility.

## 9.3 Reliability

The system shall:

- Recover gracefully from parser/LLM/OCR failures.
- Preserve user progress through autosave.
- Resume interrupted processing.
- Avoid data loss during restart.
- Support idempotent reprocessing of documents.

## 9.4 Auditability

The system shall maintain a detailed audit trail of:

- Document upload and replacement
- Extraction runs
- User edits
- Category changes
- Gap resolution actions
- Calculation runs
- XML generation events
- Submission lock events

## 9.5 Usability

The UI shall:

- Be understandable for non-tax experts.
- Use plain language.
- Provide step-by-step workflow guidance.
- Clearly identify required vs optional actions.
- Be responsive for desktop and tablet-sized screens.

## 9.6 Maintainability

The system architecture shall:

- Keep tax rules modular by assessment year.
- Separate OCR, extraction, classification, calculation, and XML generation concerns.
- Support adding new document parsers without major redesign.
- Allow replacement of local LLM/vector DB components.

## 10. Technical Architecture Requirements

## 10.1 Deployment Model

The solution shall run as containerized local services.

Required containerized components may include:

- Frontend web application
- Python backend API
- Local relational database
- Local vector database
- Local LLM runtime
- OCR/document processing service
- Background worker service

The system shall provide:

- Docker-based local startup
- Persistent local volumes for documents and database files
- Configuration through local environment files

## 10.2 Frontend Requirements

The frontend shall be a web-based UI.

The frontend shall support:

- Filing dashboard
- New filing wizard
- Document upload and preview
- Extraction review
- Categorization review and editing
- Gap resolution workflow
- Calculation review screen
- XML download screen
- Historical filing browser

The UI should provide:

- Progress tracking
- Toast/error messaging
- Inline warnings
- Human-readable explanations
- Accessibility-conscious forms and navigation

## 10.3 Backend Requirements

The backend shall be implemented in Python.

The backend shall own:

- Document management
- Parsing orchestration
- OCR integration
- AI reasoning orchestration
- Rule-based validation
- Tax calculation engine
- XML generation
- Audit logging
- Persistence management

The backend should expose:

- REST APIs or equivalent web APIs
- Background job APIs/status tracking
- Structured validation responses

## 10.4 Local LLM Requirements

The system shall use a local LLM for reasoning-related tasks such as:

- Document interpretation assistance
- Low-confidence classification support
- Natural language dialogue
- Gap explanation
- Summarization of extracted information

The selected V1 local LLM shall be:

- `Qwen2.5 Instruct (14B)`

The local LLM shall not be the sole source of truth for deterministic tax calculations.

The system shall prefer:

- Rule-based and deterministic engines for final tax logic.
- LLM use for assistance, extraction interpretation, and conversational guidance.
- Containerized local deployment of the selected model with Python-accessible API integration.

## 10.5 Vector Database Requirements

A local vector database may be used for:

- Retrieval of document templates
- Retrieval of tax guidance snippets stored locally
- Matching document layouts to known parser templates
- Internal help/document understanding

The selected V1 local vector database technology shall be:

- `pgvector`

The vector DB must:

- Run locally.
- Store only local embeddings.
- Be optional if deterministic template matching is sufficient.
- Run inside the selected local `PostgreSQL` database.

## 10.6 Database Requirements

The system shall use a local database for in-progress and historical data.

The selected V1 local relational database shall be:

- `PostgreSQL`

Suggested stored entities:

- Users or profiles
- Filings
- Filing versions
- Documents
- Document processing runs
- Extracted fields
- Category assignments
- Manual overrides
- Gap items
- Calculation snapshots
- Generated artifacts
- Audit events

The system should support:

- Transactional integrity
- Schema migrations

## 11. Data Model Requirements

Minimum domain entities shall include:

- Taxpayer Profile
- Filing
- Assessment Year
- Financial Year
- Document
- Document Version
- Parsed Item
- Income Entry
- Deduction Entry
- Tax Credit Entry
- Gap Item
- Calculation Snapshot
- ITR Form Decision
- Generated XML Artifact
- Submission Record
- Audit Log Entry

Each important entity should include:

- Created timestamp
- Updated timestamp
- Status
- Source provenance
- Version identifier

## 12. Validation and Rule Engine Requirements

The system shall implement deterministic rule engines for:

- Assessment year and financial year consistency
- Mandatory document checks
- PAN/date/number format validation
- ITR form eligibility rules
- Tax calculation rules
- XML field completeness

The rules engine shall be:

- Versioned by assessment year
- Testable independently
- Configurable without rewriting the whole application

## 13. Error Handling Requirements

The system shall handle and classify errors such as:

- Unsupported file type
- Corrupted file
- Password-protected document
- OCR failure
- Parser failure
- Ambiguous extraction
- Rule conflict
- Missing mandatory data
- XML generation failure
- Local AI runtime unavailable

The system shall present user-friendly remediation guidance for each major failure type.

## 14. Reporting and Export Requirements

The system should provide downloadable outputs including:

- Final ITR XML
- Human-readable tax computation summary
- Filing checklist / gap report
- Audit/export package for future reference

The system may also support:

- Local PDF export of tax summary

## 15. Compliance and Governance Requirements

The system shall be designed so that:

- Tax rules are mapped per assessment year.
- Generated XML matches the relevant official schema for that year.
- User consent is clear before locking a filing.
- Sensitive financial data handling is documented.

The product should include:

- Disclaimer that the tool assists filing but user remains responsible for final verification and submission.
- Clear indication of unsupported tax scenarios in the current version.

## 16. Suggested Modules

Suggested logical modules:

- Filing Management Module
- Taxpayer Profile Module
- Document Intake Module
- OCR and Parsing Module
- Extraction Review Module
- Classification and Reconciliation Module
- Gap Analysis Module
- Tax Rule Engine
- ITR Determination Module
- Tax Calculation Engine
- XML Generation Module
- Audit and History Module
- Local AI Orchestration Module
- Local Storage Module

## 17. Acceptance Criteria

The system will be considered functionally ready for an initial release when:

1. A user can create a new filing for an Indian assessment year.
2. A user can upload multiple tax-related documents locally.
3. The system validates whether each document is relevant and year-appropriate.
4. The system parses supported documents locally and extracts tax-relevant fields.
5. The system presents extracted values and categories for user review.
6. The user can edit values, change categories, and save validated data.
7. The system identifies missing information/documents and asks follow-up questions.
8. The system blocks finalization until critical gaps are resolved or marked not applicable with confirmation.
9. The system recommends the appropriate ITR form with explanation.
10. The system calculates taxes locally and presents a clear computation summary.
11. The user can approve the calculation and generate a valid XML file for the chosen ITR and assessment year.
12. The user can mark the filing as submitted/done, after which it becomes read-only.
13. The user can reopen historical filings in read-only mode and resume non-submitted filings.
14. No tax data is transmitted outside the local environment during core workflows.
15. The system supports foreign income and foreign asset related personal filing inputs within supported ITR-1 and ITR-2 scenarios, including INR conversion for supported foreign-currency amounts.

## 18. Risks and Design Considerations

Important design risks:

- Indian tax rules and XML schemas change by assessment year.
- OCR quality may vary significantly across scanned documents.
- AIS, 26AS, and user documents may conflict and require reconciliation logic.
- Local LLM quality may not be sufficient for deterministic extraction in all cases.
- Capital gains and special-case tax logic can become complex quickly.
- Unsupported edge cases must be explicitly identified rather than guessed.

Recommended design approach:

- Use deterministic tax rules wherever possible.
- Keep AI assistive, not authoritative, for final tax outcomes.
- Require user validation for low-confidence fields and non-obvious interpretations.
- Build per-document parser adapters and rule versioning from the start.

## 19. Future Enhancements

Potential future enhancements:

- Direct government portal integration where legally and technically feasible
- E-verification workflow support
- Amendment / revised return workflow
- Multi-user / CA-assisted review mode
- Notice response assistance
- More language support
- Smarter import from prior-year return
- Advanced reconciliation dashboards
- Mobile-friendly companion experience

## 20. Resolved Product Decisions

The following product decisions are fixed for the current scope:

- V1 shall support only ITR-1 and ITR-2.
- V1 shall support broader personal filing scenarios, not only salaried individuals.
- Amended/revised return workflows are out of scope for V1 and planned for V2.
- Encryption at rest is not mandatory for V1.
- The system architecture shall be single-user for V1.
- The selected V1 local LLM shall be `Qwen2.5 Instruct (14B)`.
- The selected V1 local relational database shall be `PostgreSQL`.
- The selected V1 local vector database technology shall be `pgvector`.

The following decisions still need to be finalized during detailed design:

- Which document types are supported in V1 in the first parser set
- Which container runtime/serving layer will be used to host `Qwen2.5 Instruct (14B)` locally
- Which OCR stack will be standardized
