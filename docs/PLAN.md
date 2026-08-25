# MatHelp — Plan técnico y de producto

> **Mat**emática + **Help**, y el mate que se comparte.
> Juego de matemática para primaria (6–12), preparado para crecer a secundaria (13–17).
> Stack: **Fitz** + **Fitz LiveViews** + **PostgreSQL**, todo **dockerizado**, **i18n desde el día 1**, **mobile-first**.

---

## 📍 Estado — actualizado 23/08/2026

**Fase actual: F7 — Secundaria. ✅ COMPLETA (2026-08-24). F7.0 (modelo + filtro por
modalidad) + F7.1 (Ciclo Básico aritmética + teclado con ±) + F7.2 (Ecuaciones:
1er grado + cuadrática + sistemas 2×2) + F7.3 (Finanzas: interés simple/compuesto,
%, descuento, punto de equilibrio — diferencial comercial) + F7.4 (Trigonometría:
triángulo rectángulo con figura SVG — Pitágoras + razón 30°) + F7.5 (Funciones:
evaluar f(x) lineal/cuadrática/exponencial con fórmula + gráfico SVG) CERRADAS.
F0…F6 cerradas. Con esto la secundaria (Ciclo Básico + Ciclo Orientado con los
diferenciales por modalidad) queda cubierta. Próximo: definir F8 o pulido/nuevas
modalidades según feedback.**

> **F6 (2026-08-23)** — cuatro piezas de pulido:
> - **Reanudar partida** (`src/live_game.fitz`): el Desafío del día es el modo
>   reanudable. `GET /desafio` detecta la sesión sin terminar del perfil
>   (`ended_at IS NULL`, con `0 < idx < N`) y ofrece **Continuar** (reconstruye
>   `idx/total/correct/score` desde los `attempts` del mismo seed) o **Empezar de
>   nuevo** (`POST /desafio/nuevo` → abandona la vieja). El `@ws` reusa la sesión
>   abierta en vez de crear una nueva. Ciclo de vida `ended_at` cerrado en los 3
>   modos (contrarreloj hace housekeeping de sprints abandonados; práctica y
>   desafío lo setean al cerrar). E2E dedicado `tools/e2e_reanudar.py` con
>   **paridad `fitz run` ↔ binario** (una sola sesión reusada, 10 attempts,
>   `ended_at` seteado, empezar-de-nuevo abandona). Reanudar de práctica queda
>   como follow-up (su banda de dificultad no se persiste).
> - **Accesibilidad** (`src/layout.fitz` + `src/brand.fitz`): skip-link "Saltar
>   al contenido" (`<main id="main" tabindex="-1">`), foco visible universal
>   (`:focus-visible` con `--mh-tinta`, que se invierte por tema → contrasta con
>   cualquier fondo), inputs incluidos. Ya había `role="status"` en feedback,
>   `aria-label` en topbar/timer, `<html lang>`, `prefers-reduced-motion`, dark
>   mode. Las opciones de respuesta ya eran `<button type="button">`.
> - **Sonido opcional** (`public/sound.js` + toggle 🔊/🔇 en el topbar): beeps
>   de acierto/error sintetizados con Web Audio (cero assets, offline), preferencia
>   en `localStorage`, disparados por `data-fb-seq` (índice único por respuesta,
>   nuevo en `feedback_banner`) para no repetir. Audio desbloqueado con el primer
>   gesto (política de autoplay).
> - **Instalable / PWA**: `public/manifest.webmanifest` ampliado (id/lang/dir/
>   categories, icon `any` + `maskable`) + `public/sw.js` (service worker
>   cache-first de estáticos, red para páginas) registrado desde `sound.js`.
> Verificado: `fitz check` + `fitz test` 67/0 + `fitz build` nativo + smoke HTTP
> (skip-link, toggle, `/sound.js` + `/sw.js` + manifest servidos) + E2E reanudar
> `run` ↔ `build`. **Falta la prueba real (Lighthouse mobile + Android físico),
> que es el criterio de aceptación del autor.**
>
> **Dogfooding del core en F6:** re-confirmado **FITZ-22** en vivo (una llamada
> cross-módulo a `feedback_banner` con aridad vieja pasó `fitz check` pero la cazó
> `fitz build`) — el CLI instalado es **fitz 0.58.0**, y el fix de check-time de
> FITZ-22 está en 0.59.0; bumpear el CLI lo caza al chequear. Observación menor
> (no bug): el pool de DB del intérprete (`fitz run`) tarda ~1-2s tras responder
> `/` en estar write-ready — una ráfaga de writes en ese arranque puede fallar
> en silencio; solo dev (prod usa el binario). Ningún bug nuevo del core.

> **F5 (2026-08-23)** — `src/parent.fitz`: `@get /panel` (family-level,
> selector de hijo por `/panel/{pid}`, validando `family_id`) con stat_cards
> (ejercicios / racha / medallas / minutos), aciertos + progreso por tema
> (`progress_bar` por destreza, % = `progreso_pct`), errores frecuentes
> (`bar_chart` de prompts fallados + lista con correcta/respondió), tiempo por
> día (`bar_chart`), evolución del rating (`bar_chart`, AVG diario) y meta
> diaria editable (`@post /panel/meta` → `profiles.daily_goal`, clamp 1..200 +
> defensa cross-familia). Componentes `stat_card`/`bar_chart`/`progress_bar` de
> `fitz_liveviews.ui.*`. Histórico de rating: tabla nueva `mastery_snapshots`
> (`migrations/0002_f5_mastery_snapshots.sql`) + upsert diario en
> `actualizar_mastery`. i18n es-AR/en (26 claves `panel.*`). Verificado:
> `fitz check` + `fitz test` 67/0 + `fitz run` (todas las secciones con datos)
> + `fitz build` nativo + **paridad `fitz run` ↔ binario** (HTML idéntico
> módulo line-endings del layout). Reportes por SQL crudo (consistente con
> mastery/progreso; el ORM de relaciones queda para cuando se pida).

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

> **F3 — Motor adaptativo (cerrado 22/08/2026):** el corazón de "que aprenda".
> **Elo-lite** por destreza (`mastery.rating`, arranca en 800): cada respuesta
> recalcula el rating con la logística de Elo (`pow(10, ...)` nativo), sube al
> acertar / baja al fallar según la sorpresa. **Selección 70/20/10** (§7): al
> abrir la partida se congela el snapshot de ratings por operación; `gen_adaptive`
> elige el próximo ejercicio (70% zona de desarrollo próximo a su grado efectivo,
> 20% repaso de la op más floja, 10% desafío un grado arriba), determinista desde
> `(seed, idx, snapshot)` — render, scoring y persistencia derivan el MISMO
> ejercicio. **Repaso espaciado** (1/3/7/16/35 días, reinicio ante error) en
> `due_at` vía `NOW() + interval`. **Racha diaria** (`streaks`, upsert por
> respuesta) + **medallas** (`awards`: `primer_mate`, `racha7`). **Desafío del
> día** (`/desafio` + `/live/desafio`): 10 del mix adaptativo, sin reloj, alimenta
> la racha. **Mi progreso** (`/progreso`): mate-progreso (barra por destreza) +
> medallas + racha. El upsert de mastery/streaks/awards es SQL crudo atómico
> (`ON CONFLICT`) — el ORM de Fitz no tiene upsert nativo. Verificado con la
> **simulación §11** (un chico con habilidad fija responde 2.000 ejercicios: el
> rating converge a ±80 de su habilidad real y la dificultad servida lo sigue,
> hacia arriba y hacia abajo) + **E2E completo** (contrarreloj/desafío/práctica +
> mastery/racha/medallas/progreso persistidos) en **paridad bit-a-bit `fitz run`
> ↔ binario nativo** (mismo rating tras los mismos aciertos, coherencia 12/12
> respuestas correctas). Dos hallazgos nuevos del core anotados en el norte de
> fitz: **FITZ-21** (loader: un test homónimo del módulo que importa se
> auto-importa → ciclo; workaround: renombrar) y **FITZ-22** (check✓/build✗: el
> checker no caza aridad incorrecta en una fn importada, el codegen sí).

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

