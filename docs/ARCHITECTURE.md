# VAR OS — Arquitectura Técnica (Fase 2)

| | |
|---|---|
| **Documento** | Arquitectura v1.0 |
| **Depende de** | `docs/PRD.md` |
| **Estado** | Fase 2 |

---

## 0. Decisiones de arquitectura que se apartan del brief (y por qué)

Como CTO, tres decisiones se desvían de la propuesta inicial. Se documentan explícitamente, tal como se pidió:

1. **IA: gateway multi-proveedor, no acoplamiento directo a "OpenAI API".**
   Acoplar el Reality Engine directamente al SDK de OpenAI es un riesgo existencial: un cambio de pricing, un outage prolongado, o un rate limit agresivo tumba el producto entero. En su lugar, el `AI Gateway Service` expone una interfaz interna (`LLMProvider`) con adaptadores para OpenAI (primario), Anthropic (fallback/calidad) y un modelo open-weight autoalojado (Llama/Mixtral vía vLLM) para tareas no creativas de bajo riesgo (clasificación, extracción). Esto no cambia la experiencia de usuario ni el stack "preferido" — sigue siendo OpenAI el proveedor principal en producción — pero evita bloqueo de proveedor (vendor lock-in) y permite negociar costos.

2. **Backend: monolito modular primero, microservicios después — no microservicios desde el día 1.**
   El brief pide "microservicios". Para el tamaño de equipo de un MVP (probablemente < 8 ingenieros), microservicios completos desde el inicio son deuda operativa prematura (N repos, N pipelines de CI/CD, tracing distribuido desde el día 1, coste de coordinación). Se construye un **monolito modular** en FastAPI con límites de módulo estrictos (cada módulo es un bounded context DDD con su propio esquema lógico dentro del mismo Postgres, su propio router, su propia capa de dominio) de forma que la extracción futura a microservicios reales sea un refactor mecánico, no una reescritura. El Reality Engine sí se separa como servicio independiente desde el día 1 porque su perfil de carga (CPU/IO-bound en llamadas a IA, alta latencia, necesidad de colas) es fundamentalmente distinto del resto del CRUD.

3. **Base de datos: se añade pgvector sobre PostgreSQL para memoria semántica**, en vez de introducir una base de datos vectorial separada (Pinecone/Weaviate). Reduce superficie operativa y mantiene una sola fuente de verdad transaccional + vectorial mientras el volumen lo permita (hasta el orden de decenas de millones de embeddings). Se documenta el punto de migración a un vector store dedicado en §7.

Todo lo demás sigue el stack solicitado: Flutter, FastAPI, PostgreSQL, Redis, Supabase (Auth/Storage/Realtime), Stripe, Docker, AWS.

---

## 1. Vista de contenedores (C4 — Nivel 2)

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLIENTES                                   │
│  Flutter App (iOS, Android, Web/PWA, macOS)                            │
│  - Riverpod (state mgmt) · GoRouter (navegación) · Dio (HTTP)          │
│  - Supabase Flutter SDK (auth session, realtime, storage)              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS (REST) + WSS (streaming del pipeline)
┌───────────────────────────────▼─────────────────────────────────────────┐
│                         EDGE / API GATEWAY                              │
│   AWS API Gateway + ALB → Kong (o Traefik) como capa de gateway interna  │
│   - TLS termination · WAF (AWS WAF) · Rate limiting global · JWT verify │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
       ┌───────────────┬─────────┴─────────┬──────────────────┐
       │               │                   │                   │
┌──────▼──────┐ ┌──────▼───────┐  ┌────────▼────────┐ ┌────────▼────────┐
│  Core API     │ │ Reality      │  │  Billing API     │ │  Analytics/       │
│  Service      │ │ Engine        │  │  Service         │ │  Events Service   │
│  (FastAPI,    │ │ Service       │  │  (FastAPI)       │ │  (FastAPI +       │
│  monolito     │ │ (FastAPI +    │  │  - Stripe        │ │  Kafka/SQS)       │
│  modular)     │ │ workers async)│  │    webhooks       │ │                   │
└──────┬──────┘ └──────┬───────┘  └────────┬────────┘ └────────┬────────┘
       │               │                    │                   │
       │        ┌──────▼───────┐            │                   │
       │        │ AI Gateway    │            │                   │
       │        │ Service       │            │                   │
       │        │ (OpenAI/      │            │                   │
       │        │ Anthropic/    │            │                   │
       │        │ vLLM adapter) │            │                   │
       │        └──────┬───────┘            │                   │
       │               │                    │                   │
