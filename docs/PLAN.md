# MatHelp — Plan técnico y de producto

> **Mat**emática + **Help**, y el mate que se comparte.
> Juego de matemática para primaria (6–12), preparado para crecer a secundaria (13–17).
> Stack: **Fitz** + **Fitz LiveViews** + **PostgreSQL**, todo **dockerizado**, **i18n desde el día 1**, **mobile-first**.

---

## 📍 Estado — actualizado 22/08/2026

**Fase actual: F3 — Que aprenda. El slice de NAVEGACIÓN está cerrado (menú
§6.5 + elegir juego + práctica libre); falta el motor adaptativo. F0/F1/F2
cerradas.**

> **Migración a nativo (fitz v0.55 + liveviews v0.50):** los módulos-workaround de
> F0 (`rng`, `fmt`, `cookies`) se borraron y ahora se usan `rand`/`num`/`@cookie`
> nativos; `assets` sirve el manifest como estático (`@server(static_dir=)`) y el
> favicon queda generado. `layout` e i18n (catálogos horneados) se quedan por
> decisión de arquitectura. **MatHelp compila a binario nativo** (`fitz build` →
> distroless en Docker) — el bug de codegen `T?` (FITZ-09) que lo bloqueaba está
> cerrado, junto con cookies cross-module (v0.54) y `Map<Str,Any>.keys()` (v0.55),
> todos encontrados por este dogfooding. Ver `CLAUDE.md` §"Migrado a nativo".

> **F1 — Identidad (cerrada 21/08/2026):** registro/login de familia con
> Argon2id (`hash.password`/`hash.verify`), sesión stateless con JWT en cookie
> `HttpOnly`, alta y selección de perfiles (con PIN opcional, comparado
> server-side), rutas de juego protegidas (redirect a `/login` sin sesión).
> Todo con `<form method="POST">` **nativo, sin una línea de JavaScript**.
> Verificado E2E con `curl` (login, cookie `HttpOnly`, redirect sin sesión,
> PIN, logout, i18n es-AR/en) y con **paridad bit-a-bit `fitz run` ↔ binario
> nativo** (`fitz build` v0.56). Dos hallazgos nuevos de la clase check✓/build✗
> (`FITZ-15`/`FITZ-16`, coerción/inferencia en `match`) anotados en el core con
> repro y workaround aislado en la app.

> **F2 — Primer juego (cerrada 22/08/2026):** el contrarreloj de las cuatro
> operaciones, jugable de punta a punta. Generadores deterministas (`rand.seeded`
> nativo) reproducibles desde `(seed, idx)` — una partida se reconstruye desde
> dos enteros; `Quiz.fitzv` como LiveComponent SSR; cronómetro **server-pushed
> por WebSocket** (`@background` + `spawn(timer(ws))` + `sleep`); persistencia de
> cada respuesta a Postgres apenas ocurre (`@table GameSession` + `Attempt`).
> Todo número por `num.format` (locale), todo texto por `t(locale, k)`.
> Verificado con **tests** (19 `@test`: reproducibilidad, correctitud, división
> exacta, distribución del PRNG sobre 6.000 tiradas) y con un **E2E completo**
> (registro → perfil → `/jugar` → WS con reloj bajando 60→57 → responder →
> feedback → sesión + attempt persistidos), en **paridad bit-a-bit `fitz run` ↔
> binario nativo** contra `fitz 0.58`. Este dogfooding cerró **5 hallazgos del
> core**: FITZ-01(a) `rand`/`num` cross-módulo en codegen (bloqueaba el binario
> nativo del juego), FITZ-18 `getrandom` no inyectado con auth+rand global,
> FITZ-17 (checker no cazaba bloque `{}` sin `return`), FITZ-19 (`@ws` con `?` +
> fall-through) y FITZ-20 (tests de `tests/` importando módulos de `src/`).

> **F3 — Navegación (slice, cerrada 22/08/2026):** el árbol shallow de §6.5
> vivo, data-driven, sin JavaScript. Home de juego con cinco accesos (Jugar ya
> / Desafío / Elegir juego / Práctica libre / Mi progreso); **Elegir juego**
> (`/juegos`) es una grilla filtrada por `profile.grade` desde el catálogo
> `src/juegos.fitz` (contrarreloj jugable, el resto bloqueado por grado o
> "próximamente" F4/F5 — sumar un juego es una fila); **Práctica libre**
> (`/practica` → tema → dificultad → `/jugar/practica`) **sin reloj ni puntaje**,
> reusando el `Quiz.fitzv` en modo práctica (tema fijo + banda de dificultad que
> mapea a un grado efectivo del generador vía `gen_for`), con `GameSession.mode
> = "practica"` y la config viajando al `@ws` por cookie (el `@ws` no acepta
> path params). Desafío del día y Mi progreso quedan como placeholder amable —
> dependen del motor adaptativo, que es el resto de F3. Verificado con **8
> `@test` nuevos** (banda→grado, `gen_for` timed idéntico a `gen_mix`, tema fijo
> reproducible, temas por grado) y **paridad bit-a-bit `fitz run` ↔ binario
> nativo**: rutas SSR idénticas (módulo line-endings) y práctica live por WS con
> el mismo `mode="practica"` + attempt correcto en Postgres, sin regresión del
> contrarreloj. Verificado contra `fitz 0.58.0` local; el Docker pasa a
> `fitz:v0.58.1` (release aditivo — MatHelp no ejercita la feature nueva de
> v0.58.1, su `gen_arith` mantiene el `RandGen` local).

### ✅ Hecho