> **F4 — Más juegos (cerrada 22/08/2026):** cinco juegos nuevos, cada uno
> enchufado como el patrón §6.5 —**una fila en `src/juegos.fitz` + un `.fitzv` +
> un `live_*.fitz`**— reusando el motor adaptativo (`gen_for` + snapshot de
> mastery) y la persistencia por respuesta (Attempt + `actualizar_mastery` +
> `registrar_y_premiar`), así **cada juego alimenta mastery/racha igual que el
> contrarreloj**. **Verdadero o Falso** (`/vf`, 60s adaptativo): afirmación
> `a op b = shown` + dos botones gigantes; `vf_shown` determinista (mitad verdad,
> mitad distractor). **Completá el hueco** (`/completa`, ronda de 10 sin reloj):
> `a op __ = answer` con **teclado numérico propio** (`<button>`, no `<input>`
> → sin teclado del SO; entrada como Int en `keypad.fitz`). **Escalera de
> tablas** (`/escalera`): multiplicación pura, subís un escalón por acierto,
> bajás dos por error, llegás a la cima (10); adaptativo sobre `r_mul`. **El
> kiosco** (`/kiosco`): comprás y calculás el vuelto con teclado, precios en
> pesos (`fmt_money`), producto **localizado** (§4); generador nuevo
> `gen_kiosco`. **Fracciones a la vista** (`/fracciones`): barra pintada (divs,
> no SVG por el diff) y elegís la fracción; generador nuevo `gen_frac` con
> **distractores no equivalentes** (cross-mult), respuesta como Str. Verificado
> con **21 `@test` nuevos** (67 totales; `tests/kiosco.fitz`,
> `tests/fracciones.fitz`, `tests/teclado.fitz`, más los de `gen_arith`) + `fitz
> build` (binario nativo) + **E2E paridad bit-a-bit `fitz run` ↔ binario** de los
> cinco (`tools/e2e_game.py`: HTTP auth + WS + verificación en Postgres — attempts
> persistidos, mastery movido, racha del día), más las mecánicas validadas
> end-to-end (teclado que re-renderiza, escalera que sube/baja, vuelto del
> kiosco, barra→fracción correcta). Contra `fitz 0.58.0`. **Ningún bug nuevo del
> core** — solo se pegó FITZ-21 (ya conocido: un test no puede llamarse igual que
> el módulo que importa → `tests/teclado.fitz`, no `keypad`). El `mode 'escalera'`
> se sumó al CHECK de `sessions` (`migrations/0001_init.sql` + ALTER en la DB).

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
| **F3-motor** · Elo-lite (esperado/nuevo_rating/dificultad_objetivo/intervalo_repaso/progreso_pct) | `src/engine.fitz` | 13 `@test` incl. simulación §11 (converge ±80, dificultad sigue) |
| **F3-motor** · Selección adaptativa 70/20/10 (`gen_adaptive` + `grado_efectivo` + `op_mas_floja`) | `src/gen_arith.fitz` | 6 `@test` + coherencia E2E render↔scoring 12/12 |
| **F3-motor** · Persistencia de mastery (upsert `ON CONFLICT` por respuesta) | `src/mastery.fitz` | E2E: `sum(seen)` = nº respuestas, rating movido, `due_at` repaso |
| **F3-motor** · Racha diaria + medallas (`registrar_actividad`/`racha_actual`/`otorgar`) | `src/streaks.fitz` | E2E: racha7 con 6 días preseed + hoy, `primer_mate` |
| **F3-motor** · Desafío del día (`/desafio` + `/live/desafio`, 10 del mix) | `src/live_game.fitz` | E2E: sesión `mode=desafio total=10`, alimenta la racha |
| **F3-motor** · Mi progreso (`/progreso`: mate-progreso + medallas + racha) | `src/progreso.fitz` | E2E: barras por destreza + medalla + racha renderizados |
| **F3-motor** · `@table Mastery`/`Streak`/`Award` | `src/models.fitz` | Match exacto con `0001_init.sql` + writes reales |
| **F3-motor** · 9 claves i18n nuevas (progreso, medallas) es-AR/en | `locales/*.json`, `src/cat_*.fitz` | 119 claves × 2 locales, sin faltantes |
| **F4** · Verdadero o Falso (afirmación + 2 botones, 60s adaptativo) | `src/VerdaderoFalso.fitzv`, `vf_view.fitz`, `live_vf.fitz`, `gen_arith.vf_shown` | 3 `@test` + E2E paridad `run`↔binario (mode `truefalse`) |
| **F4** · Completá el hueco (teclado numérico propio, ronda de 10) | `src/Completa.fitzv`, `completa_view.fitz`, `live_completa.fitz`, `keypad.fitz` | 5 `@test` (`tests/teclado.fitz`) + E2E paridad + teclado end-to-end |
| **F4** · Escalera de tablas (mult., sube1/baja2, cima 10, adaptativo por `r_mul`) | `src/Escalera.fitzv`, `escalera_view.fitz`, `live_escalera.fitz`, `gen_arith.gen_escalera` | 2 `@test` + E2E paridad + mecánica end-to-end (mode `escalera`) |
| **F4** · El kiosco (vuelto en pesos, teclado, producto localizado) | `src/Kiosco.fitzv`, `kiosco_view.fitz`, `live_kiosco.fitz`, `gen_kiosco.fitz`, `fmt.fitz` | 5 `@test` (`tests/kiosco.fitz`) + E2E paridad + vuelto end-to-end (mode `kiosco`) |
| **F4** · Fracciones a la vista (barra pintada, distractores no-equivalentes) | `src/Fracciones.fitzv`, `frac_view.fitz`, `live_fracciones.fitz`, `gen_frac.fitz` | 6 `@test` (`tests/fracciones.fitz`) + E2E paridad + barra→fracción end-to-end (mode `fracciones`) |
| **F4** · Teclado numérico compartido + `fmt_money` + `mode 'escalera'` | `src/keypad_view.fitz`, `fmt.fitz`, `migrations/0001_init.sql` | Teclado `<button>` (sin teclado del SO), reusado por Completá + Kiosco |
| **F4** · Harness E2E reusable (HTTP auth + WS + Postgres) | `tools/e2e_game.py` | Paridad `run`↔binario de los cinco juegos |
| **F4** · 16 claves i18n nuevas (vf, kp, escalera, kiosco, frac) es-AR/en | `locales/*.json`, `src/cat_*.fitz` | 140 claves × 2 locales, sin faltantes |

**F0: 33 tests** contra `fitz 0.47.0`. **F1: E2E `curl` + paridad `run`↔binario**
contra `fitz 0.56.0`. **F2: 19 `@test` + E2E completo (HTTP + WS + persistencia) +
paridad bit-a-bit `fitz run` ↔ binario nativo** contra `fitz 0.58.0`.
**F3-nav: 27 `@test` (8 nuevos de práctica) + E2E de navegación + práctica live
por WS + paridad bit-a-bit `run` ↔ binario** contra `fitz 0.58.0` (Docker en
`fitz:v0.58.1`). **F3-motor: 46 `@test` totales (19 nuevos del motor:
`tests/motor.fitz` con la simulación §11 + 6 de selección adaptativa en
`tests/generators.fitz`) + E2E completo (mastery/racha/medallas/desafío/progreso
contra Postgres) + paridad bit-a-bit `run` ↔ binario** contra `fitz 0.58.0`.
**F4: 67 `@test` totales (21 nuevos: 5 del teclado en `tests/teclado.fitz`, 5 del
kiosco en `tests/kiosco.fitz`, 6 de fracciones en `tests/fracciones.fitz`, 5 de
V/F/escalera en `tests/generators.fitz`) + `fitz build` (binario nativo) + E2E
paridad bit-a-bit `run` ↔ binario de los cinco juegos (`tools/e2e_game.py`) +
mecánicas validadas end-to-end** contra `fitz 0.58.0`.

