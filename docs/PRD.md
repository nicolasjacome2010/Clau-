# VAR OS — Product Requirements Document (PRD)

**Variable Reality Operating System**
*El sistema operativo para tomar decisiones.*

| | |
|---|---|
| **Documento** | PRD v1.0 |
| **Estado** | Fase 1 — Diseño de producto |
| **Propietario** | Oficina del CTO / CPO |
| **Última actualización** | 2026-08-03 |
| **Confidencialidad** | Interno |

---

## 0. Resumen ejecutivo

VAR OS no es un chatbot ni un oráculo. Es un **simulador de decisiones**: un sistema que toma una decisión real que un humano está a punto de tomar, la descompone, la modela contra docenas de variables (psicológicas, económicas, sociales, temporales, de riesgo), genera **múltiples líneas temporales plausibles** ("realidades variables") derivadas de esa decisión, las compara entre sí con criterios explícitos, y devuelve una recomendación trazable — nunca una predicción mística.

La metáfora de producto es la de un **cockpit de simulación de vuelo para tu vida**: el usuario no pregunta "¿qué pasará?", sino "si hago X, ¿qué mundos se abren, cuáles se cierran, y cuál se parece más a donde quiero llegar?".

VAR OS se diferencia de la categoría "AI companion / chatbot de consejos" (Replika, Character.AI, ChatGPT genérico) al negarse a ser conversacional por defecto. Es un producto de **estado**: cada decisión vive como un objeto persistente (una "Simulación") con historial, versiones, bifurcaciones y aprendizaje acumulado — más parecido a Palantir Foundry o a un IDE que a una app de mensajería.

---

## 1. Visión

> Que tomar una decisión importante sin simular sus consecuencias se sienta tan anticuado como programar sin control de versiones.

En 10 años, VAR OS es la capa de sistema operativo sobre la que las personas y las organizaciones razonan sus decisiones de alto impacto — profesionales, financieras, relacionales, estratégicas — de la misma forma en que hoy usan un calendario o una hoja de cálculo, pero con inteligencia de simulación en vez de aritmética.

## 2. Misión

Construir el motor de simulación de decisiones más riguroso, transparente y humano del mundo, combinando IA generativa, teoría de decisiones, teoría de juegos, economía conductual y psicología — sin nunca pretender predecir el futuro, sino **iluminar el espacio de futuros posibles** y las palancas que el usuario controla dentro de él.

### Principios no negociables

1. **Nunca afirmar certeza.** Todo output se presenta como probabilístico, con intervalos de confianza y supuestos explícitos.
2. **Trazabilidad total.** Todo ranking o recomendación debe poder explicarse: qué variables, qué pesos, qué fuentes.
3. **El usuario decide.** El sistema simula y ordena opciones; nunca decide por el usuario ni infantiliza su agencia.
4. **Privacidad como arquitectura, no como política.** Los datos de decisiones personales son el activo más sensible que existe; se tratan como datos de salud.
5. **Un sistema operativo, no un feed.** No hay scroll infinito, no hay variable-reward loops, no hay diseño adictivo. El éxito se mide en decisiones bien tomadas, no en tiempo en app.

## 3. Objetivos

### Objetivos de producto (12 meses)
- Lanzar MVP funcional con Reality Engine v1 (8 agentes) y 3 tipos de simulación (Carrera, Relaciones, Finanzas/Negocio).
- Alcanzar un NPS ≥ 55 entre usuarios que completan al menos una simulación end-to-end.
- Lograr que el 40% de usuarios activos regrese a revisar el resultado de una decisión pasada ("closing the loop") — la métrica que valida que el producto realmente ayuda, no solo entretiene.

### Objetivos de negocio (12–24 meses)
- 100,000 usuarios registrados, 15,000 suscriptores de pago en los primeros 12 meses post-lanzamiento público.
- CAC payback < 6 meses en el tier Pro.
- Explorar un canal B2B (VAR OS for Teams) para decisiones estratégicas de equipos/founders hacia el mes 18.

### Objetivos técnicos
- Latencia P95 de una simulación completa (pipeline de 11 agentes) < 25s mediante paralelización y streaming parcial de resultados.
- Disponibilidad 99.9% del API core.
- Arquitectura capaz de escalar horizontalmente a 1M+ usuarios sin rediseño (ver Fase 2 — Arquitectura).

## 4. El problema