| Qué | Dónde | Verificado con |
|---|---|---|
| Identidad visual (logo, paleta, lockup) | `brand/` | Render a 16–128 px |
| PRNG determinístico | `src/rng.fitz` | 18 tests, incluida distribución sobre 6.000 tiradas |
| Formateo por locale (es-AR / en) | `src/fmt.fitz` | 15 tests: decimales, %, dinero, negativos |
| Cookies (leer / setear / borrar) | `src/cookies.fitz` | `Set-Cookie` correcto vía curl |
| i18n: catálogos JSON → módulos Fitz | `locales/*.json`, `tools/gen_i18n.py`, `src/cat_*.fitz` | 61 claves × 2 locales, sin faltantes |
| Traducción + resolución de locale | `src/i18n.fitz` | Cambio de idioma end-to-end |
| Shell mobile-first + dark mode | `src/layout.fitz`, `src/brand.fitz` | Capturas a 390 px, light y dark |
| Assets como rutas | `src/assets.fitz` | `/favicon.svg` y `/manifest.webmanifest` → 200 |
| Footer permanente con links a los repos | `src/brand.fitz` | En todas las pantallas |
| Home + cambio de idioma + placeholders | `src/main.fitz` | `curl` sobre las 5 rutas |
| Esquema de base completo | `migrations/0001_init.sql` | 7 tablas con FK, índices y CHECK |
| Docker (app + Postgres) | `Dockerfile`, `docker-compose.yml` | Pendiente de correr en tu máquina |
| Scripts de Windows | `start.bat`, `stop.bat`, `logs.bat`, `reset.bat` | Pendiente de correr en tu máquina |
| **F1** · Modelos de auth (`@table Family` + `Profile`) | `src/models.fitz` | `fitz check` + queries reales contra Postgres |
| **F1** · Registro/login de familia (Argon2id + JWT + cookie `HttpOnly`) | `src/auth.fitz` | `curl` E2E + paridad `run`↔binario |
| **F1** · Alta y selección de perfiles (con PIN server-side) | `src/perfiles.fitz` | `curl` E2E (alta, elegir, PIN malo/bueno) |
| **F1** · Rutas de juego protegidas + home según sesión | `src/main.fitz` | `curl` E2E (redirect a `/login` sin sesión) |
| **F1** · 24 claves i18n nuevas (registro/perfiles/PIN) es-AR/en | `locales/*.json`, `src/cat_*.fitz` | `gen_i18n.py` sin faltantes + `lang=en` E2E |
| **F2** · Generadores deterministas + − × ÷ (reproducibles desde seed+idx) | `src/gen_arith.fitz` | 14 `@test` (reproducibilidad, correctitud, división exacta, rangos, distribución) |
| **F2** · Tests del PRNG sembrado (distribución) | `tests/rng.fitz`, `tests/generators.fitz` | `fitz test` 19/19 verde |
| **F2** · Motor de ronda + scoring | `src/engine.fitz` | Puntos por acierto + dificultad |
| **F2** · Render del quiz (prompt, opciones, resumen — i18n + `num.format`) | `src/quiz_view.fitz`, `src/fmt.fitz` | E2E: opciones formateadas por locale |
| **F2** · `Quiz.fitzv` (LiveComponent: `answer` + `tick`) | `src/Quiz.fitzv`, CSS en `src/brand.fitz` | Estado en el component store |
| **F2** · `/jugar` live + `@ws /live/quiz` + cronómetro por WS + persistencia | `src/live_game.fitz` | E2E WS (reloj 60→57, answer, sesión + attempt en Postgres) |
| **F2** · `@table GameSession` + `Attempt` | `src/models.fitz` | Match exacto con `0001_init.sql` + writes reales |
| **F2** · 3 claves i18n nuevas (jugar de nuevo, de, segundos) | `locales/*.json`, `src/cat_*.fitz` | 89 claves × 2 locales, sin faltantes |
| **F3-nav** · Catálogo de juegos data-driven (grilla por grado) | `src/juegos.fitz` | `fitz check` + grilla renderizada (1 jugable + 5 lock + 7 soon) |
| **F3-nav** · Home de juego §6.5 (5 accesos) + placeholders desafío/progreso | `src/main.fitz` | E2E: 5 links del menú, placeholder i18n |
| **F3-nav** · Elegir juego (`/juegos`) + Práctica libre (`/practica` → tema → dificultad) | `src/menu.fitz` | E2E: temas del grado, 3 bandas, cookie+redirect |
| **F3-nav** · Práctica live (Quiz en modo práctica, sin reloj ni puntaje) | `src/live_game.fitz`, `src/Quiz.fitzv`, `src/quiz_view.fitz` | E2E WS: `mode='practica'` + attempt correcto en Postgres, sin regresión del timed |
| **F3-nav** · `gen_for` + `grade_for_band` + `temas_practica` + `tema_valido` | `src/gen_arith.fitz` | 8 `@test` (banda→grado, timed≡gen_mix, reproducible, temas por grado) |
| **F3-nav** · 21 claves i18n nuevas (juegos, temas, bandas, próximamente) | `locales/*.json`, `src/cat_*.fitz` | 110 claves × 2 locales, sin faltantes |

**F0: 33 tests** contra `fitz 0.47.0`. **F1: E2E `curl` + paridad `run`↔binario**
contra `fitz 0.56.0`. **F2: 19 `@test` + E2E completo (HTTP + WS + persistencia) +
paridad bit-a-bit `fitz run` ↔ binario nativo** contra `fitz 0.58.0`.
**F3-nav: 27 `@test` (8 nuevos de práctica) + E2E de navegación + práctica live
por WS + paridad bit-a-bit `run` ↔ binario** contra `fitz 0.58.0` (Docker en
`fitz:v0.58.1`).

### 🔜 Lo que sigue

| Fase | Qué falta | Bloqueado por |
|---|---|---|
| **F3-nav** ✅ | menú §6.5 + elegir juego (grilla por grado) + práctica libre (tema+dificultad) | — |
| **F3-motor** ← acá vamos | `mastery` + Elo-lite, repaso espaciado, racha diaria, mate-progreso, desafío del día (10 del mix adaptativo) | — |
| **F4** | V/F, completá el hueco, teclado numérico propio, escalera de tablas, el kiosco, fracciones visuales | F2 |
| **F5** | Panel del padre con reportes | F3 |
| **F6** | Reanudar partida, accesibilidad, sonido opcional, instalable | F2 |
| **F7** | Secundaria (13–17) | F4 |

### 🐛 Hallazgos nuevos al dockerizar

Tres cosas que solo aparecieron al construir la imagen — ninguna se veía en desarrollo:

1. **La imagen oficial `ghcr.io/thegreekman76/fitz` no trae `git`**, así que no puede resolver dependencias `{ git = ... }` adentro del container. Resuelto con una etapa `vendor` que clona aparte y una dependencia `{ path = ... }` vía `fitz.docker.toml`.

2. **`fitz check` y `fitz run` aceptan `Str + Any`, `fitz build` no.** Un `let chars = []` infiere `List<Any>` y el codegen rechaza la concatenación. Anotación explícita y listo — pero es un error que solo aparece al compilar.

3. **Bug de codegen: las funciones que devuelven `T?` compilan mal.** Emite `return ()` en vez de `return None`. Afecta también a `flv_cookie` **dentro de fitz-liveviews**, así que no se puede esquivar desde la app. Detalle y repro de 20 líneas en `docs/BUG-fitz-option-codegen.md` → candidato a `FITZ-09`.

