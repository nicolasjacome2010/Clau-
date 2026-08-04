# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**VAR OS** (Variable Reality Operating System) — a decision-simulation product (not a chatbot, not a prediction tool). Full product/technical design lives in `docs/`, read in this order:

1. `docs/PRD.md` — vision, users, user stories, navigation map, roadmap, business model, KPIs.
2. `docs/ARCHITECTURE.md` — system architecture, service boundaries, and **§0 explicitly documents where the implementation deviates from the original brief and why** (multi-provider AI gateway instead of OpenAI-only, modular monolith instead of microservices-from-day-1, pgvector instead of a separate vector DB). Read §0 before assuming the brief's stack is followed literally.
3. `docs/REALITY_ENGINE.md` — the 13-agent decision-simulation pipeline (Safety Gate → Comprehension → ... → Learning), each agent's prompt/input/output JSON contract and error handling. **All 13 agents are now implemented** (see `reality_engine/`): Agents 0-10 run inline in `AnalysisPipeline`/`SimulationPipeline`; Agent 11 (Memoria) runs at the end of `SimulationPipeline` and is an enhancement, never a failure reason; Agent 12 (Aprendizaje) is deliberately outside both pipelines, behind its own on-demand `POST /v1/calibrate` endpoint.
4. `docs/DATABASE.md` — full normalized schema. Implemented so far: `identity` (`users`, `user_profiles`), `goals`, `decisions`, `simulations`/`simulation_scenarios`/`decision_outcomes` (`simulation_steps` and the separate `simulation_synthesis` table are not — see `simulations/infrastructure/models.py`), and `user_bias_profile`/`memory_embeddings` (the latter stores its vector as JSON, not pgvector's `vector(1536)` — see `memory/infrastructure/repository.py`); the rest is design-only.
5. `docs/UX_DESIGN.md` — screen-by-screen design system (color, type, motion, wireframes) for the future Flutter client. Not yet implemented.

Only **Core API modules 1-5 ("identity", "goals", "decisions", "simulations", "memory")** plus **Reality Engine Agents 0-12 (all 13)** have been built. Everything else in those docs is design, not yet code — don't assume a feature exists just because it's documented.

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
    simulations/domain/reality_engine_port.py        # port + its OWN DTOs — never imports reality_engine's types
    simulations/domain|application|infrastructure|api # RunSimulationUseCase (decisions+goals+Reality Engine,
                                                        # persists Agent 11's memory when present) and
                                                        # ReportDecisionOutcomeUseCase (Agent 12, closes the loop)
    memory/domain/similarity.py                       # pure cosine_similarity, no numpy
    memory/domain|application|infrastructure|api       # UserBiasProfile (weighted-average updates), MemoryEmbedding
  migrations/    Alembic (async, drives off core_api.config.Settings, not a static URL in alembic.ini)
                 0001 identity, 0002 goals, 0003 decisions, 0004 simulations+simulation_scenarios, 0005 memory,
                 0006 decision_outcomes
  tests/unit/    Use cases against in-memory fakes of the domain repository interfaces
  tests/integration/  Repositories against a real SQLite round-trip; API against FastAPI TestClient;
                       the Reality Engine HTTP client against an httpx.MockTransport (no real network)
reality_engine/  Reality Engine service — SEPARATE Python project/venv, not part of backend/
                 (docs/ARCHITECTURE.md §2.2: different load profile, deployed independently)
  src/reality_engine/
    ai_gateway/domain/ports.py            # LLMProvider + EmbeddingProvider ports, ModelTier, *GenerationError
    ai_gateway/application/gateway.py      # AIGateway: retry + fallback across providers per tier, and for embeddings
    ai_gateway/infrastructure/             # fake_provider.py/fake_embedding_provider.py (tests) +
                                            # openai_provider.py/openai_embedding_provider.py (real)
    pipeline/domain/schemas.py             # per-agent JSON contracts (Pydantic), Agents 0-12
    pipeline/agents/                        # one file per agent (safety_gate, comprehension, summary,
                                             # goals_extraction, emotions, psychology, risk_analysis,
                                             # scenario_generation, comparison, ranking, synthesis,
                                             # memory, learning) +
                                             # _language_guards.py (shared deterministic/imperative-language checks)
    pipeline/orchestrator.py                 # AnalysisPipeline (0-6) and SimulationPipeline (0-11, Agent 11
                                              # memory-building never fails the simulation)
    api/                                    # FastAPI router — /v1/safety-check, /v1/analyze, /v1/simulate, /v1/calibrate
  tests/unit/, tests/integration/            # gateway retry/fallback (LLM + embeddings), mocked-OpenAI adapters,
                                              # each agent, both orchestrators, API
docker-compose.yml   Full local stack: Postgres (pgvector image) + Redis + core-api + reality-engine
.github/workflows/backend-ci.yml, reality-engine-ci.yml   Lint (ruff) + type check (mypy --strict) + tests, each path-filtered to its own service directory
```

There is no Flutter client or Billing service yet. All 13 Reality Engine agents are implemented, and Core API is fully wired to Agents 11-12: `RunSimulationUseCase` persists Agent 11's memory summary/embedding into `memory` when present (never blocking the simulation if absent), and `ReportDecisionOutcomeUseCase` (`POST /v1/decisions/{id}/outcome`) sends a past simulation's scenarios back to Agent 12 via `/v1/calibrate`, then persists the resulting `DecisionOutcome` and its effect on `UserBiasProfile`. `simulations` calls `reality_engine`'s `/v1/simulate` and `/v1/calibrate` synchronously over HTTP (`simulations/infrastructure/reality_engine_client.py`) — there's no queue yet (see that module's docstring for why that's an accepted, documented gap, not an oversight).

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
docker compose up --build  # from repo root: Postgres + Redis + Core API + Reality Engine together

# reality_engine/ (Reality Engine)
cd reality_engine
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests && mypy src && pytest -v
```

CI (`.github/workflows/backend-ci.yml`, `reality-engine-ci.yml`) runs exactly `ruff check`, `mypy src`, and `pytest -v` in each service's own directory — keep local commands matching that so CI never surprises you.

## Architecture conventions

### Core API (`backend/`) — established by `identity`/`goals`/`decisions`/`simulations`/`memory`, follow for every new bounded context

- **Layering is directional and non-negotiable**: `api/` → `application/` (use cases) → `domain/` (entities + abstract repository interfaces, zero framework imports) ← `infrastructure/` (SQLAlchemy models + concrete repositories implementing the domain interfaces). Use cases depend on the domain interfaces, never on `infrastructure` directly (Dependency Inversion). See `backend/README.md` for the exact file layout to copy for the next bounded context.
- **Repository pattern everywhere.** Every persistence access goes through an ABC defined in `domain/repositories.py`; production code gets `SqlAlchemy*Repository`, tests get either an in-memory fake (unit tests) or the real repository against SQLite (integration tests) — never mock the ORM directly.
- **Ownership scoping**: endpoints operate on "my X" using the caller's JWT identity, never an arbitrary `user_id` from the request body/path (see `goals/api/router.py`, `decisions/api/router.py`). A resource that exists but belongs to someone else returns 404, not 403 — never confirm the existence of another user's data (see the `GoalNotFoundError`/`DecisionNotFoundError` docstrings).
- **Aggregate invariants live in the domain entity, not the use case.** `Decision.with_status()` is the only way to change a decision's status and enforces the allowed state-machine transitions itself (`domain/entities.py`); the use case only handles lookup/ownership/persistence. Follow this pattern for any future aggregate with a lifecycle, instead of validating transitions in the use case or (worse) the API layer.
- **Sensitive free-text fields are encrypted at the repository boundary**, not in the domain and not in the API layer. `decisions/infrastructure/repository.py` calls `core_api/crypto.py`'s `FieldEncryptor` to encrypt on write / decrypt on read; the domain `Decision` entity only ever holds plaintext in memory. `FernetFieldEncryptor` is an interim single-key implementation — production must swap in per-user AWS KMS-derived keys (docs/ARCHITECTURE.md §11) behind the same `FieldEncryptor` interface, no caller changes needed.
- **Datetimes**: use the shared `UTCDateTime` type decorator from `core_api/db.py` for any timezone-aware column, not raw `DateTime(timezone=True)`. SQLite (used in integration tests) silently drops tzinfo on round-trip; this decorator normalizes it back to UTC on read so tests and Postgres behave identically. This was a real bug caught while building `identity` — don't reintroduce it in new modules.
- **JSON/JSONB columns**: declare as `JSON().with_variant(JSONB, "postgresql")` (see `identity/infrastructure/models.py`) so models stay portable to the SQLite test path.
- **Auth**: services never call Supabase Auth directly — `core_api/auth/token_verifier.py` verifies the JWT Supabase already issued (JWKS, cached). `GetOrCreateUserUseCase` does JIT provisioning: the domain `User` row is created on the first authenticated request, not on a signup webhook.
- **Calling the other service never leaks its types across the boundary.** `simulations/domain/reality_engine_port.py` defines its own plain dataclasses for what a simulation outcome looks like; `simulations/infrastructure/reality_engine_client.py` is the only file that knows Reality Engine's actual JSON shape (validated with local, HTTP-layer-only Pydantic models) and translates it into those dataclasses. Never `import reality_engine` from `backend/` — they're separate deployable services with separate dependency sets.
- **Cross-bounded-context orchestration belongs in one use case, not scattered.** `RunSimulationUseCase` is the only place that reads from `decisions` and `goals` and writes to `simulations` (and, when Reality Engine returned a memory summary, to `memory`) in the same operation; `ReportDecisionOutcomeUseCase` is the equivalent for closing the loop — it reads `decisions`+`simulations`, calls Reality Engine's `/v1/calibrate`, and writes to both `simulations` (the new `DecisionOutcome`) and `memory` (the `UserBiasProfile` update). Each bounded context still only exposes its own repository interface, so the coupling is visible at the use case's constructor, not hidden inside a repository.
- **Domain aggregates that update incrementally expose a `with_*` method that computes the new state, not a setter.** `UserBiasProfile.with_bias_observation()` folds a new observation into an existing bias via weighted moving average (never overwrites), same shape as `Decision.with_status()` — the entity computes its own next state, the use case just persists it.
- **A vector column stored as portable JSON instead of a real vector type must document its migration point in the repository, not just in a comment somewhere else.** `memory/infrastructure/repository.py`'s docstring is the single place that says when/how `find_similar`'s linear scan becomes a real pgvector query — anyone touching that file sees the constraint immediately.

### Reality Engine (`reality_engine/`) — established by the AI Gateway + all 13 agents

- **Never call a model provider's SDK directly from a pipeline agent.** Agents depend on `AIGateway.generate_structured(tier=..., response_model=...)` or (for Agent 11) `AIGateway.embed(text)`, never on `openai`/`anthropic` clients directly. Adding a provider means writing a new `LLMProvider`/`EmbeddingProvider` in `ai_gateway/infrastructure/` — no caller changes.
- **Memory (Agent 11) is an enhancement, never a failure reason.** `SimulationPipeline._try_build_memory` catches `LLMGenerationError`/`EmbeddingGenerationError` and returns `None` — the rest of the simulation (scenarios, comparison, ranking, synthesis) is served either way. Apply the same posture to any future agent that only enriches an already-successful result.
- **Learning (Agent 12) lives outside both pipelines.** It only runs behind its own `POST /v1/calibrate` endpoint, triggered explicitly when a user reports what happened with a past decision (docs/PRD.md CU8) — never on every `/v1/simulate` call. Since Reality Engine is stateless between calls, the caller (Core API) resends the original scenarios/ranking it already has persisted; `LearningAgent` never fetches or stores anything itself.
- **Fail-safe, not fail-open, on any AI Gateway error.** `SafetyGateAgent` treats "no provider configured" and "provider exhausted its retries" identically to "the model said high risk": always escalate to the conservative outcome, never let unscreened input silently proceed. Apply the same posture to any future agent that gates the pipeline.
- **Deterministic checks run before LLM calls, not after**, when a fast, free, always-available pre-screen can short-circuit an expensive/uncertain model call (see `_deterministic_prescreen` in `pipeline/agents/safety_gate.py`). They can only escalate risk, never lower what the model would have said.
- **Deterministic post-processing stays out of the model's hands too.** `GoalsExtractionAgent` and `ScenarioGenerationAgent` normalize weights/probabilities to sum to 100 in plain code after the LLM call, never by re-prompting — same principle as Agent 9 (`RankingAgent`), which is a pure function over Agent 8's output and takes no `AIGateway` at all.
- **A model's own words are never silently rewritten.** `pipeline/agents/_language_guards.py` checks Agent 7/10 output for deterministic-future or imperative language (docs/PRD.md §2, "nunca afirmar certeza" / "el usuario decide"). On a hit, the agent retries the LLM call (up to `max_language_retries`); if the violation persists, it raises `LLMGenerationError` rather than serve or silently edit non-compliant text. Apply this pattern, not string-patching, to any future agent with a linguistic constraint.
- **Each agent is one class with one `run()` method**, constructor-injected with `AIGateway` (except `RankingAgent`, which needs none). The orchestrator (`pipeline/orchestrator.py`: `AnalysisPipeline` for 0-6, `SimulationPipeline` wrapping it and adding 7-10) is the only place that sequences agents and owns the short-circuit-on-unsafe branch. Don't let an agent call another agent directly.
- **Real provider adapters are tested against a mocked client, not the network.** `test_openai_provider.py` verifies prompt construction, JSON parsing, and error mapping with `unittest.mock.AsyncMock` — there is no `OPENAI_API_KEY` in CI or in this environment. `FakeLLMProvider` (canned responses/errors, in order) is for testing gateway and agent logic; it is never imported outside `tests/`.

### Both services

- **Strict typing**: `mypy --strict` is enforced in CI for both `backend/` and `reality_engine/`. Generic containers need type args (`dict[str, Any]`, not `dict`); anything read off an untyped attribute (e.g. `request.app.state.*`) needs an explicit `cast`.
- **Module-by-module discipline**: don't start a new bounded context or agent until the current one has domain + application + infrastructure + api (where applicable) + unit tests + integration tests + a passing `ruff`/`mypy`/`pytest` run. This mirrors the explicit build rule this project was commissioned under — partial modules are worse than fewer modules.
