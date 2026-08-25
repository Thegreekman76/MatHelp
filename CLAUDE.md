# MatHelp — instrucciones para Claude Code

Juego de matemática para chicos de primaria (6–12), después secundaria.
Mobile-first, es-AR + en, PostgreSQL, dockerizado. 100 % Fitz + Fitz LiveViews.

**Antes de tocar nada, leé `docs/PLAN.md`.** Ahí está el estado actual, lo que falta por fase y la deuda anotada.

---

## Las dos reglas que no se rompen

1. **Ningún string visible se escribe en un template.** Siempre `t(locale, "clave")`.
2. **Ningún número crudo en la UI.** Siempre `fmt_int` / `fmt_dec` / `fmt_pct` / `fmt_money`.

La segunda no es cosmética. En Argentina se escribe `1.234,5`, en inglés `1,234.5`. Un juego de matemática que muestra mal los decimales le está enseñando mal al chico que lo usa. Es un bug de producto, no de formato.

Corolario: `locale_from_cookie(cookie)` es la **primera línea de todo handler**, incluido el `@ws`. Si el locale no llega al socket, los diffs vuelven en el idioma equivocado — fácil de cometer, confuso de debuggear.

---

## Migrado a nativo (fitz v0.55 + liveviews v0.50) — sin módulos-workaround

MatHelp nació sobre Fitz v0.47, que todavía no tenía varias features, así que las envolvía en módulos aislados. **Ese trabajo cerró el backlog de dogfooding: desde fitz v0.55 + fitz-liveviews v0.50 todo es nativo** y los workarounds se borraron.

| Antes (workaround, borrado) | Ahora (nativo) |
|---|---|
| `src/rng.fitz` (PRNG propio) | `rand.seeded(n)` — secuencia reproducible run↔build (FITZ-01). Lo usará el juego (F2). |
| `src/fmt.fitz` (formato locale) | `num.format` / `num.percent` / `num.currency` (FITZ-04). Lo usará el juego (F2). |
| `src/cookies.fitz` (parser propio) | `@cookie(name=)` para leer + `Response { cookies: [Cookie {...}] }` para escribir |
| manifest en `src/assets.fitz` | `public/manifest.webmanifest` + `@server(static_dir="public")` |

**Se quedan** (decisiones de arquitectura, no workarounds):

- **`src/i18n.fitz` + `cat_*.fitz`**: catálogos horneados por `tools/gen_i18n.py`. `fs.read()` existe, pero hornear en compile-time es más rápido (sin fs ni parser JSON por request) — elección deliberada.
- **`src/layout.fitz`**: shell del documento de F0 (páginas estáticas). `live_layout_with` de liveviews es para páginas **live** (inyecta el runtime WebSocket); se evalúa cuando el juego (F2) tenga páginas interactivas.
- **`src/assets.fitz`**: el favicon se GENERA con `logo_svg_raw()` (single-source-of-truth de la marca) — sigue siendo una ruta `@get`, no un archivo duplicado.

Regla: usá la feature nativa. No reintroduzcas workarounds. Si encontrás un bug del lenguaje, anotalo en el `norte-mathelp.md` del repo que corresponda con repro mínimo — MatHelp es el **dogfooding de Fitz**.

---

## Trampas de Fitz — cerradas y vigentes

**`fitz check`/`fitz run` no garantizan que `fitz build` funcione.** Antes de cerrar un cambio, corré `fitz build`.

Trampas que MatHelp encontró y que **ya están cerradas** (fitz v0.49–v0.55):

- `Str?` con `return null` adentro → E0308 (**FITZ-09, cerrado**). Ya no hace falta el centinela `""`.
- `let x = []` → `List<Any>` + `Str + Any` rechazado (**FITZ-10, cerrado**). Igual conviene anotar listas vacías.
- cookies cross-module en `fitz build` (**cerrado en fitz v0.54**) y `@cookie` sobre `@ws` (**v0.53**).
- `Map<Str,Any>.keys()` en el codegen (**cerrado en fitz v0.55**).

Vigentes:

- Las **listas son por referencia**. `let out = items` alias-ea: si mutás, rompés la del llamador. Copiá con `.map(fn(v) => v)`.
- Interpolar un `Html` en un string imprime `Html { raw: "..." }`. Siempre `.raw`.
- Las **llaves literales de CSS van escapadas** `\{` `\}` dentro de un string de Fitz.
- **Nunca un `<style>`/`<script>` dentro del root diffeado**: se degrada a reemplazo completo **en silencio**. Todo el CSS va al `<head>` en `layout.fitz`.
- Los statements de top level corren al arrancar; `fn main()` sola no corre nada.
- `fitz run src/main.fitz` **no resuelve dependencias**. Usá `fitz run` a secas (modo manifiesto).
- **Residual conocido de fitz** (follow-up abierto): un map literal `Map<Str,Any>` **no-vacío** (`{ "k": 10 }`) no coacciona entradas → E0308. Construí el map vacío + `m[k] = v`.
- **check✓/build✗ en aridad de fns importadas (FITZ-22).** `fitz check` NO caza una llamada con aridad incorrecta a una fn de otro módulo; recién explota en `fitz build`. Refuerza la regla: corré `fitz build` antes de cerrar. (Anotado en el norte de fitz.)
- **Un test no puede llamarse igual que el módulo que importa (FITZ-21).** `tests/foo.fitz` con `from foo import ...` (apuntando a `src/foo.fitz`) se auto-importa → "ciclo de imports". Por eso el test del motor es `tests/motor.fitz`, no `tests/engine.fitz`. (Anotado en el norte de fitz.)
- **El ORM no tiene upsert nativo.** Para "insert-or-update" (mastery, streaks, awards) usá `conn.exec("INSERT ... ON CONFLICT (...) DO UPDATE ...", [params])` — atómico y race-safe. La lista de params puede ser heterogénea (`[Int, Str, Float, ...]`) pero debe ser **literal inline** en el call site (no una variable) para que `fitz build` la acepte.

---

## Comandos

```
fitz check           typecheck de todo
fitz test            los tests de tests/*.fitz
fitz run             servidor en :3000 (modo manifiesto, resuelve deps)
fitz dev             con recarga automática
fitz build           OBLIGATORIO antes de cerrar un cambio
python tools/gen_i18n.py    recompila los catálogos desde locales/*.json
```

Docker: `start.bat` / `stop.bat` / `logs.bat` / `reset.bat`.

---

## Dos manifiestos

`fitz.toml` usa `{ git = ... }`. `fitz.docker.toml` usa `{ path = "/vendor/..." }` porque la imagen oficial de Fitz no trae `git`.

**Si tocás las dependencias, actualizá los dos.** Es la trampa más fácil de este repo.

Para desarrollo con los repos al lado, en `fitz.toml`:
```toml
fitz_liveviews = { path = "../fitz-liveviews" }
```

---

## Traducciones

Fuente de verdad: `locales/*.json`. Después de editarlos, `python tools/gen_i18n.py`.

**El generador falla si a un locale le falta una clave.** Es a propósito. No lo saltees ni relajes la validación.

`src/cat_*.fitz` son **generados**. No los edites a mano.

---

## Si algo se rompe: ¿es la app o el lenguaje?

Los tres repos están en el mismo workspace, así que hay una tentación real de arreglar MatHelp para esquivar un bug de Fitz. **Preguntate primero de quién es el problema.**

Si es del lenguaje o del framework: anotalo en el `norte-mathelp.md` del repo que corresponda, con evidencia `archivo:línea` y repro mínimo, y recién después poné el workaround acá — aislado y con el ID del backlog en el comentario.

MatHelp es el dogfooding de Fitz. Un bug que se esconde detrás de un workaround silencioso es un bug que se le va a aparecer al próximo usuario.

---

## Fases