### 🔜 Lo que sigue

| Fase | Qué falta | Bloqueado por |
|---|---|---|
| **F3-nav** ✅ | menú §6.5 + elegir juego (grilla por grado) + práctica libre (tema+dificultad) | — |
| **F3-motor** ✅ | `mastery` + Elo-lite, selección 70/20/10, repaso espaciado, racha diaria, medallas, desafío del día, mate-progreso | — |
| **F4** ✅ | V/F, completá el hueco (teclado propio), escalera de tablas, el kiosco, fracciones a la vista | — |
| **F5** ✅ | Panel del padre: reportes por hijo (progreso, errores, tiempo, evolución) + metas configurables | F3 |
| **F6** ✅ | Reanudar partida (desafío), accesibilidad (foco visible + skip-link), sonido opcional, instalable/PWA | F2 |
| **F7** | Secundaria (13–17): Ciclo Básico (enteros, potencias/raíces, ecuaciones, sistemas) + Ciclo Orientado con diferencial por modalidad (finanzas→comercial, trig/vectores→industrial). Currículum en §5.b, juegos en §6.b, sub-fases en §11.b | F2 (motor + keypad ya están) |

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

## 5.b Currículum — secundaria argentina (13 a 17/18 años) — F7

La secundaria son **6 años** (en varias provincias 5; **técnica 6–7**), partidos en
**Ciclo Básico (1°–3°, común a TODAS las modalidades)** y **Ciclo Orientado /
Superior (4°–6°: un núcleo común + lo que agrega cada orientación)**. Toda la
Matemática se organiza en cuatro ejes NAP: **Números y Operaciones · Álgebra y
Funciones · Geometría y Medida · Probabilidad y Estadística** (fuentes: NAP
Ciclo Básico y Orientado de educ.ar; diseños curriculares de Buenos Aires,
Córdoba y Corrientes).

**Modelo de datos — decisión pendiente para F7:** hoy `Profile.grade: Int` es
1..7 (primaria). Para secundaria, extender la numeración a **8..13 = 1°..6° de
secundaria** (helper `grade_a_nivel(grade) -> (nivel, año)`), o sumar un campo
`nivel`. Recomendado: extender `grade` (el motor adaptativo igual manda por el
`rating` de `mastery`; el grado solo *siembra* el rango del generador). La
**modalidad** (bachiller / comercial / industrial) sí necesita un campo nuevo en
`Profile` (`modalidad: Str = "comun"`) que solo aplica en el Ciclo Orientado
(4°–6°) para decidir qué temas de modalidad aparecen.

### Ciclo Básico (común a bachiller, comercial e industrial)

| Año (edad) | Ejes / temas | `topic_code` |
|---|---|---|
| **1° (12–13)** | Enteros (Z) 4 operaciones + potencia y orden. Divisibilidad, mcm/mcd. Racionales (Q). Proporcionalidad directa/inversa, **porcentaje**. Ecuaciones de 1er grado simples. Ángulos, triángulos, perímetro/área. Estadística: frecuencias, promedio | `ent.suma`, `ent.resta`, `ent.mult`, `ent.div`, `num.mcd_mcm`, `num.primos`, `frac.*`, `prop.directa`, `prop.inversa`, `pct.basico`, `ec.lineal1`, `geo.angulos`, `geo.area`, `est.promedio` |
| **2° (13–14)** | Racionales completos, **notación científica**, potencias de exponente entero. Ecuaciones **e inecuaciones** de 1er grado. **Función lineal** (pendiente, ordenada). **Teorema de Pitágoras**. Áreas y volúmenes de cuerpos. Probabilidad simple | `pot.notacion`, `pot.entera`, `ec.lineal`, `ineq.lineal`, `func.lineal`, `geo.pitagoras`, `geo.volumen`, `prob.simple` |
| **3° (14–15)** | Reales (R): **radicación**, potencias de exponente racional. **Sistemas de ecuaciones 2×2**. **Función cuadrática** (intro: parábola, vértice, raíces). Semejanza, **Thales**, **razones trigonométricas** del triángulo rectángulo (sen/cos/tan). Estadística: media/mediana/moda, dispersión | `raiz.cuadrada`, `raiz.enesima`, `sist.2x2`, `func.cuadratica`, `geo.thales`, `trig.rectangulo`, `est.central`, `est.dispersion` |

### Ciclo Orientado (4°–6°): núcleo común + modalidad

**Núcleo común** (todas): función **cuadrática, polinómica, racional, exponencial,
logarítmica y trigonométrica**; **ecuación de 2° grado** y sistemas; **polinomios**
(operaciones, factoreo, Ruffini, Gauss); **trigonometría** (identidades, teorema
del seno/coseno); **sucesiones/progresiones**; **combinatoria y probabilidad**;
**estadística** (muestreo, correlación). Hacia 5°/6°, **límite y derivada** según
orientación.
`func.cuadratica`, `ec.cuadratica`, `poly.oper`, `poly.factoreo`, `func.racional`,
`func.exponencial`, `func.log`, `ec.exp`, `trig.identidades`, `trig.teoremas`,
`suc.aritmetica`, `suc.geometrica`, `comb.*`, `prob.compuesta`, `est.correlacion`,
`analisis.limite`, `analisis.derivada`

| Modalidad | Campo `modalidad` | Qué agrega/enfatiza en el Ciclo Orientado | `topic_code` propios |
|---|---|---|---|
| **Bachiller** (general / cs. sociales / cs. naturales) | `"bachiller"` | El núcleo común. En **Cs. Naturales/Exactas** profundiza **análisis** (límite, derivada, estudio de funciones); en sociales/humanidades pesa más **estadística y probabilidad** | `analisis.*`, `est.*`, `prob.*` |
| **Comercial** (Economía y Administración) | `"comercial"` | Núcleo **+ Matemática Financiera**: interés **simple/compuesto**, descuento, **anualidades/rentas**, amortización, TNA/TEA, VAN/TIR básico. Funciones de **costo/ingreso/beneficio**, **punto de equilibrio**. Fuerte estadística | `fin.interes_simple`, `fin.interes_compuesto`, `fin.descuento`, `fin.anualidad`, `fin.equilibrio`, `func.costo` |
| **Industrial** (Técnica) | `"industrial"` | La de **más matemática**: materias separadas (Matemática + **Análisis Matemático** + **Matemática Aplicada**). Agrega **trigonometría avanzada, vectores, matrices/determinantes, números complejos, geometría analítica, cálculo** aplicado | `trig.avanzada`, `vec.*`, `matriz.*`, `complejo.*`, `geo.analitica`, `analisis.*` |

**Los `topic_code` reservan el nombre** (como en primaria): el motor y `mastery`
los reconocen cuando aterrice cada generador. La edad/año **sugiere** el punto de
entrada; el `rating` de Elo-lite manda igual que en primaria.

---

## 6. Los juegos

Todos pensados para **pulgar en celular**: botones grandes, nada de arrastrar, nada que dependa de `hover`.

| # | Juego | Mecánica | Temas | Fase |
|---|---|---|---|---|
| 1 | **Contrarreloj** | 60 s, opción múltiple, 4 botones grandes | todos | F2 |
| 2 | **Verdadero o Falso** | 2 botones gigantes — el más fácil de usar en el colectivo | todos | F4 |
| 3 | **Completá el hueco** | `7 × __ = 56` con **teclado numérico propio** en pantalla | todos | F4 |
| 4 | **Escalera de tablas** | Subís un escalón por acierto, caés dos por error | `mult.*` | F4 |
| 5 | **Problemas** | 16 tipos de la vida real en pools por nivel (kiosco, ahorro, edades, cuadras, promedios, porcentajes, precio unitario…), sin repetir problema en la ronda | `add`, `sub`, `mul.tabla`, `dec.dinero`, `div.exacta` | F4 · enriquecido F8.B (antes "El kiosco", sólo vuelto) |
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

