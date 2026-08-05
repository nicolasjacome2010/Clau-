# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**VAR OS** (Variable Reality Operating System) — a decision-simulation product (not a chatbot, not a prediction tool). Full product/technical design lives in `docs/`, read in this order:

1. `docs/PRD.md` — vision, users, user stories, navigation map, roadmap, business model, KPIs.
2. `docs/ARCHITECTURE.md` — system architecture, service boundaries, and **§0 explicitly documents where the implementation deviates from the original brief and why** (multi-provider AI gateway instead of OpenAI-only, modular monolith instead of microservices-from-day-1, pgvector instead of a separate vector DB). Read §0 before assuming the brief's stack is followed literally.
3. `docs/REALITY_ENGINE.md` — the 13-agent decision-simulation pipeline (Safety Gate → Comprehension → ... → Learning), each agent's prompt/input/output JSON contract and error handling. **All 13 agents are now implemented** (see `reality_engine/`): Agents 0-10 run inline in `AnalysisPipeline`/`SimulationPipeline`; Agent 11 (Memoria) runs at the end of `SimulationPipeline` and is an enhancement, never a failure reason; Agent 12 (Aprendizaje) is deliberately outside both pipelines, behind its own on-demand `POST /v1/calibrate` endpoint.
4. `docs/DATABASE.md` — full normalized schema. Implemented so far: `identity` (`users`, `user_profiles`), `goals`, `decisions`, `simulations`/`simulation_scenarios`/`decision_outcomes` (`simulation_steps` and the separate `simulation_synthesis` table are not — see `simulations/infrastructure/models.py`), `user_bias_profile`/`memory_embeddings` (the latter stores its vector as JSON, not pgvector's `vector(1536)` — see `memory/infrastructure/repository.py`), and `subscriptions`/`stripe_events` (§2.12-2.13); the rest is design-only.
5. `docs/UX_DESIGN.md` — screen-by-screen design system (color, type, motion, wireframes) for the Flutter client. **Design system + Splash/Onboarding/Auth/Home/Clarificación/Resultados+Síntesis+Cierre de ciclo/Mis Decisiones/Memoria/Perfil de Objetivos (Pantallas 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 13 of §2) are implemented** (see `app/`); Pantallas 6, 8, 14-15 (Simulación en vivo, Comparación, Suscripción, Ajustes) are still design-only.

Only **Core API modules 1-6 ("identity", "goals", "decisions", "simulations", "memory", "billing")**, **Reality Engine Agents 0-12 (all 13)**, and the **Flutter client's foundation + seven feature verticals** (`app/`: design system, routing, networking scaffold, Splash → Onboarding → Auth → Home → Clarificación → Resultados/Síntesis/Cierre de ciclo, plus Mis Decisiones / Memoria / Perfil de Objetivos in the nav shell) have been built. Everything else in those docs is design, not yet code — don't assume a feature exists just because it's documented.

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
                                                        # persists Agent 11's memory when present),
                                                        # ReportDecisionOutcomeUseCase (Agent 12, closes the loop,
                                                        # once per decision) and ListDecisionOutcomesUseCase
    memory/domain/similarity.py                       # pure cosine_similarity, no numpy
    memory/domain|application|infrastructure|api       # UserBiasProfile (weighted-average updates), MemoryEmbedding
    billing/domain/stripe_port.py                     # port + its OWN DTOs — never imports the `stripe` SDK
    billing/domain|application|infrastructure|api      # Subscription (Stripe-is-source-of-truth read replica),
                                                        # StripeEvent (append-only webhook idempotency log)
  migrations/    Alembic (async, drives off core_api.config.Settings, not a static URL in alembic.ini)
                 0001 identity, 0002 goals, 0003 decisions, 0004 simulations+simulation_scenarios, 0005 memory,
                 0006 decision_outcomes, 0007 billing (subscriptions+stripe_events),
                 0008 decision_outcomes.decision_id unique (one closed loop per decision)
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
app/             Flutter client — SEPARATE Dart/Flutter project, not part of backend/ or reality_engine/
                 (docs/ARCHITECTURE.md §3)
  lib/
    main.dart                             # entry point: ProviderScope + MaterialApp.router
    design_system/                        # "VAR Design System" (docs/UX_DESIGN.md §1) — var_colors.dart,
                                           # var_typography.dart, var_spacing.dart, var_motion.dart, var_theme.dart
                                           # (the only file that assembles tokens into ThemeData)
    core/network/api_client.dart          # Dio + auth/logging interceptors — never imports a `features/` type
    core/routing/                          # GoRouter: app_routes.dart (paths) + app_router.dart
    features/splash|onboarding|auth/       # Pantallas 1-3 (docs/UX_DESIGN.md §2), each domain|presentation
                                           # (+ data/ where a port has a concrete adapter)
    features/clarification/                # Pantalla 5, REAL: chip questions whose first answer
                                           # resolves the `vertical`, then creates the decision
    features/decisions/                    # domain shared by Home, Mis Decisiones and Clarificación
                                           # (owned by none): ApiDecisionsRepository calls GET and
                                           # POST /v1/decisions for real over the shared Dio;
                                           # DecisionsController fetches ALL decisions once, deduped
                                           # by Riverpod across every screen that reads them
    features/goals/                        # Pantalla 13, REAL: ApiGoalsRepository calls GET/POST
                                           # /v1/goals + PATCH /v1/goals/{id}; also owns GoalOption
                                           # (the seed list) that Onboarding shares
    features/home/                         # Pantalla 4, REAL: nav shell (bottom nav mobile /
                                           # NavigationRail tablet+) — all 4 destinations now real
    features/memory/                       # Pantalla 12, REAL: ApiMemoryRepository calls GET /v1/
                                           # memory/bias-profile for real; bias text is rendered as-is
                                           # (LLM free text, not a code) — no client-side translation table
    features/simulations/                  # Pantallas 7 + 9 + 11, REAL: ApiSimulationsRepository calls
                                           # GET/POST /v1/decisions/{id}/simulations (90s timeout on
                                           # the POST — the pipeline blocks 15-30s) and
                                           # POST /v1/decisions/{id}/outcome. Opened by tapping
                                           # any decision from Home or Mis Decisiones.
                                           # SafetyGateResult.requiresReferral is checked before any
                                           # rendering: a halt shows SafetyReferral and nothing else.
                                           # OutcomeSection (close-the-loop) only renders under a
                                           # completed simulation — 409 otherwise
    features/shared/                       # widgets no single feature owns: StepIndicator (Onboarding
                                           # + Clarificación)
  test/design_system/, test/features/      # one widget-test file per screen/feature
  .github/workflows/app-ci.yml             # dart format --set-exit-if-changed + flutter analyze + flutter test
docker-compose.yml   Full local stack: Postgres (pgvector image) + Redis + core-api + reality-engine
.github/workflows/backend-ci.yml, reality-engine-ci.yml, app-ci.yml   Lint/format + type check + tests, each path-filtered to its own directory
```

`billing` is implemented as a bounded context inside the Core API monolith, not the separate microservice the original brief described (docs/ARCHITECTURE.md §0's "modular monolith, not microservices-from-day-1" deviation applies here too). All 13 Reality Engine agents are implemented, and Core API is fully wired to Agents 11-12: `RunSimulationUseCase` persists Agent 11's memory summary/embedding into `memory` when present (never blocking the simulation if absent), and `ReportDecisionOutcomeUseCase` (`POST /v1/decisions/{id}/outcome`) sends a past simulation's scenarios back to Agent 12 via `/v1/calibrate`, then persists the resulting `DecisionOutcome` and its effect on `UserBiasProfile`. **A loop closes exactly once**: a second report answers 409, and the guard runs *before* the Reality Engine call so a duplicate costs neither a model round trip nor a second fold into the user's bias profile (`with_calibration_delta`/`with_bias_observation` are incremental — a duplicate would silently distort the user's own calibration, not just add a row); `decision_outcomes.decision_id` is unique in the database too (migration 0008), which is what holds when two concurrent reports both pass the guard. `ListDecisionOutcomesUseCase` (`GET /v1/outcomes`) answers "which of my loops are already closed" in one call — a collection rather than `GET /decisions/{id}/outcome`, since per-decision reads would be an N+1 against a list screen. `simulations` calls `reality_engine`'s `/v1/simulate` and `/v1/calibrate` synchronously over HTTP (`simulations/infrastructure/reality_engine_client.py`) — there's no queue yet (see that module's docstring for why that's an accepted, documented gap, not an oversight). `billing` integrates Stripe (Checkout, Customer Portal, webhooks) via `billing/infrastructure/stripe_client.py`'s `StripeApiClient`, with `subscriptions` as a read-only replica of Stripe's own state and `stripe_events` as an append-only idempotency log (docs/ARCHITECTURE.md §9) — no `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` in CI or this environment, so the real adapter is tested against a mocked `stripe.StripeClient`, never the network. `app/` has its design system, routing/networking scaffold, and Splash→Onboarding→Auth→Home→Clarificación→Resultados/Síntesis/Cierre de ciclo→Mis Decisiones→Memoria→Perfil de Objetivos built and tested, but has no real Supabase Auth adapter yet (`LocalStubAuthRepository` is an explicitly-labeled interim stand-in — see `app/README.md`'s "desviaciones documentadas") and none of Pantallas 6/8/14-15 (live simulation streaming, comparison table, billing UI, settings). `decisions/ApiDecisionsRepository` is a real integration against both `GET` and `POST /v1/decisions`, shared by Home ("Decisiones activas"), Mis Decisiones (grouped by Activas/Completadas/Archivadas) and Clarificación through one `DecisionsController` so no two screens double-fetch. **`POST /v1/decisions` requires a `vertical` enum the free-text capture field can't supply, so the app asks instead of guessing**: Home hands the text to Pantalla 5 (Clarificación), whose first chip question resolves it, and only then is the decision created — the spec's own mechanism for that screen, not a workaround. The non-`vertical` answers are folded into `raw_input` as a delimited block (`clarification/domain/raw_input_composer.dart`) because the backend has no columns for them and `raw_input` is what reaches `/v1/simulate`; the user's own words are preserved verbatim above it. Clarificación pops back to Home rather than continuing to Pantalla 6, which needs a pipeline-progress WebSocket the backend doesn't expose. Mis Decisiones does not yet show the spec's ">60 días sin cerrar el ciclo" indicator: the backend endpoint it needs now exists (`GET /v1/outcomes`), but the client isn't wired to it yet — a pending increment, no longer a blocked one. `memory/ApiMemoryRepository` is a real integration against `GET /v1/memory/bias-profile`; its "Exportar mis datos"/"Borrar todo mi historial" buttons are visible per spec but show a "coming soon" notice, since the backend has no data-export/delete-all endpoint yet. `goals/ApiGoalsRepository` is a real integration too — but `GET /v1/goals` only ever returns *active* goals (`ListActiveGoalsUseCase`, no `include_inactive` flag), so deactivating one removes it from the client's view for good; Perfil de Objetivos therefore labels that action "Quitar" rather than a reversible-sounding toggle, and re-activation needs a backend change. `simulations/ApiSimulationsRepository` is a real integration against `GET`/`POST /v1/decisions/{id}/simulations`; since the `POST` blocks for the whole pipeline with no progress channel, `DecisionResultScreen` shows an honest indeterminate wait (plus the spec's reassurance micro-copy past ~15s) instead of Pantalla 6's stage animation, and the repository raises the request timeout to 90s so the app-wide 10s default can't abort a healthy run. **A `halt_and_refer` from the Safety Gate replaces the entire result**: `simulation.safetyGate.requiresReferral` is checked before any other branch, so scenarios/synthesis present in the payload are never rendered and there is no "ver de todos modos" escape (docs/PRD.md §18); an *empty* `safety_gate_result` — a run that failed before reaching Agent 0 — deliberately does **not** read as a halt, so a transport failure is reported as a failure rather than as a crisis referral. Pantalla 11 (cierre de ciclo, docs/PRD.md CU8) is the bottom section of that same screen rather than a screen of its own — the spec calls it "detalle de decisión pasada + cierre de ciclo", and that detail is what Pantallas 7+9 already render; `OutcomeSection` posts to `POST /v1/decisions/{id}/outcome` and only appears under a `completed` simulation (409 otherwise). **The client does not yet read `GET /v1/outcomes`**, so on opening a decision it still offers the prompt without knowing whether that loop was already closed; the backend now answers 409 on a duplicate rather than calibrating twice, so the worst case is a rejected request instead of a corrupted bias profile. Wiring the client to that endpoint also unblocks Pantalla 10's ">60 días" indicator — one increment, two screens. `calibration_delta` is rendered raw on a -100..100 axis with an animated needle and no invented interpretation (`UserBiasProfile.with_calibration_delta` calls its own formula "a starting formula, not a validated calibration model"), while `system_errors_identified` is shown verbatim; a `null` `closest_scenario_id` is stated as the blind spot docs/REALITY_ENGINE.md §2 says it is, never resolved to a nearest match client-side.

## Commands

Three independent projects (two Python, one Dart/Flutter), each with its own dependency setup — always `cd` into the right one first.

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

# app/ (Flutter client)
cd app
flutter pub get
flutter analyze && flutter test && dart format --output=none --set-exit-if-changed lib test
flutter run --dart-define=API_BASE_URL=http://localhost:8000  # requires a device/emulator or `-d chrome`
```

CI (`.github/workflows/backend-ci.yml`, `reality-engine-ci.yml`, `app-ci.yml`) runs exactly the commands above (minus `flutter run`, minus `alembic`/`docker compose`) in each project's own directory — keep local commands matching that so CI never surprises you.

## Architecture conventions

### Core API (`backend/`) — established by `identity`/`goals`/`decisions`/`simulations`/`memory`/`billing`, follow for every new bounded context

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
- **A replica of an external system's state is only ever written by the one handler that consumes that system's own change events — never by request-driven use cases.** `Subscription` (`billing/domain/entities.py`) mirrors Stripe's own subscription state; only `HandleStripeWebhookEventUseCase` calls `SubscriptionRepository.upsert()`. `CreateCheckoutSessionUseCase`/`CreatePortalSessionUseCase` only ever read it. Webhook processing is idempotent by construction: `StripeEventRepository.exists(stripe_event_id)` is checked before applying any effect, so Stripe's own retry-until-2xx behavior can never double-apply a webhook.

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

### Flutter client (`app/`) — established by the design system + `splash`/`onboarding`/`auth`

- **Screens never hardcode a color, font size, spacing value, or animation curve/duration.** Every visual constant comes from `design_system/` (`VarColors`, `VarTypography`, `VarSpacing`, `VarMotion`) or `Theme.of(context)` (which `VarTheme` assembles from those same tokens) — docs/UX_DESIGN.md §1.1 is explicit that color represents probability/alignment, "nunca decoración gratuita," so a stray hex value is a design-system violation, not a style nit.
- **`core/` never imports a `features/*` type.** `core/network/api_client.dart`'s `accessTokenProvider` is a plain `Provider<String?>` that `features/auth` overrides once a real session exists — the dependency direction is features → core, same one-way rule as backend's `api → application → domain ← infrastructure` layering, just expressed as "don't import upward" instead of ABCs.
- **A port gets a concrete adapter only when there's something real to call.** `features/auth/domain/auth_repository.dart` and `features/onboarding/domain/onboarding_repository.dart` exist now so screens are built against a stable interface; `LocalStubAuthRepository` is loudly named and doc-commented as an interim stand-in, never silently passed off as the real Supabase adapter. Follow this instead of leaving a screen directly calling a placeholder HTTP call inline.
- **Every screen gets a widget-test file that exercises real navigation** (`test/features/<feature>/`), built by wrapping the screen(s) under test in a real `GoRouter` + `ProviderScope`, not by asserting on isolated widget trees — see `onboarding_screen_test.dart`/`auth_screen_test.dart` for the pattern. Design-system token tests (`test/design_system/`) are plain `test()`s, not `testWidgets()`, except where they need Flutter bindings (e.g. `google_fonts`, which requires `TestWidgetsFlutterBinding.ensureInitialized()` and `GoogleFonts.config.allowRuntimeFetching = false` so tests never hit the network).
- **Motion must communicate state, not decorate.** `VarMotion.nonStreamingCeiling` documents that almost every animation in this app should resolve within ~350ms; the one documented exception is the future pipeline-streaming screen (Pantalla 6), which is allowed up to ~20s because it represents real work in progress (docs/UX_DESIGN.md §1.4).
- **A refusal from the backend is rendered as a refusal, checked first.** `DecisionResultScreen` asks `simulation.safetyGate.requiresReferral` before every other branch, so a `halt_and_refer` can't fall through to scenario rendering no matter what else the payload carries — the client half of `SafetyGateAgent`'s fail-safe posture. The named getter lives on the domain type (`SafetyGateResult`), not as a string comparison at the call site, so there's exactly one place to get it right. `SafetyReferral` deliberately hardcodes no crisis hotline numbers: they're country- and language-specific, and a dead number shown to someone in crisis is worse than none — a locale-aware, professionally-reviewed list is a required pre-launch deliverable (docs/PRD.md §18).
- **Never fake progress the client can't observe.** While `POST /v1/decisions/{id}/simulations` blocks, `RunningIndicator` shows an indeterminate wait and, past ~15s, the spec's reassurance micro-copy — not a synthetic progress bar, which docs/UX_DESIGN.md warns "rompería confianza si se estanca". Same posture as the rest of the app's honest gaps (mic capture, GDPR export): show the true state, don't simulate the missing one.

### All three (backend, reality_engine, app)

- **Strict typing everywhere**: `mypy --strict` is enforced in CI for `backend/` and `reality_engine/`; `app/`'s `flutter analyze` (default `flutter_lints` rule set) is the Dart-side equivalent, plus a `dart format --set-exit-if-changed` check so formatting is never a review nit. Generic containers need type args (`dict[str, Any]`, not `dict`); anything read off an untyped attribute (e.g. `request.app.state.*`) needs an explicit `cast`.
- **Module-by-module discipline**: don't start a new bounded context, agent, or Flutter feature until the current one has its full layer set (domain + application + infrastructure + api for backend services; domain + presentation [+ data where a real adapter exists] for `app/` features) + tests + a passing lint/type/test run. This mirrors the explicit build rule this project was commissioned under — partial modules are worse than fewer modules.