Las personas toman decisiones que definen años de su vida (cambiar de carrera, terminar una relación, invertir capital, aceptar una oferta, mudarse de país) con:
- Sesgos cognitivos no examinados (aversión a la pérdida, descuento hiperbólico, sesgo de confirmación).
- Un círculo social que opina desde su propia experiencia, no desde la del usuario.
- Herramientas inadecuadas: notas mentales, listas de pros/contras en una servilleta, o un chatbot genérico que responde con generalidades y no recuerda nada la próxima vez.

No existe hoy una categoría de producto que trate "tomar una decisión" como un **objeto de primera clase** con estado, historial y simulación estructurada. VAR OS crea esa categoría.

## 5. Usuarios objetivo

### Persona 1 — "El Estratega Personal" (núcleo del ICP)
Alejandro, 29, product manager. Toma 2-3 decisiones grandes al año (cambiar de trabajo, mudarse, invertir). Usa Notion, hojas de cálculo de decisión, ha probado terapia y coaching. Quiere estructura, no un amigo virtual. Paga por herramientas que le ahorren errores caros.

### Persona 2 — "La Fundadora"
Marina, 34, cofundadora de una startup seed-stage. Decisiones: pivotear o no, despedir a un cofundador, levantar ronda o no. Necesita simular escenarios de negocio con variables de mercado y equipo. Candidata directa al tier B2B/Team.

### Persona 3 — "El que está en una encrucijada vital"
Javier, 41, considerando terminar un matrimonio de 12 años. Alta carga emocional, baja capacidad de pensar con claridad. Necesita que el producto sea empático en el tono pero riguroso en el análisis — el mayor riesgo de producto y el mayor foso ético.

### Persona 4 (secundaria, roadmap v2) — "El equipo ejecutivo"
Comités de dirección que simulan decisiones estratégicas colectivas (fusiones, lanzamientos, reestructuras). Multi-usuario, multi-perspectiva.

## 6. Casos de uso

| # | Caso de uso | Vertical | Prioridad |
|---|---|---|---|
| CU1 | "¿Debo aceptar esta oferta de trabajo o quedarme?" | Carrera | MVP |
| CU2 | "¿Debo terminar esta relación?" | Relaciones | MVP |
| CU3 | "¿Debo invertir mis ahorros en X?" | Finanzas | MVP |
| CU4 | "¿Debo pivotear mi startup?" | Negocio | v1.1 |
| CU5 | "¿Debo mudarme de país?" | Vida/Carrera | v1.1 |
| CU6 | "¿Debo confrontar a esta persona?" | Relaciones/Conflicto | v1.2 |
| CU7 | Comparar dos decisiones simultáneas ("Modo Bifurcación") | Transversal | v1.2 |
| CU8 | Revisar una decisión pasada contra lo que realmente ocurrió (feedback loop de aprendizaje) | Transversal | MVP (simplificado) |
| CU9 | Simulación colaborativa de equipo | B2B | v2 |

## 7. User Stories (por épica)

### Épica A — Onboarding y captura de la decisión
- Como usuario nuevo, quiero describir mi decisión en lenguaje natural (texto o voz) para no tener que llenar un formulario rígido.
- Como usuario, quiero que el sistema me haga preguntas de clarificación cuando mi input es ambiguo, para asegurar que la simulación parte de una base correcta.
- Como usuario, quiero definir explícitamente qué objetivo estoy optimizando (dinero, felicidad, estabilidad, crecimiento, relaciones) para que el ranking de escenarios refleje mis valores y no los del sistema.

### Épica B — Simulación
- Como usuario, quiero ver el progreso del pipeline de agentes en tiempo real (streaming), para sentir que el sistema está "pensando" y no solo cargando.
- Como usuario, quiero recibir entre 3 y 5 escenarios de futuro plausibles, no uno solo, para explorar el espacio de posibilidades real.
- Como usuario, quiero que cada escenario muestre probabilidad relativa, supuestos clave, riesgos y un horizonte temporal, para poder juzgar su plausibilidad yo mismo.

### Épica C — Comparación y decisión
- Como usuario, quiero comparar escenarios lado a lado en una matriz de criterios (alineación con objetivo, riesgo, reversibilidad, horizonte), para decidir con estructura.
- Como usuario, quiero una síntesis final en lenguaje humano que explique el "por qué" del ranking, no solo un número.

