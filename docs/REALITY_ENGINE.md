# VAR OS — Reality Engine (Fase 3)

| | |
|---|---|
| **Documento** | Reality Engine Spec v1.0 |
| **Depende de** | `docs/PRD.md`, `docs/ARCHITECTURE.md` |
| **Estado** | Fase 3 |

---

## 0. Principio de diseño

El Reality Engine **no responde preguntas**. Recibe una decisión, la procesa a través de un pipeline determinista de agentes especializados, y produce un objeto `SimulationResult` estructurado. Cada agente:

- Tiene **una sola responsabilidad** (Single Responsibility a nivel de prompt, no solo de código).
- Recibe y produce **JSON tipado** (validado contra un JSON Schema / modelo Pydantic — nunca texto libre entre agentes).
- Es **reintentable de forma aislada**: si el agente 7 falla, no hace falta re-ejecutar del 1.
- Registra su input/output en `simulation_steps` (auditoría y debugging — ver Fase 4) para trazabilidad total (principio no negociable del PRD §2).

Se añade un agente que el brief no listó explícitamente pero que es una decisión de arquitectura obligatoria como CTO: el **Agente 0 — Risk & Safety Gate**, que corre antes de cualquier procesamiento creativo. Sin él, el sistema podría generar "escenarios de futuro" sobre una situación de crisis (ideación suicida, violencia doméstica, etc.), lo cual es inaceptable. Este agente puede **terminar el pipeline anticipadamente**.

## 1. El pipeline

```
Input crudo del usuario (texto/voz transcrita)
        │
        ▼
┌───────────────────┐
│ 0. Risk & Safety   │──── si ALTO riesgo ──→ Derivación a recursos de ayuda (fin del pipeline)
│    Gate            │
└─────────┬─────────┘
          │ riesgo aceptable
          ▼
┌───────────────────┐
│ 1. Comprensión      │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 2. Resumen          │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 3. Extracción de    │
│    Objetivos        │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 4. Extracción de    │
│    Emociones        │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 5. Análisis         │
│    Psicológico      │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 6. Análisis de      │
│    Riesgos          │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 7. Generación de    │
│    Escenarios       │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 8. Comparación       │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 9. Ranking           │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 10. Síntesis         │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 11. Memoria          │──→ escribe en memory_embeddings / user_bias_profile
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 12. Aprendizaje      │──→ (asíncrono, no bloquea la respuesta al usuario)
│     (calibración)    │
└───────────────────┘
```

Los agentes 1–6 pueden paralelizarse parcialmente donde no hay dependencia estricta de datos (p. ej. Emociones y Análisis Psicológico pueden correr en paralelo una vez existe el Resumen); el orquestador (§2 Arquitectura) lo expresa como grafo, no como cadena estrictamente secuencial, para minimizar latencia.

---

## 2. Especificación de cada agente

Convención: todos los agentes reciben además un `context` común (`user_id`, `decision_id`, `simulation_id`, `locale`, perfil de memoria resumido si existe) que se omite en los ejemplos por brevedad, salvo cuando es relevante para el agente.

### Agente 0 — Risk & Safety Gate

- **Responsabilidad**: Detectar si el input del usuario describe una situación de riesgo agudo (autolesión, daño a terceros, abuso, crisis de salud mental) que no debe procesarse como una "simulación de decisión" normal. Combina un clasificador de IA con reglas deterministas (listas de patrones de alto riesgo) — nunca depende solo del LLM.
- **Prompt (sistema)**:
  > "Eres un clasificador de seguridad. NO respondas a la decisión del usuario. Tu única tarea es clasificar el texto en una de estas categorías de riesgo: `none`, `moderate_distress`, `acute_risk`. `acute_risk` incluye cualquier mención de autolesión, suicidio, daño a otra persona, abuso o crisis médica aguda. Ante la duda, clasifica hacia arriba (más riesgo), nunca hacia abajo. Responde solo JSON según el esquema."
