# Addendum al backlog — hallazgos construyendo MatHelp

> Pegá esto en Claude Code después del prompt principal, o directamente si ya
> tenés los `norte-mathelp.md` escritos. Son hallazgos **nuevos**, encontrados
> escribiendo y dockerizando MatHelp de verdad — no releyendo los docs.

---

## CONTEXTO

Ya está construida la **fase F0 de MatHelp** (cimientos: shell mobile-first, i18n es-AR/en, marca, assets, esquema de Postgres, Docker). 33 tests pasando, todo verificado contra `fitz 0.47.0` compilado desde el repo.

En el camino aparecieron **cuatro hallazgos que no estaban en la auditoría original**, más una refutación importante. Ninguno salió de leer documentación: los cuatro salieron de correr el compilador.

Agregalos a los `docs/norte-mathelp.md` con los IDs que van abajo, y **re-priorizá la lista completa** teniéndolos en cuenta — porque uno de ellos cambia el orden.

---

## FITZ-09 · Codegen: las funciones que devuelven `T?` compilan mal — **ALTO**

**Estado:** confirmado con repro mínimo.

Una función que declara `-> Str?` y hace `return null` o `return <valor>` genera Rust que no compila. El codegen emite `return ()` donde va `return None`, y devuelve el valor sin envolver en `Some(...)`.

**Repro completo, 20 líneas, sin dependencias:**

```fitz
// src/main.fitz
fn primera_parte(s: Str?) -> Str? {
    let raw: Str = match s {
        null => return null,
        v => v,
    }
    for parte in raw.split(",") {
        return parte
    }
    return null
}

@get("/")
fn home() -> Str {
    return match primera_parte("a,b") {
        null => "nada",
        v => v,
    }
}

@server(3000)
fn main() => 0
```

```
$ fitz check   →  ✓ no type errors
$ fitz run     →  🏔️  Fitz HTTP escuchando en http://0.0.0.0:3000
$ fitz build   →  ✗ error[E0308]: mismatched types
```

**Rust generado, los dos defectos:**

```rust
pub fn read_cookie(mut header: Option<String>, mut name: String) -> Option<String> {
    let mut raw: String = (match header.clone() { None => { return () }, Some(h) => h.clone() });
//                                                         ^^^^^^^^^ esperaba Option<String>, encontró ()
    ...
    ... __g[__e as usize].clone() };
//      ^^^^^^^^^^^^^^^^^^^^^^^^^ esperaba Option<String>, encontró String
//      help: try wrapping the expression in `Some`
```

El propio `rustc` sugiere el arreglo.

**Por qué es alto y no medio:** no alcanza con evitarlo en el código de la app. `flv_cookie`, **dentro de fitz-liveviews**, tiene exactamente el mismo patrón:

```
error[E0308]: mismatched types
    --> src/fitz_liveviews.rs:1432:76
1431 | pub fn flv_cookie(mut cookie: Option<String>, mut name: String) -> Option<String> {
1432 |     let mut raw: String = (match cookie.clone() { None => { return () }, ... });
     |                                                            ^^ expected `Option<String>`, found `()`
```

O sea: **cualquier proyecto que dependa de fitz-liveviews y compile a nativo choca con esto**, haga lo que haga en su propio código. Y `flv_cookie` no es una función marginal — es la que resuelve el locale y la sesión desde la cookie del handshake, la que necesita toda app con i18n o con auth.

**Verificá específicamente si `examples/admin` compila hoy con `fitz build`**, o si solo se probó con `fitz run`. Si es lo segundo, la app insignia del framework no compila a nativo.

**Consecuencia real en MatHelp:** el Dockerfile corre el intérprete en vez del binario nativo. Se pierde el ~9x de performance y el runtime distroless. La versión compilada quedó comentada en el Dockerfile, lista para descomentar.

**Criterio de aceptación:**
1. El repro compila con `fitz build` y `GET /` devuelve `"a"`.
2. `fitz-liveviews` compila entero, `flv_cookie` incluida.
3. El repro da salida idéntica por `fitz run` y por `fitz build`.

---

## FITZ-10 · `Str + Any`: lo acepta `check`, lo rechaza `build` — **MEDIO**

**Estado:** confirmado.

```fitz
fn agrupar(digitos: Str, sep: Str) -> Str {
    let chars = []              // infiere List<Any>
    for c in digitos.split("") {
        chars.push(c)
    }
    let out = ""
    out = out + chars[0]        // ← acá
    return out
}
```

```
$ fitz check  →  ✓ no type errors
$ fitz build  →  ✗ codegen: operador `+` no aplicable a `Str` y `Any` en codegen
```

**Workaround:** anotar `let chars: List<Str> = []`.

**Lo que importa no es el workaround:** el checker infiere `Any` para un `[]` vacío y no propaga hacia atrás desde el `push`, o el codegen es más estricto que el checker. Sea cual sea, el usuario se entera al compilar. **Misma familia que FITZ-09 y que los format specs.**

---

## FITZ-11 · La imagen oficial de Docker no trae `git` — **MEDIO**

**Estado:** confirmado en un build real.

```
> [builder 5/5] RUN fitz build:
0.524 ✗ no se pudieron resolver las dependencias: dep `fitz_liveviews` (git):
      could not invoke `git` (No such file or directory (os error 2)).
      Install it and make sure it is on the PATH.
```

