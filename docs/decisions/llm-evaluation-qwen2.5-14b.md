# LLM Evaluation Decision: Qwen2.5 Instruct (14B)

## 1. Purpose

This document records the LLM decision for V1 of the Indian personal income tax filing assistant.

It is based on the broader comparison in [llm-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/llm-comparison-tax-assistant.md) and captures:

- the selected model
- why it was chosen
- why other options were not chosen as the primary V1 model
- implementation implications
- evaluation points to validate during integration

## 2. Selected Model

The selected V1 local LLM is:

- `Qwen2.5 Instruct (14B)`

## 3. Why Qwen2.5 Instruct (14B) Was Chosen

This model was selected because it best matches the needs of this software:

- strong structured reasoning
- strong extraction-assistance behavior
- good classification support
- strong user-facing explanation quality
- local deployment compatibility
- clean Python integration path
- good fit for English-first V1 workflows

For this product, the LLM is not the tax calculator. It is mainly responsible for:

- interpreting ambiguous document text
- helping categorize extracted items
- asking smart follow-up questions
- explaining missing information
- helping the UI feel natural and easy to understand

`Qwen2.5 Instruct (14B)` is a strong fit for those tasks.

## 4. Decision Summary Against Requirements

## Requirement 1: Local only

Decision:

- Satisfied

Why:

- `Qwen2.5 Instruct (14B)` can run fully locally through a self-hosted containerized runtime.

## Requirement 2: Docker compatible

Decision:

- Satisfied

Why:

- The model can be hosted in a Dockerized local serving stack such as `Ollama` or another compatible local inference server.

## Requirement 3: Should work well for Indian tax assistant workflows

Decision:

- Satisfied with architectural guardrails

Why:

- The model is strong at structured reasoning and explanation tasks.
- Final Indian tax logic will remain deterministic in Python.
- This keeps the LLM in the role it is best suited for.

## Requirement 4: Python integration

Decision:

- Satisfied

Why:

- The model can be consumed from Python through a local HTTP API or native client library depending on the serving stack chosen.

## Requirement 5: Easy-to-use interface

Decision:

- Satisfied

Why:

- `Qwen2.5 Instruct (14B)` can be exposed through a simple local API, which is easy for the backend to call.

## Requirement 6: Strong fit for software requirements

Decision:

- Satisfied

Why:

- The model is well suited for document interpretation, classification help, explanation quality, and gap-resolution dialogue.

## 5. Why 14B Instead of 7B

The `14B` variant was chosen over `7B` because:

- the product relies on structured reasoning and ambiguity handling
- tax-document interpretation quality is more important than using the smallest possible model
- the extra model capacity should improve:
  - explanation quality
  - classification assistance
  - harder extraction interpretation cases
  - foreign-income and foreign-asset document handling support

Tradeoff:

- `14B` will require more local compute resources than `7B`
- inference may be slower on weaker hardware

This tradeoff is acceptable because correctness support and reasoning quality matter more than minimal resource usage for this product.

## 6. Why Other Options Were Not Selected as Primary V1 Model

## Llama 3.1 Instruct

Why it was not chosen as primary:

- It is a strong alternate, but Qwen is the better fit for structured reasoning and extraction-assistance-heavy workflows.

Why it still matters:

- It remains the best fallback benchmark if Qwen underperforms in real testing.

## Gemma 3

Why it was not chosen as primary:

- It is attractive for lighter hardware, but the product prioritizes reasoning quality over the lightest deployment profile.

Why it still matters:

- It remains a useful fallback if hardware constraints become severe.

## Mistral Small

Why it was not chosen as primary:

- It is a strong model family, but it is not as clear a fit as Qwen for this product’s extraction-assistance and structured-tax-workflow needs.

Why it still matters:

- It remains an alternate option if future evaluation reveals better behavior on specific tasks.

## 7. Recommended Serving Approach

The selected model should initially be served through:

- `Ollama`

Why:

- simplest local deployment
- easy Docker support
- easy Python integration
- easy operational model management

The following serving decision is still open:

- whether `Ollama` remains sufficient for latency/performance, or whether a more advanced serving layer such as `vLLM` is needed later

## 8. Expected Role of the LLM in the System

The LLM should be used for:

- document interpretation when deterministic parsing is incomplete
- extraction-assistance for ambiguous text
- suggested categorization of extracted items
- plain-English explanation of why a document is relevant or not relevant
- user-facing explanation of missing gaps
- natural language clarification questions
- simplified explanation of tax calculations already produced by the deterministic engine

The LLM should not be used for:

- final tax calculation
- authoritative ITR eligibility decision without deterministic validation
- silent mutation of authoritative financial data
- unsupported legal/tax conclusions without rule-based backing

## 9. Risks of This Choice

## Risk 1: Local hardware may be insufficient

Impact:

- slow inference
- reduced UX quality

Mitigation:

- keep `Qwen2.5-7B-Instruct` as a fallback profile
- allow model configuration at deployment time

## Risk 2: The model may still hallucinate tax interpretations

Impact:

- incorrect user guidance if unguarded

Mitigation:

- keep deterministic tax logic in Python
- restrict the model to assistive use cases
- require user confirmation for ambiguous suggestions

## Risk 3: Some document formats may still be too difficult

Impact:

- inconsistent assistance quality for complex statements

Mitigation:

- prioritize parser adapters and deterministic extraction first
- use the LLM only as a fallback interpretation layer

## 10. Validation Checklist for Integration

Before finalizing this model in implementation, validate that it performs adequately on:

1. Form 16 explanation and structured interpretation support
2. Bank interest statement interpretation
3. Dividend statement categorization assistance
4. RSU / ESOP related explanation and event interpretation support
5. Gap clarification prompts that are easy for a non-expert user to understand
6. Tax-calculation explanation grounded strictly in backend-produced numbers
7. Stable JSON or structured-output prompting for assistant workflows

## 11. Final Decision

The V1 project will proceed with:

- `Qwen2.5 Instruct (14B)` as the local LLM

This is the best choice because it offers the strongest balance of:

- local deployability
- Docker compatibility
- Python integration
- structured reasoning quality
- extraction assistance quality
- natural explanation quality

## 12. Related Documents

- Requirements: [requirements-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/requirements/requirements-tax-ai-assistant.md)
- Comparison: [llm-comparison-tax-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/decisions/llm-comparison-tax-assistant.md)
- Design: [design-tax-ai-assistant.md](/Users/vikrampande/AI%20CA%20Agent/docs/design/design-tax-ai-assistant.md)
