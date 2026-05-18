# NeuGate — Design & documentation index

Use this page to navigate product intent, architecture, and integration. The [README](../README.md) covers how to run and deploy the service.

## Documents

| Document | Audience | Contents |
|----------|----------|----------|
| [PRD.md](PRD.md) | Product, platform | Goals, API contract, phases, NFRs, consumer relationship |
| [AGENTIC_SEMANTIC_PIPELINE.md](AGENTIC_SEMANTIC_PIPELINE.md) | Engineering | Hybrid pipeline (FAISS + LLM), agnostic `policy`, seed dataset, env vars, readiness |
| [INTEGRATION.md](INTEGRATION.md) | Consumer backends | Auth, endpoints, request/response examples, HTTP errors, cURL |

## Architecture at a glance

```text
POST /v1/evaluate
  → validate request
  → phase 1: agentic FAISS (local, no LLM)
  → phase 2: Red Team classifier (OpenAI), only if phase 1 passes
  → proceed | short_circuit + cached_response
```

NeuGate does **not** store per-consumer policy on disk. Each request includes `policy` (`critical_blocks`, `soft_blocks`, `pivot_templates`). `project_id` is for logging only.

## Related work outside this repo

Consumers (e.g. Jamie Oliver AI) own brand policy, Red Team matrices, and feature flags such as `NEUGATE_ENABLED`. See `jamie-oliver-ai/docs/guardrails/` for the Jamie guardrails PRD and implementation plan.