- **Input**:
```json
{ "raw_input": "string", "input_modality": "text | voice_transcript" }
```
- **Output**:
```json
{
  "risk_level": "none | moderate_distress | acute_risk",
  "signals_detected": ["string"],
  "safe_to_proceed": true,
  "recommended_action": "proceed | proceed_with_care | halt_and_refer"
}
```
- **Errores posibles**: `ambiguous_classification` (el modelo devuelve baja confianza) → se resuelve escalando siempre a la categoría más conservadora, nunca reintentando para "bajar" el riesgo. `schema_validation_failed` → reintento inmediato con temperatura 0; si falla dos veces, se trata como `acute_risk` por defecto (fail-safe, no fail-open).

### Agente 1 — Comprensión

- **Responsabilidad**: Convertir el input crudo (potencialmente desordenado, coloquial, con voz transcrita imperfecta) en una representación estructurada y neutral de "la decisión" que se está evaluando, sin interpretar aún emociones ni objetivos.
- **Prompt (sistema)**:
  > "Extrae de este texto la decisión concreta que la persona está evaluando. Identifica: la pregunta central, las opciones explícitas mencionadas (si las hay), el contexto factual relevante (personas, plazos, cifras). No opines. No completes información que no esté en el texto; si falta información crítica, indícalo en `missing_info`."
- **Input**: `{ "raw_input": "string" }`
- **Output**:
```json
{
  "decision_question": "string",
  "explicit_options": ["string"],
  "factual_context": { "entities": ["string"], "deadlines": ["string"], "figures": ["string"] },
  "missing_info": ["string"],
  "requires_clarification": true
}
```
- **Errores posibles**: `insufficient_input` (texto demasiado corto/vago) → dispara flujo de clarificación (PRD §11) devolviendo hasta 3 preguntas dirigidas en vez de avanzar el pipeline.

### Agente 2 — Resumen

- **Responsabilidad**: Producir un resumen canónico y compacto de la decisión (usado como contexto compartido por los agentes siguientes, para no reenviar el texto crudo completo a cada uno — control de costo de tokens).
- **Prompt (sistema)**:
  > "Resume la siguiente decisión estructurada en un párrafo de máximo 120 palabras, en tono neutral, apto para ser usado como contexto por otros sistemas analíticos. No añadas juicios de valor."
- **Input**: output del Agente 1.
- **Output**: `{ "summary": "string (<=120 words)" }`
- **Errores posibles**: `summary_too_long` → truncado determinista + regeneración con instrucción reforzada de longitud.

### Agente 3 — Extracción de Objetivos

- **Responsabilidad**: Identificar qué está optimizando realmente el usuario (dinero, estabilidad, crecimiento, felicidad, relaciones, status, libertad, etc.), incluyendo objetivos implícitos no declarados explícitamente, y asignar pesos relativos.
- **Prompt (sistema)**:
  > "A partir del resumen de la decisión y del perfil de objetivos declarado por el usuario (si existe), identifica hasta 5 objetivos que la persona está intentando optimizar. Para cada uno, asigna un peso relativo (suma 100) basado en el énfasis del texto y, si existe, el historial de objetivos previos del usuario. Distingue objetivos explícitos (dichos directamente) de inferidos."
- **Input**: `{ "summary": "string", "declared_goals": ["string"], "user_goal_profile": {} }`
- **Output**:
```json
{
  "goals": [
    { "name": "string", "weight": 0, "source": "explicit | inferred" }
  ]
}
```
- **Errores posibles**: `weights_do_not_sum_100` → normalización determinista post-procesamiento (no se re-llama al modelo solo por esto).

### Agente 4 — Extracción de Emociones

- **Responsabilidad**: Detectar el estado emocional del usuario respecto a la decisión (ansiedad, ilusión, culpa, miedo, alivio anticipado, etc.) para calibrar tono de la síntesis final y alimentar al Análisis Psicológico. No terapéutico, no diagnóstico.
- **Prompt (sistema)**:
  > "Identifica las emociones dominantes expresadas o implícitas en el texto respecto a esta decisión. No hagas diagnóstico clínico. Devuelve emociones con intensidad relativa (0-1) y evidencia textual breve que las respalde."
