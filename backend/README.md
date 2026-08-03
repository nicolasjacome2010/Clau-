# VAR OS — Core API

Monolito modular (Clean Architecture / DDD selectivo) descrito en `docs/ARCHITECTURE.md §4`. Bounded contexts implementados hasta ahora: **identity**, **goals**.

## Estructura

```
src/core_api/
  main.py                  # FastAPI app factory
  config.py                # Settings (pydantic-settings, prefijo VAROS_)
  db.py                    # Engine/session compartidos + tipos SQLAlchemy comunes
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
migrations/                 # Alembic (async) — 0001 identity, 0002 goals
tests/
  unit/                     # Casos de uso contra fakes en memoria
  integration/               # Repositorios contra SQLite real + API contra TestClient
```

## Desarrollo local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # y completa VAROS_SUPABASE_URL

# stack completo (Postgres + Redis + API) desde la raíz del repo:
docker compose up --build

# o solo la API contra un Postgres local ya corriendo:
uvicorn core_api.main:app --reload
```

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
