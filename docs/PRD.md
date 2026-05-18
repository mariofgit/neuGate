# PRD — NeuGate: semantic pre-backend gate

| Field | Value |
|--------|--------|
| **Product** | NeuGate (neuForce platform service) |
| **Type** | Platform / infrastructure — intent and safety proxy |
| **Status** | Implemented (v0.1) |
| **Consumers** | Jamie Oliver AI and other neuForce products |

## 1. Summary

NeuGate is a **brand-agnostic** HTTP service that classifies user messages **before** embeddings, RAG retrieval, or agent tools run in the consumer backend. It returns `proceed` or `short_circuit` with an optional `cached_response` (rotated pivot text supplied by the consumer).

Defense in depth uses two phases:

1. **Local agentic semantic gate** (FAISS + sentence-transformers, no LLM).
2. **LLM Red Team classifier** (OpenAI structured output) using the consumer’s `policy` categories.

## 2. Goals

| ID | Goal |
|----|------|
| G-1 | Block generic agentic abuse (MCP, channels, resource exhaustion) with low latency and no per-request embedding API calls. |
| G-2 | Classify consumer-defined risk categories (illegal, hate, off-topic, etc.) via LLM when phase 1 passes. |
| G-3 | Remain **agnostic**: no per-brand config on disk; `policy` travels in every request body. |
| G-4 | Expose batch certification via `POST /v1/test-runner` with in-memory datasets from the consumer. |

## 3. Non-goals

- Storing consumer Red Team datasets on the NeuGate server.
- Replacing the consumer’s system prompt or output moderation.
- Guaranteeing zero false negatives on adversarial inputs.

## 4. API contract

### `POST /v1/evaluate`

| Field | Required | Description |
|-------|----------|-------------|
| `project_id` | Yes | Correlation / logging (not a config lookup key). |
| `message` | Yes | User text (1–16000 chars). |
| `policy` | Yes | `critical_blocks`, `soft_blocks`, `pivot_templates` (≥1). |

### Response

| Field | Description |
|-------|-------------|
| `is_violation` | Whether to block downstream retrieval/tools. |
| `category` | `safe_domain`, consumer block label, or `agentic_*` from phase 1. |
| `action` | `proceed` or `short_circuit`. |
| `cached_response` | Pivot text when `short_circuit`; else `null`. |

### `POST /v1/test-runner`

Same `project_id` + `policy`; `test_dataset[]` with `prompt` and `expected_category`.

## 5. Authentication

- When `NEUGATE_API_KEY` is set: required on `/v1/*` via `X-API-Key` or `Authorization: Bearer`.
- When unset: auth disabled (local dev only; log warning).
- `/health`, `/health/ready`: no auth.

## 6. Pipeline

| Order | Phase | Technology | LLM? |
|-------|--------|------------|------|
| 0 | Request validation | Pydantic | No |
| 1 | Agentic semantic gate | FAISS + sentence-transformers | No |
| 2 | Red Team classifier | OpenAI structured JSON | Yes |

Phase 1 uses a fixed internal seed (6 attack vectors). Phase 2 uses categories from the request `policy`.

## 7. Non-functional requirements

| Area | Target |
|------|--------|
| Phase 1 latency | &lt;20 ms p95 (local, warm index) |
| End-to-end evaluate | ~800 ms p95 (includes LLM; tune in staging) |
| Availability | Consumer may fail-open on timeout/5xx (Jamie: `proceed`) |
| Readiness | `OPENAI_API_KEY` set; agentic index loaded when `NEUGATE_AGENTIC_ENABLED=true` |

## 8. Environment variables

See [README.md](../README.md#environment-variables).

## 9. Consumer integration (example: Jamie Oliver AI)

Jamie owns `jamie-policy.json`, `red_team_matrix.json`, and `NEUGATE_ENABLED`. On each chat turn, `backend-search` POSTs `message` + `policy` to NeuGate. On `short_circuit`, Jamie returns `cached_response` and skips recipe RAG/tools.

Jamie guardrails PRD/plan: `jamie-oliver-ai/docs/guardrails/`.

## 10. Success criteria

- [x] Phase 1 blocks seeded agentic prompts at ≥ configured cosine threshold.
- [x] Phase 2 classifies safe cooking vs policy violations with consumer `policy`.
- [x] `test-runner` returns accuracy report without persisting prompts.
- [ ] Consumer PR (Jamie) wires client + certification suite.

## 11. Related docs

- [AGENTIC_SEMANTIC_PIPELINE.md](AGENTIC_SEMANTIC_PIPELINE.md)
- [INTEGRATION.md](INTEGRATION.md)
- [README.md](../README.md)
