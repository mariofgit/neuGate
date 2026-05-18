# NeuGate

Semantic filter proxy: classifies user messages **before** embeddings, RAG, or tools in the consumer backend. Returns `proceed` or `short_circuit` with an optional pivot message.

## Documentation

| Doc | Purpose |
|-----|---------|
| **[docs/DESIGN.md](docs/DESIGN.md)** | Index — product, architecture, integration |
| **[docs/PRD.md](docs/PRD.md)** | Product requirements (goals, contract, NFRs) |
| **[docs/AGENTIC_SEMANTIC_PIPELINE.md](docs/AGENTIC_SEMANTIC_PIPELINE.md)** | Hybrid pipeline design (FAISS + LLM) |
| **[docs/INTEGRATION.md](docs/INTEGRATION.md)** | Consumer integration (auth, API, cURL) |

Interactive API: `{base_url}/docs` (OpenAPI) when the server is running.

## API (summary)

| Endpoint | Role |
|----------|------|
| `POST /v1/evaluate` | Gate a single user message (`message` + consumer `policy`) |
| `POST /v1/test-runner` | Batch Red Team / regression (`test_dataset` in body) |
| `GET /health` | Liveness |
| `GET /health/ready` | Readiness (OpenAI key, agentic index) |

Full request/response shapes and HTTP codes: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Local development

```bash
cd neuGate
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[agentic,dev]"
python scripts/seed_vector_db.py
cp .env.example .env
# Set OPENAI_API_KEY and optionally NEUGATE_API_KEY

uvicorn neugate.main:app --host 0.0.0.0 --port 8080 --app-dir src
```

```bash
curl -s http://localhost:8080/health/ready
```

Tests (mocked LLM, no real OpenAI in CI by default):

```bash
pytest
pytest -m unit
pytest -m integration
```

## Docker

```bash
docker build -t neugate:local .
docker run --rm -p 8080:8080 \
  -e OPENAI_API_KEY=sk-... \
  -e NEUGATE_API_KEY=your-service-key \
  -v "$(pwd)/config:/app/config:ro" \
  neugate:local
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required in production) |
| `NEUGATE_API_KEY` | Service-to-service key for `/v1/*` (required in production) |
| `OPENAI_MODEL` | Classifier model (default: `gpt-4o-mini`) |
| `NEUGATE_LLM_TIMEOUT_SECONDS` | LLM timeout |
| `NEUGATE_PORT` | HTTP port (default: `8080`) |
| `NEUGATE_TEST_RUNNER_MAX_CASES` | Max batch cases (default: `100`) |
| `NEUGATE_TEST_RUNNER_CONCURRENCY` | Concurrent LLM calls in test-runner (default: `10`) |
| `NEUGATE_AGENTIC_ENABLED` | Agentic FAISS phase (default: `true`) |
| `NEUGATE_AGENTIC_THRESHOLD` | Cosine block threshold (default: `0.82`) |
| `NEUGATE_AGENTIC_INDEX_PATH` | FAISS index path |
| `NEUGATE_AGENTIC_META_PATH` | Index metadata path |
| `NEUGATE_AGENTIC_MODEL` | sentence-transformers model |

See `.env.example` for legacy config paths used in local tests only.

## Integration

Place NeuGate in front of the main backend: on `short_circuit`, return `cached_response` and skip RAG/tools; on `proceed`, continue normally. Consumers send `policy` on every call — see [docs/INTEGRATION.md](docs/INTEGRATION.md).
