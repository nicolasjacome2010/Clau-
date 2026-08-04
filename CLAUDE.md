# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**VAR OS** (Variable Reality Operating System) — a decision-simulation product (not a chatbot, not a prediction tool). Full product/technical design lives in `docs/`, read in this order:

1. `docs/PRD.md` — vision, users, user stories, navigation map, roadmap, business model, KPIs.
2. `docs/ARCHITECTURE.md` — system architecture, service boundaries, and **§0 explicitly documents where the implementation deviates from the original brief and why** (multi-provider AI gateway instead of OpenAI-only, modular monolith instead of microservices-from-day-1, pgvector instead of a separate vector DB). Read §0 before assuming the brief's stack is followed literally.
3. `docs/REALITY_ENGINE.md` — the 13-agent decision-simulation pipeline (Safety Gate → Comprehension → ... → Learning), each agent's prompt/input/output JSON contract and error handling. Agents 0-6 are implemented so far (see `reality_engine/`); 7-12 (scenario generation onward) are not.
4. `docs/DATABASE.md` — full normalized schema. Only the `identity` (`users`, `user_profiles`), `goals`, and `decisions` slices are implemented so far; the rest is design-only.
5. `docs/UX_DESIGN.md` — screen-by-screen design system (color, type, motion, wireframes) for the future Flutter client. Not yet implemented.

Only **Core API modules 1-3 ("identity", "goals", "decisions")** plus **Reality Engine Agents 0-6** (the "analysis" half of the pipeline, up through Análisis de Riesgos) have been built. Everything else in those docs is design, not yet code — don't assume a feature exists just because it's documented.

## Repository layout

```
docs/            Product + architecture + Reality Engine + DB + UX design docs (see above)
backend/         Core API service (Python/FastAPI, Clean Architecture monolith — see docs/ARCHITECTURE.md §4)
  src/core_api/
    main.py, config.py, db.py, dependencies.py   # app factory, settings, shared DB/DI plumbing
    crypto.py                                       # field-level encryption port (docs/DATABASE.md §5)
    auth/                                          # Supabase JWT verification
    identity/domain|application|infrastructure|api # bounded context: user profile, JIT provisioning
    goals/domain|application|infrastructure|api     # bounded context: user's weighted decision goals
    decisions/domain|application|infrastructure|api # bounded context: the Decision aggregate root
  migrations/    Alembic (async, drives off core_api.config.Settings, not a static URL in alembic.ini)
                 0001 identity tables, 0002 goals table, 0003 decisions table
  tests/unit/    Use cases against in-memory fakes of the domain repository interfaces
  tests/integration/  Repositories against a real SQLite round-trip; API against FastAPI TestClient
reality_engine/  Reality Engine service — SEPARATE Python project/venv, not part of backend/
                 (docs/ARCHITECTURE.md §2.2: different load profile, deployed independently)
  src/reality_engine/
    ai_gateway/domain/ports.py            # LLMProvider port, ModelTier, LLMGenerationError
    ai_gateway/application/gateway.py      # AIGateway: retry + fallback across providers per tier
    ai_gateway/infrastructure/             # fake_provider.py (tests) + openai_provider.py (real, Structured Outputs)
    pipeline/domain/schemas.py             # per-agent JSON contracts (Pydantic), Agents 0-6
    pipeline/agents/                        # safety_gate, comprehension, summary, goals_extraction,
                                             # emotions, psychology, risk_analysis — one file per agent
    pipeline/orchestrator.py                 # AnalysisPipeline: chains 0-6, short-circuits if Agent 0 halts
    api/                                    # FastAPI router — POST /v1/safety-check, POST /v1/analyze
  tests/unit/, tests/integration/            # gateway retry/fallback, mocked-OpenAI adapter, each agent, orchestrator, API
docker-compose.yml   Full local stack: Postgres (pgvector image) + Redis + core-api
.github/workflows/backend-ci.yml, reality-engine-ci.yml   Lint (ruff) + type check (mypy --strict) + tests, each path-filtered to its own service directory
```

There is no Flutter client, Billing service, `simulations`, or `memory` bounded context yet, and the Reality Engine pipeline has Agents 0-6 of 13 — `simulations` (in `backend/`) is next, and it needs Agents 7-12 (Generación de Escenarios onward, still not built) to actually produce a full simulation result, so building it means growing `reality_engine/` further, not just `backend/`. Agents 11-12 (Memoria, Aprendizaje) additionally need the `memory` bounded context in Core API, which doesn't exist yet either.

## Commands

Two independent Python projects, each with its own venv and dependencies — always `cd` into the right one first.

```bash
# backend/ (Core API)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests && mypy src && pytest -v
pytest tests/unit/identity/test_use_cases.py::test_get_or_create_user_is_idempotent  # single test
alembic upgrade head       # needs VAROS_DATABASE_URL, see .env.example
docker compose up --build  # from repo root: Postgres + Redis + API together

# reality_engine/ (Reality Engine)
cd reality_engine
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests && mypy src && pytest -v
```

CI (`.github/workflows/backend-ci.yml`, `reality-engine-ci.yml`) runs exactly `ruff check`, `mypy src`, and `pytest -v` in each service's own directory — keep local commands matching that so CI never surprises you.

## Architecture conventions

