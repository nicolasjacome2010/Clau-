# VAR OS — Core API

Monolito modular (Clean Architecture / DDD selectivo) descrito en `docs/ARCHITECTURE.md §4`. Bounded contexts implementados hasta ahora: **identity**, **goals**, **decisions**, **simulations**, **memory**, **billing**.

## Estructura

```
src/core_api/
  main.py                  # FastAPI app factory
  config.py                # Settings (pydantic-settings, prefijo VAROS_)
  db.py                    # Engine/session compartidos + tipos SQLAlchemy comunes
  crypto.py                 # Cifrado de campos sensibles (FieldEncryptor, docs/DATABASE.md §5)
  dependencies.py          # DI compartida (sesión de DB, identidad autenticada, repos)
  auth/
    token_verifier.py      # Verificación de JWT de Supabase (+ doble de test)
  identity/
    domain/                # Entidades, excepciones, interfaces de repositorio
    application/            # Casos de uso (GetOrCreateUser, UpdateUserProfile)
    infrastructure/          # Modelos SQLAlchemy + repositorios concretos
    api/                     # Router FastAPI + esquemas Pydantic
  goals/
    domain/ | application/ | infrastructure/ | api/   # mismo patrón que identity
  decisions/
    domain/                # Decision (agregado raíz, máquina de estados de status)
    application/ | infrastructure/ | api/   # infra cifra/descifra raw_input en el borde
  simulations/
    domain/reality_engine_port.py   # puerto + DTOs propios — nunca importa tipos de reality_engine/
    domain/                          # Simulation, SimulationScenario, DecisionOutcome (inmutables)
    application/                      # RunSimulationUseCase (decisions+goals+Reality Engine, guarda
                                        # memoria semántica si el Agente 11 la produjo) y
                                        # ReportDecisionOutcomeUseCase (cierra el ciclo vía Agente 12)
    infrastructure/
      reality_engine_client.py         # adaptador HTTP real: /v1/simulate y /v1/calibrate
    api/                              # /v1/decisions/{id}/simulations, /v1/simulations/{id},
                                        # /v1/decisions/{id}/outcome
  memory/
    domain/similarity.py             # cosine_similarity puro, sin numpy
    domain/                           # UserBiasProfile (media móvil ponderada), MemoryEmbedding
    application/                       # incluye dedup por similitud > 0.92 al guardar un embedding
    infrastructure/                     # embedding como JSON — ver docstring del repo para la migración a pgvector
    api/                              # /v1/memory/bias-profile, /v1/memory/embeddings(/search)
  billing/
    domain/stripe_port.py            # puerto + DTOs propios — nunca importa el SDK `stripe` directamente
    domain/                           # Subscription (réplica de solo-lectura), StripeEvent (append-only)
    application/                       # Get/CreateCheckoutSession/CreatePortalSession +
                                        # HandleStripeWebhookEventUseCase (idempotente por stripe_event_id)
    infrastructure/
      stripe_client.py                 # adaptador real (stripe.StripeClient, *_async — no bloquea el loop)
    api/                              # /v1/billing/subscription, /checkout-session, /portal-session, /webhook
migrations/                 # Alembic (async) — 0001 identity, 0002 goals, 0003 decisions,
                             # 0004 simulations, 0005 memory, 0006 decision_outcomes, 0007 billing
tests/
  unit/                     # Casos de uso contra fakes en memoria
  integration/               # Repositorios contra SQLite real + API contra TestClient
```

## Desarrollo local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # y completa VAROS_SUPABASE_URL y VAROS_FIELD_ENCRYPTION_KEY

# stack completo (Postgres + Redis + Core API + Reality Engine) desde la raíz del repo:
docker compose up --build

# o solo la API contra un Postgres local ya corriendo:
uvicorn core_api.main:app --reload
```

`simulations` necesita el servicio `reality_engine/` corriendo y alcanzable en `VAROS_REALITY_ENGINE_BASE_URL` (por defecto `http://localhost:8100`) para que `POST /v1/decisions/{id}/simulations` funcione — sin `OPENAI_API_KEY` configurada ahí, el Reality Engine sigue respondiendo pero siempre falla seguro (`HALT_AND_REFER`), así que la simulación se crea igual, con `status=partial`.

Cuando una simulación se completa y el Reality Engine incluyó un resumen de memoria (Agente 11), `RunSimulationUseCase` lo persiste automáticamente en `memory` — sin bloquear la simulación si el Reality Engine no lo produjo. `POST /v1/decisions/{id}/outcome` cierra el ciclo (docs/PRD.md CU8): reenvía los escenarios de la última simulación completada al Reality Engine (`/v1/calibrate`, Agente 12) junto con lo que el usuario reporta que pasó realmente, y persiste tanto el `DecisionOutcome` como el efecto en `UserBiasProfile`.

`billing` necesita `VAROS_STRIPE_SECRET_KEY`/`VAROS_STRIPE_WEBHOOK_SECRET` (ver `.env.example`) para crear sesiones de Checkout/Customer Portal reales y para verificar la firma de los webhooks — sin ellos, `/v1/billing/checkout-session` y `/v1/billing/portal-session` devuelven 503, y `/v1/billing/webhook` rechaza todo con 400 (fail-closed, no fail-open, misma postura que el Safety Gate del Reality Engine). Stripe es la fuente de verdad del estado de suscripción (docs/ARCHITECTURE.md §9): `Subscription` es una réplica de solo lectura que solo `HandleStripeWebhookEventUseCase` escribe, y `stripe_events` es un log append-only de idempotencia — un evento reenviado por Stripe (reintenta hasta recibir 2xx) es un no-op, nunca se reaplica.

## Migraciones

```bash
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
```

## Calidad — correr antes de cada commit

```bash
ruff check src tests
mypy src
pytest -v
```

Los tests de integración usan SQLite en memoria (no Postgres) para ser rápidos y deterministas en CI; la compatibilidad multi-dialecto que eso ejercita (por ejemplo el fallback de upsert en `identity/infrastructure/repository.py`) está documentada donde ocurre. Los tests unitarios usan repositorios en memoria que implementan las mismas interfaces de dominio, nunca SQLAlchemy directamente.

## Añadir el siguiente módulo (bounded context)

Sigue el mismo patrón que `identity/`: `domain` → `application` → `infrastructure` → `api`, con tests unitarios sobre fakes y tests de integración sobre el repositorio real. No añadas un módulo nuevo sin su propia migración de Alembic y su propia cobertura de tests — es la regla que mantiene el monolito modular realmente modular.
