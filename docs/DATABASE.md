# VAR OS — Modelo de Base de Datos (Fase 4)

| | |
|---|---|
| **Documento** | Database Design v1.0 |
| **Motor** | PostgreSQL 16+ (RDS Multi-AZ) + extensión `pgvector` |
| **Depende de** | `docs/ARCHITECTURE.md`, `docs/REALITY_ENGINE.md` |
| **Estado** | Fase 4 |

---

## 0. Principios de diseño

- **Normalización a 3FN** como base; desnormalización puntual solo donde el patrón de acceso lo justifica explícitamente (se marca con comentario `-- DENORMALIZED:` y su razón).
- **UUIDv7** como PK en todas las tablas (ordenable por tiempo, mejor para índices que UUIDv4, evita el problema de exponer IDs secuenciales).
- **Soft delete NO se usa por defecto.** Dado el requisito de GDPR/CCPA (derecho al olvido real, Fase 2 §11), el borrado de datos de usuario es un hard delete en cascada. Las tablas que sí necesitan retención de auditoría (`audit_log`, `stripe_events`) son append-only e inmutables por diseño, no por convención de "no borrar".
- **Particionamiento por rango de fecha** en `events` y `simulation_steps` (alto volumen), mensual, con archivado automático a S3/Parquet tras 12 meses.
- **`created_at`/`updated_at`** en toda tabla mutable, gestionados por trigger (`updated_at`) — nunca seteados manualmente desde la aplicación.

## 1. Diagrama entidad-relación (vista lógica)

```
users ──1:1── user_profiles
  │
  ├──1:N── goals
  │
  ├──1:N── decisions ──1:N── simulations ──1:N── simulation_scenarios
  │                              │                       │
  │                              ├──1:N── simulation_steps
  │                              │
  │                              └──1:1── simulation_synthesis
  │
  ├──1:N── decision_outcomes  (feedback de cierre de ciclo, referencia a decisions)
  │
  ├──1:1── user_bias_profile
  ├──1:N── memory_embeddings
  │
  ├──1:1── subscriptions
  ├──1:N── stripe_events (no referencia directa a user_id garantizada; se resuelve por customer_id)
  │
  ├──1:N── notifications
  ├──1:N── events (analítica, particionada)
  └──1:N── audit_log (append-only)
```

## 2. Tablas

### 2.1 `users`
Réplica de dominio del usuario autenticado en Supabase Auth (fuente de verdad de credenciales = Supabase; esta tabla es el agregado de dominio en el Postgres propio).

| Columna | Tipo | Notas |
|---|---|---|
| id | uuid (PK) | igual al `sub` del JWT de Supabase |
| email | citext, unique | |
| display_name | text | |
| locale | text | default `es` |
| onboarding_completed_at | timestamptz, null | |
| deleted_at | timestamptz, null | marcador transitorio de "borrado en curso" antes del hard-delete físico (job async), no un soft-delete permanente |
| created_at / updated_at | timestamptz | |

### 2.2 `user_profiles`
| Columna | Tipo | Notas |
|---|---|---|
| user_id (PK, FK users) | uuid | |
| life_context | jsonb | contexto declarado en onboarding (ocupación, etapa de vida) |
| risk_tolerance | smallint | 1-5, autoevaluado en onboarding |
| timezone | text | |

### 2.3 `goals`
Objetivos/valores declarados por el usuario, usados por el Agente 3 (Reality Engine).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| user_id (FK) | uuid | |
| name | text | ej. "estabilidad financiera" |
| default_weight | smallint | 0-100, ponderación por defecto |
| is_active | boolean | default true |
| created_at | timestamptz | |

### 2.4 `decisions`
Agregado raíz — una decisión que el usuario está evaluando. Persiste entre múltiples simulaciones (una decisión puede re-simularse si cambia el contexto).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| user_id (FK) | uuid | |
| title | text | generado por Agente 1 (Comprensión) o editado por el usuario |
| vertical | text | enum lógico: `career, relationships, finance, business, relocation, conflict` |
| status | text | enum: `draft, clarifying, simulating, completed, archived` |
| raw_input_encrypted | bytea | cifrado a nivel de aplicación (pgcrypto), contenido sensible |
| created_at / updated_at | timestamptz | |