### Core API (`backend/`) — established by `identity`/`goals`/`decisions`, follow for every new bounded context

- **Layering is directional and non-negotiable**: `api/` → `application/` (use cases) → `domain/` (entities + abstract repository interfaces, zero framework imports) ← `infrastructure/` (SQLAlchemy models + concrete repositories implementing the domain interfaces). Use cases depend on the domain interfaces, never on `infrastructure` directly (Dependency Inversion). See `backend/README.md` for the exact file layout to copy for the next bounded context.
- **Repository pattern everywhere.** Every persistence access goes through an ABC defined in `domain/repositories.py`; production code gets `SqlAlchemy*Repository`, tests get either an in-memory fake (unit tests) or the real repository against SQLite (integration tests) — never mock the ORM directly.
- **Ownership scoping**: endpoints operate on "my X" using the caller's JWT identity, never an arbitrary `user_id` from the request body/path (see `goals/api/router.py`, `decisions/api/router.py`). A resource that exists but belongs to someone else returns 404, not 403 — never confirm the existence of another user's data (see the `GoalNotFoundError`/`DecisionNotFoundError` docstrings).
- **Aggregate invariants live in the domain entity, not the use case.** `Decision.with_status()` is the only way to change a decision's status and enforces the allowed state-machine transitions itself (`domain/entities.py`); the use case only handles lookup/ownership/persistence. Follow this pattern for any future aggregate with a lifecycle, instead of validating transitions in the use case or (worse) the API layer.
- **Sensitive free-text fields are encrypted at the repository boundary**, not in the domain and not in the API layer. `decisions/infrastructure/repository.py` calls `core_api/crypto.py`'s `FieldEncryptor` to encrypt on write / decrypt on read; the domain `Decision` entity only ever holds plaintext in memory. `FernetFieldEncryptor` is an interim single-key implementation — production must swap in per-user AWS KMS-derived keys (docs/ARCHITECTURE.md §11) behind the same `FieldEncryptor` interface, no caller changes needed.
- **Datetimes**: use the shared `UTCDateTime` type decorator from `core_api/db.py` for any timezone-aware column, not raw `DateTime(timezone=True)`. SQLite (used in integration tests) silently drops tzinfo on round-trip; this decorator normalizes it back to UTC on read so tests and Postgres behave identically. This was a real bug caught while building `identity` — don't reintroduce it in new modules.
- **JSON/JSONB columns**: declare as `JSON().with_variant(JSONB, "postgresql")` (see `identity/infrastructure/models.py`) so models stay portable to the SQLite test path.
- **Auth**: services never call Supabase Auth directly — `core_api/auth/token_verifier.py` verifies the JWT Supabase already issued (JWKS, cached). `GetOrCreateUserUseCase` does JIT provisioning: the domain `User` row is created on the first authenticated request, not on a signup webhook.

### Reality Engine (`reality_engine/`) — established by the AI Gateway + Agents 0-6

- **Never call a model provider's SDK directly from a pipeline agent.** Agents depend on `AIGateway.generate_structured(tier=..., response_model=...)`, never on `openai`/`anthropic` clients. Adding a provider means writing a new `LLMProvider` in `ai_gateway/infrastructure/` — no caller changes.
- **Fail-safe, not fail-open, on any AI Gateway error.** `SafetyGateAgent` treats "no provider configured" and "provider exhausted its retries" identically to "the model said high risk": always escalate to the conservative outcome, never let unscreened input silently proceed. Apply the same posture to any future agent that gates the pipeline.
- **Deterministic checks run before LLM calls, not after**, when a fast, free, always-available pre-screen can short-circuit an expensive/uncertain model call (see `_deterministic_prescreen` in `pipeline/agents/safety_gate.py`). They can only escalate risk, never lower what the model would have said.
- **Deterministic post-processing stays out of the model's hands too.** `GoalsExtractionAgent` normalizes weights to sum to 100 in plain code after the LLM call, never by re-prompting — same principle as Agent 9 (Ranking) in `docs/REALITY_ENGINE.md`, which is a pure function over Agent 8's output, not a model call at all.
- **Each agent is one class with one `run()` method**, constructor-injected with `AIGateway`; the orchestrator (`pipeline/orchestrator.py`) is the only place that sequences them and owns the short-circuit-on-unsafe branch. Don't let an agent call another agent directly.
- **Real provider adapters are tested against a mocked client, not the network.** `test_openai_provider.py` verifies prompt construction, JSON parsing, and error mapping with `unittest.mock.AsyncMock` — there is no `OPENAI_API_KEY` in CI or in this environment. `FakeLLMProvider` (canned responses/errors, in order) is for testing gateway and agent logic; it is never imported outside `tests/`.

### Both services

- **Strict typing**: `mypy --strict` is enforced in CI for both `backend/` and `reality_engine/`. Generic containers need type args (`dict[str, Any]`, not `dict`); anything read off an untyped attribute (e.g. `request.app.state.*`) needs an explicit `cast`.
- **Module-by-module discipline**: don't start a new bounded context or agent until the current one has domain + application + infrastructure + api (where applicable) + unit tests + integration tests + a passing `ruff`/`mypy`/`pytest` run. This mirrors the explicit build rule this project was commissioned under — partial modules are worse than fewer modules.
