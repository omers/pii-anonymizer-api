# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
make dev              # Run with auto-reload on port 8000
make install          # Install all deps + spaCy model (use this first)
make setup-dev        # Install deps + pre-commit hooks

# Testing
make test             # Run all tests (80% coverage required)
make test-cov         # Run tests with HTML/XML/terminal coverage report
make test-unit        # Run unit tests only (-m unit)
make test-integration # Run integration tests only (-m integration)
make test-verbose     # Verbose output

# To run a single test file or function:
pytest tests/test_code.py
pytest tests/test_code.py::test_function_name -v

# Code quality
make lint             # flake8 + mypy
make format           # black + isort
make check            # lint + test (pre-commit)

# Docker
make docker-build && make docker-run
```

## Architecture

Single-file FastAPI app ([main.py](main.py)) — no separate router or service modules. All logic lives in one file (~518 lines).

**Request flow:**
1. `POST /anonymize` receives `AnonymizeRequest` (text, language, optional `AnonymizationConfig`)
2. Request logging middleware captures timing
3. Validation: text length (default max 10,000 chars), language against `SUPPORTED_LANGUAGES`
4. `AnalyzerEngine.analyze()` — Presidio NLP detection using spaCy `en_core_web_lg`
5. Filter to requested entity types (if specified); otherwise detect all 13 types
6. Build per-entity operator config based on `AnonymizationStrategy` (REPLACE, REDACT, HASH, MASK, ENCRYPT)
7. `AnonymizerEngine.anonymize()` — apply operators to text
8. Return `AnonymizeResponse` with anonymized text, `DetectedEntity` list, and timing metrics

**Key classes in main.py:**
- `Config` — reads env vars (`DEFAULT_LANGUAGE`, `LOG_LEVEL`, `MAX_TEXT_LENGTH`, `SUPPORTED_LANGUAGES`, `CORS_ORIGINS`)
- `AnonymizationStrategy` enum — maps to Presidio operator names
- `EntityType` enum — 13 PII types (PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, etc.)
- `AnonymizeRequest` / `AnonymizeResponse` / `AnonymizationConfig` / `DetectedEntity` — Pydantic v2 models
- Lifespan context manager initializes `AnalyzerEngine` and `AnonymizerEngine` at startup

**Other endpoints:** `GET /health`, `GET /metrics` (psutil), `GET /info`, `GET /test/error/{error_type}` (dev only)

## Environment

Copy `env.example` to `.env`. Key variables:

| Variable | Default | Notes |
|---|---|---|
| `DEFAULT_LANGUAGE` | `en` | |
| `MAX_TEXT_LENGTH` | `10000` | |
| `SUPPORTED_LANGUAGES` | `en,es,fr,de,it` | |
| `CORS_ORIGINS` | `*` | |
| `LOG_LEVEL` | `INFO` | |

## Tests

- `tests/conftest.py` — shared fixtures (test client, sample text, mocks)
- `tests/test_code.py` — unit tests for anonymization logic
- `tests/test_integration.py` — end-to-end API tests
- `tests/test_config.py` — config/validation tests
- `tests/test_performance.py` — load/perf benchmarks (`-m performance`)
- `tests/test_simple.py` — smoke tests (no heavy presidio imports)

Coverage minimum is 80% (enforced by `pytest.ini`).

## CI

GitHub Actions runs on push/PR: multi-Python (3.9–3.12), multi-platform (Ubuntu, macOS, Windows). See [.github/workflows/ci.yml](.github/workflows/ci.yml).
