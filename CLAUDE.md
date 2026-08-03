# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**VAR OS** (Variable Reality Operating System) — a decision-simulation product (not a chatbot, not a prediction tool). Full product/technical design lives in `docs/`, read in this order:

1. `docs/PRD.md` — vision, users, user stories, navigation map, roadmap, business model, KPIs.
2. `docs/ARCHITECTURE.md` — system architecture, service boundaries, and **§0 explicitly documents where the implementation deviates from the original brief and why** (multi-provider AI gateway instead of OpenAI-only, modular monolith instead of microservices-from-day-1, pgvector instead of a separate vector DB). Read §0 before assuming the brief's stack is followed literally.
3. `docs/REALITY_ENGINE.md` — the 13-agent decision-simulation pipeline (Safety Gate → Comprehension → ... → Learning), each agent's prompt/input/output JSON contract and error handling. Not yet implemented in code.
4. `docs/DATABASE.md` — full normalized schema. Only the `identity` (`users`, `user_profiles`) and `goals` slices are implemented so far; the rest is design-only.
5. `docs/UX_DESIGN.md` — screen-by-screen design system (color, type, motion, wireframes) for the future Flutter client. Not yet implemented.

Only **Phase 6, modules 1-2 ("identity", "goals")** of the backend have been built. Everything else in those docs is design, not yet code — don't assume a feature exists just because it's documented.

## Repository layout

```
docs/            Product + architecture + Reality Engine + DB + UX design docs (see above)
backend/         Core API service (Python/FastAPI, Clean Architecture monolith — see docs/ARCHITECTURE.md §4)
  src/core_api/
    main.py, config.py, db.py, dependencies.py   # app factory, settings, shared DB/DI plumbing
    auth/                                          # Supabase JWT verification
    identity/domain|application|infrastructure|api # bounded context: user profile, JIT provisioning
    goals/domain|application|infrastructure|api     # bounded context: user's weighted decision goals
  migrations/    Alembic (async, drives off core_api.config.Settings, not a static URL in alembic.ini)
                 0001 identity tables, 0002 goals table
  tests/unit/    Use cases against in-memory fakes of the domain repository interfaces
  tests/integration/  Repositories against a real SQLite round-trip; API against FastAPI TestClient
docker-compose.yml   Full local stack: Postgres (pgvector image) + Redis + core-api
.github/workflows/backend-ci.yml   Lint (ruff) + type check (mypy --strict) + tests, path-filtered to backend/
```

There is no Flutter client, Reality Engine service, Billing service, or any bounded context beyond `identity`/`goals` yet — `decisions` is next per the roadmap in `docs/PRD.md` §12 and the module-by-module build rule below.

## Commands (run from `backend/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check src tests      # lint
mypy src                  # strict type check (mypy --strict is configured in pyproject.toml)
pytest -v                 # full suite
pytest tests/unit/identity/test_use_cases.py::test_get_or_create_user_is_idempotent  # single test

alembic upgrade head       # apply migrations (needs VAROS_DATABASE_URL, see .env.example)
alembic revision --autogenerate -m "description"

docker compose up --build  # from repo root: Postgres + Redis + API together
```

CI (`.github/workflows/backend-ci.yml`) runs exactly `ruff check`, `mypy src`, and `pytest -v` — keep local commands matching that so CI never surprises you.

## Architecture conventions (established by `identity`/`goals` — follow for every new module)

- **Layering is directional and non-negotiable**: `api/` → `application/` (use cases) → `domain/` (entities + abstract repository interfaces, zero framework imports) ← `infrastructure/` (SQLAlchemy models + concrete repositories implementing the domain interfaces). Use cases depend on the domain interfaces, never on `infrastructure` directly (Dependency Inversion). See `backend/README.md` for the exact file layout to copy for the next bounded context.
- **Repository pattern everywhere.** Every persistence access goes through an ABC defined in `domain/repositories.py`; production code gets `SqlAlchemy*Repository`, tests get either an in-memory fake (unit tests) or the real repository against SQLite (integration tests) — never mock the ORM directly.
- **Ownership scoping**: endpoints operate on "my X" using the caller's JWT identity, never an arbitrary `user_id` from the request body/path (see `goals/api/router.py`). A resource that exists but belongs to someone else returns 404, not 403 — never confirm the existence of another user's data (see the `GoalNotFoundError` docstring).
- **Datetimes**: use the shared `UTCDateTime` type decorator from `core_api/db.py` for any timezone-aware column, not raw `DateTime(timezone=True)`. SQLite (used in integration tests) silently drops tzinfo on round-trip; this decorator normalizes it back to UTC on read so tests and Postgres behave identically. This was a real bug caught while building `identity` — don't reintroduce it in new modules.
- **JSON/JSONB columns**: declare as `JSON().with_variant(JSONB, "postgresql")` (see `identity/infrastructure/models.py`) so models stay portable to the SQLite test path.
- **Auth**: services never call Supabase Auth directly — `core_api/auth/token_verifier.py` verifies the JWT Supabase already issued (JWKS, cached). `GetOrCreateUserUseCase` does JIT provisioning: the domain `User` row is created on the first authenticated request, not on a signup webhook.
- **Strict typing**: `mypy --strict` is enforced in CI. Generic containers need type args (`dict[str, Any]`, not `dict`); anything read off an untyped attribute (e.g. `request.app.state.*`) needs an explicit `cast`.
- **Module-by-module discipline**: don't start a new bounded context until the current one has domain + application + infrastructure + api + unit tests + integration tests + a passing `ruff`/`mypy`/`pytest` run, matching what `identity`/`goals` have. This mirrors the explicit build rule this project was commissioned under — partial modules are worse than fewer modules.