Los tres son de la misma familia: **cosas que andan interpretadas y explotan compiladas** (T2). Este proyecto ya encontró tres en una tarde.

### ⚠️ Deuda anotada

- ~~**Sin auth todavía**~~ **CERRADO en F1**: sesión JWT + cookie `HttpOnly`, rutas de juego protegidas con redirect a `/login`.
- **`secure: false` en la cookie de sesión**: MatHelp corre en la red de casa sin HTTPS (con `secure:true` el browser no manda la cookie sobre http). Activar `secure` detrás de un proxy TLS antes de exponerlo — junto con `JWT_SECRET` real.
- **El esquema sigue creándolo el SQL init**, no `fitz db migrate`: `models.fitz` modela solo `Family` + `Profile` (lo que usa F1). El paso a `fitz db diff/migrate` se hace cuando F2 sume el resto de los `@table`.
- **`JWT_SECRET` con valor por defecto** en `.env.example`. Cambiarlo antes de exponerlo fuera de la red de casa.
- **El esquema lo crea Postgres al primer arranque** (`docker-entrypoint-initdb.d`), no `fitz db migrate`. Desde F1 pasa a migraciones de verdad.
- **`fitz_liveviews` pineado a `v0.47.0`** por git. Si trabajás con el repo al lado, cambiá la línea en `fitz.toml` por `path`.
- **El contenedor corre el intérprete, no el binario nativo.** Se pierde el ~9x de performance y el runtime distroless. No es una elección: es el bug de codegen del punto 3. La versión compilada está en el `Dockerfile`, comentada y lista para descomentar cuando se arregle.
- **`fitz.docker.toml` duplica `fitz.toml`.** Si tocás las dependencias, hay que reflejarlo en los dos. Desaparece si `fitz build` acepta un override de dependencias por CLI.

---

## 0. Decisiones ya tomadas

| Decisión | Elegido |
|---|---|
| Alcance MVP | Primaria completa (6–12), arquitectura lista para secundaria |
| Usuarios | Cuenta de familia (padre/madre) + perfiles de hijos + panel de reportes |
| Idiomas | `es-AR` (base) + `en`, arquitectura multi-locale |
| Render | 100% SSR con LiveViews (WebSocket diffs). Sin offline por ahora |
| Datos | PostgreSQL vía el ORM de Fitz |
| Infra | Docker + docker-compose (app + db) |
| UI | Mobile-first (celu y tablet primero, PC después) |
| Marca | Logo MatHelp propio + footer permanente "Hecho con Fitz y Fitz LiveViews" |

---

## 1. Análisis de la tecnología — qué me da y qué me falta

Cloné y leí **`Thegreekman76/fitz` v0.47.0** y **`Thegreekman76/fitz-liveviews` v0.47.0**. Esto no sale de los blogs: sale del código y los docs del repo.

### 1.1 Lo que juega a favor (y bastante)

| Necesidad de MatHelp | Qué lo resuelve | Dónde está |
|---|---|---|
| UI reactiva sin build de JS | `.fitzv` con `state {}` / `event ...()` / `<template>` + diff por WS | `examples/counter/src/Counter.fitzv` |
| Cronómetro de partida | `@background` + `spawn(tick(ws))` + `sleep(1000)` + `ws.send(flv_frame(...))` | `docs/liveviews.md:434` |
| Login de padres | Argon2id (`hash.password` / `hash.verify`) + JWT + cookie `HttpOnly` | `examples/admin/src/auth.fitz` |
| Persistencia | ORM con `@table`, `@has_many`, `.where(closure)`, `db.transaction` | `boilerplates/api-orm-full` |
| Migraciones | `fitz db diff` / `migrate` / `rollback` / `status` | `docs/guide.md:13070` |
| Docker | `fitz docker init` genera Dockerfile multi-stage + compose con Postgres + healthcheck | `src/docker.rs` |
| i18n | Patrón `t(locale, "key")` + cookie de idioma + `<html lang>` | `examples/admin/src/i18n.fitz` |
| Componentes UI | 38 componentes (`button`, `card`, `progress_bar`, `modal`, `toast`, `tabs`, `stepper`…) | `docs/ui-components.md` |
| Dark mode | Tokens `--flv-*` + `theme_boot_script`, sin viajar por el WS | `docs/styling.md` |
| Tests | `@test` + `assert_eq` en `tests/*.fitz` | `docs/guide.md:10321` |

### 1.2 Los ocho huecos reales, y cómo los tapo

Esto es lo importante del análisis. Cada uno **bloquearía** el proyecto si lo descubrimos a mitad de camino.

**① No existe `random` en la stdlib de Fitz.**
Un juego de matemática es, esencialmente, un generador de números aleatorios. No hay `rand`, `random` ni nada equivalente — verificado contra `builtin_names()` y la lista de módulos del LSP.
→ **Solución:** `src/rng.fitz`, un **xorshift32 propio** (determinístico, ~15 líneas). Semilla por partida derivada de `Uuid.v4()` + `DateTime.now().timestamp()`.
→ **Beneficio inesperado:** al ser determinístico, en la base guardo `seed + índice` en vez del ejercicio completo. Una partida entera se reconstruye desde 2 enteros, y el panel del padre puede "rejugar" exactamente lo que vio el chico.

**② No hay servido de archivos estáticos.** Cero. No hay `static/`, ni `@static`, ni `ServeDir`.
→ **Solución: assets como rutas.** `Response` ya soporta `content_type` y `body_bytes: Bytes?`, así que:
```fitz
@get("/favicon.svg")
fn favicon() -> Response => Response {
    content_type: "image/svg+xml",
    headers: { "Cache-Control": "public, max-age=604800" },
    body: mathelp_mark_svg(),
}
```
Lo mismo para `/manifest.webmanifest` (→ instalable en el celu) y, si sumamos sonidos, `bytes_from_b64` + `body_bytes`. El logo va **SVG inline** en el shell, así que no cuesta ni un request.

**③ El parser del diff rechaza `<script>` y `<style>` dentro del root de la LiveView.**
→ **Solución:** todo el CSS va en el `<head>` del shell (fuera del nodo diffeado) o en `<style scoped>` del `.fitzv` (que el compilador extrae). Ningún `<style>` suelto adentro del `id="root"`.

