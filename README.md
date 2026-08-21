# MatHelp

**Matemática que se comparte.** Juego de matemática para practicar las operaciones, de primaria a secundaria.

Mobile-first, en español rioplatense e inglés, hecho 100 % con [Fitz](https://github.com/Thegreekman76/fitz) y [Fitz LiveViews](https://github.com/Thegreekman76/fitz-liveviews).

---

## Arrancar

Necesitás **Docker Desktop** corriendo. Nada más — ni Fitz, ni Rust, ni Postgres instalados.

```
start.bat
```

Eso construye todo, levanta la app y Postgres, y te abre el browser en `http://localhost:3000`.

La primera vez tarda unos minutos porque compila el binario nativo. Después arranca en segundos.

| Script | Qué hace |
|---|---|
| `start.bat` | Levanta todo y abre el browser |
| `stop.bat` | Apaga los contenedores (los datos quedan) |
| `logs.bat` | Logs en vivo |
| `reset.bat` | Borra la base y el volumen — pide confirmación |

### Verlo en el celular

`start.bat` te imprime la IP de tu máquina en la red local. Desde el celu, conectado al mismo WiFi, entrá a `http://<esa-ip>:3000`.

Como hay `manifest.webmanifest`, desde el browser del celular podés hacer "Agregar a pantalla de inicio" y se abre sin barra, como una app.

### Si falla el build

Si el error es al bajar `ghcr.io/thegreekman76/fitz`, usá el fallback que compila Fitz desde el código fuente:

```
docker compose -f docker-compose.yml -f docker-compose.source.yml up -d --build
```

Tarda bastante más la primera vez, pero después Docker cachea la capa.

---

## Desarrollo sin Docker

Con Fitz instalado:

```
fitz check      # typecheck de todo
fitz test       # 33 tests
fitz run        # servidor en :3000
fitz dev        # con recarga automática
fitz build      # binario nativo (~9x más rápido que el intérprete)
```

Necesitás Postgres andando y `DATABASE_URL` apuntándole (o dejá que el chequeo de estado marque desconectado — la app igual levanta).

Si tenés el repo de `fitz-liveviews` al lado, cambiá la dependencia en `fitz.toml`:

```toml
fitz_liveviews = { path = "../fitz-liveviews" }
```

---

## Traducir

Los catálogos viven en `locales/*.json`. Editás el JSON y corrés:

```
python tools/gen_i18n.py
```

Eso los compila a módulos Fitz (`src/cat_*.fitz`). Existe ese paso porque Fitz todavía no puede leer archivos en runtime.

**El script falla si a un locale le falta una clave** — a propósito: es lo que evita que alguien agregue texto y se olvide de traducirlo.

Para agregar un idioma: creá `locales/<code>.json`, corré el generador, e importá el catálogo nuevo en `src/i18n.fitz`.

---

## Cómo está armado

```
src/
  main.fitz       rutas y arranque
  config.fitz     configuración por entorno
  layout.fitz     shell mobile-first (head, topbar, footer)
  brand.fitz      logo SVG inline, footer, CSS
  i18n.fitz       t(locale, clave) + resolución del locale
  cat_*.fitz      catálogos (GENERADOS — no editar)
  rng.fitz    ⟵  aislado: PRNG determinístico
  fmt.fitz    ⟵  aislado: números por locale
  cookies.fitz ⟵ aislado: sesión e idioma
  assets.fitz ⟵  aislado: favicon y manifest como rutas
```

Los módulos marcados **⟵ aislado** envuelven limitaciones actuales de Fitz v0.47.0, **usando la firma que va a tener la solución oficial**. El día que el lenguaje las incorpore, migrar es borrar el archivo y cambiar un import — no refactorizar la app.

El detalle de cada una está en `docs/PLAN.md` §1.2 y §1.4.

---

## Dos reglas que no se rompen

1. **Ningún string visible se escribe en un template.** Siempre `t(locale, "clave")`.
2. **Ningún número crudo en la UI.** Siempre `fmt_int` / `fmt_dec` / `fmt_pct` / `fmt_money`.

La segunda no es cosmética: en Argentina se escribe `1.234,5`, en inglés `1,234.5`. Un juego de matemática que muestra mal los decimales le está enseñando mal al chico.

---

*Hecho con [Fitz](https://github.com/Thegreekman76/fitz) y [Fitz LiveViews](https://github.com/Thegreekman76/fitz-liveviews).*
