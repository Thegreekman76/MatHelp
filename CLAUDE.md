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

F0 cimientos ✅ · F1 auth y perfiles ✅ · F2 primer juego ✅ · **F3 navegación ✅ (menú §6.5 + elegir juego + práctica libre) → F3 motor adaptativo ← acá** · F4 más juegos · F5 panel del padre · F6 pulido · F7 secundaria

El detalle de cada una, en `docs/PLAN.md`.
