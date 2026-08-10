# VAR OS — Diseño de Interfaz (Fase 5)

| | |
|---|---|
| **Documento** | UX/UI Design System v1.0 |
| **Depende de** | `docs/PRD.md` |
| **Estado** | Fase 5 |

---

## 0. Filosofía de diseño

VAR OS no se ve como una app de consumo (Instagram, TikTok) ni como un chatbot (burbujas de mensaje). Se ve como un **instrumento de precisión**: cockpit, panel de control, sala de mapas. Referencias de tono visual: Apple (claridad, tipografía, espacio negativo), Palantir (densidad de datos con jerarquía clara, sensación de "sistema serio"), Linear/Arc (micro-interacciones pulidas, modernidad).

**No hay**: scroll infinito, contadores de "likes", notificaciones de urgencia artificial, gamificación barata (rachas, puntos). El único elemento "lúdico" tolerado es la metáfora visual de líneas temporales/realidades — pero se usa para **claridad analítica**, no para dopamina.

## 1. Sistema de diseño — fundamentos

### 1.1 Paleta de color

Concepto: "Espacio-tiempo" — fondo oscuro profundo por defecto (el producto se percibe mejor en dark mode, como un instrumento de navegación nocturna), con acentos de color que representan **probabilidad y alineación**, nunca decoración gratuita.

| Token | Dark (default) | Light | Uso |
|---|---|---|---|
| `bg.primary` | `#0A0B0F` | `#FFFFFF` | fondo base |
| `bg.surface` | `#14151C` | `#F5F5F7` | cards, paneles |
| `bg.elevated` | `#1E202B` | `#FFFFFF` (con sombra) | modales, sheets |
| `text.primary` | `#F5F6FA` | `#0A0B0F` | |
| `text.secondary` | `#9295A6` | `#5B5E6E` | |
| `accent.primary` | `#5B8CFF` (azul "señal") | `#3D6BE0` | CTAs, elementos activos |
| `accent.gradient` | gradiente `#5B8CFF → #B37BFF` | mismo, opacidad ajustada | "Reality Engine trabajando" (loading, streaming) |
| `signal.high` | `#3DDC97` (verde) | `#1FA871` | alta alineación / bajo riesgo |
| `signal.medium` | `#F5B942` | `#C98F1E` | media alineación/riesgo |
| `signal.low` | `#FF6B6B` | `#E14A4A` | baja alineación / alto riesgo |
| `divider` | `#2A2C38` | `#E4E4E8` | |

Nunca se usa rojo/verde como único diferenciador (accesibilidad — daltonismo); siempre acompañado de longitud de barra + texto (ver §1.5 Accesibilidad).

### 1.2 Tipografía

- **Display/Headlines**: "Fragment" o alternativa libre equivalente (geométrica, ligeramente condensada, con carácter técnico) — transmite "sistema", no "app amigable".
- **Cuerpo de texto**: "Inter" — máxima legibilidad, neutral, excelente soporte de idiomas (crítico para es/en desde el día 1).
- **Monoespaciada** ("JetBrains Mono" o similar): usada deliberadamente para números de probabilidad, scores y IDs de escenario — refuerza la sensación de "dato preciso, no opinión".

Escala tipográfica (base 16px, ratio 1.25): `12 / 14 / 16 / 20 / 25 / 31 / 39 / 49px`.

### 1.3 Iconografía

Set de íconos custom de trazo fino (1.5px), geométrico, sin relleno por defecto (relleno solo en estado activo/seleccionado). Íconos clave propios del producto (no genéricos de librería): el ícono de "escenario" (una línea ramificándose en 3), el ícono de "síntesis" (líneas convergiendo), el ícono de "memoria" (espiral sutil). Estos tres se convierten en parte de la identidad de marca.

### 1.4 Animación y motion

- Curva estándar: `cubic-bezier(0.22, 1, 0.36, 1)` ("ease-out expresivo") para entradas; `cubic-bezier(0.4, 0, 1, 1)` para salidas.
- Duraciones: micro-interacciones 120-180ms, transiciones de pantalla 250-350ms, la animación de "streaming del pipeline" es la única animación de larga duración tolerada (hasta ~20s) porque comunica trabajo real, no decoración.
- Principio: **toda animación debe comunicar estado del sistema**, nunca ser puramente decorativa (esto es coherente con "no engagement loops" del PRD).

### 1.5 Accesibilidad

