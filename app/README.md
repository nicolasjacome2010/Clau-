# VAR OS — App (Flutter)

Cliente Flutter (docs/ARCHITECTURE.md §3, docs/UX_DESIGN.md). **Estado actual: todas las pantallas de `docs/UX_DESIGN.md` §2 están implementadas menos la 6 (Simulación en vivo), que espera un WebSocket de progreso que el backend no expone.** Splash → Onboarding → Auth → Home → Clarificación → Resultados/Comparación/Síntesis → Cierre de ciclo, más Mis Decisiones, Memoria, Perfil de Objetivos, Suscripción y Ajustes; con auth real de Supabase y todo lo demás contra el backend real. Los 4 destinos del nav shell son reales: no queda ningún placeholder. La Pantalla 6 es diseño, no código todavía; no asumas que existen solo porque están documentadas (misma regla que `CLAUDE.md` aplica al resto del repo).

## Estructura

```
lib/
  main.dart                 # entry point: ProviderScope + MaterialApp.router
  design_system/            # "VAR Design System" (docs/UX_DESIGN.md §1) — la única fuente
                             # de colores/tipografía/espaciado/motion; las pantallas nunca
                             # hardcodean valores hex/tamaños propios
    var_colors.dart           # tokens bg.*/text.*/accent.*/signal.*/divider (dark first)
    var_typography.dart       # escala 12/14/16/20/25/31/39/49, Space Grotesk/Inter/JetBrains Mono
    var_spacing.dart          # ritmo de espaciado + touch target mínimo (44pt, §1.5)
    var_motion.dart           # curvas ease-out/ease-in + duraciones (§1.4)
    var_breakpoints.dart      # mobile <600 / tablet 600-1024 / desktop >1024 (§1.6)
    var_palette.dart          # ThemeExtension con la mitad semántica del color; las pantallas
                               # leen `context.varColors.x`, nunca la constante *Dark*
    var_theme.dart            # ensambla los tokens en ThemeData — único lugar que lo hace
  core/
    network/api_client.dart   # Dio + interceptor de auth (token del feature `auth`) +
                               # logging estructurado (stand-in — ver docstring)
    routing/                  # GoRouter: app_routes.dart (paths) + app_router.dart (rutas)
  features/
    splash/                   # Pantalla 1 — animación de bifurcación una vez, navega a onboarding
    onboarding/                # Pantalla 2 — 3 pasos (intro x2 + selección de objetivos)
      domain/                   # OnboardingRepository (puerto). La lista semilla de objetivos
                                 # vive en goals/, que Perfil de Objetivos también usa
      presentation/               # OnboardingController (Notifier) + screens/ + widgets/
    auth/                      # Pantalla 3 — magic link + "probar sin cuenta", REAL
      domain/auth_repository.dart # puerto — nunca se llama a Supabase directo desde la UI
      data/supabase_auth_repository.dart # adaptador real (probado contra un http.Client falso)
      data/supabase_config.dart          # credenciales por --dart-define + isSupabaseConfigured
      data/local_stub_auth_repository.dart # binding sin credenciales; no emite token, a propósito
      presentation/
        controllers/session_controller.dart # el token vigente; main.dart lo inyecta en core/
    billing/                   # Pantalla 14 — Suscripción/Facturación, REAL
      domain/                    # Subscription, BillingPlan, BillingRepository, UrlOpener (puerto)
      data/api_billing_repository.dart # GET /v1/billing/subscription + checkout/portal sessions
      data/billing_config.dart         # price ids y BILLING_RETURN_URL por --dart-define
      data/url_launcher_opener.dart    # abre Stripe en el navegador externo, nunca en un webview
      presentation/               # SubscriptionController (plan real) + BillingActionController
                                   # (checkout/portal) + plan_card.dart
    clarification/             # Pantalla 5 — preguntas dirigidas con chips; su primera
                               # respuesta resuelve el `vertical` y recién ahí se crea la decisión
      domain/                    # ClarificationQuestion (las 3 preguntas), raw_input_composer.dart
      presentation/               # ClarificationController (.family sobre el texto capturado)
    decisions/                 # dominio compartido por Home, Mis Decisiones y Clarificación —
                               # no vive dentro de home/ porque ninguna pantalla es su dueña
      domain/                    # DecisionSummary, DecisionVerticalOption, DecisionsRepository
      data/api_decisions_repository.dart # adaptador real: GET y POST /v1/decisions vía Dio
      presentation/
        controllers/decisions_controller.dart # AsyncNotifier de TODAS las decisiones — un solo
                                                # fetch compartido por Home ("activas") y Mis
                                                # Decisiones (agrupadas), gracias al dedup de Riverpod
        widgets/                  # decision_status_style.dart (color+label por status,
                                   # compartido), my_decisions_tab_content.dart (Pantalla 10)
    goals/                     # Pantalla 13 — Perfil de Objetivos, REAL. También dueña de
                               # GoalOption (la lista semilla), que Onboarding comparte
      domain/                    # Goal, GoalOption, GoalsRepository (puerto)
      data/api_goals_repository.dart # adaptador real: GET/POST /v1/goals, PATCH /v1/goals/{id}
      presentation/               # GoalsController + chips editables + sliders tras "Ajuste avanzado"
    home/                      # Pantalla 4 — "El Mapa de Realidades", REAL (no placeholder)
      presentation/
        widgets/                  # input de decisión, card de decisión activa (compacta), nav shell
    memory/                    # Pantalla 12 — Memoria, REAL
      domain/                    # BiasObservation, UserBiasProfile, MemoryRepository (puerto)
      data/api_memory_repository.dart # adaptador real: GET /v1/memory/bias-profile vía Dio
      presentation/
        controllers/bias_profile_controller.dart # AsyncNotifier, refresh()
        widgets/                  # calibration_gauge.dart, bias_pattern_card.dart,
                                   # memory_tab_content.dart (botones GDPR incl.)
    simulations/               # Pantallas 7 + 8 + 9 + 11 — escenarios, comparación, síntesis y
                               # cierre de ciclo, REAL. Se abre tocando cualquier decisión
      domain/                    # Simulation, SimulationScenario, GoalAlignment,
                                 # SafetyGateResult (requiresReferral), DecisionOutcome,
                                 # SimulationsRepository (+ errores tipados 409/503)
      data/api_simulations_repository.dart # adaptador real: GET/POST
                                            # /v1/decisions/{id}/simulations y
                                            # POST /v1/decisions/{id}/outcome (timeout largo),
                                            # GET /v1/outcomes
      presentation/
        controllers/decision_simulation_controller.dart # AsyncNotifier .family por decisión
        controllers/outcomes_controller.dart            # AsyncNotifier de GET /v1/outcomes —
                                                         # una lectura compartida por Pantallas 10 y 11
        controllers/decision_outcome_controller.dart    # AsyncNotifier .family — deriva su estado
                                                         # inicial de esa lista compartida
        widgets/                  # score_bar.dart (0-100 con polaridad), scenario_card.dart,
                                   # synthesis_section.dart, safety_referral.dart,
                                   # running_indicator.dart, outcome_section.dart,
                                   # calibration_needle.dart, comparison_view.dart
                                   # (tabla real en desktop / swipe por criterio en mobile)
    settings/                  # Pantalla 15 — Ajustes. La apariencia es REAL (persistida);
                               # privacidad, notificaciones e idioma dicen por qué no lo son
      domain/settings_repository.dart  # puerto — preferencias del dispositivo, no del perfil
      data/preferences_settings_repository.dart # shared_preferences; guarda el NOMBRE del enum
      presentation/               # ThemeModeController + settings_screen.dart
    shared/presentation/       # widgets que ninguna feature es dueña: step_indicator.dart
                               # (Onboarding y Clarificación)
test/
  design_system/              # tokens
  features/                    # un archivo de test de widget por pantalla/feature
```