### Épica D — Memoria y aprendizaje
- Como usuario recurrente, quiero que el sistema recuerde decisiones pasadas y patrones en mis sesgos, para que cada simulación nueva sea más precisa que la anterior.
- Como usuario, quiero poder volver 6 meses después y decirle al sistema "esto es lo que realmente pasó", para cerrar el ciclo y calibrar la confianza del modelo en futuras simulaciones.

### Épica E — Cuenta, privacidad y monetización
- Como usuario, quiero exportar o borrar permanentemente todos mis datos de decisión en un clic.
- Como usuario free, quiero simulaciones limitadas por mes con upgrade claro a Pro sin dark patterns.

## 8. Arquitectura funcional (vista de producto)

```
┌─────────────────────────────────────────────────────────────┐
│                         VAR OS Client                        │
│              (Flutter — iOS / Android / Web / macOS)         │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTPS / WSS
┌───────────────────────────▼───────────────────────────────────┐
│                        API Gateway (Edge)                     │
│        Auth · Rate limit · Routing · Observabilidad           │
└───────────────────────────┬───────────────────────────────────┘
                            │
        ┌───────────────────┼─────────────────────┐
        │                   │                      │
┌───────▼───────┐  ┌────────▼────────┐   ┌──────────▼─────────┐
│  Core Service   │  │ Reality Engine  │   │ Billing / Account   │
│ (usuarios,      │  │ (pipeline de    │   │ Service (Stripe,    │
│ sesiones,       │  │ 11 agentes IA)  │   │ suscripciones)      │
│ objetivos)      │  │                 │   │                     │
└───────┬───────┘  └────────┬────────┘   └──────────┬─────────┘
        │                   │                        │
        └───────────┬───────┴────────────┬───────────┘
                    │                    │
            ┌───────▼───────┐   ┌────────▼────────┐
            │  PostgreSQL     │   │  Redis (cache,   │
            │  (fuente de     │   │  colas, rate     │
            │  verdad)        │   │  limit)          │
            └─────────────────┘   └──────────────────┘
```

*(Ver Fase 2 — `docs/ARCHITECTURE.md` para el detalle de infraestructura completo.)*

## 9. Mapa de navegación

```
Splash
 └─ Onboarding (3 pantallas + captura de objetivo de vida)
     └─ Auth (Login / Registro / SSO)
         └─ Home ("El Mapa de Realidades")
             ├─ Nueva Simulación
             │   ├─ Captura de decisión (texto/voz)
             │   ├─ Clarificación (chat guiado, no libre)
             │   ├─ Pantalla de Simulación en vivo (pipeline streaming)
             │   └─ Resultado
             │       ├─ Vista Escenarios (cards de líneas temporales)
             │       ├─ Vista Comparación (matriz)
             │       ├─ Síntesis final
             │       └─ Guardar / Compartir / Programar revisión
             ├─ Mis Decisiones (historial)
             │   └─ Detalle de decisión pasada
             │       └─ "¿Qué pasó realmente?" (feedback de calibración)
             ├─ Perfil de Objetivos y Valores
             ├─ Memoria (qué ha aprendido el sistema sobre mí)
             ├─ Suscripción / Facturación
             └─ Ajustes (privacidad, exportar/borrar datos, notificaciones)
```

## 10. Wireframes ASCII (nivel producto — detalle visual completo en Fase 5)

### Home — "El Mapa de Realidades"
```
┌──────────────────────────────────────────┐
│  VAR OS                         ⚙ 👤      │
│                                            │
│   "¿Qué decisión estás enfrentando?"      │
│  ┌──────────────────────────────────────┐ │
│  │ Escribe o habla...              🎙   │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Decisiones activas                       │
│  ┌────────────┐ ┌────────────┐            │
│  │ Oferta de  │ │ Mudarme a  │            │
│  │ trabajo Z  │ │ Lisboa     │            │
│  │ 3 escenarios│ │ En progreso│           │
│  └────────────┘ └────────────┘            │
│                                            │
│  [ Mis Decisiones ]  [ Memoria ]           │
└──────────────────────────────────────────┘
```

