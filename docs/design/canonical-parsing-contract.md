# Canonical Parsing Contract

## 1. Purpose

This document defines the canonical field contract that all document parsers should target before normalization and review.

The goal is to prevent every parser from inventing its own field vocabulary. Instead, all supported document types should converge into a stable internal representation that Phase 3 normalization and Phase 4 review can rely on.

## 2. General Rules

- Canonical field names use `snake_case`.
- Canonical fields should represent semantic meaning, not source formatting.
- Informational fields may be preserved even if they do not create normalized tax items.
- Not every canonical field becomes a tax item.
- Parsers should prefer canonical names over raw source labels whenever meaning is clear.
- When meaning is unclear, extraction should fall back to review instead of forcing a misleading canonical field.

## 3. Field Categories

Canonical fields should be grouped mentally into:

- identification fields
- period/year fields
- party/entity fields
- monetary tax-item candidate fields
- monetary support/reference fields
- document metadata fields

## 4. Salary Document Contract

This contract applies to:

- `form16`
- `salary_slip`

### 4.1 Required Identification and Period Fields

- `assessment_year`
- `financial_year`
- `employee_name`
- `employer_name`

### 4.2 Preferred Identity Fields

- `pan`
- `tan`

### 4.3 Salary Monetary Fields

These fields may produce normalized review candidates:

- `gross_salary`
- `basic_salary`
- `salary_income`
- `tax_deducted`
- `professional_tax`

### 4.4 Salary Informational or Supporting Fields

These fields are useful for traceability or later refinement, but should not automatically become final tax items in the current implementation unless explicitly supported:

- `house_rent_allowance`
- `special_allowance`
- `other_allowance`
- `bonus`
- `provident_fund_employee`
- `provident_fund_employer`
- `net_pay`
- `payslip_month`
- `payslip_period`

### 4.5 Current Normalization Intent

Current Phase 3 normalization for salary-family documents should treat:

- `gross_salary`
- `basic_salary`
- `salary_income`

as `salary_income` candidates.

It should treat:

- `tax_deducted`
- `tax_collected`

as `tds_credits` candidates when supported by the source document context.

It may treat:

- `professional_tax`
- `standard_deduction`

as deduction-related review candidates where appropriate.

It should not currently auto-normalize:

- `net_pay`
- `house_rent_allowance`
- `special_allowance`
- `bonus`

unless explicit rules are later added.

## 5. Interest Document Contract

This contract applies to:

- `interest_certificate`
- `bank_statement`

### 5.1 Required or Preferred Fields

- `assessment_year`
- `financial_year`
- `account_holder_name`
- `issuer_name`
- `interest_income`

### 5.2 Supporting Fields

- `account_number_masked`
- `interest_period`
- `tax_deducted`

### 5.3 Normalization Intent

- `interest_income` should produce `interest_income` candidates
- `tax_deducted` should produce `tds_credits` candidates where relevant

## 6. TDS and Information Statement Contract

This contract applies to:

- `form26as`
- `ais`

### 6.1 Common Fields

- `assessment_year`
- `financial_year`
- `deductor_name`
- `income_paid`
- `tax_deducted`
- `tax_collected`
- `salary_income`
- `interest_income`
- `dividend_income`

### 6.2 Normalization Intent

- `tax_deducted` and `tax_collected` should map into `tds_credits`
- `salary_income` should map into `salary_income`
- `interest_income` should map into `interest_income`
- `dividend_income` should map into `domestic_dividend_income`

## 7. Foreign Income Contract

This contract applies to:

- `foreign_dividend_statement`
- `broker_statement`
- `rsu_statement`
- `esop_statement`

### 7.1 Common Fields

- `country`
- `broker_platform`
- `security_identifier`
- `event_date`
- `foreign_dividend_amount`
- `withholding_amount`

### 7.2 Normalization Intent

- `foreign_dividend_amount` should map into `foreign_dividend_income`
- `withholding_amount` should remain reviewable and may map to support or credit-related candidates depending on the supported workflow

## 8. Parser Implementation Rule

Whenever a new parser is added, it should declare:

- which canonical fields it can populate reliably
- which fields are required for a successful parse
- which fields are optional
- which normalized categories it is allowed to influence

## 9. Review and Gap Rule Dependency

Phase 4 gap and review logic should depend on canonical fields and normalized categories, not source-specific wording.

That means:

- missing `Form 16` logic should depend on salary-related categories, not raw labels
- interest-support gaps should depend on `interest_income`
- deduction-proof gaps should depend on supported deduction categories