`ghcr.io/thegreekman76/fitz` existe y baja bien — pero sin `git` adentro, `fitz build` **no puede resolver ninguna dependencia declarada como `{ git = ... }`**.

Y hoy `{ git = ... }` es la **única** forma de declarar una dependencia externa: el registry público todavía no existe, y `{ path = ... }` no sirve dentro de un container.

O sea: **la imagen oficial no puede construir ningún proyecto con dependencias.** Justo el caso que la imagen existe para resolver.

**Arreglo:** una línea en el Dockerfile de la imagen (`apt-get install -y --no-install-recommends git ca-certificates`).

**Workaround en MatHelp:** etapa `vendor` sobre Alpine que clona fitz-liveviews, más un `fitz.docker.toml` paralelo que apunta la dependencia a `{ path = "/vendor/..." }`. Funciona, pero obliga a mantener **dos manifiestos en sincronía** — trampa clásica para un olvido.

**Vale la pena evaluar también:** un `fitz build --dep-override nombre=ruta` que evitaría el manifiesto duplicado en cualquier build containerizado.

---

## FITZ-12 · Paréntesis redundantes en el `match` generado — **BAJO (cosmético)**

El propio `rustc` avisa:

```
2459 -     let mut volver: String = (match referer.clone() { ... });
2459 +     let mut volver: String = match referer.clone() { ... };
```

Un build de MatHelp emite **194 warnings**, y buena parte son de este patrón. Sacar los paréntesis limpiaría el ruido y haría visibles los warnings que sí importan.

---

## FLV-10 · `flv_cookie` no compila a nativo — **ALTO**

Es la manifestación de FITZ-09 dentro de fitz-liveviews (ver arriba). Lo anoto con ID propio para que quede en el archivo del repo correcto y se verifique ahí.

Cuando FITZ-09 se arregle, el criterio de cierre de FLV-10 es: `fitz build` compila la librería entera **y** `examples/admin` compila y corre igual que interpretado.

---

## REFUTACIÓN · Los format specs sí compilan (FITZ-04, corrección parcial)

Verificado empíricamente **sobre el binario compilado**, no sobre los docs:

```fitz
let n: Int = 1234567
let r: Float = 0.42
return "{n:,}|{r:.1%}"
```

```
$ fitz build && ./target/release/probe2 && curl /fmt
"1,234,567|42.0%"
```

**Compilan.** La tabla de `docs/guide.md:1266` está desactualizada y conviene corregirla — me hizo diseñar un workaround que no hacía falta.

Pero fijate la salida: `1,234,567` y `42.0%`. En es-AR eso es `1.234.567` y `42,0 %`. **La parte de FITZ-04 que sigue vigente es la del locale, y esa sí importa**: un juego de matemática que muestra mal los decimales le está enseñando mal al chico.

Bonus verificado en el mismo probe: **`@post` ya acepta `form-urlencoded`**. El login de MatHelp es un `<form method="POST">` nativo, sin una línea de JS. El comentario de `examples/admin/src/auth.fitz` que dice lo contrario está desactualizado.

---

## LO QUE ESTO LE HACE A T2

Cuatro hallazgos en una tarde. **Tres de los cuatro son la misma cosa:**

| Hallazgo | `fitz check` | `fitz run` | `fitz build` |
|---|---|---|---|
| FITZ-09 · `T?` | ✓ | ✓ | ✗ |
| FITZ-10 · `Str + Any` | ✓ | ✓ | ✗ |
| FITZ-04 · format specs | ✓ | ✓ | ✓ *(los docs mienten)* |
| FITZ-06 · `preload` | ✓ | ✗ *silencioso* | ✓ |

Un proyecto real, en una tarde, encontró tres divergencias entre interpretado y compilado. **No es mala suerte: es que no hay nada que las detecte.**

Mi sugerencia, y creo que vale más que cualquiera de los arreglos puntuales:

> Un test de paridad que corra el mismo corpus de `.fitz` por las dos vías
> —`fitz run` y `fitz build`— y diffee la salida. Los `examples/` y los
> `boilerplates/` ya son ese corpus: 360 archivos que hoy solo se prueban
> por una de las dos vías.

Hubiera cazado los tres solos, y va a cazar el próximo antes de que lo encuentre un usuario dockerizando a las once de la noche.

**Sugerencia de re-priorización:** subir T2 por encima de varias features nuevas. Un lenguaje que a veces se comporta distinto al compilar es un problema de confianza, no de features — y la confianza es lo que hace que alguien apueste un proyecto real al lenguaje.

---

## PEDIDO CONCRETO

1. Agregá FITZ-09 a FITZ-12 y FLV-10 a los `norte-mathelp.md` correspondientes, con el formato de ficha ya establecido.
2. Corregí la ficha de FITZ-04 con la refutación (compilan; falta locale).
3. Corregí `docs/guide.md:1266` y el comentario de `examples/admin/src/auth.fitz` — los dos están desactualizados y hacen que la gente escriba workarounds al pedo.
4. Verificá si `examples/admin` compila hoy con `fitz build`.
5. **Re-priorizá la lista completa** con estos hallazgos adentro, y decime si T2 te parece que sube.