**④ `live_layout()` tiene el `<head>` hardcodeado** (título fijo "Fitz LiveView", sin viewport configurable ni meta propias).
→ **Solución:** no uso `live_layout` — uso **`app_shell(title, lang, head_extra, …)`**, que ya expone el head. Lo envuelvo en un `game_layout(...)` propio que le inyecta `viewport-fit=cover`, `theme-color`, `apple-mobile-web-app-capable`, el manifest y el favicon. Un solo lugar para tocar.

**⑤ Fitz no tiene API de filesystem.** Solo `load_env()`. **No puedo leer catálogos JSON de i18n en runtime.**
→ **Corrijo lo que habíamos hablado:** los catálogos **no** pueden ser JSON leídos en caliente. Pero no perdemos el formato amigable para traductores:
- Fuente de verdad: `locales/es-AR.json`, `locales/en.json` (editables por cualquiera, diffeables en git).
- `tools/gen_i18n.py` los compila a `src/i18n/cat_es_ar.fitz` y `cat_en.fitz` (un `match` sobre la clave).
- Un `@test` verifica que **ninguna clave falte en ningún locale** — el CI rompe si alguien agrega texto sin traducir.

**⑥ Los format specs no conocen locale.** ~~Y solo funcionan en `fitz run`.~~
**Corregido tras la auditoría en repo:** los specs **sí compilan** en `fitz build` — la tabla de `docs/guide.md:1266` está desactualizada. La limitación real que queda es que el separador de miles está **hardcodeado estilo inglés**: en es-AR necesitamos `1.234,5`, en en-US `1,234.5`.
→ **Solución:** `fmt.fitz` propio con `fmt_num` / `fmt_pct` / `fmt_money(locale, x)`. **Regla:** ningún número crudo en la UI, nunca. Siempre vía `fmt.*`.

**⑦ El estado de los componentes vive en memoria del proceso, sin eviction ni persistencia.**
→ **Solución:** `instance_id = Uuid.v4()` por socket (aísla las partidas entre chicos), y **cada respuesta se persiste a Postgres apenas ocurre** — la memoria es caché, no fuente de verdad. Si el server se reinicia a mitad de partida, se pierde la ronda en curso y nada más.

**⑧ `.preload()` en `fitz run` es un no-op SILENCIOSO** — no tira error: devuelve las relaciones vacías. Es peor que fallar. Además `.is_in([...])` exige lista literal, y no hay ENUM nativo de Postgres.
→ **Solución:** joins explícitos en `db_queries.fitz` (nunca `preload` en código que corra interpretado); `.is_in` con lista calculada → `db.query(... = ANY($1))` aislado en ese mismo módulo; enums como `Str` + `@check_constraint`.

### 1.3 Buenas noticias (auditoría contra el repo, no contra los docs)

Tres cosas que la documentación decía que no se podían y **sí se pueden**. Cada una borra un workaround entero:

- **`<form method="POST">` nativo funciona** — `@post` ya acepta `form-urlencoded`. El login de MatHelp sale **sin una línea de JavaScript**, contra lo que dice el comentario de `examples/admin/src/auth.fitz`.
- **Los format specs sí compilan en `fitz build`.** La tabla de `docs/guide.md:1266` está desactualizada. No hay que evitarlos: solo falta el locale.
- **`DataGrid` ya colapsa a cards abajo de 640 px.** El panel del padre en el celu sale gratis.

Moraleja para el resto del proyecto: **verificar contra el código, no contra los docs.** Los docs de un proyecto que se mueve rápido van atrás.

### 1.4 Regla de aislamiento — workarounds fáciles de borrar

Cada limitación vive **detrás de un módulo con la firma que va a tener la solución oficial**. El día que llegue, migrar es borrar un archivo y cambiar un import — no refactorizar la app.

| Módulo | Envuelve | Cuando llegue… | Migración |
|---|---|---|---|
| `rng.fitz` | xorshift32 con la firma de `rand.seeded()` | módulo `rand` en core | borrar archivo, cambiar import |
| `cookies.fitz` | `set_cookie` / `read_cookie` | `@cookie` + `Response.cookies` | reemplazar 2 funciones |
| `fmt.fitz` | `fmt_num` / `fmt_pct` / `fmt_money(locale, x)` | `num.format(x, locale:)` | reemplazar el cuerpo |
| `i18n.fitz` + `cat_*.fitz` | `t(locale, key)` sobre catálogos compilados | `fs.read()` | cambiar solo el loader |
| `assets.fitz` | un `@get` por archivo | `static_dir` en `@server` | borrar las rutas |
| `db_queries.fitz` | joins manuales + `ANY($1)` crudo | `preload` en intérprete, `.is_in(var)` | reemplazar por ORM |
| `game_layout.fitz` | wrapper sobre `app_shell` | `live_layout_with` | opcional, ya está bien |

`cookies.fitz` es el más importante de los siete: **un parser de cookies mal escrito es un agujero de seguridad**, y un solo lugar es auditable.

### 1.5 Riesgos que asumo conscientemente

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Sin reconnect con replay de estado (deuda declarada del framework) | Si el celu pierde señal, se corta la partida | Persistir cada respuesta al toque + pantalla "reanudar partida" |
| Latencia del WS en cada tap | En 3G rural puede sentirse lento | Feedback optimista en CSS (`:active`) + ronda pre-generada; si molesta, migrar el juego a target WASM |
| Ecosistema chico | No hay libs de terceros | Todo lo que necesitamos ya está en `fitz_liveviews.ui.*` |
| Bugs del lenguaje | Sos vos el que los arregla 🙂 | Cada fase deja tests `@test`; los hallazgos van como issues al repo de Fitz |

---

## 2. Arquitectura

```
┌──────────────── docker compose ────────────────┐
│                                                │
│  ┌───────────────┐        ┌─────────────────┐  │
│  │  mathelp-app  │◄──────►│  mathelp-db     │  │
│  │  binario Fitz │  ORM   │  postgres:16    │  │
│  │  @server(3000)│        │  volumen pgdata │  │
│  └───────┬───────┘        └─────────────────┘  │
└──────────┼─────────────────────────────────────┘
           │ HTTP + WebSocket (mismo puerto)
     ┌─────▼─────┐
     │ Celular / │  SSR + diffs. ~5 KB de JS inline. Sin build.
     │  tablet   │
     └───────────┘
```

**Flujo de una partida**

1. `GET /jugar/{modo}` → shell + `live_embed` con el primer ejercicio ya renderizado (sin flash).
2. El browser abre `WS /live/juego`; manda la cookie `HttpOnly` sola → el socket resuelve perfil y locale.
3. `spawn(timer_tick(ws))` arranca el cronómetro (1 push por segundo).
4. Cada tap manda `data-flv-click="responder"` + `data-flv-value-opcion="56"`.
5. El handler corrige, actualiza `mastery`, genera el siguiente ejercicio con el PRNG y devuelve el diff.
6. Al terminar: `INSERT` de la sesión + resumen + medallas.

