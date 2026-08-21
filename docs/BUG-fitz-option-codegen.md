# Bug de codegen: funciones que devuelven `T?` compilan mal

> ✅ **CERRADO** — arreglado en fitz **v0.49.0** (FITZ-09). Este documento queda
> como registro histórico del hallazgo. `Str?` con `return null`/`return <valor>`
> ya compila (`return None`/`Some(...)`). MatHelp ya no usa el centinela `""`.

**Repo:** `Thegreekman76/fitz` · **Versión:** v0.47.0 (cerrado en v0.49.0)
**Severidad:** alta — bloqueaba `fitz build` para cualquier proyecto que use `fitz-liveviews`
**ID del backlog:** `FITZ-09` `[hallazgo propio del dogfooding]`
**Encontrado:** construyendo MatHelp, al dockerizar (F0)

---

## Resumen

Una función que declara `-> Str?` y hace `return null` o `return <valor>` en su cuerpo genera Rust que no compila. El codegen emite `return ()` donde correspondía `return None`, y devuelve el valor sin envolver en `Some(...)`.

**`fitz check` pasa. `fitz run` funciona perfecto. `fitz build` falla.** Es exactamente el patrón de T2: mismo código, dos comportamientos, y el problema aparece recién al compilar para producción.

**Lo importante:** no alcanza con evitarlo en el código propio. `flv_cookie`, **dentro de `fitz-liveviews`**, tiene el mismo patrón. Cualquier proyecto que dependa de la librería y compile a nativo choca con esto, haga lo que haga en su propio código.

---

## Reproducción

20 líneas, sin dependencias:

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
$ fitz check
✓ src/main.fitz — no type errors

$ fitz run
🏔️  Fitz HTTP escuchando en http://0.0.0.0:3000     # anda bien

$ fitz build
✗ cargo build failed to compile the generated code:
error[E0308]: mismatched types
```

---

## Rust generado (los dos defectos)

### 1. `return null` → `return ()` en vez de `return None`

```rust
pub fn read_cookie(mut header: Option<String>, mut name: String) -> Option<String> {
    let mut raw: String = (match header.clone() { None => { return () }, Some(h) => h.clone() });
//                                                         ^^^^^^^^^ esperaba Option<String>, encontró ()
```

### 2. `return <valor>` sin envolver en `Some(...)`

```rust
    ... __g[__e as usize].clone() };
//      ^^^^^^^^^^^^^^^^^^^^^^^^^ esperaba Option<String>, encontró String
//      help: try wrapping the expression in `Some`
```

El propio `rustc` sugiere el arreglo.

---

## Impacto en fitz-liveviews

```
error[E0308]: mismatched types
    --> src/fitz_liveviews.rs:1432:76
     |
1431 | pub fn flv_cookie(mut cookie: Option<String>, mut name: String) -> Option<String> {
1432 |     let mut raw: String = (match cookie.clone() { None => { return () }, Some(c) => c.clone() });
     |                                                            ^^ expected `Option<String>`, found `()`
```

`flv_cookie` es la función que resuelve el locale y la sesión desde la cookie del handshake — o sea, **la que necesita cualquier app con i18n o con auth**. Está en el camino crítico del ejemplo `admin`, que es la app insignia del framework.

Vale la pena verificar si `examples/admin` compila hoy con `fitz build`, o si solo se probó con `fitz run`.

---

## Un tercer defecto, más leve, en el mismo build

El codegen emite un `match` envuelto en paréntesis y el propio `rustc` avisa que sobran:

```
2459 -     let mut volver: String = (match referer.clone() { ... });
2459 +     let mut volver: String = match referer.clone() { ... };
```

Es solo un warning, pero contribuye a los 194 warnings del build. Sacar los paréntesis redundantes limpiaría bastante ruido.

---

## Workaround que estamos usando en MatHelp

Evitar `T?` como tipo de retorno. En vez de eso, centinela:

```fitz
// En vez de -> Str? con return null
fn read_cookie(header: Str?, name: Str) -> Str {   // "" = ausente
    let raw = match header {
        null => "",
        h => h,
    }
    ...
    return ""
}
```

Sirve para nuestro código, pero **no para `flv_cookie`**, que está en la librería. Por eso el Dockerfile de MatHelp corre el intérprete (`fitz run`) en vez del binario nativo — perdiendo el ~9x de performance y el runtime distroless.

---

## Criterio de aceptación sugerido

1. El repro de arriba compila con `fitz build` y devuelve `"a"` en `GET /`.
2. `fitz-liveviews` compila entero con `fitz build`, `flv_cookie` incluido.
3. Un test de paridad: el repro corre con `fitz run` y con `fitz build`, y la salida es idéntica.

Sobre el punto 3 — este bug es un argumento fuerte para **T2**: si hubiera un test que corre el mismo corpus de `.fitz` por las dos vías y diffea la salida, esto se habría cazado solo. Puede valer más que el arreglo puntual.

---

## Cómo lo encontramos

No apareció escribiendo el código: apareció **dockerizando**. En desarrollo usábamos `fitz run`, todo verde, `fitz check` limpio, 33 tests pasando. El primer `fitz build` lo destapó.

Es el peor momento posible para encontrarlo: cuando ya creías que estabas listo para desplegar.
