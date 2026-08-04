# VAR OS — Reality Engine

Servicio independiente del Core API (`docs/ARCHITECTURE.md §2.2`): su perfil de carga (IO-bound esperando respuestas de IA, alta latencia, necesidad de colas) es fundamentalmente distinto al del resto del backend CRUD.

**Estado actual: Agentes 0-10 de 13 están implementados** — todo el pipeline salvo Memoria y Aprendizaje. `AnalysisPipeline` encadena 0-6 (`POST /v1/analyze`); `SimulationPipeline` la extiende con 7-10 (`POST /v1/simulate`) hasta producir escenarios rankeados y una síntesis. **Faltan los Agentes 11-12** (Memoria, Aprendizaje) porque necesitan el bounded context `memory` de Core API, que no existe todavía. Tampoco hay orquestador de grafo con paralelización real, workers async, ni streaming de progreso por WebSocket (todo eso descrito en `docs/ARCHITECTURE.md §2.2`) — la ejecución es secuencial.

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
    domain/schemas.py         # contratos JSON de cada agente (Pydantic), Agentes 0-10
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
      _language_guards.py               # detectores compartidos de lenguaje determinista/imperativo
    orchestrator.py             # AnalysisPipeline (0-6) y SimulationPipeline (0-10)
  api/                        # router FastAPI (/v1/safety-check, /v1/analyze, /v1/simulate)
tests/
  unit/ai_gateway/            # retry/fallback del gateway + adaptador OpenAI mockeado
  unit/pipeline/               # cada agente aislado + ambos orquestadores
  integration/                  # API vía TestClient
```

## Decisión de diseño: fail-safe, no fail-open

Si `VAROS_RE_OPENAI_API_KEY` no está configurada, el tier `safety_classification` queda sin proveedores. El `SafetyGateAgent` **nunca deja pasar contenido sin clasificar**: sin proveedor configurado, o si el proveedor falla tras sus reintentos, la respuesta siempre es `HALT_AND_REFER`. Un despliegue mal configurado falla cerrado, no abierto — ver `config.py` y los tests en `tests/unit/pipeline/test_safety_gate.py`.

La lista de patrones deterministas en `pipeline/agents/safety_gate.py` es un punto de partida, **no una lista validada clínica o legalmente** — está marcado explícitamente en el código. Antes de cualquier lanzamiento real hace falta revisión profesional (`docs/PRD.md §18`).

## Decisión de diseño: guardianes lingüísticos, no reescritura silenciosa

`docs/PRD.md §2` es no negociable en "nunca afirmar certeza" y "el usuario decide". Los Agentes 7 (Escenarios) y 10 (Síntesis) validan su propia salida contra listas de patrones (`pipeline/agents/_language_guards.py`) buscando lenguaje de futuro afirmativo ("serás", "pasará") o imperativo ("deberías", "debes"). Si lo encuentran, **piden al modelo que regenere** (hasta `max_language_retries` veces) — nunca reescriben o recortan el texto del modelo por su cuenta. Si el lenguaje problemático persiste, el agente falla con `LLMGenerationError` en vez de servir un resultado que viole el principio del producto. Misma lógica de humildad que en Agente 0: listas curadas, no un clasificador lingüístico riguroso.

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