- **Input**: `{ "raw_input": "string", "summary": "string" }`
- **Output**:
```json
{
  "emotions": [ { "label": "string", "intensity": 0.0, "evidence": "string" } ],
  "overall_emotional_load": "low | medium | high"
}
```
- **Errores posibles**: `no_emotional_signal` (texto puramente factual) → válido, se devuelve `emotions: []` sin forzar detección.

### Agente 5 — Análisis Psicológico

- **Responsabilidad**: Identificar sesgos cognitivos relevantes en juego (aversión a la pérdida, sesgo de confirmación, descuento hiperbólico, efecto del statu quo, sesgo de autoridad por presión social, etc.) y patrones del perfil histórico del usuario (si `memory` tiene un `user_bias_profile`).
- **Prompt (sistema)**:
  > "Basado en la decisión, el estado emocional detectado y (si existe) el historial de sesgos previos de este usuario, identifica qué sesgos cognitivos podrían estar distorsionando su evaluación de las opciones. Para cada sesgo, explica en una frase cómo se manifiesta específicamente en este caso. No listes sesgos genéricos sin evidencia en el texto."
- **Input**: `{ "summary": "string", "emotions": {}, "user_bias_profile": {} }`
- **Output**:
```json
{
  "biases_detected": [ { "bias": "string", "manifestation": "string", "confidence": 0.0 } ],
  "psychological_readiness": "low | medium | high"
}
```
- **Errores posibles**: `low_confidence_all_biases` → se incluyen igual pero marcados, la UI los muestra con menor énfasis visual (Fase 5).

### Agente 6 — Análisis de Riesgos

- **Responsabilidad**: Mapear riesgos objetivos asociados a cada opción explícita (financieros, de carrera, relacionales, de salud, de reversibilidad) independientemente del estado emocional del usuario — es el contrapeso "frío" al análisis psicológico.
- **Prompt (sistema)**:
  > "Para cada opción identificada, lista los riesgos objetivos relevantes (financiero, temporal, relacional, de reputación, de salud, de reversibilidad) con una estimación de severidad e irreversibilidad. Sé concreto y basado en el contexto factual dado, no genérico."
- **Input**: `{ "decision_question": "string", "explicit_options": [], "factual_context": {} }`
- **Output**:
```json
{
  "risk_map": [
    { "option": "string", "risks": [ { "type": "string", "severity": "low|medium|high", "reversibility": "low|medium|high" } ] }
  ]
}
```
- **Errores posibles**: `option_without_risks` (opción trivial) → válido, `risks: []`.

### Agente 7 — Generación de Escenarios

- **Responsabilidad**: El corazón creativo del sistema. Genera entre 3 y 5 "líneas temporales" plausibles derivadas de la decisión, integrando todo lo anterior (objetivos, emociones, sesgos, riesgos). Cada escenario incluye una probabilidad relativa (no absoluta — suman 100% entre sí, no representan certeza estadística real) y supuestos explícitos.
- **Prompt (sistema)**:
  > "Genera entre 3 y 5 escenarios de futuro plausibles (6-24 meses de horizonte) resultantes de esta decisión, usando el mapa de riesgos, objetivos y contexto dados. Cada escenario debe: (1) derivar de una combinación coherente de opción + supuestos externos razonables, (2) declarar sus supuestos explícitamente, (3) tener una probabilidad relativa respecto a los demás escenarios (suman 100), (4) NUNCA presentarse como un hecho futuro — usa condicional ('podrías', 'es plausible que'), nunca futuro afirmativo ('serás', 'pasará')."
- **Input**: agregado de outputs de agentes 2, 3, 5, 6.
- **Output**:
```json
{
  "scenarios": [
    {
      "id": "string",
      "title": "string",
      "based_on_option": "string",
      "narrative": "string (condicional, no afirmativo)",
      "assumptions": ["string"],
      "relative_probability": 0,
      "time_horizon_months": 0
    }
  ]
}
```
- **Errores posibles**: `narrative_uses_deterministic_language` → validador lingüístico post-hoc (regex/clasificador ligero) que detecta frases en futuro afirmativo y fuerza regeneración — es una salvaguarda de producto, no solo de estilo (PRD §2, principio "nunca afirmar certeza"). `probabilities_do_not_sum_100` → normalización determinista.