┌──────▼───────────────▼────────────────────▼───────────────────▼────────┐
│                        CAPA DE DATOS Y MENSAJERÍA                       │
│  PostgreSQL (RDS Multi-AZ, + pgvector)   Redis (ElastiCache)            │
│  Supabase (Auth, Storage, Realtime)      SQS / Redis Streams (colas)    │
│  S3 (backups, exports, assets)           OpenSearch (logs, opcional)    │
└──────────────────────────────────────────────────────────────────────────┘
```

## 2. Servicios

### 2.1 Core API Service (monolito modular)
Responsable de: usuarios, perfiles, objetivos/valores, sesiones de simulación (metadata), historial, notificaciones, orquestación de alto nivel (dispara al Reality Engine y persiste su resultado).

Módulos internos (bounded contexts DDD):
- `identity` — perfil de usuario, preferencias, sincronizado con Supabase Auth (Supabase es la fuente de verdad de credenciales; Core replica el perfil de dominio).
- `goals` — objetivos y valores del usuario que parametrizan el ranking de escenarios.
- `decisions` — el agregado raíz "Decision" (una decisión del usuario) y su ciclo de vida.
- `simulations` — el agregado "Simulation" (una corrida del Reality Engine sobre una Decision), sus escenarios y su síntesis.
- `memory` — resúmenes de largo plazo y perfil psicológico/de sesgos acumulado (ver Fase 3, Agente de Aprendizaje).
- `notifications` — recordatorios de cierre de ciclo, alertas de suscripción.

### 2.2 Reality Engine Service
Servicio independiente, stateless a nivel de proceso, con estado delegado a Postgres/Redis. Ejecuta el pipeline de 11 agentes (Fase 3). Arquitectura interna:
- **API de entrada**: recibe `SimulationRequest` desde Core API vía cola (SQS/Redis Streams), no vía llamada síncrona — una simulación puede tardar 15–30s y no debe bloquear un request HTTP.
- **Orquestador de pipeline**: implementado como grafo dirigido de agentes (LangGraph o implementación propia ligera sobre `asyncio`), con paso de estado tipado (Pydantic) entre nodos.
- **Workers**: pool de workers async (Celery o arq sobre Redis) que ejecutan cada etapa del pipeline y publican progreso incremental a un canal Redis Pub/Sub, que el Core API reenvía al cliente vía WebSocket para la experiencia de "streaming en vivo" (PRD §11).
- **Risk & Safety Gate**: nodo obligatorio, no opcional, ejecutado antes de generar escenarios; puede abortar el pipeline y devolver una respuesta de derivación a ayuda profesional (PRD §18).

### 2.3 AI Gateway Service
Abstrae proveedores de LLM detrás de una interfaz común (`generate(prompt, schema, model_tier)`). Responsabilidades: selección de modelo por tier de tarea (clasificación ligera vs. síntesis creativa), retries con backoff, fallback entre proveedores, validación de salida contra JSON Schema (rechaza y reintenta si el modelo alucina una estructura inválida), y **tracking de costo por usuario/simulación** para control de márgenes.

### 2.4 Billing Service
Integración con Stripe (Checkout, Customer Portal, Webhooks). Fuente de verdad de estado de suscripción vive en Stripe; Postgres mantiene una réplica de solo lectura (tabla `subscriptions`) sincronizada por webhook, nunca al revés.

### 2.5 Analytics/Events Service
Recolecta eventos de producto (activación, uso de features, embudo de conversión) de forma desacoplada (fire-and-forget desde los demás servicios vía cola) para no acoplar latencia de negocio a analítica. Alimenta un warehouse (ver §8).

### 2.6 Justificación multi-proveedor de IA (detalle de la decisión §0.1)
El `AI Gateway` define tres tiers de modelo:
- **Tier "reasoning-creative"** (generación de escenarios, síntesis): OpenAI GPT-5.x (primario), Claude (fallback si OpenAI degrada).
- **Tier "structured-extraction"** (extracción de objetivos, emociones, resumen): modelo más económico/rápido (GPT-5-mini o equivalente), con posibilidad de mover a un modelo autoalojado cuando el volumen lo justifique.
- **Tier "safety-classification"** (Risk & Safety Gate): modelo dedicado de clasificación + reglas deterministas (nunca solo LLM) — la seguridad del usuario no depende únicamente de un modelo probabilístico.

## 3. Frontend (Flutter)

- **Arquitectura**: Clean Architecture por feature (`presentation / domain / data`), inspirada en el patrón "feature-first". Cada feature (`decision_capture`, `simulation_result`, `memory`, `billing`, etc.) es independiente y testeable en aislamiento.
- **State management**: Riverpod (proveedores generados con `riverpod_generator`), preferido sobre Bloc por menor boilerplate y mejor DX en un equipo pequeño; Bloc queda como alternativa si el equipo crece y prioriza estructura explícita sobre velocidad.
- **Navegación**: GoRouter con rutas declarativas y deep-linking (necesario para notificaciones de "cierre de ciclo").
- **Networking**: Dio + interceptores (auth, refresh token automático, logging estructurado).
- **Realtime**: cliente WebSocket propio para el streaming del pipeline (no reutiliza Supabase Realtime aquí, porque el streaming del Reality Engine es un canal de aplicación, no un cambio de fila en DB — Supabase Realtime sí se usa para sincronizar estado de `decisions`/`simulations` entre dispositivos del mismo usuario).
- **Diseño**: sistema de diseño propio ("VAR Design System") — tokens de color/tipografía/espaciado versionados como paquete Dart interno, consumido también por futuras superficies (dashboard web B2B). Detalle completo en Fase 5.
- **Offline-first parcial**: historial de decisiones cacheado localmente (Drift/SQLite) para lectura offline; la simulación en sí requiere conexión.

## 4. Backend (Python + FastAPI)

- **Estructura por servicio** (Clean Architecture / Hexagonal):
```
service/
  api/            # routers FastAPI, esquemas Pydantic de request/response (adaptador HTTP)
  domain/         # entidades, value objects, reglas de negocio puras (sin dependencias externas)
  application/    # casos de uso / servicios de aplicación, orquestan domain + repos
  infrastructure/ # repositorios concretos (SQLAlchemy), clientes externos (Stripe, AI Gateway)
  tests/
