# VAR OS — App (Flutter)

Cliente Flutter (docs/ARCHITECTURE.md §3, docs/UX_DESIGN.md). **Estado actual: fundación + primer feature vertical (Splash → Onboarding → Auth) implementados end to end.** El resto de las 15 pantallas de `docs/UX_DESIGN.md` §2 (Home, Clarificación, Simulación en vivo, Resultados, Memoria, Suscripción, Ajustes) es diseño, no código todavía — no asumas que existen solo porque están documentadas (misma regla que `CLAUDE.md` aplica al resto del repo).

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
    home/                      # solo un placeholder de navegación — Pantalla 4 real es el
                               # siguiente módulo, no está construida aquí
test/
  design_system/              # tokens
  features/                    # un archivo de test de widget por pantalla
```

## Decisiones de diseño y desviaciones documentadas

- **Tipografía "Fragment" sustituida por Space Grotesk.** "Fragment" (docs/UX_DESIGN.md §1.2, display/headlines) no es una familia de fuente libremente redistribuible; Space Grotesk es la alternativa geométrica de licencia abierta más cercana disponible en Google Fonts. Ver `pubspec.yaml`.
- **Riverpod sin `riverpod_generator` todavía.** docs/ARCHITECTURE.md §3 especifica "proveedores generados con `riverpod_generator`". Este primer incremento usa la API clásica (`Notifier`/`NotifierProvider`) para no añadir un paso de `build_runner` a un grafo de providers que todavía es pequeño (2 controllers). Es una desviación documentada, no silenciosa — se adopta codegen cuando el número de features lo justifique.
- **`auth`/`onboarding` no hablan con un backend real todavía.** `LocalStubAuthRepository` (ver su docstring) es un adaptador interino: acepta cualquier email válido y no hace red. `OnboardingRepository` (puerto) tampoco tiene implementación concreta — capturar objetivos ocurre antes de autenticarse en el flujo real del producto (Pantalla 3 permite "probar antes de registrarse"), así que enviarlos a `POST /v1/goals` del backend solo tiene sentido una vez exista una sesión de Supabase real. Wiring de `SupabaseAuthRepository`/`ApiGoalsRepository` es el siguiente incremento de integración, no una pieza olvidada.
- **Sin refresh de token automático en `core/network/api_client.dart`.** Depende de la misma sesión de Supabase real que `auth` todavía no tiene. Documentado en el archivo, mismo patrón que el resto del repo (p. ej. `simulations/infrastructure/reality_engine_client.py`'s "no queue yet").
- **`HomePlaceholderScreen` no es la Pantalla 4 real.** Es solo un destino de navegación para que `onboarding`/`auth` sean end-to-end testeables; "El Mapa de Realidades" (con captura de decisión, cards de decisiones activas, bottom nav) es su propio módulo futuro.

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