### Agente 8 — Comparación

- **Responsabilidad**: Puntuar cada escenario contra los objetivos ponderados del usuario (Agente 3) y el mapa de riesgos (Agente 6), produciendo una matriz de criterios explícita y auditable.
- **Prompt (sistema)**:
  > "Para cada escenario, evalúa qué tan bien satisface cada objetivo ponderado del usuario (0-100) y asigna un score de riesgo y de reversibilidad. Justifica cada score en una frase. Sé consistente: si dos escenarios comparten un supuesto, su score en el criterio afectado debe ser coherente entre sí."
- **Input**: escenarios (Agente 7) + objetivos (Agente 3) + mapa de riesgos (Agente 6).
- **Output**:
```json
{
  "comparison_matrix": [
    {
      "scenario_id": "string",
      "goal_alignment_scores": [ { "goal": "string", "score": 0, "justification": "string" } ],
      "risk_score": 0,
      "reversibility_score": 0
    }
  ]
}
```
- **Errores posibles**: `inconsistent_scoring_across_scenarios` → validado por el agente 9 (Ranking), que puede solicitar re-evaluación puntual de un escenario específico (reintento acotado, no del pipeline completo).

### Agente 9 — Ranking

- **Responsabilidad**: Calcular un score final ponderado por escenario (combinando alineación de objetivos, riesgo, reversibilidad) mediante una función determinista (no un LLM) sobre los datos estructurados del Agente 8 — el ranking numérico final **no se le pide a un modelo generativo**, se calcula en código para garantizar reproducibilidad y auditabilidad total.
- **"Prompt"**: N/A — este agente es una función pura de agregación, no un agente de IA generativa. Se documenta aquí porque es un nodo del pipeline con el mismo contrato de input/output que los demás.
- **Input**: `comparison_matrix` + `goals` (pesos).
- **Output**:
```json
{
  "ranking": [ { "scenario_id": "string", "final_score": 0.0, "rank": 1 } ]
}
```
- **Errores posibles**: `tie_between_scenarios` → se resuelve mostrando ambos como "empatados" en la UI en vez de forzar un desempate artificial (honestidad del producto sobre falsa precisión).

### Agente 10 — Síntesis

- **Responsabilidad**: Traducir la matriz de comparación y el ranking en una explicación humana, empática y accionable — el único output que la mayoría de usuarios leerá en detalle. Debe explicar el "por qué" del ranking, mencionar los sesgos detectados relevantes con tacto, y cerrar con una pregunta reflexiva (no una orden).
- **Prompt (sistema)**:
  > "Escribe una síntesis en segunda persona, cálida pero rigurosa, de máximo 250 palabras, que explique por qué el escenario mejor rankeado se alinea más con los objetivos declarados, mencione con tacto (no acusatoriamente) algún sesgo relevante detectado, y termine con una pregunta abierta que invite a la reflexión, no con una orden ('deberías'). Nunca uses lenguaje de certeza sobre el futuro."
- **Input**: ranking + comparison_matrix + biases_detected + emotions.
- **Output**: `{ "synthesis": "string (<=250 words)", "reflective_question": "string" }`
- **Errores posibles**: `imperative_language_detected` (usa "deberías/debes") → validador lingüístico fuerza regeneración; es un principio de producto (PRD §2.3, "el usuario decide").

### Agente 11 — Memoria

- **Responsabilidad**: Persistir un resumen embebido (vector) de esta decisión + los sesgos detectados + los objetivos, para enriquecer futuras simulaciones del mismo usuario. Actualiza `user_bias_profile` de forma incremental (media móvil ponderada, no sobrescritura total).
- **Prompt (sistema)**:
  > "Genera un resumen de máximo 60 palabras de esta decisión y su resultado de simulación, optimizado para ser recuperado semánticamente en el futuro como contexto de decisiones similares de la misma persona."