```
- **Repository Pattern**: toda persistencia pasa por interfaces (`DecisionRepository`, `SimulationRepository`) definidas en `domain/`, implementadas en `infrastructure/`. Los casos de uso dependen de la interfaz (Dependency Inversion), nunca de SQLAlchemy directamente.
- **Dependency Injection**: `Depends()` de FastAPI para wiring de repositorios/servicios; para lógica de dominio compleja se evalúa `dependency-injector` si el grafo de dependencias crece.
- **Tipado fuerte**: Pydantic v2 en todos los límites de servicio; `mypy --strict` en CI.
- **DDD** aplicado selectivamente: agregados (`Decision`, `Simulation`, `User`) con invariantes protegidas en el dominio; se evita DDD ceremonial en módulos simples tipo CRUD (`notifications`).

## 5. Base de datos — PostgreSQL

RDS PostgreSQL Multi-AZ, extensión `pgvector` habilitada. Esquema detallado completo en `docs/DATABASE.md` (Fase 4). Particionamiento por rango de fecha en tablas de alto volumen (`events`, `simulation_steps`) desde el diseño inicial para facilitar retención/archivado.

## 6. Cache y colas — Redis

- **Cache**: perfil de usuario, objetivos, resultados de simulación recientes (TTL configurable), rate-limit counters.
- **Colas**: Redis Streams (o SQS si se prefiere gestión completamente administrada en AWS — recomendado para producción por durabilidad; Redis Streams como alternativa de menor latencia) para despachar `SimulationRequest` al Reality Engine y eventos de analítica.
- **Pub/Sub**: canal de progreso de pipeline consumido por el Core API para reenviar a WebSocket.

## 7. Memoria semántica (pgvector → punto de migración)

Los resúmenes de sesión y perfiles de sesgos (Fase 3, Agente de Memoria) se embeben (`text-embedding-3-large` o equivalente) y se almacenan en una tabla `memory_embeddings` con índice `ivfflat`/`HNSW` vía pgvector. **Umbral de migración documentado:** si el volumen supera ~50M vectores o la latencia P95 de búsqueda semántica supera 150ms bajo carga, se migra a un vector store dedicado (Qdrant/Pinecone) sin cambiar la interfaz de dominio (`MemoryRepository`), gracias al Repository Pattern.

## 8. Autenticación — Supabase Auth

- Supabase Auth como IdP: email/password, OAuth (Google, Apple — obligatorio para App Store), magic link.
- JWT emitido por Supabase, verificado por el API Gateway (JWKS) antes de llegar a cualquier servicio interno — los servicios internos nunca hablan directo con Supabase Auth, solo validan el JWT ya emitido.
- Row Level Security (RLS) de Supabase se usa como **segunda capa de defensa** (defense in depth) en las tablas que Supabase gestiona directamente (si se usa su Postgres gestionado) o se replica el patrón de RLS a nivel de aplicación si el Postgres de dominio es el RDS propio (recomendado — ver §9).

**Decisión:** el Postgres transaccional de dominio (`decisions`, `simulations`, etc.) vive en **RDS propio**, no en el Postgres gestionado de Supabase, para mantener control total de performance tuning, extensiones (pgvector, particionamiento) y evitar acoplar el core del producto al plano de control de un tercero. Supabase se usa para lo que resuelve mejor out-of-the-box: Auth, Storage de archivos (exports PDF, adjuntos) y Realtime de sincronización ligera entre dispositivos.

## 9. Pagos — Stripe

Checkout hospedado (no se construye UI de tarjeta propia → PCI scope mínimo). Webhooks (`checkout.session.completed`, `customer.subscription.updated/deleted`, `invoice.payment_failed`) procesados de forma idempotente (tabla `stripe_events` con `event_id` único) actualizando la réplica local de estado de suscripción. Customer Portal de Stripe para gestión de plan/cancelación (evita construir UI de billing compleja en MVP).

## 10. Observabilidad

- **Logs estructurados** (JSON) con `structlog`, correlación por `trace_id` propagado desde el Gateway a través de todos los servicios (incluye el pipeline de agentes — cada paso del Reality Engine loguea su `trace_id` + `simulation_id`).
- **Tracing distribuido**: OpenTelemetry SDK en cada servicio, exportado a un backend (Grafana Tempo o AWS X-Ray).
- **Métricas**: Prometheus (via `prometheus-fastapi-instrumentator`) + Grafana dashboards: latencia por endpoint, latencia por agente del pipeline, tasa de error del AI Gateway por proveedor, costo de IA por simulación.
- **Alertas**: latencia P95 del pipeline > umbral, tasa de fallback del proveedor primario de IA > 5%, error rate de Billing > 0.
- **Error tracking**: Sentry en frontend y backend.

## 11. Seguridad

- WAF en el borde (AWS WAF, reglas OWASP managed).
- Rate limiting en dos capas: Gateway (por IP/anónimo) y por usuario autenticado (Redis token bucket), con límites más estrictos en endpoints de simulación (costosos en IA).
- Cifrado en tránsito (TLS 1.3 everywhere) y en reposo (RDS + S3 con KMS).
- Datos de decisión tratados como datos sensibles: cifrado a nivel de campo (pgcrypto o cifrado de aplicación) para el contenido textual crudo de las decisiones y la síntesis, no solo cifrado de disco.
- Secrets en AWS Secrets Manager, nunca en variables de entorno planas en repos ni en imágenes Docker.
- Principio de menor privilegio en IAM; cada servicio tiene su propio rol.
- Auditoría: tabla `audit_log` inmutable (append-only) para accesos a datos sensibles y acciones administrativas.
- Cumplimiento: diseño preparado para GDPR/CCPA desde el día 1 (derecho al olvido implementado como hard-delete real, no soft-delete, en `identity` y cascada documentada; ver Fase 4).

## 12. Escalabilidad

- Servicios stateless detrás de ALB, autoescalado horizontal por CPU/latencia en ECS/EKS.
- Reality Engine escala independientemente del Core API (su perfil de carga es distinto — IO-bound esperando IA).
- Lectura de historial de decisiones cacheada agresivamente (Redis) — patrón de acceso es "leer mucho, escribir poco" en `decisions`/`simulations` una vez creadas.
- Particionamiento de tablas de eventos por fecha; archivado a S3 (Parquet) para analítica histórica vía Athena, evitando que la tabla operacional crezca sin límite.
- Read replicas de RDS para analítica/reportería, aislando esa carga de la transaccional.

## 13. CI/CD

- GitHub Actions: pipeline por servicio (monorepo con paths filtrados) — lint (`ruff`), tipado (`mypy`), tests (`pytest` con cobertura mínima gateada), build de imagen Docker, scan de vulnerabilidades (Trivy), push a ECR, deploy a EKS vía Helm/Argo CD (GitOps — el estado deseado del cluster vive en un repo de manifiestos, no en pipelines imperativos).
- Frontend Flutter: pipeline separado — análisis estático (`flutter analyze`), tests (widget + unit), build por plataforma, distribución a TestFlight/Play Console internal track automatizada en `main`.
- Entornos: `dev` → `staging` → `production`, promoción manual con aprobación a `production`.
- Migraciones de DB (Alembic) como paso de pipeline separado y reversible, ejecutado antes del rollout de la nueva versión del servicio.

## 14. Contenedores y orquestación

- Docker multi-stage builds (imagen final mínima, sin toolchain de build).
- Kubernetes (EKS) en producción; `docker-compose` para desarrollo local reproduciendo todos los servicios + Postgres + Redis.
- Helm charts por servicio; HPA (Horizontal Pod Autoscaler) basado en CPU y en métricas custom (profundidad de cola del Reality Engine) vía KEDA para el caso específico de picos de simulaciones.

## 15. Rate limiting (detalle)

| Ámbito | Límite propuesto | Justificación |
|---|---|---|
| Anónimo (pre-signup) | 1 simulación de prueba / dispositivo / 24h | Permitir "probar antes de registrarse" sin abuso |
| Free | 2 simulaciones/mes | Modelo de negocio (PRD §14) |
| Pro/Elite | Soft-limit alto + rate limit técnico (ej. 20/hora) | Proteger el sistema de abuso, no la experiencia normal |
| API pública (v2) | Por API key, cuotas configurables | Modelo B2B futuro |

## 16. Resumen del stack final

| Capa | Tecnología |
|---|---|
| Frontend | Flutter (Riverpod, GoRouter, Dio) |
| Backend | Python 3.12 + FastAPI, Clean Architecture/DDD selectivo |
| Reality Engine | FastAPI + workers async (Celery/arq), orquestación tipo grafo |
| IA | AI Gateway propio · OpenAI (primario) · Anthropic (fallback) · vLLM autoalojado (tareas ligeras) |
| Base de datos | PostgreSQL (RDS Multi-AZ) + pgvector |
| Cache/Colas | Redis (ElastiCache) + SQS |
| Auth/Storage/Realtime ligero | Supabase |
| Pagos | Stripe |
| Infraestructura | Docker + Kubernetes (EKS) en AWS, GitOps (Argo CD) |
| Observabilidad | OpenTelemetry, Prometheus/Grafana, Sentry |

---

*Fin de Fase 2. Continúa en `docs/REALITY_ENGINE.md` (Fase 3).*
