# VAR OS — App (Flutter)

Cliente Flutter (docs/ARCHITECTURE.md §3, docs/UX_DESIGN.md). **Estado actual: fundación + Pantallas 1, 2, 3, 4, 5, 7, 9, 10, 11, 12 y 13 implementadas end to end (Splash → Onboarding → Auth → Home → Clarificación → Resultados/Síntesis → Cierre de ciclo, + Mis Decisiones, Memoria y Perfil de Objetivos en el nav shell), y la creación de decisiones, la simulación y el cierre de ciclo funcionan contra el backend real.** Los 4 destinos del nav shell son reales: ya no queda ningún placeholder. El resto de `docs/UX_DESIGN.md` §2 (Simulación en vivo, Comparación, Suscripción, Ajustes) es diseño, no código todavía — no asumas que existen solo porque están documentadas (misma regla que `CLAUDE.md` aplica al resto del repo).

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
    auth/                      # Pantalla 3 — email/OAuth + "probar sin cuenta"
      domain/auth_repository.dart # puerto — nunca se llama a Supabase directo desde la UI
      data/local_stub_auth_repository.dart # adaptador interino, ver su docstring
      presentation/
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
    simulations/               # Pantallas 7 + 9 + 11 — escenarios, síntesis y cierre de ciclo,
                               # REAL. Se abre tocando cualquier decisión (Home o Mis Decisiones)
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
                                   # calibration_needle.dart
    shared/presentation/       # widgets que ninguna feature es dueña: step_indicator.dart
                               # (Onboarding y Clarificación)
test/
  design_system/              # tokens
  features/                    # un archivo de test de widget por pantalla/feature
```

## Decisiones de diseño y desviaciones documentadas

- **Tipografía "Fragment" sustituida por Space Grotesk.** "Fragment" (docs/UX_DESIGN.md §1.2, display/headlines) no es una familia de fuente libremente redistribuible; Space Grotesk es la alternativa geométrica de licencia abierta más cercana disponible en Google Fonts. Ver `pubspec.yaml`.
- **Riverpod sin `riverpod_generator` todavía.** docs/ARCHITECTURE.md §3 especifica "proveedores generados con `riverpod_generator`". Este primer incremento usa la API clásica (`Notifier`/`NotifierProvider`) para no añadir un paso de `build_runner` a un grafo de providers que todavía es pequeño (2 controllers). Es una desviación documentada, no silenciosa — se adopta codegen cuando el número de features lo justifique.
- **`auth` no habla con un backend real todavía.** `LocalStubAuthRepository` (ver su docstring) es un adaptador interino: acepta cualquier email válido y no hace red. Un `SupabaseAuthRepository` real es el siguiente incremento de integración, no una pieza olvidada.
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
- **Memoria (Pantalla 12) tiene los botones "Exportar mis datos"/"Borrar todo mi historial" visibles pero sin backend detrás.** El spec es explícito en que deben ser visibles (no escondidos en Ajustes), pero el backend no tiene ningún endpoint de exportación/borrado de datos todavía — tocarlos muestra un aviso "llega en un próximo módulo" en vez de fingir la acción. `bias.bias` se renderiza tal cual lo escribió el LLM (docs/REALITY_ENGINE.md Agente 5/12: es texto libre en español, no un código), así que no hay tabla de traducción cliente-side que mantener sincronizada.

## Desarrollo local

```bash
flutter pub get
flutter run                      # requiere un emulador/dispositivo o Chrome (-d chrome)
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

## Calidad — correr antes de cada commit

```bash
flutter analyze
flutter test
dart format --output=none --set-exit-if-changed lib test
```