---

## 3. Modelo de datos (PostgreSQL)

```fitz
@table("families")                    // la cuenta que administra el padre/madre
type Family {
    @primary id: Int = 0
    email: Str = ""
    @hidden password_hash: Str = ""
    display_name: Str = ""
    locale: Str = "es-AR"
    @db_default created_at: DateTime
    @has_many("Profile", via="family_id", on_delete="cascade") profiles: List<Profile> = []
}

@table("profiles")                    // cada hijo/a
type Profile {
    @primary id: Int = 0
    @belongs_to("Family", on_delete="cascade") family_id: Int = 0
    name: Str = ""
    avatar: Str = "mate"              // clave de avatar SVG inline
    birth_year: Int = 0               // edad derivada → nunca desactualizada
    grade: Int = 0                    // 1..7 primaria
    locale: Str = "es-AR"
    @hidden pin: Str = ""             // opcional, 4 dígitos, para que no se metan entre hermanos
    daily_goal: Int = 10              // ejercicios/día
    @db_default created_at: DateTime
}

@table("sessions")                    // una partida
type GameSession {
    @primary id: Int = 0
    @belongs_to("Profile", on_delete="cascade") profile_id: Int = 0
    mode: Str = ""                    // quiz | truefalse | fillgap | numpad | story | ...
    topic_code: Str = ""
    level: Int = 1
    seed: Int = 0                     // ← reproduce la partida entera
    started_at: DateTime
    ended_at: DateTime?  = null
    total: Int = 0
    correct: Int = 0
    score: Int = 0
    duration_ms: Int = 0
}

@table("attempts")                    // una respuesta
type Attempt {
    @primary id: Int = 0
    @belongs_to("GameSession", on_delete="cascade") session_id: Int = 0
    @belongs_to("Profile", on_delete="cascade") profile_id: Int = 0
    skill_code: Str = ""              // "mult.tabla.7", "frac.equiv", ...
    idx: Int = 0                      // índice dentro del seed
    prompt: Str = ""                  // texto canónico, para el reporte del padre
    expected: Str = ""
    given: Str = ""
    correct: Bool = false
    ms: Int = 0
    difficulty: Int = 1
    @db_default created_at: DateTime
}

@table("mastery")                     // dominio por destreza (motor adaptativo)
@unique(profile_id, skill_code)
type Mastery {
    @primary id: Int = 0
    @belongs_to("Profile", on_delete="cascade") profile_id: Int = 0
    skill_code: Str = ""
    rating: Float = 800.0             // Elo-lite del chico en esa destreza
    seen: Int = 0
    hits: Int = 0
    streak: Int = 0
    avg_ms: Int = 0
    last_seen_at: DateTime?  = null
    due_at: DateTime? = null          // repaso espaciado
}

@table("awards")                      // medallas y logros
@unique(profile_id, code)
type Award {
    @primary id: Int = 0
    @belongs_to("Profile", on_delete="cascade") profile_id: Int = 0
    code: Str = ""                    // "racha7", "tablas_completas", "primer_mate"
    @db_default earned_at: DateTime
}

@table("streaks")                     // racha diaria
@unique(profile_id, day)
type Streak {
    @primary id: Int = 0
    @belongs_to("Profile", on_delete="cascade") profile_id: Int = 0
    day: Date
    exercises: Int = 0
    goal_met: Bool = false
}
```

El **currículum no va en la base**: vive en `src/curriculum.fitz` como código, para que el compilador valide que todo `skill_code` usado existe. La base guarda solo el `code`.

---

## 4. i18n desde el minuto cero

**Reglas duras**

1. Ningún string visible se escribe en el template. Siempre `t(locale, "clave")`.
2. Todo número que se muestre pasa por `fmt_num(locale, x)` — la coma decimal argentina no es negociable.
3. El `locale` viaja como cookie (`mathelp_lang`, 1 año) y se lee tanto en el `@get` como en el `@ws` con `@header(name="cookie")`.
4. `<html lang="{locale}">` siempre, por accesibilidad y por el lector de pantalla.
5. Un `@test` falla el build si a un locale le falta una clave.

**Lo que el i18n tiene que cubrir además del texto**

| Aspecto | es-AR | en |
|---|---|---|
| Decimal / miles | `1.234,5` | `1,234.5` |
| Moneda (juego del kiosco) | `$ 1.250` | `$1,250.00` |
| División | `÷` y también la "casita" (algoritmo argentino) | long division |
| Multiplicación | `×` | `×` / `*` |
| Nombres de grado | 1º a 7º grado | 1st–7th grade |
| Contexto de los problemas | kiosco, colectivo, empanadas, figuritas | store, bus, cookies, cards |
| Hora | 24 h + "y cuarto / menos cuarto" | 12 h AM/PM |

Ese último punto es el que hace la diferencia: **los enunciados con historia también se localizan**, no solo los botones. `es-AR` habla de figuritas y del 60; `en` habla de otra cosa.

---

## 5. Currículum — primaria argentina (6 a 12 años)

Organizado por edad, con los `topic_code` que usa el motor. Alineado a los NAP. Cubre los **cinco ejes NAP** en toda la progresión: número y operaciones, **medida**, **geometría**, **proporcionalidad**, y **estadística/probabilidad** — no solo aritmética.