### Resultado — Vista Escenarios
```
┌──────────────────────────────────────────┐
│ ← Oferta de trabajo Z                     │
│                                            │
│  Escenario A · Probabilidad relativa 38%  │
│  "Aceptas, creces rápido, alto estrés"    │
│  Alineación con objetivo ████████░░ 82%   │
│  Riesgo        ████░░░░░░ 40%             │
│  Reversibilidad ██░░░░░░░░ 20%            │
│                                            │
│  Escenario B · Probabilidad relativa 29%  │
│  "Rechazas, negocias en tu empresa actual"│
│  Alineación ██████░░░░ 61%                │
│  ...                                      │
│                                            │
│  [ Comparar todos ]     [ Ver síntesis ]  │
└──────────────────────────────────────────┘
```

## 11. Flujos UX principales

**Flujo crítico: de la duda a la decisión (target: < 4 minutos hasta el primer escenario)**
1. Usuario abre la app → input de decisión (texto/voz, sin fricción, sin login forzado en el primer uso — "try before signup").
2. Sistema clarifica con máximo 3 preguntas dirigidas (nunca chat abierto).
3. Usuario selecciona/confirma el objetivo que optimiza.
4. Pipeline corre con streaming visual del progreso por etapas (comprensión → escenarios → síntesis).
5. Resultado: escenarios + comparación + síntesis, con CTA para guardar (requiere cuenta) o iterar.

**Flujo de retención: el cierre del ciclo**
- 30/60/90 días después de una simulación, notificación opcional: "¿Qué pasó con tu decisión sobre X?" → input breve → el sistema recalibra su modelo de confianza para ese usuario (ver Fase 3, agente de Aprendizaje).

## 12. Roadmap

| Fase | Contenido | Horizonte |
|---|---|---|
| **MVP** | 3 verticales (Carrera, Relaciones, Finanzas), 8 agentes core, iOS+Android+Web, Stripe, tier Free/Pro | 0–4 meses |
| **v1.1** | Verticales Negocio y Mudanza, Modo Bifurcación (comparar 2 decisiones), export a PDF | 5–7 meses |
| **v1.2** | Agente de Confrontación/Conflicto, memoria de largo plazo con embeddings, calibración de confianza por usuario | 8–10 meses |
| **v2** | VAR OS for Teams (simulación colaborativa multi-stakeholder), API pública para desarrolladores | 11–18 meses |
| **v3** | Modelos de simulación de mercado en tiempo real (integraciones de datos económicos), marketplace de "lentes de decisión" (frameworks de terceros: estoicismo, teoría de juegos avanzada, principios de un inversor específico) | 18–24 meses |

## 13. Modelo de negocio

**Freemium B2C con upsell a suscripción, expansión posterior a B2B.**

- **Free**: 2 simulaciones completas/mes, 3 escenarios por simulación, sin memoria de largo plazo, sin export.
- **Pro** (individuo): simulaciones ilimitadas, hasta 5 escenarios, memoria y calibración, export PDF, Modo Bifurcación.
- **Founder/Elite**: todo lo de Pro + agente de negocio avanzado, prioridad de cómputo (latencia reducida), soporte humano de onboarding.
- **Teams** (v2, B2B): asientos por equipo, simulaciones colaborativas, panel de administración, SSO empresarial.

## 14. Modelo de suscripción (pricing propuesto)

| Tier | Precio (mensual) | Precio (anual) |
|---|---|---|
| Free | $0 | — |
| Pro | $19/mes | $180/año (-21%) |
| Elite | $49/mes | $470/año (-20%) |
| Teams | desde $39/asiento/mes | Contactar ventas |

*Justificación:* posicionamiento premium consciente — el producto compite por percepción con herramientas de decisión profesional (coaching ejecutivo, terapia, asesoría financiera), no con apps de productividad de $5/mes. El precio comunica seriedad y filtra usuarios que buscan "un chatbot barato".

## 15. Definición de MVP

**Incluye:** Onboarding, captura de decisión (texto+voz), clarificación guiada, pipeline de 8 agentes (Comprensión, Resumen, Extracción de objetivos, Extracción de emociones, Análisis psicológico, Riesgos, Generación de escenarios, Síntesis), 3 verticales, historial de decisiones, feedback de cierre de ciclo simplificado, Auth (Supabase), pagos (Stripe), apps iOS/Android/Web (Flutter).

**Explícitamente fuera de MVP:** Modo Bifurcación, memoria de largo plazo con embeddings, agente de Aprendizaje con recalibración automática, colaboración multi-usuario, API pública.

## 16. Stack tecnológico (resumen — detalle en Fase 2)