## Decisiones de diseño y desviaciones documentadas

- **Tipografía "Fragment" sustituida por Space Grotesk.** "Fragment" (docs/UX_DESIGN.md §1.2, display/headlines) no es una familia de fuente libremente redistribuible; Space Grotesk es la alternativa geométrica de licencia abierta más cercana disponible en Google Fonts. Ver `pubspec.yaml`.
- **Riverpod sin `riverpod_generator` todavía.** docs/ARCHITECTURE.md §3 especifica "proveedores generados con `riverpod_generator`". Este primer incremento usa la API clásica (`Notifier`/`NotifierProvider`) para no añadir un paso de `build_runner` a un grafo de providers que todavía es pequeño (2 controllers). Es una desviación documentada, no silenciosa — se adopta codegen cuando el número de features lo justifique.
- **`auth` es real: `SupabaseAuthRepository` (magic link + sesión anónima).** La sesión la persiste el SDK, así que un usuario que vuelve no parpadea por un estado deslogueado, y el token llega al interceptor de Dio a través de `SessionController` — que `main.dart` inyecta sobre el `accessTokenProvider` de `core/`. Esa inversión ocurre en el composition root justamente para que `core/` siga sin importar nada de `features/`.
- **No hay reintento-con-refresh en el interceptor, y no debe haberlo.** El SDK de Supabase refresca la sesión en segundo plano y publica el token nuevo por `accessTokenChanges`, así que cada request ya lee el vigente. Reimplementar el refresh en la capa HTTP competiría con el del SDK, y dos componentes refrescando el mismo token es exactamente cómo se dispara la detección de reutilización de refresh tokens.
- **Sin credenciales configuradas, el binding cae al stub — y el stub no emite token.** `--dart-define=SUPABASE_URL/SUPABASE_PUBLISHABLE_KEY` (se acepta también el viejo `SUPABASE_ANON_KEY`) decide cuál adaptador se usa. Sin ellos las llamadas al Core API salen sin `Authorization` y vuelven 401, y cada pantalla muestra su estado de error real: un build sin credenciales debe verse roto de la forma en que *está* roto, no simular una sesión cuyas peticiones fallan por razones que la UI no puede explicar.
- **Los botones de OAuth de la Pantalla 3 siguen sin implementarse.** Necesitan redirect URLs por plataforma (deep link, URL scheme de iOS, intent filter de Android) y este proyecto todavía no tiene identificadores de bundle; un método en el puerto que ninguna pantalla puede alcanzar sería peor que su ausencia.
- **Los objetivos capturados en Onboarding no se envían todavía.** `OnboardingRepository` (puerto) sigue sin implementación concreta: capturar objetivos ocurre *antes* de autenticarse (Pantalla 3 permite "probar antes de registrarse"), y `POST /v1/goals` exige un JWT. El adaptador ya existe (`ApiGoalsRepository`, que Perfil de Objetivos usa de verdad); lo que falta es el momento correcto para llamarlo — justo después de la primera petición autenticada, en paralelo al JIT provisioning que hace `GetOrCreateUserUseCase` en el backend. Depende de tener auth real, no de código de este feature.
- **Sin refresh de token automático en `core/network/api_client.dart`.** Depende de la misma sesión de Supabase real que `auth` todavía no tiene. Documentado en el archivo, mismo patrón que el resto del repo (p. ej. `simulations/infrastructure/reality_engine_client.py`'s "no queue yet").
- **El `vertical` se resuelve preguntando, no adivinando.** `POST /v1/decisions` exige un `vertical` (career/relationships/finance/business/relocation/conflict) que el campo de texto libre de Home no puede aportar. En vez de inventar un default silencioso que mal-clasificaría datos reales, el input de Home entrega el texto a Pantalla 5 (Clarificación), cuya primera pregunta con chips lo resuelve explícitamente; recién ahí se crea la decisión. Es el mecanismo que el propio spec define para esa pantalla ("opciones de respuesta rápida (chips) siempre que sea posible"), no un rodeo inventado.
- **Las respuestas no-`vertical` de Clarificación se anexan a `raw_input`.** El backend solo acepta `raw_input` + `vertical`, así que plazo y opciones-en-mente no tienen columna propia — y `raw_input` es justo lo que llega a `/v1/simulate`, así que ese contexto mejora la simulación en vez de perderse. El texto del usuario nunca se reescribe ni se entremezcla: se preserva literal y las respuestas van en un bloque delimitado abajo (`raw_input_composer.dart`). Persistirlas como columnas propias es la forma correcta a largo plazo y el siguiente paso documentado.
- **Clarificación vuelve a Home al crear la decisión, no sigue a Pantalla 6.** "Simulación en vivo" transmite el progreso del pipeline por un WebSocket que el backend no expone todavía (docs/ARCHITECTURE.md §2.2 lo describe; `simulations` llama al Reality Engine de forma síncrona, sin canal de progreso). La decisión aparece en "Decisiones activas" como `draft`, que es lo honesto sobre dónde está.
- **El ícono de micrófono sigue mostrando "próximo módulo"** — necesita permisos de micrófono por plataforma y wiring de STT que este incremento no construye.
- **Quitar un objetivo es irreversible desde el cliente.** `GET /v1/goals` solo devuelve objetivos activos (`ListActiveGoalsUseCase`, sin parámetro `include_inactive`), así que un objetivo desactivado desaparece y nada puede volver a listarlo para reactivarlo. Por eso la acción se llama "Quitar" — lo que el usuario realmente experimenta — en vez de un toggle que suene reversible. Reactivar necesita un cambio de backend, no un rodeo en el cliente. Ver el docstring de `GoalsRepository`.
- **El indicador "sin cerrar el ciclo" lleva palabras, no solo el punto ámbar.** El wireframe pide un punto; docs/UX_DESIGN.md §1.5 prohíbe que el color sea el único portador de significado, así que va acompañado del texto "Sin cerrar" y del mismo dato en el label de accesibilidad. Y se enuncia como estado, nunca como demanda: el propio spec dice "invita, no presiona", así que no hay badge, ni contador, ni llamada a la acción.
- **Resultados (Pantallas 7 + 9) muestra una espera indeterminada, no la Pantalla 6.** `POST /v1/decisions/{id}/simulations` bloquea durante todo el pipeline (15-30s) y no hay canal de progreso, así que la pantalla muestra un spinner honesto — y pasados ~15s el micro-copy tranquilizador que el spec pide — en vez de una barra de progreso sintética que fingiría saber en qué etapa va. `ApiSimulationsRepository` sube el timeout a 90s para esa llamada, porque el default de 10s abortaría una corrida perfectamente sana.
- **Un `halt_and_refer` del Safety Gate reemplaza *todo* el resultado.** `SafetyReferral` se comprueba antes que cualquier otra cosa: aunque el payload traiga escenarios y síntesis, no se renderiza ninguno, y no hay escape del tipo "ver de todos modos" (docs/PRD.md §18: "se niega y redirige"). Un `safe_to_proceed: false` sin `recommended_action` explícito también refiere — falla hacia lo conservador, igual que `SafetyGateAgent` en el Reality Engine. A la inversa, un `safety_gate_result` vacío (una corrida que falló *antes* de llegar al Agente 0) **no** se lee como crisis: se reporta como fallo, que es lo que es.
- **`SafetyReferral` no hardcodea números de crisis, a propósito.** Los recursos son específicos por país e idioma, y un número equivocado o muerto mostrado a alguien en crisis es peor que ninguno. La copy apunta a ayuda profesional en términos generales; una lista real, localizada y revisada por los profesionales que docs/PRD.md §18 ya exige antes de lanzar es un entregable requerido, no un pulido opcional. Ver el docstring del widget.
- **El cierre de ciclo (Pantalla 11) vive al pie de la pantalla de resultados, no en una pantalla propia.** El spec la llama "detalle de decisión pasada + cierre de ciclo", y el detalle de una decisión pasada es exactamente lo que Pantallas 7+9 ya renderizan; separarlas obligaría a re-pedir la misma simulación para mostrar los mismos escenarios encima del mismo prompt. Solo se ofrece sobre una simulación `completed`: sin ella `POST /v1/decisions/{id}/outcome` responde 409 y no habría nada contra qué calibrar.
- **Un solo `GET /v1/outcomes` alimenta dos pantallas.** `OutcomesController` lo lee una vez y Riverpod lo comparte: la pantalla de resultados sabe si el ciclo de *esta* decisión ya se cerró (y muestra el resultado en vez de re-ofrecer el prompt), y Mis Decisiones marca las decisiones completadas que llevan >60 días sin cerrar. El endpoint es una colección justamente por eso — preguntarlo por decisión sería un N+1 contra una pantalla de lista, y hay un test que fija ese contrato (cinco filas, una sola lectura).
- **El 409 ambiguo se resuelve preguntando, no parseando.** El backend responde 409 tanto para "este ciclo ya está cerrado" como para "esta decisión no tiene simulación completada", y solo el texto los distingue. El cliente no compara ese string a través de un límite de servicio: relee `GET /v1/outcomes` y, si hay un outcome para esta decisión, muestra ese resultado; si no, es el otro conflicto. Correcto sin importar cómo se redacte el mensaje en el futuro.
- **Si `GET /v1/outcomes` falla, el prompt igual se ofrece.** Es mucho más probable que el ciclo esté abierto a que esté cerrado, y el `POST` responde 409 si no lo está — esconder el prompt costaría más que un 409 ocasional.
- **El resultado de la calibración se muestra crudo, sin interpretarlo.** `calibration_delta` va de -100 a 100 y ni docs/REALITY_ENGINE.md define qué significa su signo — `UserBiasProfile.with_calibration_delta` llama a su propia fórmula "a starting formula, not a validated calibration model". La aguja anima de 0 al valor reportado (la microinteracción que pide el spec: "una aguja que se ajusta sutilmente") y el número se muestra tal cual; no hay copy del tipo "¡acertamos un 72%!". Lo que sí se muestra en palabras es `system_errors_identified`: en qué se equivocó la simulación, según el propio Agente 12.
- **Un `closest_scenario_id` nulo se dice, no se disimula.** docs/REALITY_ENGINE.md §2 trata "lo que pasó no se parece a ningún escenario" como un resultado valioso —un punto ciego del sistema— y prohíbe forzar una coincidencia; el cliente lo enuncia como tal en vez de elegir el escenario más cercano por su cuenta.
- **La comparación (Pantalla 8) es una vista de la misma pantalla de resultados, no una ruta aparte.** El spec las llama "Resultado: Vista Escenarios" y "Resultado: Vista Comparación"; volver a pedir la misma simulación para mostrar los mismos números de otra forma sería trabajo que nadie pidió. El toggle solo aparece con dos o más escenarios — con uno solo no hay nada contra qué compararlo.
- **La alineación se muestra una fila por objetivo, nunca promediada.** El wireframe dibuja una sola fila "Alineación objetivo", pero cada escenario trae un score por objetivo y el cliente no recibe los pesos relativos del usuario; promediarlos inventaría una ponderación igualitaria y la presentaría como opinión del sistema. Cada objetivo tiene su fila y el usuario pondera — que es la postura del producto entero.
- **Un objetivo contra el que un escenario nunca fue evaluado se muestra como "—", no como 0.** "Sin dato" y "sale pésimo" son afirmaciones distintas.
- **La probabilidad relativa se dibuja en color neutro** (`ScorePolarity.neutral`): un 38% de probabilidad no es una buena ni una mala noticia, y pintarlo de verde o rojo afirmaría una opinión que el sistema no tiene.
- **El pago nunca ocurre dentro de la app.** Ambos botones piden al backend una URL hospedada por Stripe y se la pasan al navegador *externo* (`LaunchMode.externalApplication`), no a un webview: renderizar el formulario de tarjeta de alguien dentro de la app esconde justamente las señales —barra de direcciones, candado— con las que distingue una página de pago de una de phishing. Ningún dato de tarjeta toca este proceso.
- **El plan cambia cuando Stripe lo confirma, no cuando el usuario abre el checkout.** `Subscription` es una réplica del estado de Stripe que solo escribe el manejador de webhooks, así que tras abrir la URL el cliente **re-lee** `GET /v1/billing/subscription` en vez de asumir la compra — quien cerró la pestaña sigue en Free, que es la verdad. Hay un test que fija exactamente eso.
- **El precio mostrado se configura junto al precio que se cobra.** Un número hardcodeado en un binario publicado puede quedar desincronizado del precio que Stripe factura, y eso es un problema de defensa del consumidor, no un detalle de estilo. Por eso `STRIPE_PRICE_PRO_LABEL` vive al lado de `STRIPE_PRICE_PRO`, y un plan sin precio configurado muestra qué incluye sin afirmar cuánto cuesta ni ofrecer un botón muerto. La solución correcta a largo plazo es un `GET /v1/billing/plans` que lea Stripe.
- **Sin dark patterns, y con un test que lo fija.** El spec los prohíbe por nombre ("sin 'más popular' artificial, sin temporizadores de urgencia falsos"), así que hay un test que verifica su *ausencia* — es la única forma de que siga siendo cierto cuando la copy evolucione. La única card destacada es la del plan actual, que es información, no persuasión.
- **Ajustes solo controla lo que de verdad puede controlar.** La apariencia (Dark/Claro/Como el sistema) es real: se persiste en el dispositivo y `MaterialApp` la sigue. Privacidad, notificaciones e idioma aparecen con el motivo por el que todavía no funcionan (faltan endpoints de exportación/borrado, no hay servicio de notificaciones, la app está solo en español). Un switch que no conmuta nada sería peor que su ausencia.
- **La apariencia es una preferencia del dispositivo, no del perfil.** Un teléfono en oscuro de noche y un escritorio en claro de día son el mismo usuario, así que sincronizarla al servidor sería incorrecto, no solo trabajo extra. Se guarda el *nombre* del enum, no su índice: un índice repuntaría en silencio todas las preferencias guardadas el día que alguien reordene `ThemeMode`.
- **El default es "como el sistema", y la recomendación de dark es copy, no una elección pre-hecha** por el usuario (el spec pide exactamente eso). Mientras la preferencia guardada se lee, se muestra dark: es el tema diseñado primero, así que quien eligió dark no ve un flash claro al arrancar.
- **Memoria (Pantalla 12) tiene los botones "Exportar mis datos"/"Borrar todo mi historial" visibles pero sin backend detrás.** El spec es explícito en que deben ser visibles (no escondidos en Ajustes), pero el backend no tiene ningún endpoint de exportación/borrado de datos todavía — tocarlos muestra un aviso "llega en un próximo módulo" en vez de fingir la acción. `bias.bias` se renderiza tal cual lo escribió el LLM (docs/REALITY_ENGINE.md Agente 5/12: es texto libre en español, no un código), así que no hay tabla de traducción cliente-side que mantener sincronizada.

## Desarrollo local

```bash
flutter pub get
flutter run                      # requiere un emulador/dispositivo o Chrome (-d chrome)
flutter run --dart-define=API_BASE_URL=http://localhost:8000

# Con auth real (sin esto, el binding cae al stub y todo responde 401):
flutter run \
  --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=SUPABASE_URL=https://xxxx.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

## Calidad — correr antes de cada commit

```bash
flutter analyze
flutter test
dart format --output=none --set-exit-if-changed lib test
```