| Edad | Grado | Ejes | `topic_code` |
|---|---|---|---|
| 6 | 1º | Conteo hasta 100, comparar/ordenar, suma/resta sin llevar, series, reconocer figuras, medida informal | `num.conteo`, `num.comparar`, `add.simple`, `sub.simple`, `pat.series`, `geo.figuras`, `med.informal` |
| 7 | 2º | Hasta 1.000, ±con llevada, doble/mitad, inicio de tablas, valor posicional (centena), figuras y cuerpos, calendario y dinero simple | `add.llevada`, `sub.prestada`, `num.dobles`, `mult.tabla.2`/`.5`/`.10`, `num.posicional`, `geo.cuerpos`, `med.tiempo`, `dec.dinero` |
| 8 | 3º | Tablas completas, división exacta, valor posicional (10.000), fracciones de uso social (medio/cuarto), figuras y ángulo recto, medida amplia | `mult.tabla.*`, `div.exacta`, `num.posicional`, `frac.parte`, `geo.figuras`, `geo.angulos`, `med.longitud`, `med.capacidad`, `med.peso`, `med.tiempo` |
| 9 | 4º | División con resto, fracciones simples y comparación, perímetro, dinero, numeración grande (decenas/centenas de mil), clasificar figuras y cuerpos, capacidad/peso/tiempo | `div.resto`, `frac.parte`, `frac.comparar`, `geo.perimetro`, `dec.dinero`, `num.grande`, `geo.figuras`, `geo.cuerpos`, `med.capacidad`, `med.peso`, `med.tiempo` |
| 10 | 5º | Fracciones equivalentes y suma, decimales (± y ×), área y ángulos, superficie/SIMELA, proporcionalidad directa (inicio) | `frac.equiv`, `frac.suma`, `dec.suma`, `dec.mult`, `geo.area`, `geo.angulos`, `med.superficie`, `prop.directa` |
| 11 | 6º | Porcentaje, proporcionalidad directa e inversa, potencias, múltiplos/divisores/primos/mcd/mcm, volumen, operatoria plena de fracciones/decimales, estadística (gráficos, promedio) | `pct.basico`, `prop.directa`, `prop.inversa`, `pot.cuadrados`, `num.mcd_mcm`, `num.primos`, `geo.volumen`, `frac.mult`, `dec.mult`, `est.grafico`, `est.promedio` |
| 12 | 7º | Enteros (4 operaciones), operatoria completa de racionales, ecuaciones simples, razones/escala/%, geometría (área/volumen/construcciones), estadística y probabilidad | `ent.suma`, `ent.mult`, `frac.div`, `dec.div`, `alg.ecuacion1`, `prop.razon`, `prop.escala`, `geo.construccion`, `est.promedio`, `prob.simple` |

**Enfoque.** El norte pedagógico es **resolución de situaciones problemáticas** (ver §6.6) — el problema antes que el cálculo mecánico —, alineado a NAP, en todos los grados.

**Cobertura por eje (estado).** F2 cerró **número y operaciones**. Los ejes **medida** (`med.*`), **geometría** (`geo.*`), **proporcionalidad** (`prop.*`) y **estadística/probabilidad** (`est.*`/`prob.simple`) están mapeados por grado arriba pero **aún sin generador** — entran en F4/F5 (ver §6). Los `topic_code` ya reservan el nombre para que el motor y el `mastery` los reconozcan cuando lleguen.

**Nota de diseño:** la edad **sugiere** el punto de entrada, no lo impone. Un chico de 9 que arrasa con las tablas ve división con resto sin pedir permiso; uno que traba en la resta con llevada baja solo. La edad es la semilla, el `rating` de `mastery` es el que manda.

**Para tu hija de 9 (4º grado), el MVP le sirve el día 1:** división con resto, tablas a fondo, fracciones simples, perímetro y plata.

---

## 6. Los juegos

Todos pensados para **pulgar en celular**: botones grandes, nada de arrastrar, nada que dependa de `hover`.

| # | Juego | Mecánica | Temas | Fase |
|---|---|---|---|---|
| 1 | **Contrarreloj** | 60 s, opción múltiple, 4 botones grandes | todos | F2 |
| 2 | **Verdadero o Falso** | 2 botones gigantes — el más fácil de usar en el colectivo | todos | F4 |
| 3 | **Completá el hueco** | `7 × __ = 56` con **teclado numérico propio** en pantalla | todos | F4 |
| 4 | **Escalera de tablas** | Subís un escalón por acierto, caés dos por error | `mult.*` | F4 |
| 5 | **El kiosco** | Comprás, calculás el vuelto, con precios en pesos | `dec.dinero`, `add`, `sub` | F4 |
| 6 | **Fracciones a la vista** | Pizza/barra en SVG, elegís la fracción | `frac.*` | F4 |
| 7 | **¿Qué hora es?** | Reloj de agujas en SVG | `med.tiempo` | F5 |
| 8 | **Problemas con historia** | Enunciado corto y localizado, respuesta numérica | 4º–7º | F5 |
| 9 | **Geometría** | Figura en SVG, calculás perímetro/área | `geo.*` | F5 |
| 10 | **Práctica libre** | Elegís tema y nivel, sin reloj ni puntaje | todos | F3 |
| 11 | **Desafío del día** | 10 ejercicios del mix adaptativo, alimenta la racha | todos | F3 |

**Motivación (sin volverlo un casino):**
- El progreso de la ronda es **un mate que se llena** — la barra es el logo. Cada acierto es una cebada.
- Racha diaria con meta configurable por el padre (default 10 ejercicios).
- Medallas por dominio real, no por tiempo de pantalla: "tablas completas", "10 días seguidos", "fracciones sin errores".
- **Sin vidas, sin timers de espera, sin nada que empuje a jugar más de la cuenta.** El error muestra el procedimiento correcto, no un cartel rojo.

---

## 6.5 Navegación / IA de juego (F3–F5)

> **Estado (22/08/2026): implementado en el slice F3-navegación.** El árbol de
> abajo está vivo (`/`, `/juegos`, `/practica` → tema → dificultad → juego). Lo
> pendiente son los nodos que dependen del motor adaptativo: **Desafío del día**
> (10 del mix) y **Mi progreso** (mate-progreso + medallas + racha), hoy
> placeholder. La grilla de juegos ya filtra por grado; solo el **contrarreloj**
> es jugable (los demás llegan en F4/F5).

**Decisión de diseño:** para un chico de 6–12 NO se arma un árbol profundo
`grado → nivel → juego` (mucho tap, se pierde — anti-patrón para esa edad). El
menú se **aplana** apoyándose en lo que la app ya sabe:

- **El grado NO se elige por juego** → viene del perfil (F1). Solo *filtra* qué
  juegos/temas aparecen y *escala* los rangos del generador (`ops_for_grade`,
  `add_max`, `mul_max`, que ya están en `gen_arith`).
- **El nivel NO se elige (casi nunca)** → es **adaptativo** (`mastery`/Elo-lite
  de F3): el juego sube/baja la dificultad solo. El único lugar con selector de
  nivel explícito es **Práctica libre**.
- **El juego SÍ se elige**, pero de una grilla **ya filtrada al grado**.

Árbol real (shallow: 2 taps al juego):