## 6.b Juegos de secundaria (F7)

La secundaria es más simbólica/gráfica que la primaria, pero **buena parte encaja
directo con el motor actual** (opción múltiple / teclado numérico, deterministas
seed+idx). Clasificados por esfuerzo de UI:

**✅ Encajan ya con el motor (respuesta numérica / opción múltiple):**

| # | Juego | Mecánica | Temas | Modalidad |
|---|---|---|---|---|
| 12 | **Potencias y raíces** | opción múltiple / teclado | `ent.*`, `pot.*`, `raiz.*`, `pot.notacion` | común (1°–3°) |
| 13 | **Ecuaciones** | teclado numérico (reusa `keypad`): 1er grado → sistemas 2×2 → cuadráticas, respuesta = valor de x | `ec.lineal`, `sist.2x2`, `ec.cuadratica` | común |
| 14 | **Finanzas** | teclado: interés simple/compuesto, %, descuento, punto de equilibrio | `fin.*`, `pct.basico` | **comercial** (diferencial) |
| 15 | **Trigonometría** | triángulo rectángulo, dado cateto/ángulo → hipotenusa/razón, respuesta numérica | `trig.rectangulo`, `geo.pitagoras` | común / industrial |
| 16 | **Evaluar función** | opción múltiple: dado f(x), calcular f(a); o hallar raíz/vértice | `func.lineal`, `func.cuadratica`, `func.exponencial` | común |

**🔶 Necesitan UI nueva (SVG inline, ya hay patrón en `brand.fitz`/reloj):**
- **Reconocer funciones** (elegir la parábola/recta/exponencial correcta del gráfico).
- **Geometría con figura** (área/perímetro/volumen leyendo el dibujo — ya mapeado como `geo.*` desde F5).
- **Vectores** (industrial): suma gráfica, módulo.

**🔴 Fuera de un juego de opción rápida** (no van): demostraciones, factoreo
simbólico largo, derivadas/integrales simbólicas, matrices grandes. Para eso el
formato "juego" no sirve; queda como límite consciente de la app.

**Diferencial por modalidad:** el juego **Finanzas (#14)** es lo que distingue a la
orientación **comercial**; **Trigonometría/Vectores** y el peso de `analisis.*`
distinguen a la **industrial/técnica**; el **bachiller** vive del núcleo común +
más estadística. Un chico ve el mix de su `grade` + los juegos de su `modalidad`.

---

## 6.5 Navegación / IA de juego (F3–F5)

> **Estado (22/08/2026): F3 + F4 completas.** El árbol de abajo está vivo
> ENTERO: `/`, `/juegos`, `/practica` → tema → dificultad, **Desafío del día**
> (`/desafio`, 10 del mix adaptativo, alimenta la racha) y **Mi progreso**
> (`/progreso`: mate-progreso + medallas + racha). El nivel dentro del
> contrarreloj/desafío es adaptativo (Elo-lite + selección 70/20/10). La grilla
> de juegos filtra por grado y ya tiene **seis juegos con mecánica propia**:
> contrarreloj, Verdadero/Falso, Completá el hueco, Escalera de tablas, El kiosco
> y Fracciones a la vista (F4). Los que faltan (¿Qué hora es?, Geometría,
> Porcentaje, Volumen, Enteros, Ecuaciones, Problemas con historia) llegan en
> F5/F7.

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
| **F3 — Que aprenda** ✅ | navegación (menú §6.5 + elegir juego + práctica) + motor adaptativo (`mastery` Elo-lite, selección 70/20/10, repaso espaciado, racha diaria, medallas, desafío del día, mate-progreso) | Simulación §11 (rating converge ±80, dificultad sigue) ✅ + E2E completo + paridad bit-a-bit `run`↔binario ✅ |
| **F4 — Más juegos** ✅ | V/F, completá el hueco (teclado propio), escalera de tablas, el kiosco, fracciones a la vista | 5 modos jugables en celu + paridad `run`↔binario ✅ |
| **F5 — Panel del padre** ✅ | Reportes por hijo: progreso por tema, errores frecuentes, tiempo, evolución; metas configurables | Gráficos con `bar_chart` / `progress_bar` / `stat_card` — `src/parent.fitz` |
| **F6 — Pulido** ✅ | Reanudar partida (desafío), accesibilidad (foco visible + skip-link; ya había dark mode/`lang`/reduced-motion), sonido opcional (Web Audio), instalable/PWA (manifest + service worker) — `src/live_game.fitz`, `layout`/`brand`, `public/sound.js`, `public/sw.js`. **Pendiente: Lighthouse mobile + prueba real en un Android.** | Lighthouse mobile + prueba real en un Android |
| **F7 — Secundaria** | Currículum 13–17 (§5.b) + juegos nuevos (§6.b) + plan por sub-fases (§11.b). Mayormente generadores nuevos + `keypad` (ya existe); único cambio de schema: campo `Profile.modalidad` + extender `grade` a 8..13 | Generadores deterministas (paridad seed+idx), `fitz test` de cada generador, E2E de un juego por sub-fase |

**F0 → F2 es el corazón.** Al cerrar F2 ya hay un juego real en el celular; todo lo demás es acumular.

---

## 11.b Plan de F7 (secundaria) por sub-fases

Orden: primero el **Ciclo Básico** (común a todas las modalidades → máxima
cobertura, sin decisión de modalidad), luego el **diferencial de modalidad**
arrancando por **comercial** (finanzas, todo numérico, alto valor pedagógico).
Cada sub-fase = generador(es) + un juego; cada una cierra con `fitz build`
nativo verde (**check✓ no garantiza build✓**) + `fitz test` de paridad + E2E.

- **F7.0 — Modelo + navegación. ✅ (2026-08-24)** Campo `Profile.modalidad`
  (`"comun"` | `"bachiller"` | `"comercial"` | `"industrial"`) + `grade` extendido
  a **8..13** (= 1°..6° secundaria). Migración `migrations/0003_f7_secundaria.sql`
  (idempotente, `ADD COLUMN IF NOT EXISTS`) + espejo en `models.fitz`. Helpers en
  `engine.fitz`: `es_secundaria` (≥8), `anio_secundaria` (grade−7), `es_ciclo_orientado`
  (≥11 = 4° sec) y `modalidad_valida` (normaliza a un valor conocido) — 8 `@test`
  en `tests/secundaria.fitz`. Formulario de perfil: selector de grado con optgroups
  **Primaria/Secundaria** + `<select>` de **orientación** (i18n `grado.8-13`,
  `modalidad.*`). La grilla tolera grade 8-13 (todos los juegos actuales se
  desbloquean; los específicos de secundaria se suman con `min_grade` 8+ en F7.1+).
  Verificado: `fitz test` 75/0 + `fitz build` nativo + smoke (crear perfil sec 4°
  comercial → persiste `grade=11, modalidad='comercial'`; modalidad inválida →
  `comun`; grilla con 6 juegos). **Único cambio de schema de toda F7.**
  *Filtro de la grilla por modalidad: CERRADO en F7.3 (`Juego.modalidad` +
  `grilla_juegos` filtra por la modalidad del perfil; Finanzas sólo aparece para
  comercial).*
- **F7.1 — Ciclo Básico, aritmética: enteros con signo. ✅ (2026-08-24)** Un perfil
  de secundaria (grade ≥ 8) juega las cuatro operaciones con **enteros con signo**
  (resta sin forzar a≥b, mult/div con signo, división exacta) en **todos los juegos
  de opción múltiple existentes** — Contrarreloj, Desafío, Práctica, V/F, Escalera —
  **sin pantalla nueva**. Cómo: `gen_arith` gana `gen_sec` (camino de secundaria,
  primaria queda bit-a-bit intacta) + `candidatos_signed` + rangos por grado 8-13
  + `grado_efectivo`/`grade_for_band` que no cruzan el límite primaria/secundaria;
  el render swapea `fmt_int`→**`fmt_operando`** en los operandos (parentiza negativos,
  byte-idéntico en ≥0, paridad de primaria). 8 `@test` nuevos en `tests/secundaria.fitz` (determinismo, invariantes con
  signo, primaria sin negativos, `fmt_operando`). Verificado: `fitz test` 83/0 +
  `fitz build` nativo + smoke (perfil sec 4° → `(-65) − (-13)`, `225 + (-98)`, opciones
  negativas; perfil primaria → positivo sin paréntesis). `topic_code`: `add`/`sub`/`mul`/`div`
  (reusa las destrezas; el grado siembra el signo). *Casi cero UI nueva, paridad intacta.*
- **F7.1.b — Potencias y raíces. ✅ (2026-08-24)** Juego dedicado nuevo "Potencias
  y raíces" (`/potencias`, `min_grade` 8) que REUSA el componente Quiz (mode
  `"potencias"`, no adaptativo). Genera `a^b` (base 2..9, a veces negativa —
  regla del signo por paridad del exponente) y √/∛ exactas (radicando = r^n). El
  display propio lo arma `prompt_potencia` (`base^exp` / `√rad` / `∛rad`), sin
  tocar el prompt binario `a op b` de los otros juegos. `gen_arith` gana `ipow`
  (pura) + `gen_potencia` + rama `"potencias"` en `gen_for`; `quiz_view` gana
  `quiz_potencias` + dispatch; `live_potencias.fitz` nuevo (ruta + `@ws` + persist,
  modela el Desafío). Migración `0004_f7_potencias.sql` suma `'potencias'` al CHECK
  de `sessions.mode`. `topic_code`: `pot.entera`, `raiz.enesima`. 3 `@test` (ipow,
  determinismo, invariantes a^b/answer^b). Verificado: `fitz test` 86/0 + `fitz build`
  nativo + smoke (juego en grilla, `/potencias` renderiza, WS sirve `(-7)^3` / `8^2` /
  `∛125` / `√49`, persiste sesión `mode='potencias'`).