- **Input**: resumen + goals + biases_detected + ranking.
- **Output**: `{ "memory_summary": "string", "embedding_ready_text": "string" }` (el embedding en sí se calcula fuera del LLM, vía el modelo de embeddings del AI Gateway).
- **Errores posibles**: `duplicate_memory_entry` (decisión muy similar a una reciente) → se fusiona con la entrada existente en vez de duplicar (deduplicación por similitud de coseno > 0.92).

### Agente 12 — Aprendizaje (calibración)

- **Responsabilidad**: Ejecutarse **de forma asíncrona y diferida** (no bloquea la respuesta al usuario) cuando el usuario reporta qué pasó realmente con una decisión pasada (CU8, PRD §6). Compara la probabilidad relativa asignada al escenario que más se acercó a lo ocurrido contra el resultado real, y ajusta el "Calibration Score" del usuario y, agregado, del sistema.
- **Prompt (sistema)**:
  > "Dado el resultado real reportado por el usuario y los escenarios previamente generados, identifica cuál escenario se acercó más a lo ocurrido y en qué se equivocó la simulación (supuestos incorrectos, sesgo no detectado, riesgo subestimado/sobrestimado). Sé específico y honesto sobre los errores del sistema."
- **Input**: `{ "reported_outcome": "string", "original_scenarios": [], "original_ranking": [] }`
- **Output**:
```json
{
  "closest_scenario_id": "string",
  "calibration_delta": 0.0,
  "system_errors_identified": ["string"],
  "user_bias_profile_update": {}
}
```
- **Errores posibles**: `outcome_does_not_match_any_scenario` (ocurrió algo que ningún escenario anticipó) → esto es un dato valioso, no un error a ocultar: se registra explícitamente como "blind spot" y se usa para mejorar prompts del Agente 7 en agregado (proceso de mejora de producto, no solo de usuario individual).

---

## 3. Contrato de estado entre agentes

El orquestador mantiene un objeto `SimulationState` (Pydantic) que se va enriqueciendo — cada agente lee un subconjunto y escribe su propia sección, nunca sobreescribe secciones ajenas:

```python
class SimulationState(BaseModel):
    simulation_id: UUID
    raw_input: str
    safety: SafetyGateOutput | None = None
    comprehension: ComprehensionOutput | None = None
    summary: SummaryOutput | None = None
    goals: GoalsOutput | None = None
    emotions: EmotionsOutput | None = None
    psychology: PsychologyOutput | None = None
    risks: RiskOutput | None = None
    scenarios: ScenariosOutput | None = None
    comparison: ComparisonOutput | None = None
    ranking: RankingOutput | None = None
    synthesis: SynthesisOutput | None = None
    memory: MemoryOutput | None = None
```

Cada transición se persiste en `simulation_steps` (Fase 4) con `input_snapshot`, `output_snapshot`, `model_used`, `latency_ms`, `cost_usd`, `status` (`success | retried | failed`). Esto habilita tanto debugging como el futuro "modo transparencia" de producto (mostrarle al usuario curioso exactamente cómo se llegó a un resultado — diferenciador frente a cajas negras).

## 4. Manejo de errores a nivel de pipeline (no solo por agente)

- **Reintentos**: máximo 2 reintentos por agente con backoff, temperatura reducida en el segundo intento (más determinista).
- **Fallback de proveedor**: si OpenAI falla 2 veces, el AI Gateway reintenta automáticamente con Anthropic para ese paso específico (transparente para el orquestador).
- **Fallo irrecuperable de un agente no crítico** (p.ej. Memoria): el pipeline continúa y entrega resultado al usuario; el paso fallido se reintenta en background (no bloquea UX).
- **Fallo irrecuperable de un agente crítico** (Comprensión, Generación de Escenarios, Síntesis): el usuario recibe un estado `simulation_failed` explícito con opción de reintentar, nunca un resultado parcial disfrazado de completo.
- **Timeout global del pipeline**: 45s; si se excede, se devuelven los escenarios ya generados aunque falte comparación/ranking/síntesis fina (degradación elegante), marcados como "resultado parcial".

---

*Fin de Fase 3. Continúa en `docs/DATABASE.md` (Fase 4).*