Frontend: Flutter. Backend: Python + FastAPI (arquitectura limpia, DDD donde aporte valor). DB: PostgreSQL. Cache/colas: Redis. Storage/Realtime/Auth: Supabase. IA: gateway multi-proveedor con OpenAI como proveedor primario (decisión de arquitectura documentada en Fase 2 §2.6). Infra: Docker + Kubernetes en AWS. Pagos: Stripe.

## 17. Análisis competitivo

| Producto | Categoría | Fortaleza | Por qué VAR OS gana |
|---|---|---|---|
| ChatGPT / Claude genérico | Asistente conversacional | Flexibilidad, alcance | No tiene estado de "decisión" persistente, no estructura escenarios comparables, no aprende del resultado real |
| Replika / Character.AI | Compañía/entretenimiento | Vínculo emocional | Optimiza engagement, no calidad de decisión; sin rigor analítico |
| Coaches/terapeutas humanos | Servicio profesional | Empatía, responsabilidad humana | No escala, costoso, sin modelado cuantitativo de escenarios; VAR OS es complemento, no reemplazo (se declara explícitamente en producto) |
| Herramientas de decisión clásicas (matrices de decisión, Cost-Benefit apps) | Productividad | Estructura simple | Estáticas, sin IA generativa, sin generación de escenarios, sin lenguaje natural |
| Palantir Foundry (referencia de ambición, no competidor directo) | Enterprise decision intelligence | Rigor, trazabilidad | VAR OS trae ese rigor al individuo, con UX consumer-grade |

**Foso defendible:** la combinación de (a) memoria longitudinal de decisiones + resultados reales por usuario, que mejora la calibración del sistema con el tiempo, y (b) un pipeline de agentes especializado en decisión (no un prompt genérico), es difícil de replicar rápido por un competidor que solo envuelve un LLM genérico.

## 18. Riesgos

| Riesgo | Tipo | Mitigación |
|---|---|---|
| Usuario interpreta el output como predicción determinista | Ético/legal | Lenguaje de producto obligatorio en probabilidades, disclaimers estructurales (no solo texto legal), diseño visual que refuerza incertidumbre (barras, rangos, nunca "esto pasará") |
| Casos de alto riesgo emocional (crisis, ideación de daño) mal manejados por el pipeline | Seguridad del usuario / legal | Agente de "Risk & Safety Gate" obligatorio antes de cualquier síntesis (ver Fase 3); protocolos de derivación a recursos de ayuda profesional; nunca simular escenarios que impliquen autolesión o daño a terceros — el sistema se niega y redirige |
| Nombre "VAR" genera confusión con Video Assistant Referee / conflicto de marca | Legal/marca | Validar registro de marca antes de lanzamiento público; nombre de marca final a confirmar en due diligence legal (fuera de alcance de este documento) |
| Dependencia de un solo proveedor de IA (OpenAI) | Técnico/negocio | Gateway de IA abstraído por proveedor desde el día 1 (ver Fase 2) para permitir fallback multi-modelo |
| Costo de inferencia por simulación (11 agentes) erosiona margen | Negocio | Paralelización, modelos más pequeños para sub-tareas no creativas, caching de análisis intermedios, presupuesto de tokens por tier |
| Percepción de "app de adivinación" en marketing | Producto/marca | Todo lenguaje público usa "simulación", "escenarios", "probabilidad relativa" — nunca "predicción" ni "futuro" a secas |

## 19. KPIs y métricas

**Activación**
- % de usuarios que completan una simulación end-to-end en su primera sesión (target MVP: 60%).
- Tiempo hasta el primer escenario (target: < 4 min).

**Retención**
- Retención D30 (target: 25%), D90 (target: 15%).
- % de usuarios que registran el resultado real de una decisión pasada ("loop closure rate", target: 40%) — métrica norte del producto.

**Monetización**
- Conversión Free→Pro (target: 6% en 60 días).
- CAC payback period (target: < 6 meses en Pro).
- Churn mensual de suscripción (target: < 4%).

**Calidad del sistema**
- Precisión de calibración: correlación entre probabilidad asignada a un escenario y su ocurrencia real reportada (métrica propia, "Calibration Score").
- Latencia P95 del pipeline completo.
- NPS post-simulación.

---

*Fin de Fase 1. Continúa en `docs/ARCHITECTURE.md` (Fase 2).*