```
Home de juego  (sabe: perfil → grado, mastery → nivel)
├── ▶  Jugar ya          → Contrarreloj, mix adaptativo        (1 tap)
├── 🎯 Desafío del día    → 10 del mix, alimenta la racha       (1 tap)
├── 🎮 Elegir juego       → grilla de juegos DEL GRADO          (2 taps)
│      └── [juego]        → arranca en nivel adaptativo
├── 📚 Práctica libre     → tema (del grado) → dificultad → jugar (3 taps, único con nivel)
└── 🏅 Mi progreso        → mate-progreso, medallas, racha
```

**Elegir juego (por grado):** la grilla viene filtrada por `profile.grade`. Los
juegos que aún no le tocan salen bloqueados con el grado que los abre. Qué grilla
ve cada grado:

| Grado | Cartas visibles |
|---|---|
| 1º | Contrarreloj · V/F · Práctica |
| 2º–3º | + Escalera de tablas · ¿Qué hora es? · Completá el hueco |
| 4º | + El kiosco · Fracciones · Problemas con historia |
| 5º | + Geometría (perímetro/área) |
| 6º | + Porcentaje · Volumen |
| 7º | + Enteros · Ecuaciones |

**El nivel dentro de un juego es adaptativo, no un menú.** Al tocar un juego NO
aparece "Nivel 1 / 2 / 3": arranca directo y el motor elige la dificultad según
el `mastery` del chico (70% zona de desarrollo próximo, 20% repaso, 10% un
escalón arriba — ver §7). El nivel se *muestra como progreso*, nunca como picker.

**Práctica libre — el ÚNICO lugar con nivel explícito:** tema (solo los del
grado) → dificultad en 3 bandas (😊 fácil / 😐 medio / 😤 difícil), que mapean a
rangos de `difficulty` (1–2 / 3 / 4–5) del generador.

**Cómo se mapea al modelo que ya existe (nada de un menú por combinación):**
- *"Por grado"* = un `if grade >= N` sobre la grilla + los rangos por grado de
  `gen_arith`. Un solo menú + un filtro.
- *"Por nivel"* = `difficulty: 1..5` del generador (ya existe) + el `rating` de
  `mastery` (F3) que elige cuál servir. Las 3 bandas de Práctica libre son un
  atajo a esos rangos.
- *"Por juego"* = un `topic_code` + un `.fitzv` + una fila `{juego, min_grado,
  icono}`. El menú es **data-driven**: el filtro sale gratis.

O sea: **un esqueleto de menú, tres filtros** (grado del perfil, nivel del
mastery, disponibilidad del juego) — no se mantiene un menú por combinación.

---

## 6.6 Situaciones problemáticas (razonamiento, tema transversal)

No es un juego más: es **el eje que entrena el razonamiento** (leer, modelar,
decidir *qué* operación aplicar), que las tablas y el cálculo suelto no dan. Es
una competencia NAP central, así que en MatHelp es un **tema transversal desde 1º
grado**, no un juego tardío. Escala con el grado sin cambiar de mecánica:

| Grado | Situación típica (es-AR) | Modela |
|---|---|---|
| 1º | "Tenés 5 figuritas y te regalan 3. ¿Cuántas tenés?" | suma simple |
| 2º | "Había 12 empanadas y se comieron 5. ¿Cuántas quedan?" | resta con contexto |
| 3º | "Cada colectivo lleva 40 personas. ¿Cuántas en 3 colectivos?" | multiplicación |
| 4º | "60 figuritas para 5 amigos, en partes iguales. ¿Cuántas a cada uno?" | división · dinero |
| 5º | "La pizza tiene 8 porciones y comiste 3/8. ¿Cuánto queda?" | fracciones |
| 6º | "Una remera de $2.000 tiene 20% de descuento. ¿Cuánto pagás?" | porcentaje |
| 7º | "Si 3 lápices cuestan $600, ¿cuánto cuestan 7?" | proporcionalidad / razón |

**Diseño (`gen_story`):** enunciados **templados y localizados** — el generador
elige una plantilla del grado (`"Tenés {a} {objeto} y te regalan {b}…"`), llena
los operandos con el PRNG determinista (mismo `(seed, idx, grade)` ⇒ mismo
problema, reproducible como el resto) y deriva la respuesta de la operación. El
**contexto se localiza, no solo los botones** (es-AR: figuritas, empanadas,
colectivo, kiosco; en: su equivalente) — es el punto de §4. Un banco de
plantillas por grado × tema, con distractores del mismo estilo que `gen_arith`.

**Dónde aparece:**
- Como **juego dedicado** ("Situaciones problemáticas" / "Problemas con historia")
  en la grilla, desde 1º.
- **Mezclado en el Desafío del día** y en Práctica libre (tema propio), para que
  el razonamiento no quede en un rincón sino en el mix diario.

En la grilla por grado, súmese a la fila de cada grado desde 1º (con contextos de
suma/resta) y hasta 7º (proporcionalidad). Va a `mastery` con sus propios
`skill_code` (`problema.suma`, `problema.division`, `problema.porcentaje`…), así
el motor adaptativo también gradúa el razonamiento, no solo el cálculo.

---

## 7. Motor adaptativo

```
mastery.rating   ← Elo-lite por destreza (arranca en 800)
item.difficulty  ← 1..5, definida por el generador

acierto  → rating += K × (1 − esperado)
error    → rating -= K × esperado
esperado  = 1 / (1 + 10^((dif×200 + 400 − rating) / 400))
```

Selección del próximo ejercicio: **70 % en zona de desarrollo próximo** (dificultad ≈ rating), **20 % repaso** (destrezas con `due_at` vencido), **10 % desafío** (un escalón arriba). El repaso espaciado usa intervalos 1 / 3 / 7 / 16 / 35 días, reiniciados ante error.

Además, el tiempo de respuesta cuenta: acertar en 2 s no es lo mismo que acertar en 20 s. `avg_ms` alimenta la fluidez, que es lo que realmente se busca en las tablas.

---

## 8. UI mobile-first

**Reglas**

- Diseño desde **360 px** de ancho. La PC es solo "el mismo layout centrado con más aire".
- Área táctil mínima **56 px** de alto; botones de respuesta ~72 px.
- Todo lo importante en el **tercio inferior** de la pantalla (zona del pulgar). El enunciado arriba, las opciones abajo.
- `viewport-fit=cover` + `env(safe-area-inset-bottom)` para el notch y la barra de gestos.
- Tipografía con `clamp()`, sin media queries para el tamaño de fuente.
- Sin `hover` como único indicador; feedback en `:active` (instantáneo, no espera al WS).
- Dark mode automático (los tokens `--flv-*` ya lo traen).
- Objetivo: **jugable con una sola mano, en vertical**. Tablet: dos columnas.