F0 cimientos ✅ · F1 auth y perfiles ✅ · F2 primer juego ✅ · **F3 que aprenda ✅ (navegación §6.5 + motor adaptativo: Elo-lite, selección 70/20/10, repaso espaciado, racha diaria, medallas, desafío del día, mate-progreso)** · **F4 más juegos ✅ (V/F, completá el hueco con teclado propio, escalera de tablas, el kiosco, fracciones a la vista — cada uno enchufado como fila en `juegos.fitz` + `.fitzv` + `live_*.fitz`, alimenta mastery/racha igual que el contrarreloj)** · **F5 panel del padre ✅** · **F6 pulido ✅ (reanudar desafío + `ended_at`; accesibilidad foco-visible + skip-link; sonido opcional `public/sound.js`; PWA `public/sw.js` + manifest — falta Lighthouse/Android real)** · **Pulido general (2026-08-24, `game_ui.fitz` compartido): (1) `resumen_estrellas` (★ por precisión + frase de aliento i18n) en los 10 resúmenes; ronda perfecta 10/10 → estrellas con brillo (`.mh-estrellas.perfect`). (2) micro-animaciones en `brand.fitz` (pop acierto, shake error, medalla bounce, slot scale, estrellas) + `prefers-reduced-motion` extendido a animaciones. (3) **SONIDO revivido**: el `sound.js` de F6 estaba muerto (escuchaba `.q-fb[data-fb-seq]` pero ningún banner lo emitía salvo quiz) — ahora los 8 juegos restantes emiten `data-fb-seq` (beep por acierto/error). (4) elogio VARIADO: `correcto_msg(locale, seq)` rota 4 frases positivas por respuesta (antes siempre "¡Muy bien!"). E2E verifica estrellas + perfect + `data-fb-seq` run↔binario. (5) **RACHA visible**: campo `racha` en los 10 componentes (sube en acierto, resetea en error), insignia `racha_badge` (🔥N, "hot" a partir de 5) en el HUD de todos los juegos (threading a los sub-fns de render en quiz/vf/escalera). (6) **barra de progreso** `progreso_bar(total, limit)` en los juegos de ronda fija (keypad + frac + quiz desafío/potencias). E2E verifica `q-racha` + `q-progress` run↔binario. (7) **error variado + amable**: `incorrecto_msg(locale, seq, resp)` rota 3 frases que dan aliento (antes una sola). (8) **confetti** CSS en la ronda perfecta (`confetti_html` + 12 piezas en brand.fitz, respeta reduced-motion). (9) **teclado físico** (`public/sound.js`): en los juegos de teclado, las teclas 0-9/⌫/Enter/± disparan los botones (gateado a la presencia de botones de dígito). E2E verifica `mh-confetti` en 10/10. (10) **mejor racha**: `mejor_racha_html` muestra "🔥 Mejor racha: N" en la pantalla final (la mayor cantidad de aciertos seguidos de la ronda, persiste aunque después se falle; `racha_max` en los 10 componentes). (11) **sonido de hito**: acorde ascendente C5-E5-G5 (`chord()`) al llegar a 5/10 seguidos (la insignia lleva `data-racha`, `sound.js` lo observa). E2E verifica `mh-mejor-racha` en 10/10.** · **F7 secundaria ✅ (F7.0 modelo: `Profile.modalidad` + `grade` 8..13 + form con orientación; F7.1 enteros con signo: `gen_arith.gen_sec` + `fmt_operando` parentiza negativos → los juegos de opción múltiple sirven enteros con signo a secundaria sin pantalla nueva, primaria bit-a-bit intacta, `Completá` clampeado a positivo; F7.1.b juego "Potencias y raíces" (`/potencias`, reusa el componente Quiz en mode "potencias" + `gen_potencia` + `prompt_potencia`, migración 0004 suma el mode al CHECK); F7.1.c notación científica → **F7.1 COMPLETA**; teclado con `±` (`kp_signo` + `touched` en Completá para enteros negativos); F7.2 COMPLETA juego "Ecuaciones" (`/ecuaciones`, `Ecuaciones.fitzv` + `gen_ecuacion` 1er grado + cuadrática + sistemas 2×2 con `Exercise.a2/b2/answer2`, teclado, mode `numpad`); F7.3 COMPLETA juego "Finanzas" (`/finanzas`, `Finanzas.fitzv` + `gen_finanzas` interés simple/compuesto + % + descuento + punto de equilibrio con respuestas enteras positivas, teclado sin ±, enunciados con historia localizados `t2`/`t3` + `fmt_money`, mode `story`, `topic_code` `fin`; **diferencial COMERCIAL**: `Juego.modalidad` + `grilla_juegos` filtra por la modalidad del perfil → sólo los comerciales del Ciclo Orientado lo ven); F7.4 COMPLETA juego "Trigonometría" (`/trigonometria`, `Trigonometria.fitzv` + `trig_view.fitz` + `gen_trig` — **primer SVG dinámico del proyecto**: triángulo rectángulo con figura, Pitágoras hallar hipotenusa/cateto con ternas + razón 30° sin(30)=1/2, teclado sin ±, `triangulo_svg` estilado por clases `.tg-*`, mode `numpad`, `topic_code` `trig`, modalidad `comun`; el SVG geométrico sobrevive el diff de LiveView — FLV-02 sólo aplica a `<style>/<script>` en root); F7.5 COMPLETA juego "Funciones" (`/funciones`, `Funciones.fitzv` + `func_view.fitz` + `gen_func` — evaluar f(x) lineal/cuadrática/exponencial con FÓRMULA (con `<sup>`) + GRÁFICO SVG de la familia, respuesta posiblemente negativa → teclado con ±, mode `numpad`, `topic_code` `func`, modalidad `comun`). **F7 secundaria ✅ COMPLETA** (F7.0–F7.5))** · **F8 niveles y progresión graduada — Fase A ✅ (2026-08-24): los 5 generadores de secundaria (potencias/ecuaciones/finanzas/trig/funciones) escalan por grado (tablas `nivel_piso_*`/`nivel_techo_*`) + rampa por `idx` dentro de la ronda vía `nivel_por_idx` — antes ignoraban `grade`. `Exercise.difficulty = nivel`. Verificado E2E (`tools/e2e_niveles.py`): grade 10 sólo Pitágoras dif 1→3, grade 13 suma razón dif 2→5. **Fase B ✅ (2026-08-24): (1) rampa por idx en Fracciones; (2) el kiosco "muy pobre" (sólo vuelto) → juego "Problemas" de la vida real, renombrado a "Problemas" en /problemas ícono 🧮 (código interno sigue "kiosco"). **16 tipos en pools por nivel con contextos variados de la vida real** (N1 total/suma/ahorro/edad/cuadras, N2 vuelto/falta/comparar, N3 reparto/cuántos/unitario, N4 descuento/promedio/porcentaje, N5 oferta/combo — el tipo se elige al azar en el pool; respuestas en pesos o en cuentas/años/cuadras) + **de-dup por sesión** (gen_kiosco reconstruye 0..idx y bumpea un salt ante colisión de firma kind+números → no se repite ningún problema en la ronda, determinista/paridad). Localizado, skill por operación (add/sub/mul.tabla/dec.dinero/div.exacta), respuestas enteras exactas. E2E `tools/e2e_problemas.py`: grade 4 Y grade 7 resuelven 10/10 con 10 enunciados distintos, paridad run↔binario.** **Fase C ✅ (2026-08-24): arranque adaptativo cross-sesión en los 5 juegos de secundaria — `leer_rating(profile_id, skill)` nuevo en mastery.fitz + cada live_* lee el rating de la destreza ancla al abrir el socket y computa `eff = grado_efectivo(ctx.grade, rating)` (congelado por sesión) que usa para componente + persistencia. El que domina arranca más arriba; el de a ciegas juega a su grado; el que struggle baja. E2E `tools/e2e_fase_c.py`: 1° sec con rating 1200 arranca nivel 2 (cuadrática) vs a ciegas nivel 1. Paridad run↔binario.** F8 CERRADA entera (A escala por grado + A/B rampa en ronda + C adaptativo cross-sesión). Diseño en `docs/PLAN.md` §11.c** · **Juego NUEVO "Series" ✅ (2026-08-25): patrones numéricos ("2, 4, 6, 8, ___" → tipeá el 5º), enseña razonamiento INDUCTIVO (habilidad distinta a "calculá esto"). `gen_series.fitz` escala por nivel (N1 aritméticas, N2 +descendentes, N3 duplicar/cuadrados, N4 triplicar/diferencias-crecientes, N5 Fibonacci/×2+1/inc-diff), respuesta entero positivo (teclado sin ±), reproducible. Cableado entero: `Series.fitzv` (teclado, eventos digito/borrar/answer) + `series_view.fitz` + `live_series.fitz` (mode `series` migración 0005, skill `patron`) + carta en `juegos.fitz` (/series 🧩 min_grade 1) + registro en main + i18n (`juego.series`/`series.pregunta`/`tema.series`) + `tests/series.fitz` (reproducibilidad, no-negatividad, 4 términos, aritmética exacta grado 1, rampa). E2E `tools/e2e_series.py`: grado 2 (nivel 1) y grado 13 (hasta nivel 5, con solver de todas las familias) resuelven 10/10, paridad run↔binario. Pulido extra: `.q-done` con transición fade-in-up (`@keyframes done-in`, respeta reduced-motion).** · **Récord por juego ✅ (2026-08-25): `profile_game_stats` (migración 0006, upsert GREATEST race-safe) guarda la mejor racha histórica por (perfil, juego). `records.fitz` (`leer_record`/`guardar_record`, best-effort → 0 si falla). Cada `live_*` lee el récord al abrir el socket (→ `record_prev` en el componente, default alto 999999 para que un juego sin wirear muestre "Mejor racha" y nunca un récord falso) y lo sube al cerrar. `mejor_racha_html(locale, racha_max, record_prev)` decide: `racha_max > record_prev` → "🏆 ¡Nuevo récord: N!" (`.mh-record`), si no → "🔥 Mejor racha: N". Los 11 juegos wireados con game_code propio (contrarreloj/desafio/potencias comparten el componente quiz pero récord separado; los timed contrarreloj/vf pasan `profile_id` al `@background timer` donde vive el done; practica es infinito → sin récord). E2E (series + problemas) verifican `mh-record` + `best_streak=10` en DB, run↔binario.**

El motor adaptativo (F3) vive en `src/engine.fitz` (Elo-lite puro, testeado en
`tests/motor.fitz`), `src/gen_arith.fitz` (`gen_adaptive` 70/20/10),
`src/mastery.fitz` (upsert `ON CONFLICT` por respuesta + snapshot),
`src/streaks.fitz` (racha diaria + medallas) y `src/progreso.fitz` (Mi progreso).
El upsert de mastery/streaks/awards es SQL crudo atómico — el ORM de Fitz no
tiene upsert nativo.

El detalle de cada una, en `docs/PLAN.md`.