- Contraste mínimo AA (4.5:1) en todo texto; AAA (7:1) en texto de síntesis (el contenido más importante de leer).
- Todos los indicadores de score usan forma + color + texto numérico (nunca solo color).
- Soporte completo de `TalkBack`/`VoiceOver` con labels semánticos en cada card de escenario (no solo "card 1 de 3", sino "Escenario A, probabilidad 38%, alineación alta").
- Tamaño de touch target mínimo 44x44pt.
- Modo "texto grande" del sistema operativo respetado sin romper layout (se usa `flutter`'s text scaling con layouts flexibles, no absolutos).

### 1.6 Responsive

Breakpoints: `mobile <600px`, `tablet 600-1024px`, `desktop/web >1024px`. En desktop/web, la vista de Comparación pasa de cards apiladas a una matriz tabular real (aprovecha el ancho — ver pantalla 5).

---

## 2. Pantallas (detalle completo)

### Pantalla 1 — Splash
- Fondo `bg.primary`, logo centrado (wordmark "VAR OS" en Display font), micro-animación: una línea se bifurca en 3 y converge de nuevo en 1 punto (600ms, una sola vez, comunica la esencia del producto en el primer frame).

### Pantalla 2 — Onboarding (3 pasos + captura de objetivo de vida)
```
┌──────────────────────────────┐
│                                │
│      [ilustración abstracta   │
│       de líneas temporales]   │
│                                │
│  "No predecimos tu futuro.    │
│   Simulamos tus posibles      │
│   futuros para que elijas     │
│   con claridad."               │
│                                │
│  ● ○ ○                        │
│                                │
│         [ Continuar → ]        │
└──────────────────────────────┘
```
Paso 3 captura objetivos de vida iniciales (chips seleccionables: "Estabilidad financiera", "Crecimiento profesional", "Relaciones", "Libertad/autonomía", "Salud/bienestar" + opción custom) — alimenta `goals` (Fase 4 §2.3) desde el primer momento. Transición: fade + slight scale (no swipe horizontal genérico — se usa un efecto de "profundidad" sutil, parallax de las ilustraciones, para diferenciarse visualmente de onboarding estándar).

### Pantalla 3 — Auth
Login/registro minimalista: email + OAuth (Google/Apple). **Permite "probar antes de registrarse"**: un botón secundario "Probar una simulación primero" que lleva directo a captura de decisión en modo anónimo (rate-limited, Fase 2 §15), con banner sutil "Guarda tu resultado creando una cuenta" al final — nunca un muro de login antes de mostrar valor.

### Pantalla 4 — Home ("El Mapa de Realidades")
Ya bosquejado en PRD §10. Detalle adicional:
- El input de nueva decisión es el elemento dominante (60% del viewport en mobile), con placeholder rotativo (ejemplos reales anonimizados: "¿Debo aceptar esta oferta de trabajo?").
- El ícono de micrófono activa captura de voz con animación de onda (waveform) en tiempo real usando `accent.gradient`.
- Cards de "Decisiones activas": borde izquierdo de 3px con el color de estado (`signal.high/medium/low` según qué tan cerca está de completarse, o gris si es borrador).
- Bottom nav (mobile) / rail lateral (tablet+): Home, Mis Decisiones, Memoria, Perfil — 4 destinos máximo, sin badge de notificación agresivo (solo un punto sutil, sin número, para no generar ansiedad de "inbox zero").

### Pantalla 5 — Clarificación (chat guiado, no libre)
```
┌──────────────────────────────┐
│ Entendiendo tu decisión...     │
│                                │
│  Detecté que estás evaluando: │
│  "Aceptar oferta en Empresa Z" │
│                                │
│  Antes de simular, necesito    │
│  saber:                        │
│                                │
│  ¿Cuál es tu plazo para        │
│  decidir?                      │
│  ┌────────┐┌────────┐┌───────┐│
│  │ < 1 sem││1-4 sem ││ Sin    ││
│  │        ││        ││ plazo  ││
│  └────────┘└────────┘└───────┘│
│                                │
│  ○ ○ (2 preguntas más)         │
└──────────────────────────────┘
```
Deliberadamente **no es un chat de texto libre**: opciones de respuesta rápida (chips) siempre que sea posible, campo de texto libre solo cuando la pregunta lo requiere. Esto refuerza "sistema estructurado", no "conversación con un bot".

### Pantalla 6 — Simulación en vivo (streaming del pipeline)
```
┌──────────────────────────────┐
│                                │
│        ◐ Comprendiendo         │
│        ✓ Analizando objetivos  │
│        ✓ Mapeando riesgos      │
│        ◐ Generando escenarios  │
│        ○ Comparando            │
│        ○ Sintetizando          │
│                                │
│   [visualización animada:      │
│    líneas ramificándose        │
│    progresivamente]            │
│                                │
└──────────────────────────────┘
```
Cada etapa se ilumina en tiempo real vía WebSocket (Fase 2 §3). Si excede ~15s en una etapa, aparece micro-copy tranquilizador ("Los escenarios complejos toman un poco más — vale la pena"), nunca una barra de progreso falsa/lineal (que rompería confianza si se estanca).

### Pantalla 7 — Resultado: Vista Escenarios
Ya bosquejada en PRD §10. Cada card es expandible (tap) para ver `assumptions` y `narrative` completo. Orden por defecto: por `rank`, con el escenario #1 visualmente destacado (borde `accent.primary`, ligeramente más grande) pero **sin ocultar los demás** — el usuario siempre ve el espacio completo de opciones, coherente con "el usuario decide" (PRD §2.3).

### Pantalla 8 — Resultado: Vista Comparación
Mobile: cards apiladas por criterio (swipe horizontal entre criterios: Alineación / Riesgo / Reversibilidad).
Desktop/Web:
```
┌────────────────────────────────────────────────────────┐
│ Criterio            Escenario A   Escenario B   Esc. C   │
│ Alineación objetivo  ████████ 82%  ██████ 61%   ███ 34%  │
│ Riesgo               ████ 40%      ███ 30%      ███████72%│
│ Reversibilidad       ██ 20%        ███████ 75%  █████ 55% │
│ Probabilidad relativa 38%          29%          33%       │
└────────────────────────────────────────────────────────┘
```
Tabla real en desktop (no cards forzadas a tabla) — aprovecha que este es el público más analítico (Persona "Estratega Personal", "Fundadora").

### Pantalla 9 — Síntesis final
```
┌──────────────────────────────┐
│  ✦ Síntesis                    │
│                                │
│  "Basado en lo que más te      │
│   importa ahora mismo —        │
│   crecimiento y estabilidad —  │
│   el Escenario A se alinea     │
│   más, aunque implica mayor    │
│   riesgo a corto plazo..."     │
│                                │
│  Noté que el miedo a decepcionar│
│  a tu equipo actual podría estar│
│  pesando más de lo que tu      │
│  propio objetivo declarado     │
│  sugiere. ¿Es ese miedo algo   │
│  que quieres que pese en tu    │
│  decisión, o es ruido?         │
│                                │
│  [ Guardar decisión ]          │
│  [ Programar revisión en 90d ] │
└──────────────────────────────┘
```
Tipografía Display para la pregunta reflexiva final — es el momento emocionalmente más importante de la sesión, se le da espacio y jerarquía visual, no se trata como texto secundario.

### Pantalla 10 — Mis Decisiones (historial)
Lista cronológica, agrupada por estado (`Activas / Completadas / Archivadas`). Cada ítem completado muestra un indicador sutil de "sin cerrar el ciclo" (punto ámbar) si pasaron >60 días sin reportar resultado real — invita, no presiona.

### Pantalla 11 — Detalle de decisión pasada + cierre de ciclo
CTA principal: "¿Qué pasó realmente?" → input de texto libre corto → confirmación con micro-animación de "calibración" (una aguja/indicador que se ajusta sutilmente) comunicando que el sistema aprendió algo, reforzando el valor de cerrar el ciclo.

### Pantalla 12 — Memoria
Vista de transparencia radical: muestra al usuario, en lenguaje simple, los patrones que el sistema ha detectado sobre él ("Sueles subestimar el tiempo que necesitas para adaptarte a cambios grandes", con evidencia: "visto en 3 decisiones pasadas"). Incluye el `calibration_score` visualizado como un medidor simple, y un botón directo a "Exportar mis datos" / "Borrar todo mi historial" (cumplimiento GDPR visible, no escondido en un submenú de ajustes — refuerza confianza).

### Pantalla 13 — Perfil de Objetivos y Valores
Chips editables de objetivos (mismos que onboarding), con slider de peso relativo opcional para usuarios avanzados (oculto tras "Ajuste avanzado" para no abrumar por defecto).

### Pantalla 14 — Suscripción/Facturación
Comparación de tiers (Free/Pro/Elite) en cards simples, sin dark patterns (sin "más popular" artificial si no es honesto, sin temporizadores de urgencia falsos). Gestión vía Stripe Customer Portal embebido/enlazado (Fase 2 §9).

### Pantalla 15 — Ajustes
Privacidad (exportar/borrar datos — accesible también desde aquí), notificaciones (opt-in/out de recordatorios de cierre de ciclo), idioma, apariencia (Dark/Light/System — default System pero recomendando Dark en primer uso).

## 3. Microinteracciones destacadas

- **Selección de chip de objetivo**: escala 1.0→1.05→1.0 (150ms) + cambio de color de fondo con la curva ease-out expresiva.
- **Card de escenario al expandir**: altura anima con spring físico sutil (no un simple ease), refuerza sensación "táctil, real".
- **Barra de score**: se rellena de izquierda a derecha en 400ms al aparecer en pantalla (nunca aparece ya llena — refuerza que es un cálculo, no un dato estático).
- **Envío de input de decisión**: el campo de texto se "colapsa" hacia el ícono de navegación superior mientras la pantalla de streaming aparece — transmite continuidad espacial (no un simple corte de pantalla).

## 4. Dark mode

Dark es el modo por defecto y el diseñado primero (design-first, no "invertir colores del light"). Light mode se deriva ajustando contraste y sombras, no simplemente invirtiendo la paleta — las barras de `signal.*` mantienen legibilidad AA en ambos modos (valores ajustados, ver tabla §1.1).

---

*Fin de Fase 5 — toda la documentación de diseño de producto está completa. Comienza la Fase 6 (desarrollo por módulos) en el código del repositorio.*