- **F7.1.c — Notación científica. ✅ (2026-08-24)** Tercer sub-tipo del juego
  Potencias (`m × 10^k` → número, mantisa 2..9, exponente 2..5), con distractores
  por **orden de magnitud** (`candidatos_scinot`: un orden arriba/abajo + mantisa ±1;
  un ±offset sería indistinguible en números enormes). Display `m × 10^k` en
  `prompt_potencia`; prompt canónico en la persistencia. `topic_code`: `pot.notacion`.
  Sin migración ni i18n nuevos (va en el mode `potencias`). Test de invariantes
  extendido (m×10^k == answer + cobertura de los 3 tipos). Verificado: `fitz test`
  86/0 + `fitz build` nativo + smoke (`7 × 10^5`, `9 × 10^4` en el juego).
  **Con esto F7.1 (Ciclo Básico aritmética) queda COMPLETA**: enteros con signo +
  potencias + raíces + notación científica.
- **Teclado con signo (±) para "Completá el hueco". ✅ (2026-08-24)** El juego de
  teclado ahora acepta enteros negativos en secundaria (antes clampeaba a positivo).
  `keypad.fitz` gana `kp_signo` + `kp_append` neg-aware (acumula extendiendo la
  magnitud: −5 y "3" → −53); `keypad_view` suma la tecla `±` (solo si `con_signo`)
  + `data-flv-value-touched` en Listo; `Completa.fitzv` gana estado `touched`
  (distingue "vacío" de "0 tipeado" — el operando faltante puede ser 0/negativo en
  secundaria) + evento `signo`; el hueco muestra el negativo con `fmt_operando`;
  `live_completa` seedea `con_signo=es_secundaria(grade)` y el loop del `@ws`
  persiste por `touched` (no por `given > 0`). 4 `@test` nuevos en `tests/teclado.fitz`.
  Verificado: `fitz test` 90/0 + `fitz build` nativo + smoke (perfil sec tipea `5,3,±`
  → hueco `(-53)` → persiste `given='-53'`; primaria sin ±). *Limitación menor: el
  SSR-placeholder comparte la instancia "ssr" entre requests, así que el `±` puede
  aparecer con un flash al conectar el WS — el juego en vivo es correcto.*
  *Deuda residual: `grade_teclado` quedó sin uso en la app (lo reemplazó el ±);
  se puede borrar (+ su test) en un cleanup.*
- **F7.2 — Ecuaciones. ✅ (2026-08-24)** Juego nuevo "Ecuaciones" (`/ecuaciones`,
  `min_grade` 8) con teclado (aprovecha el `±`): el chico TIPEA la solución `x`.
  Dos tipos mezclados: **1er grado** `ax + b = c` → x (x ∈ [-12,12] con signo, se
  muestra c ya calculado) y **cuadrática** `x² = n` → x (valen ±x). Generador
  `gen_ecuacion` + `ecuacion_correcta` (la cuadrática acepta las dos raíces) en
  `gen_arith`; `ecuacion_view.fitz` nuevo (`ecuacion_screen` + `prompt_ecuacion`);
  componente `Ecuaciones.fitzv` (teclado, eventos digito/borrar/signo/answer);
  `live_ecuaciones.fitz` nuevo (ruta + `@ws` + persist, mode `numpad` — ya en el
  CHECK). `topic_code`: `ec.lineal`, `ec.cuadratica`. 4 `@test`. Verificado:
  `fitz test` 94/0 + `fitz build` nativo + smoke (resolví y respondí 6 ecuaciones
  de ambos tipos, 6/6 correctas persistidas).
- **F7.2.b — Sistemas 2×2. ✅ (2026-08-24)** Tercer tipo del juego Ecuaciones
  (op `ecsist`): se muestran las DOS ecuaciones (`ax + by = c₁`, `a2x + b2y = c₂`,
  coeficientes 1..4, det ≠ 0 → solución única entera) y el chico **tipea x** (hallar
  x exige resolver el sistema). `Exercise` gana `a2/b2/answer2` (defaults 0,
  backward-compatible — los otros generadores no cambian); `gen_ecuacion` suma la
  rama sistema; `prompt_ecuacion` muestra las dos ecuaciones (una por línea, CSS
  `.ec-sist` con `pre-line`; coeficiente 1 omitido → `x`/`y` limpio); `ecuacion_correcta`
  reusa `given == x`. `topic_code`: `sist.2x2`. 2 `@test` (cobertura de los 3 tipos,
  det ≠ 0). Verificado: `fitz test` 95/0 + `fitz build` nativo + smoke (jugué 10
  ejercicios de los 3 tipos, resolví cada sistema por eliminación, **10/10 correctas**).
  **Con esto F7.2 (Ecuaciones) queda COMPLETA**: 1er grado + cuadrática + sistemas 2×2.
  *Refinamiento futuro: pedir x E y (input de dos valores, two-step) en vez de solo x.*
