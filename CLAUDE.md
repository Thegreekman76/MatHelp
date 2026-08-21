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

## Módulos aislados: no los "mejores"

Estos siete archivos envuelven limitaciones actuales de Fitz v0.47.0, **usando a propósito la firma que va a tener la solución oficial**:

| Archivo | Envuelve | Migra a |
|---|---|---|
| `src/rng.fitz` | no hay `random` en la stdlib | `rand.seeded()` |
| `src/fmt.fitz` | los format specs no conocen locale | `num.format(x, locale:)` |
| `src/cookies.fitz` | no hay API de cookies | `@cookie` + `Response.cookies` |
| `src/i18n.fitz` + `cat_*.fitz` | no hay filesystem | `fs.read()` |
| `src/assets.fitz` | no sirve estáticos | `@server(static_dir=)` |
| `src/layout.fitz` | `live_layout` con el head fijo | `live_layout_with` |
| `db_queries` (pendiente) | `preload` roto, `.is_in` con literal | ORM |

**Están escritos para ser fáciles de borrar, no para ser bonitos.** No los refactorices para hacerlos más elegantes: el objetivo es que el día que el lenguaje incorpore la feature, migrar sea borrar un archivo y cambiar un import.

Si tenés que agregar un workaround nuevo, seguí el mismo patrón: un módulo, con la firma futura, con un comentario arriba explicando qué limitación envuelve y cuál es el ID del backlog.

---

## Trampas de Fitz v0.47.0 (todas encontradas a los golpes)

**`fitz check` y `fitz run` NO garantizan que `fitz build` funcione.** Antes de dar por cerrado cualquier cambio, corré `fitz build`. Tres casos ya conocidos:

- **Funciones que devuelven `T?`** generan Rust que no compila (`return ()` en vez de `return None`). Por eso `read_cookie` devuelve `Str` con `""` como centinela en vez de `Str?`. **No lo "arregles" volviendo a `Str?`.** Ver `docs/BUG-fitz-option-codegen.md`.
- **`let x = []` infiere `List<Any>`** y el codegen rechaza `Str + Any`, aunque el checker lo acepte. Anotá siempre el tipo de las listas vacías.
- **`.preload()` en el intérprete es un no-op silencioso**: devuelve relaciones vacías sin error. Usá joins explícitos.

**Otras:**

- Las **listas son por referencia**. `let out = items` alias-ea: si mutás, rompés la lista del llamador. Copiá con `.map(fn(v) => v)`. Hay test de regresión en `tests/rng.fitz`.
- Interpolar un `Html` en un string imprime `Html { raw: "..." }`. Siempre `.raw`.
- Las **llaves literales de CSS van escapadas** `\{` `\}` dentro de un string de Fitz.
- **Nunca un `<style>` o `<script>` dentro del root diffeado**: el parser lo degrada a reemplazo completo **en silencio**. Todo el CSS va al `<head>` en `layout.fitz`.
- Los statements de top level se ejecutan al arrancar; `fn main()` sola no corre nada.
- `fitz run src/main.fitz` **no resuelve dependencias**. Usá `fitz run` a secas (modo manifiesto).

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

F0 cimientos ✅ · **F1 auth y perfiles ← acá estamos** · F2 primer juego · F3 motor adaptativo · F4 más juegos · F5 panel del padre · F6 pulido · F7 secundaria

El detalle de cada una, en `docs/PLAN.md`.