### 2.5 `simulations`
Una corrida del Reality Engine sobre una `decision`. Una `decision` puede tener N `simulations` (re-simular tras clarificar más contexto).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| decision_id (FK) | uuid | |
| pipeline_version | text | versión del pipeline de agentes usada (permite comparar mejoras del sistema en el tiempo) |
| status | text | enum: `queued, running, completed, partial, failed` |
| safety_gate_result | jsonb | output del Agente 0 |
| total_latency_ms | integer | |
| total_cost_usd | numeric(10,4) | suma de costo de IA de todos los agentes — control de márgenes (Fase 2 §2.3) |
| started_at / completed_at | timestamptz | |

### 2.6 `simulation_steps`
**Particionada por mes (`started_at`).** Auditoría completa de cada paso del pipeline (Fase 3 §3).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| simulation_id (FK) | uuid | |
| agent_name | text | `comprehension, summary, goals, emotions, psychology, risks, scenarios, comparison, ranking, synthesis, memory, learning` |
| input_snapshot | jsonb | |
| output_snapshot | jsonb | |
| model_used | text | ej. `gpt-5.1`, `claude-...` |
| provider | text | `openai \| anthropic \| self_hosted` |
| latency_ms | integer | |
| cost_usd | numeric(10,6) | |
| status | text | `success, retried, failed` |
| retry_count | smallint | |
| started_at | timestamptz | clave de partición |

### 2.7 `simulation_scenarios`
Una fila por escenario generado (Agente 7), enriquecida con su score de comparación/ranking (Agentes 8-9).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| simulation_id (FK) | uuid | |
| title | text | |
| narrative | text | |
| assumptions | jsonb | array de strings |
| relative_probability | numeric(5,2) | suma 100 por simulación (constraint a nivel de aplicación) |
| time_horizon_months | smallint | |
| goal_alignment_scores | jsonb | output del Agente 8 |
| risk_score | numeric(5,2) | |
| reversibility_score | numeric(5,2) | |
| final_score | numeric(5,2) | output del Agente 9 (Ranking) |
| rank | smallint | |

### 2.8 `simulation_synthesis`
1:1 con `simulations` — el texto final que el usuario lee.

| Columna | Tipo | Notas |
|---|---|---|
| simulation_id (PK, FK) | uuid | |
| synthesis_text | text | |
| reflective_question | text | |
| biases_mentioned | jsonb | |

### 2.9 `decision_outcomes`
Feedback de "cierre de ciclo" (CU8) — lo que realmente pasó, usado por el Agente 12 (Aprendizaje).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| decision_id (FK) | uuid | **único** — a lo sumo un cierre de ciclo por decisión (migración 0008). No es una duplicación inocua: cada outcome pliega otra observación en `user_bias_profile`, así que reportar dos veces distorsionaría la calibración del propio usuario |
| reported_outcome | text | |
| closest_scenario_id (FK simulation_scenarios) | uuid, null | |
| calibration_delta | numeric(5,2) | |
| system_errors_identified | jsonb | |
| reported_at | timestamptz | |

### 2.10 `user_bias_profile`
1:1 con `users` — perfil acumulado de sesgos, actualizado incrementalmente por el Agente 5 y recalibrado por el Agente 12.

| Columna | Tipo | Notas |
|---|---|---|
| user_id (PK, FK) | uuid | |
| biases | jsonb | `[{ "bias": "loss_aversion", "score": 0.0, "occurrences": 0 }]` |
| calibration_score | numeric(5,2) | qué tan bien calibradas han estado las simulaciones pasadas de este usuario |
| updated_at | timestamptz | |

