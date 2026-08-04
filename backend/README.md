# VAR OS — Core API

Monolito modular (Clean Architecture / DDD selectivo) descrito en `docs/ARCHITECTURE.md §4`. Bounded contexts implementados hasta ahora: **identity**, **goals**, **decisions**, **simulations**.

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
    domain/                          # Simulation, SimulationScenario (inmutables una vez creados)
    application/                      # RunSimulationUseCase: orquesta decisions + goals + Reality Engine
    infrastructure/
      reality_engine_client.py         # adaptador HTTP real, valida la forma del JSON con Pydantic
    api/                              # /v1/decisions/{id}/simulations, /v1/simulations/{id}
migrations/                 # Alembic (async) — 0001 identity, 0002 goals, 0003 decisions, 0004 simulations
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
