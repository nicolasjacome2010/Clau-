# VAR OS — App (Flutter)

Cliente Flutter (docs/ARCHITECTURE.md §3, docs/UX_DESIGN.md). **Estado actual: fundación + Pantallas 1-4 (Splash → Onboarding → Auth → Home) implementadas end to end.** El resto de `docs/UX_DESIGN.md` §2 (Clarificación, Simulación en vivo, Resultados, Memoria, Suscripción, Ajustes) es diseño, no código todavía — no asumas que existen solo porque están documentadas (misma regla que `CLAUDE.md` aplica al resto del repo).

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
      domain/                   # GoalOption (chips semilla), OnboardingRepository (puerto)
      presentation/               # OnboardingController (Notifier) + screens/ + widgets/
    auth/                      # Pantalla 3 — email/OAuth + "probar sin cuenta"
      domain/auth_repository.dart # puerto — nunca se llama a Supabase directo desde la UI
      data/local_stub_auth_repository.dart # adaptador interino, ver su docstring
      presentation/
    home/                      # Pantalla 4 — "El Mapa de Realidades", REAL (no placeholder)
      domain/                    # DecisionSummary, DecisionsRepository (puerto)
      data/api_decisions_repository.dart # adaptador real: GET /v1/decisions vía Dio
      presentation/
        controllers/active_decisions_controller.dart # AsyncNotifier, refresh()
        widgets/                  # input de decisión, cards de decisión activa, nav shell
    shared/presentation/feature_placeholder_content.dart # contenido de los destinos del nav
                               # shell que aún no son un módulo real (Mis Decisiones/Memoria/Perfil)
test/
  design_system/              # tokens
  features/                    # un archivo de test de widget por pantalla/feature
```

## Decisiones de diseño y desviaciones documentadas

- **Tipografía "Fragment" sustituida por Space Grotesk.** "Fragment" (docs/UX_DESIGN.md §1.2, display/headlines) no es una familia de fuente libremente redistribuible; Space Grotesk es la alternativa geométrica de licencia abierta más cercana disponible en Google Fonts. Ver `pubspec.yaml`.
- **Riverpod sin `riverpod_generator` todavía.** docs/ARCHITECTURE.md §3 especifica "proveedores generados con `riverpod_generator`". Este primer incremento usa la API clásica (`Notifier`/`NotifierProvider`) para no añadir un paso de `build_runner` a un grafo de providers que todavía es pequeño (2 controllers). Es una desviación documentada, no silenciosa — se adopta codegen cuando el número de features lo justifique.
- **`auth`/`onboarding` no hablan con un backend real todavía.** `LocalStubAuthRepository` (ver su docstring) es un adaptador interino: acepta cualquier email válido y no hace red. `OnboardingRepository` (puerto) tampoco tiene implementación concreta — capturar objetivos ocurre antes de autenticarse en el flujo real del producto (Pantalla 3 permite "probar antes de registrarse"), así que enviarlos a `POST /v1/goals` del backend solo tiene sentido una vez exista una sesión de Supabase real. Wiring de `SupabaseAuthRepository`/`ApiGoalsRepository` es el siguiente incremento de integración, no una pieza olvidada.
- **Sin refresh de token automático en `core/network/api_client.dart`.** Depende de la misma sesión de Supabase real que `auth` todavía no tiene. Documentado en el archivo, mismo patrón que el resto del repo (p. ej. `simulations/infrastructure/reality_engine_client.py`'s "no queue yet").
- **Home (Pantalla 4) SÍ integra con el backend real** — `ApiDecisionsRepository` llama `GET /v1/decisions` de verdad a través del `Dio` compartido; el estado "sin sesión" se ve simplemente como una lista vacía o un error con reintento, no como un mock. Lo que **no** está wireado todavía es crear una decisión: `POST /v1/decisions` exige un `vertical` (career/relationships/finance/business/relocation/conflict) que ni el wireframe de Pantalla 4 ni el de Pantalla 5 (Clarificación) especifican cómo resolver desde un único campo de texto libre — inventar un default silencioso mal-clasificaría datos reales. El campo de entrada de decisión y el ícono de micrófono son reales visualmente pero muestran un aviso "llega en un próximo módulo" al enviarse, en vez de fingir una integración que no existe. Ver el docstring de `DecisionsRepository`.
- **El nav shell de Home tiene 4 destinos, solo 1 real.** `Mis Decisiones`/`Memoria`/`Perfil` renderizan `FeaturePlaceholderContent` — el shell (bottom nav en mobile, `NavigationRail` en tablet+, docs/UX_DESIGN.md §1.6) es completo y responsive ya, cada pantalla real detrás de esos destinos es su propio módulo futuro.

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
