# VAR OS — Reality Engine

Servicio independiente del Core API (`docs/ARCHITECTURE.md §2.2`): su perfil de carga (IO-bound esperando respuestas de IA, alta latencia, necesidad de colas) es fundamentalmente distinto al del resto del backend CRUD.

**Estado actual: los 13 agentes de docs/REALITY_ENGINE.md están implementados.** `AnalysisPipeline` encadena 0-6 (`POST /v1/analyze`); `SimulationPipeline` la extiende con 7-11 (`POST /v1/simulate`) hasta producir escenarios rankeados, una síntesis, y — si hay proveedor de embeddings configurado — un resumen listo para memoria semántica. El Agente 12 (Aprendizaje) vive fuera de ambos pipelines, en su propio endpoint (`POST /v1/calibrate`), porque solo corre cuando un usuario reporta qué pasó realmente con una decisión pasada, no en cada simulación. Este servicio sigue sin conocer `user_id`/`decision_id` ni llamar a Core API directamente — persistir en `memory` es responsabilidad de `simulations`' `RunSimulationUseCase` en `backend/`, que ya consume esta respuesta. Tampoco hay orquestador de grafo con paralelización real, workers async, ni streaming de progreso por WebSocket (todo eso descrito en `docs/ARCHITECTURE.md §2.2`) — la ejecución es secuencial.

## Por qué el Agente 0 primero

Es el único paso del pipeline que **puede terminar la ejecución anticipadamente** (`docs/REALITY_ENGINE.md §1`), y su ausencia sería el bug de seguridad más grave posible en este producto: generar "escenarios de futuro" sobre una situación de crisis real. Se construyó junto con el `AI Gateway` porque es la pieza de infraestructura que todo agente futuro necesitará.

## Estructura

```
src/reality_engine/
  main.py, config.py        # app factory, settings (prefijo VAROS_RE_)
  ai_gateway/
    domain/ports.py          # LLMProvider, EmbeddingProvider (puertos), ModelTier, *GenerationError
    application/gateway.py    # AIGateway: retry + fallback entre proveedores por tier, y para embeddings
    infrastructure/
      fake_provider.py, fake_embedding_provider.py   # dobles de test, sin red
      openai_provider.py, openai_embedding_provider.py # adaptadores reales, probados con cliente mockeado
  pipeline/
    domain/schemas.py         # contratos JSON de cada agente (Pydantic), Agentes 0-12
    agents/
      safety_gate.py            # Agente 0: reglas deterministas + clasificador LLM, fail-safe
      comprehension.py           # Agente 1
      summary.py                 # Agente 2
      goals_extraction.py        # Agente 3 (normaliza pesos de forma determinista)
      emotions.py                 # Agente 4
      psychology.py                # Agente 5
      risk_analysis.py              # Agente 6
      scenario_generation.py         # Agente 7 (tier reasoning_creative, valida lenguaje condicional)
      comparison.py                   # Agente 8
      ranking.py                       # Agente 9 — función pura, sin LLM
      synthesis.py                      # Agente 10 (tier reasoning_creative, valida lenguaje no-imperativo)
      memory.py                          # Agente 11: genera resumen + texto embebible
      learning.py                         # Agente 12: calibración on-demand, fuera de los pipelines
      _language_guards.py               # detectores compartidos de lenguaje determinista/imperativo
    orchestrator.py             # AnalysisPipeline (0-6) y SimulationPipeline (0-11)
  api/                        # router FastAPI (/v1/safety-check, /v1/analyze, /v1/simulate, /v1/calibrate)
tests/
  unit/ai_gateway/            # retry/fallback (LLM y embeddings) + adaptadores OpenAI mockeados
  unit/pipeline/               # cada agente aislado + ambos orquestadores
  integration/                  # API vía TestClient
```

## Decisión de diseño: fail-safe, no fail-open

Si `VAROS_RE_OPENAI_API_KEY` no está configurada, el tier `safety_classification` queda sin proveedores. El `SafetyGateAgent` **nunca deja pasar contenido sin clasificar**: sin proveedor configurado, o si el proveedor falla tras sus reintentos, la respuesta siempre es `HALT_AND_REFER`. Un despliegue mal configurado falla cerrado, no abierto — ver `config.py` y los tests en `tests/unit/pipeline/test_safety_gate.py`.

La lista de patrones deterministas en `pipeline/agents/safety_gate.py` es un punto de partida, **no una lista validada clínica o legalmente** — está marcado explícitamente en el código. Antes de cualquier lanzamiento real hace falta revisión profesional (`docs/PRD.md §18`).

## Decisión de diseño: guardianes lingüísticos, no reescritura silenciosa

`docs/PRD.md §2` es no negociable en "nunca afirmar certeza" y "el usuario decide". Los Agentes 7 (Escenarios) y 10 (Síntesis) validan su propia salida contra listas de patrones (`pipeline/agents/_language_guards.py`) buscando lenguaje de futuro afirmativo ("serás", "pasará") o imperativo ("deberías", "debes"). Si lo encuentran, **piden al modelo que regenere** (hasta `max_language_retries` veces) — nunca reescriben o recortan el texto del modelo por su cuenta. Si el lenguaje problemático persiste, el agente falla con `LLMGenerationError` en vez de servir un resultado que viole el principio del producto. Misma lógica de humildad que en Agente 0: listas curadas, no un clasificador lingüístico riguroso.

## Decisión de diseño: Memoria es una mejora, nunca un motivo de fallo

Si el Agente 11 falla, o no hay proveedor de embeddings configurado, `SimulationPipeline` captura el error y deja `memory: null` en la respuesta — la simulación completa (escenarios, comparación, ranking, síntesis) se entrega igual. Guardar memoria semántica es una capa encima de una simulación exitosa, no una precondición de ella (ver `SimulationPipeline._try_build_memory` en `pipeline/orchestrator.py`).

## Decisión de diseño: Aprendizaje vive fuera del pipeline

El Agente 12 no corre en cada `/v1/simulate` — se dispara explícitamente vía `POST /v1/calibrate` cuando un usuario cierra el ciclo de una decisión pasada (`docs/PRD.md`, CU8). Este servicio no conoce `user_id`/`decision_id` ni guarda estado entre llamadas: el caller (Core API) le manda `reported_outcome` + los escenarios/ranking originales (reconstruidos desde lo que ya tiene persistido) y recibe de vuelta el análisis de calibración para que Core API decida qué persistir en `memory`.

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
