# VAR OS — Reality Engine

Servicio independiente del Core API (`docs/ARCHITECTURE.md §2.2`): su perfil de carga (IO-bound esperando respuestas de IA, alta latencia, necesidad de colas) es fundamentalmente distinto al del resto del backend CRUD.

**Estado actual: solo el Agente 0 (Risk & Safety Gate) está implementado.** El pipeline completo de 13 agentes está especificado en `docs/REALITY_ENGINE.md` pero no construido — no existe todavía un endpoint `/v1/simulate`, ni orquestador de grafo, ni workers async, ni streaming de progreso por WebSocket (todo eso descrito en `docs/ARCHITECTURE.md §2.2`).

## Por qué el Agente 0 primero

Es el único paso del pipeline que **puede terminar la ejecución anticipadamente** (`docs/REALITY_ENGINE.md §1`), y su ausencia sería el bug de seguridad más grave posible en este producto: generar "escenarios de futuro" sobre una situación de crisis real. Se construyó junto con el `AI Gateway` porque es la pieza de infraestructura que todo agente futuro necesitará.

## Estructura

```
src/reality_engine/
  main.py, config.py        # app factory, settings (prefijo VAROS_RE_)
  ai_gateway/
    domain/ports.py          # LLMProvider (puerto), ModelTier, LLMGenerationError
    application/gateway.py    # AIGateway: retry + fallback entre proveedores por tier
    infrastructure/
      fake_provider.py         # doble de test, sin red
      openai_provider.py        # adaptador real (Structured Outputs), probado con cliente mockeado
  pipeline/
    domain/schemas.py         # contratos JSON de cada agente (Pydantic)
    agents/safety_gate.py       # Agente 0: reglas deterministas + clasificador LLM, fail-safe
  api/                        # router FastAPI (solo /v1/safety-check por ahora)
tests/
  unit/ai_gateway/            # retry/fallback del gateway + adaptador OpenAI mockeado
  unit/pipeline/               # Agente 0: camino determinista, camino LLM, fail-safe
  integration/                  # API vía TestClient
```

## Decisión de diseño: fail-safe, no fail-open

Si `VAROS_RE_OPENAI_API_KEY` no está configurada, el tier `safety_classification` queda sin proveedores. El `SafetyGateAgent` **nunca deja pasar contenido sin clasificar**: sin proveedor configurado, o si el proveedor falla tras sus reintentos, la respuesta siempre es `HALT_AND_REFER`. Un despliegue mal configurado falla cerrado, no abierto — ver `config.py` y los tests en `tests/unit/pipeline/test_safety_gate.py`.

La lista de patrones deterministas en `pipeline/agents/safety_gate.py` es un punto de partida, **no una lista validada clínica o legalmente** — está marcado explícitamente en el código. Antes de cualquier lanzamiento real hace falta revisión profesional (`docs/PRD.md §18`).

## Desarrollo local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # opcionalmente añade VAROS_RE_OPENAI_API_KEY

uvicorn reality_engine.main:app --reload --port 8100
```

## Calidad — correr antes de cada commit

```bash
ruff check src tests
mypy src
pytest -v
```

Los tests corren sin `OPENAI_API_KEY` real: `FakeLLMProvider` cubre el pipeline y `test_openai_provider.py` verifica el adaptador contra un cliente `AsyncOpenAI` mockeado (prompt, parseo de JSON, mapeo de errores) — nunca contra la red.