- **F7.3 — Finanzas (#14) — diferencial COMERCIAL. ✅ (2026-08-24)** Juego nuevo
  "Finanzas" (`/finanzas`, `Finanzas.fitzv` + `finanzas_view.fitz` + `live_finanzas.fitz`,
  `min_grade` 11). Generador `gen_finanzas(seed, idx, grade)` con 5 tipos:
  **interés simple** (I = C·i·t/100), **interés compuesto** (M = C·(1+i)^t, con
  `ipow`), **porcentaje** (P% de base), **descuento** (base − P%) y **punto de
  equilibrio** (Q = CostosFijos/(Precio−Costo), el tema-firma comercial). Los capitales
  son múltiplos de 1000/100 y las tasas dividen exacto → la respuesta es SIEMPRE un
  entero POSITIVO de pesos (teclado SIN ±). Enunciados con historia LOCALIZADOS
  (`fin.p_simple/p_comp/p_pct/p_desc` con `t2`/`t3` — helpers de interpolación
  posicional `{0}/{1}/{2}` nuevos en `i18n.fitz`) + `fmt_money`. La sesión persiste
  con `mode="story"` (ya en el CHECK, sin migración), `topic_code`: `fin`,
  skills `fin.interes_simple/_compuesto`, `pct.basico`, `fin.descuento`,
  `fin.punto_equilibrio`.
  **Filtro por modalidad (§11.b F7.0 pendiente, cerrado acá):** `Juego` gana
  `modalidad: Str = "comun"`; `GameCtx`/`resolver_contexto` cargan la modalidad del
  perfil; `grilla_juegos` filtra `j.modalidad == "comun" or j.modalidad == modalidad`
  → Finanzas (modalidad `"comercial"`) sólo aparece para perfiles comerciales del
  Ciclo Orientado. 6 tests nuevos (determinismo, los 5 tipos, respuestas enteras
  positivas, fórmulas exactas de simple, % y punto de equilibrio). Smoke E2E
  `tools/e2e_finanzas.py`
  RESUELVE los 10 problemas y verifica en Postgres (mode=story, 10/10 correctos,
  ended_at) — paridad bit-a-bit `fitz run` ↔ binario. **El juego que justifica la
  modalidad comercial: CONSTRUIDO.**
- **F7.4 — Trigonometría (#15). ✅ (2026-08-24)** Juego nuevo "Trigonometría"
  (`/trigonometria`, `Trigonometria.fitzv` + `trig_view.fitz` + `live_trigonometria.fitz`,
  `min_grade` 10, modalidad `comun`). **Triángulo rectángulo con FIGURA SVG inline**
  (primer SVG dinámico del proyecto — el patrón "reloj/geometría de F5" era
  aspiracional, sólo existía el logo). `gen_trig(seed, idx, grade)` con 3 tipos, todos
  con respuesta entera positiva (teclado sin ±): **Pitágoras hallar hipotenusa** y
  **hallar cateto** (ternas pitagóricas en listas paralelas → a²+b²=c² exacto), y
  **razón 30°** (sin 30°=1/2: con hipotenusa par el cateto opuesto es entero; dos
  modos: dada hip → cateto = h/2, dado cateto → hip = 2·cateto). El SVG lo dibuja
  `triangulo_svg(horiz, vert, hyp, ang)` (ángulo recto abajo-izq, marca del ángulo
  agudo cuando aplica), estilado por clases `.tg-*` en `brand.fitz` (sin `<style>`
  adentro, mitigando FLV-02). Sesión `mode="numpad"` (sin migración), `topic_code`
  `trig`, skills `trig.pitagoras`/`trig.razon`. 4 tests nuevos (determinismo, los 3
  tipos, Pitágoras cierra, razón 30°). Smoke E2E `tools/e2e_trig.py` que **RESUELVE
  cada ejercicio leyendo la figura SVG del frame vivo** — y así verifica que el SVG
  **sobrevive el diff de LiveView en cada tick** (FLV-02 no aplica a SVG geométrico
  puro: hallazgo del dogfooding). Verificado en Postgres (mode=numpad/trig, 10/10
  correctos, ended_at) con paridad bit-a-bit `fitz run` ↔ binario.
- **F7.5 — Funciones (#16). ✅ (2026-08-24)** Juego nuevo "Funciones"
  (`/funciones`, `Funciones.fitzv` + `func_view.fitz` + `live_funciones.fitz`,
  `min_grade` 11, modalidad `comun`). **Evaluar f(x)** de tres familias, mostrando
  la FÓRMULA (con `<sup>` para los exponentes) + el GRÁFICO de la familia (SVG,
  mismo patrón que Trigonometría). `gen_func(seed, idx, grade)`: **lineal**
  (`f(x)=a·x+b`, pendiente ± → gráfico sube/baja), **cuadrática** (`f(x)=a·x²+b`,
  a>0 → parábola hacia arriba), **exponencial** (`f(x)=a·base^x`, base 2/3, crece).
  La respuesta puede ser NEGATIVA (lineal/cuadrática) → teclado con ± (evento
  `signo`, como Ecuaciones). El gráfico lo dibuja `func_grafico`/`func_curva`
  (ejes + curva por familia/dirección), la fórmula `func_formula` (coef 1/−1
  omitido, término independiente con signo). Sesión `mode="numpad"` (sin
  migración), `topic_code` `func`, skills `func.lineal`/`func.cuadratica`/
  `func.exponencial`. 4 tests nuevos (determinismo, las 3 familias, evaluación
  correcta por familia, pendiente lineal con ambos signos). Smoke E2E
  `tools/e2e_funciones.py` que **RESUELVE evaluando la fórmula leída del frame
  vivo** (parseando lineal/cuadrática/exponencial + el punto x0) — y verifica que
  fórmula (con `<sup>`) y gráfico SVG sobreviven el diff. Postgres (mode=numpad/
  func, 10/10 correctos, ended_at) con paridad bit-a-bit `fitz run` ↔ binario.
  *El gráfico muestra la FAMILIA + dirección (no un plot exacto de los coeficientes)
  — reforzar "reconocer el gráfico" con recognition multiple-choice queda como
  follow-up opcional.*
- **Industrial (posterior, según demanda).** Vectores, matrices — más SVG + más
  motor; se evalúa cuando aparezca un usuario real de esa orientación.

**Arranque sugerido:** **F7.0 + F7.1** dan valor con casi cero UI nueva (reusan
todos los juegos actuales). **F7.2 (Ecuaciones)** y **F7.3 (Finanzas)** son los dos
juegos-ancla de secundaria. F7.4/F7.5 (SVG) después. Todo con paridad determinista
seed+idx e i18n es-AR/en desde el commit — igual que primaria.

---

## 11.c Niveles y progresión graduada (F8)

**El problema (verificado 2026-08-24).** La dificultad hoy es despareja:
- Aritmética (opción múltiple / contrarreloj / V·F / completá / desafío) escala por
  grado y es **adaptativa** (rating Elo F3, `grado_efectivo`), pero el snapshot se
  congela al abrir el socket → no sube *dentro* de la ronda.
- Kiosco / Fracciones escalan por grado (`kiosco_max`/`frac_den_max`) pero son fijos.
- Práctica libre usa banda 1/2/3 = grado−1/grado/grado+1.
- **Los 5 juegos de secundaria (Potencias, Ecuaciones, Finanzas, Trigonometría,
  Funciones) reciben `grade` pero lo IGNORAN**: un 1° secundaria (grade 8) y un 6°
  (grade 13) reciben la misma mezcla de sub-tipos y rangos. Ninguno sube "de a poco"
  dentro de la ronda (`idx` sólo cambia la semilla, no la dificultad).

**El objetivo.** Que cada juego, para **cada grado** (primaria 1..7, secundaria
8..13), tenga niveles que **suban de a poco en intensidad y complejidad**, para que
los chicos aprendan gradualmente mientras practican.

**El modelo — `nivel` 1..5, determinista.** Cada ejercicio tiene un `nivel`:

```
nivel = clamp( piso(grado) + idx / PASO , piso(grado) , techo(grado) )   // PASO ≈ 3
```

- **`piso`/`techo` por grado** = cotas del currículum: un grado bajo queda **capado**
  (nunca ve los sub-tipos avanzados), un grado alto **arranca más arriba** (se saltea
  lo trivial). Da el "para cada grado".
- **rampa por `idx`** dentro de `[piso, techo]`: la ronda **empieza fácil y sube de a
  poco** (primeros ejercicios en el piso, últimos más complejos). Da el "aprender de
  a poco practicando".

Como el `nivel` sale de `(idx, grado)` — ambos ya determinan el ejercicio — **se
calcula ADENTRO del generador**: cero cambios de firma, el server re-deriva idéntico
para persistir (paridad run↔build por construcción). El `nivel` setea además
`Exercise.difficulty` (1..5) → el Elo/puntaje ya lo reflejan (reusa lo existente).

**Escaleras por juego + cotas por grado:**

| Juego | N1 | N2 | N3 | N4 | N5 | piso/techo por grado |
|---|---|---|---|---|---|---|
| **Ecuaciones** | lineal x+ | lineal x± coef↑ | cuadrática x²=k | ax²+c | sistema 2×2 | 8:[1,2] 9:[1,3] 10:[2,4] 11:[2,5] 12-13:[3,5] |
| **Potencias** | cuadrados chicos | cubos + base 6-9 | raíces exactas | notación científica | exp/base ↑ | 8:[1,2] 9:[1,3] 10:[2,4] 11-13:[2,5] |
| **Trigonometría** | Pitág. hip. triples chicos | todos los triples | hallar cateto | razón 30° hip→cateto | razón 30° cateto→hip | 10:[1,3] 11:[1,4] 12-13:[2,5] |
| **Funciones** | lineal + | lineal ± | cuadrática | exponencial base 2 | exp base 3 + coef | 11:[1,3] 12:[1,4] 13:[2,5] |
| **Finanzas** | porcentaje | descuento | interés simple | interés compuesto | punto de equilibrio | 11:[1,3] 12:[1,4] 13:[2,5] |

**Fases:**
- **Fase A (el hueco real). ✅ (2026-08-24)** Helper compartido `nivel_por_idx(piso,
  techo, idx)` + `iabs` + tablas `nivel_piso_<juego>(grade)`/`nivel_techo_<juego>`
  por los 5 juegos + los 5 generadores de secundaria (`gen_potencia`/`gen_ecuacion`/
  `gen_finanzas`/`gen_trig`/`gen_func`) reescritos: computan `nivel` desde
  `(grade, idx)` y branchean el sub-tipo por nivel (antes elegían el tipo con un
  dado ignorando `grade`). `Exercise.difficulty = nivel` → el Elo/puntaje ya lo
  reflejan. Escaleras implementadas exactamente como la tabla de arriba. Tests
  actualizados/nuevos (113 total): `nivel_por_idx` (piso/rampa/techo clamp),
  cobertura por grado (`gen_finanzas_cobertura_por_grado`, `gen_ecuacion_grado_bajo_
  capado_en_lineal`, `gen_ecuacion_grado_alto_arranca_complejo`, `..._difficulty_
  sube_con_idx`), + los invariantes por juego reapuntados a grados donde el sub-tipo
  aparece. Smoke E2E `tools/e2e_niveles.py`: juega Trigonometría en grade 10 vs 13 y
  verifica **escala por grado** (g10 sólo `trig.pitagoras`; g13 suma `trig.razon` y
  ya no ve el nivel 1) **+ rampa en la ronda** (dificultad g10 1→3, g13 2→5, y el 6°
  arranca más arriba). Paridad bit-a-bit `fitz run` ↔ binario; smokes de los juegos
  (trig/funciones/finanzas) siguen 10/10.
- **Fase B. ✅ (2026-08-24)** (1) **Fracciones:** rampa por `idx` — el denominador
  máximo crece de a poco dentro de la ronda (`imin(4 + idx/2, frac_den_max(grade))`),
  sin pasar el máximo del grado. (2) **Kiosco → "Problemas":** el juego era sólo
  VUELTO ("muy pobre"); ahora es **Problemas de la vida real VARIADOS** (§6.6), con
  el sub-tipo elegido por nivel: **N1 total** (N unidades a $X → multiplicación),
  **N2 vuelto** (resta con dinero), **N3 reparto** (división exacta), **N4 cuántos
  entran** (división con $), **N5 oferta** (2 pasos: N·X y vuelto). Cada tipo con su
  enunciado localizado (es-AR/en, `kiosco.p_*` + `t4` nuevo), respuesta entera
  positiva (plata o cuenta según el tipo → el slot/feedback formatea con `fmt_money`
  o `fmt_int`), skill de mastery por operación (`mul.tabla`/`dec.dinero`/`div.exacta`
  → refuerza esas destrezas cross-juego). Renombrado de cara al usuario a
  **"Problemas"** (ruta `/problemas`, ícono 🧮); el código interno sigue "kiosco"
  (componente, `mode="kiosco"` del CHECK) como nombre histórico. `nivel_piso_kiosco`/
  `nivel_techo_kiosco`: grade 4:[1,2] 5:[1,3] 6:[2,4] 7+:[2,5]. Tests reescritos
  (`tests/kiosco.fitz`: fórmula exacta por tipo, cobertura por grado — un 4° no ve
  reparto/cuantos/oferta, un 7° sí —, rampa de dificultad) + rampa de fracciones
  (`frac_rampa_por_idx`); 115 total. Smoke E2E `tools/e2e_problemas.py`: juega en
  grade 7 resolviendo cada tipo desde el enunciado del frame → 10/10, variedad de
  skills (dec.dinero + div.exacta, ya no sólo vueltos), paridad run↔binario.
  **Ampliado (misma tanda): de 5 a 16 tipos + de-dup por sesión.** Cada nivel es un
  POOL de tipos de dificultad similar y el tipo se elige al azar en el pool → mucha
  más variedad, con **contextos variados de la vida real** (no todo kiosco):
  N1 total/suma/**ahorro**(semanas)/**edad**/**cuadras**(distancia), N2 vuelto/falta/
  comparar, N3 reparto/cuantos/**unitario**(precio c/u), N4 descuento/**promedio**/
  **porcentaje**, N5 oferta/combo. Suma operaciones nuevas (`add`, `sub`, porcentaje,
  promedio) y respuestas en pesos O en cuentas/años/cuadras según el tipo. **DE-DUP
  por sesión**: `gen_kiosco` reconstruye los problemas 0..idx y bumpea un `salt` si
  una firma (kind+números) ya salió, así en una ronda **no se repite ningún problema
  ni sus números** (determinista → el server re-deriva idéntico). Todas las respuestas
  enteras exactas por construcción (unitario/promedio/porcentaje dividen justo). Tests
  (`cada_tipo_cumple_su_formula` sobre los 16, `cobertura_por_grado` por pools,
  `sin_repetidos_en_la_ronda`); E2E `tools/e2e_problemas.py` juega grade 4 Y grade 7
  resolviendo cada tipo desde el enunciado → 10/10 + 10 enunciados distintos por ronda,
  paridad run↔binario.
- **Fase C. ✅ (2026-08-24)** Arranque adaptativo cross-sesión para los 5 juegos de
  secundaria: el rating de mastery del juego nudgea el grado EFECTIVO con el que se
  calculan piso/techo (reusa `grado_efectivo(grade, rating)` del motor F3, el mismo
  que usan los juegos de aritmética). Nuevo `leer_rating(profile_id, skill) -> Float`
  en `mastery.fitz` (default 800 = a ciegas). Cada `live_*` de secundaria, al abrir
  el socket, lee el rating de la **destreza ancla** (ecuaciones→`ec.lineal`,
  potencias→`pot.entera`, trig→`trig.pitagoras`, funciones→`func.lineal`,
  finanzas→`pct.basico`), computa `eff = grado_efectivo(ctx.grade, rating)` (congelado
  por sesión, patrón del snapshot F3), y usa `eff` para el componente Y la
  persistencia (mismo generador → paridad). Un chico que domina la destreza ancla
  arranca más arriba (hasta +3 grados, banda 8..13); uno que arranca a ciegas juega a
  su grado real; uno que struggle baja (nunca por debajo de la banda). Tests
  (`fase_c_grado_efectivo_por_rating`, `fase_c_rating_alto_sube_la_ventana_de_nivel`).
  Smoke E2E `tools/e2e_fase_c.py`: dos 1° sec en Ecuaciones — el de rating 1200 arranca
  en nivel 2 (cuadrática, boosteado a grado efectivo 10), el de a ciegas en nivel 1
  (lineal); paridad run↔binario. **Con esto F8 (niveles y progresión graduada) queda
  cerrada: escala por grado (A) + rampa en la ronda (A/B) + adaptativo cross-sesión (C).**

---

## 11.d Backlog de juegos futuros (F9)

Sumar un juego es un patrón **mecánico de ~9 archivos** (probado con Series,
2026-08-25): `gen_<x>.fitz` (generador reproducible por nivel) + `<X>.fitzv`
(componente) + `<x>_view.fitz` (render) + `live_<x>.fitz` (ruta `@get` + `@ws` +
persistencia) + fila en `juegos.fitz` (con `min_grade`/`icon`/`route`/`modalidad`)
+ migración del `CHECK sessions_mode_valido` (si estrena `mode`) + claves i18n
(ES/EN) + `tests/<x>.fitz` (invariantes del generador) + registro en `main.fitz`
(import de `live_<x>` + símbolos del componente). Dos cosas lo hacen escalable:
el menú ya **filtra por grado** (`min_grade`) y **modalidad** (común/comercial), y
el modelo de niveles de F8 (`nivel_piso_*`/`nivel_techo_*` + `nivel_por_idx`) hace
que **un mismo juego cubra de 1° a 6° secundaria** graduando dificultad — no hace
falta un juego por grado.

Cada juego nuevo debe: alimentar mastery/racha (persistir Attempt + `actualizar_mastery`
con su `skill_code`), sumar récord por juego (`leer_record`/`guardar_record` en el
`live_*`), emitir `data-fb-seq` (sonido) + `racha_badge` + `progreso_bar` (ronda
fija), y cerrar con `resumen_estrellas` + `mejor_racha_html`. Paridad `fitz run` ↔
binario + E2E dedicado (`tools/e2e_<x>.py`) obligatorios antes de cerrar.

### A — Cartas ya reservadas en el menú (`built: false` → "Próximamente")

Estas seis ya tienen su fila en `juegos.fitz` con `min_grade`; sólo falta construirlas.

| Carta | `min_grade` | Modalidad | Mecánica | Escalado por nivel |
|---|---|---|---|---|
| 📖 Historia | 1° | común | Problemas narrados cortos leídos en voz (Web Speech API, pre-lectores); elegir la operación/resultado | N1 suma/resta 1 paso → N5 varios pasos + fracciones/% |
| 🕐 Hora ✅ | 2° | común | **HECHO (2026-08-25)** — leer el **reloj analógico SVG** (agujas por `transform="rotate"`, sin trig); opción múltiple "H:MM" | N1 en punto → N2 y media → N3 cuartos → N4 de a 5 → N5 minuto exacto (los intervalos "¿cuánto falta para…?" quedan como Hora v2) |
| 📐 Geometría ✅ | 5° | común | **HECHO (2026-08-25)** — área/perímetro con **figura SVG** (cuadrado/rectángulo/triángulo/L); teclado, respuestas enteras | N1 perímetro cuadrado → N2 perímetro rect → N3 área rect → N4 área triángulo → N5 área L compuesta (el círculo con π queda como Geometría v2) |
| ％ Porcentaje | 6° | común (útil comercial) | Descuentos, IVA, recargo; enunciado con historia | N1 % simple → N2 descuento → N3 IVA 21% → N4 recargo/cuotas → N5 % sucesivos |
| 📦 Volumen | 6° | común | Volumen de cuerpos con **figura SVG 3D** (prisma, cubo, cilindro) | N1 cubo → N2 prisma → N3 cilindro → N4 con conversión de unidades → N5 compuestos |
| ± Enteros | 7° | común | **Recta numérica SVG** interactiva; suma/resta con signo (teclado con ±) | N1 recta hasta ±10 → N2 suma signos → N3 resta signos → N4 multiplicación de signos → N5 varias operaciones |

### B — Modos nuevos que cubren huecos pedagógicos (transversales, todos los grados)

No son "un tema" sino **otra forma de pensar** (como Series suma razonamiento inductivo).
Requieren mecánica de input distinta al teclado → primer candidato a definir bien.

| Modo | Ícono | Mecánica | Por qué suma | Escalado |
|---|---|---|---|---|
| Memoria / Parejas | 🃏 | Grilla de cartas; unir expresión ↔ resultado (`3×4` ↔ `12`), fracción ↔ decimal, etc. Memoria espacial + cálculo. | Otro modo cognitivo (memoria de trabajo), no "resolvé y tipeá" | N1 sumas 1 dígito → N5 fracciones/potencias; más pares por nivel |
| Ordenar / Comparar | 📊 | Arrastrar (o tocar en orden) de menor a mayor: números, fracciones, decimales, enteros con signo. | Sentido de orden y magnitud; sin él, fracciones/enteros quedan abstractos | N1 naturales → N2 decimales → N3 fracciones → N4 enteros → N5 mezcla |
| Estimación | 🎯 | "¿Está cerca?" — redondear, estimar el resultado sin calcular exacto; se acepta un rango. | Sentido numérico (number sense), la habilidad que más falta en cálculo mental | N1 redondeo a la decena → N5 estimar productos/porcentajes |

### Orden recomendado

1. ~~**🕐 Hora (2°)**~~ — ✅ **HECHO (2026-08-25)**: reloj analógico SVG + opción múltiple, 5 niveles de precisión, E2E que lee el reloj del SVG.
2. ~~**📐 Geometría (5°)**~~ — ✅ **HECHO (2026-08-25)**: cuadrado/rectángulo/triángulo/L en SVG + teclado, E2E que recomputa la fórmula.
3. **🃏 Memoria (transversal)** — el primer modo de input nuevo (grilla de cartas); define el patrón para Ordenar/Estimación. **← próximo sugerido**
4. **± Enteros (7°)** — recta numérica SVG, refuerza el signo (que hoy sólo aparece incidental en secundaria).
5. **📖 Historia (1°)** — depende de Web Speech API (pre-lectores); más UX que matemática.
6. Resto (Porcentaje, Volumen, Ordenar, Estimación) según demanda/feedback.

> **Nota de estado (2026-08-25):** con 🧩 Series, 🕐 Hora y 📐 Geometría construidos,
> el catálogo activo es de **14 juegos** (contrarreloj, V/F, series, completá, escalera,
> problemas, fracciones, hora, geometría, potencias, ecuaciones, finanzas, trigonometría,
> funciones). Este backlog llevaría el catálogo a ~21 con cobertura de 1° a 6° secundaria
> en varios modos cognitivos.

---

## 12. Lo que necesito de tu lado

1. **Versión de Fitz instalada** — `fitz --version`. El plan asume ≥ v0.42.1 (`@every` y `ws_broadcast` desde el scheduler). Si tenés menos, el cronómetro va con `@background`+`spawn`, que anda desde antes.
2. **Dónde vive el proyecto** — la carpeta conectada `D:\MathHelp` está vacía. ¿Genero todo ahí?
3. **El logo** — abajo va la propuesta. Decime si va, si le cambio algo, o si querés que pruebe otro concepto.

---

*MatHelp · Hecho con [Fitz](https://github.com/Thegreekman76/fitz) y [Fitz LiveViews](https://github.com/Thegreekman76/fitz-liveviews)*