**Footer permanente** (en todas las pantallas, respetando el safe area):

```
                    ╭─────────────────────────────╮
                    │  Hecho con Fitz y Fitz      │
                    │  LiveViews  ·  MatHelp 2026 │
                    ╰─────────────────────────────╯
```

con links a `github.com/Thegreekman76/fitz` y `github.com/Thegreekman76/fitz-liveviews`, ambos `target="_blank" rel="noopener"`, y el texto también localizado ("Hecho con" / "Built with").

---

## 9. Docker

```yaml
services:
  db:
    image: postgres:16-alpine
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: pg_isready
  app:
    build: .
    environment:
      DATABASE_URL: postgres://...@db:5432/mathelp?sslmode=disable
      JWT_SECRET: ${JWT_SECRET}
      MATHELP_DEFAULT_LOCALE: es-AR
    ports: ["3000:3000"]
    depends_on: { db: { condition: service_healthy } }
volumes: { pgdata: }
```

Base: lo que genera `fitz docker init` (multi-stage, runtime distroless, binario nativo). Le agrego:
- `migrate` automático al arrancar (o un servicio `migrator` aparte, más prolijo).
- Seed opcional de datos demo con `MATHELP_SEED=1`.
- `@server(3000, "0.0.0.0")` — sin el `0.0.0.0` el `-p` no rutea nada.

Todo el ciclo es: `docker compose up --build` y listo.

---

## 10. Estructura del proyecto

```
mathelp/
├─ fitz.toml
├─ Dockerfile · docker-compose.yml · .dockerignore · .env.example
├─ migrations/
├─ locales/            es-AR.json · en.json          ← fuente de verdad
├─ tools/gen_i18n.py   → compila los .json a .fitz
├─ src/
│  ├─ main.fitz              @server + registro de componentes
│  ├─ config.fitz            db_url, jwt_secret, nombres de cookie
│  ├─ models.fitz            los @table
│  ├─ rng.fitz               ⟵ aislado · firma de rand.seeded()
│  ├─ cookies.fitz           ⟵ aislado · set_cookie / read_cookie
│  ├─ fmt.fitz               ⟵ aislado · fmt_num / fmt_pct / fmt_money
│  ├─ i18n.fitz              t(), locale_from_cookie()
│  ├─ cat_es_ar.fitz         (generado desde locales/es-AR.json)
│  ├─ cat_en.fitz            (generado)
│  ├─ brand.fitz             logo SVG inline, footer, tokens CSS
│  ├─ game_layout.fitz       ⟵ aislado · wrapper sobre app_shell
│  ├─ assets.fitz            ⟵ aislado · /favicon.svg · /manifest.webmanifest
│  ├─ db_queries.fitz        ⟵ aislado · joins manuales + ANY($1)
│  ├─ auth.fitz              login familia (form nativo, sin JS), perfiles, logout
│  ├─ curriculum.fitz        temas, edades, destrezas
│  ├─ gen_arith.fitz         generadores + - × ÷
│  ├─ gen_frac.fitz          fracciones
│  ├─ gen_geo.fitz           geometría
│  ├─ gen_story.fitz         problemas con historia (localizados)
│  ├─ engine.fitz            selección adaptativa, Elo-lite, scoring
│  ├─ games/  Quiz.fitzv · TrueFalse.fitzv · FillGap.fitzv · NumPad.fitzv · MateBar.fitzv
│  ├─ live_game.fitz         @get + @ws + timer @background
│  ├─ parent.fitz            panel de reportes
│  └─ pages.fitz             home, elegir perfil, elegir juego, resumen
└─ tests/
   ├─ rng.fitz · generators.fitz · engine.fitz · i18n.fitz
```

---

## 11. Fases

| Fase | Qué entrega | Verificable con |
|---|---|---|
| **F0 — Cimientos** ✅ | Proyecto + compose levantando, Postgres, migraciones, shell mobile-first, i18n es-AR/en con selector, logo + footer, `/favicon.svg` + manifest | `docker compose up` → pantalla MatHelp responsive, cambio de idioma OK |
| **F1 — Identidad** ✅ | Registro/login de familia (Argon2id + JWT + cookie), alta de perfiles, selección de perfil con PIN | Login end-to-end ✓, cookie `HttpOnly` seteada ✓, redirect a `/login` sin sesión ✓, paridad `run`↔binario ✓ |
| **F2 — Primer juego** | `rng.fitz` + generadores de las 4 operaciones + `Quiz.fitzv` contrarreloj + cronómetro por WS + persistencia de sesión | **Tu hija juega.** Tests del PRNG (distribución) y de los generadores |
| **F3 — Que aprenda** | **navegación ✅** (menú §6.5 + elegir juego + práctica libre) · **pendiente:** `mastery` + Elo-lite + repaso espaciado + racha diaria + desafío del día + mate-progreso | Nav: E2E + paridad `run`↔binario ✅. Motor: simulación de 500 respuestas (el rating converge y la dificultad sigue) |
| **F4 — Más juegos** | V/F, completá el hueco, numpad propio, escalera de tablas, el kiosco, fracciones visuales | 6 modos jugables en celu |
| **F5 — Panel del padre** | Reportes por hijo: progreso por tema, errores frecuentes, tiempo, evolución; metas configurables | Gráficos con `bar_chart` / `progress_bar` / `stat_card` |
| **F6 — Pulido** | Dark mode, accesibilidad (contraste, `lang`, foco visible), reanudar partida, sonido opcional, instalable en el celu | Lighthouse mobile + prueba real en un Android |
| **F7 — Secundaria** | Currículum 13–17: enteros, ecuaciones, funciones, geometría analítica, trigonometría | Nuevos generadores, cero cambios de arquitectura |

**F0 → F2 es el corazón.** Al cerrar F2 ya hay un juego real en el celular; todo lo demás es acumular.

---

## 12. Lo que necesito de tu lado

1. **Versión de Fitz instalada** — `fitz --version`. El plan asume ≥ v0.42.1 (`@every` y `ws_broadcast` desde el scheduler). Si tenés menos, el cronómetro va con `@background`+`spawn`, que anda desde antes.
2. **Dónde vive el proyecto** — la carpeta conectada `D:\MathHelp` está vacía. ¿Genero todo ahí?
3. **El logo** — abajo va la propuesta. Decime si va, si le cambio algo, o si querés que pruebe otro concepto.

---

*MatHelp · Hecho con [Fitz](https://github.com/Thegreekman76/fitz) y [Fitz LiveViews](https://github.com/Thegreekman76/fitz-liveviews)*