### 2.11 `memory_embeddings`
Memoria semántica de largo plazo (pgvector).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| user_id (FK) | uuid | |
| decision_id (FK, null) | uuid | |
| summary_text | text | |
| embedding | vector(1536) | índice HNSW |
| created_at | timestamptz | |

### 2.12 `subscriptions`
Réplica de solo-lectura del estado de Stripe (Fase 2 §9) — Stripe es la fuente de verdad.

| Columna | Tipo | Notas |
|---|---|---|
| user_id (PK, FK) | uuid | |
| stripe_customer_id | text, unique | |
| stripe_subscription_id | text, unique, null | |
| tier | text | `free, pro, elite, team` |
| status | text | `active, past_due, canceled, trialing` |
| current_period_end | timestamptz | |
| updated_at | timestamptz | actualizado solo por el webhook handler |

### 2.13 `stripe_events`
Idempotencia de webhooks (Fase 2 §9). Append-only.

| Columna | Tipo | Notas |
|---|---|---|
| stripe_event_id (PK) | text | |
| type | text | |
| payload | jsonb | |
| processed_at | timestamptz | |

### 2.14 `notifications`
| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| user_id (FK) | uuid | |
| type | text | `loop_closure_reminder, subscription_alert, system` |
| payload | jsonb | |
| read_at | timestamptz, null | |
| scheduled_for | timestamptz | |
| created_at | timestamptz | |

### 2.15 `events`
**Particionada por mes.** Eventos de producto para analítica (Fase 2 §2.5), desacoplados vía cola — nunca escritos síncronamente en el camino crítico de negocio.

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | uuid | |
| user_id (FK, null) | uuid | null permitido para eventos anónimos pre-signup |
| event_name | text | ej. `simulation_completed`, `paywall_viewed` |
| properties | jsonb | |
| occurred_at | timestamptz | clave de partición |

### 2.16 `audit_log`
Append-only, inmutable (sin `UPDATE`/`DELETE` permitido a nivel de rol de DB). Accesos a datos sensibles y acciones administrativas (Fase 2 §11).

| Columna | Tipo | Notas |
|---|---|---|
| id (PK) | bigint identity | secuencial, no UUID, para orden estricto de auditoría |
| actor_id | uuid, null | usuario o `system` |
| action | text | ej. `decision.viewed`, `user.data_exported`, `admin.impersonation` |
| target_type / target_id | text / uuid | |
| metadata | jsonb | |
| occurred_at | timestamptz | |

## 3. Índices clave

- `decisions(user_id, status, created_at desc)` — listado de "Mis Decisiones".
- `simulation_scenarios(simulation_id, rank)` — render ordenado del resultado.
- `memory_embeddings` — índice HNSW sobre `embedding` (`vector_cosine_ops`).
- `events` — índice por partición mensual + `(user_id, event_name, occurred_at)`.
- `stripe_events(type, processed_at)` para reprocesamiento/debug de webhooks.

## 4. Cascadas de borrado (derecho al olvido)

`ON DELETE CASCADE` desde `users` hacia: `user_profiles, goals, decisions (→ simulations → simulation_steps/scenarios/synthesis), decision_outcomes, user_bias_profile, memory_embeddings, notifications`.

**Excepciones explícitas (no se borran, se anonimizan):** `events` (se anonimiza `user_id → NULL` para preservar series agregadas de producto) y `audit_log` (nunca se borra ni anonimiza — es el registro de que el borrado ocurrió). `stripe_events`/`subscriptions` siguen retención fiscal/legal estándar, desacoplados del `user_id` de dominio mediante el `stripe_customer_id`.

## 5. Cifrado de campos sensibles

`decisions.raw_input_encrypted` y el texto crudo de `simulation_steps.input_snapshot` cuando contiene el input original del usuario se cifran a nivel de aplicación (no solo TDE de RDS) — ver Fase 2 §11. La clave de cifrado por usuario se deriva de una master key en AWS KMS, nunca almacenada en la propia base de datos.

---

*Fin de Fase 4. Continúa en `docs/UX_DESIGN.md` (Fase 5).*
