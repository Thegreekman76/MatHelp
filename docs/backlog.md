# Backlog de features (post-escalado)

Acordado 2026-08-27. Se va marcando el avance acá. **Fuera de scope por ahora**:
Product / ship it (deploy a dominio + HTTPS, PWA offline pulida, landing page).

## Prioridad

### 👤 Editar perfil (agregado por el autor)

- [x] **Editar perfil + cambiar grado/año sin perder el skill.** ✅ 2026-08-28.
  Lápiz (✏️) en cada card de `/perfiles` → `/perfiles/editar/{id}` con form
  pre-seleccionado (nombre / grado / modalidad / PIN opcional). Guarda con un
  `UPDATE profiles SET name/grade/modalidad WHERE id AND family_id` (raw
  `conn.exec`). El progreso (Elo por skill, attempts, racha, mastery) está keyed
  por `profile_id` → NO se toca al cambiar grado, se preserva. PIN opcional
  (vacío = dejar el actual). Verificado E2E en browser: crear grado 2 → editar a
  grado 10 (3º secundaria) + industrial → card actualizada + re-editar preserva.
  Dogfooding: destapó un check✓/run✗ del core — `h_join(List<Html>) -> Str`
  devuelve Str, y `.raw` sobre Str panica en runtime pero `fitz check` no lo caza
  (fns de deps git se tipan `Any`; FITZ-22 solo cubrió cross-módulo local).
  Anotado en `docs/norte-mathelp.md` del repo de fitz.

### 🎓 Pedagógico

- [x] **Sección "Aprendé" (enseñar cada cálculo, no solo practicarlo).** ✅ 2026-09-22.
  **20 temas, cubre todos los juegos:** suma, resta, multiplicación, división,
  fracciones, porcentaje, enteros, geometría, volumen, hora, potencias, ecuaciones,
  trigonometría, funciones, estadística, estimación, series, problemas, ordenar,
  memoria. + 2 feature cards (📖 Aprendé / 💡 Trucos) en la landing. Nueva `/aprender`
  + `/aprender/{tema}`, separada y complementaria a `/trucos`: qué es la operación,
  usos en la vida real, **varios métodos** (del más simple al más avanzado) cada uno
  con SVG + 3 pasos + ejemplo, y un poco de historia. Todos los métodos quedan
  visibles; el recomendado para el grado del perfil abre por default (`<details>`
  nativo, sin JS). Módulo genérico `src/aprender.fitz` + CSS `.ap-*` en `brand.fitz` +
  botón 📖 en el home. Cross-links al juego y al truco relacionado. Emojis de "usos"
  parametrizados por tema (`tema_uso_emojis`). Verificado E2E (render real: la ficha
  abre el método recomendado según el grado). 1164 claves i18n con paridad ES/EN.
  **Cubre todos los temas de los juegos** — la sección está completa. **Tanda de mejoras
  (2026-09-22):** +18 métodos/subtemas nuevos (huecos reales: círculo, duración, contar
  la diferencia, restas repetidas, simplificar, qué % es, potencias de 10, dos pasos,
  tabla de valores, gráfico de barras, dibujar el problema, capacidad, conteo salteado,
  comparar/valor absoluto de negativos, aplicación trig, estimar cantidades, series
  decrecientes) + animaciones SVG (rectas que saltan, grillas que se llenan, barras que
  crecen, líneas/flechas que se dibujan, agujas del reloj), gateadas por
  prefers-reduced-motion. 1254 claves i18n con paridad.
- [ ] **Feedback al errar con explicación** (máximo valor de aprendizaje). Hoy al
  fallar solo muestra "era X". Sumar el PASO: cómo se llega al resultado
  ("3/4 de 12 = 12 ÷ 4 × 3 = 9"). Por tipo de ejercicio / por juego.
- [x] **Repaso inteligente afinado** ✅ 2026-08-28. El motor Elo-lite ya escribía
  `due_at` (repaso espaciado, intervalo [1,3,7,16,35] días) pero NUNCA se leía:
  `/repaso` elegía solo por `rating ASC`. Ahora `weakest_skill` prioriza las
  destrezas VENCIDAS (`due_at < NOW()`) y entre ellas la más floja; sin ninguna
  vencida, cae a la más floja. Verificado contra Postgres.
- [x] **Más contenido: Estadística** ✅ 2026-08-28. Juego nuevo (promedio / mediana
  / moda / rango) con respuestas enteras + teclado, escala por grado (6°→6º sec).
  Cadena completa: `gen_estadistica` + `Estadistica.fitzv` + `estad_view` +
  `live_estadistica` (@get + @ws) + migración 0017 + fila en `juegos.fitz` + casos
  en `progreso`/`parent` + i18n ES/EN + CSS. Explicación al errar por tipo
  ((a+b+c)÷n, máx−mín, mediana ordenada, moda). 3 tests del generador. Verificado
  E2E en browser + `fitz build`.

### 👨‍👩‍👧 Familia / retención

- [x] **Reporte semanal por email a los padres** ✅ 2026-08-28. `@cron("0 9 * * 1")`
  (lunes 9:00 UTC) + `smtp.send` del core. Módulo `reporte.fitz`: itera las
  familias con actividad esta semana, arma un resumen por hijo (ejercicios,
  % aciertos, destreza a reforzar) y lo manda al email del padre (HTML + texto,
  i18n ES/EN). APAGADO por default (`MATHELP_WEEKLY_REPORT=1` + config SMTP para
  activar); no spamea familias sin actividad; best-effort (un fallo no corta las
  demás). Config nueva en `config.fitz` + `.env.example` (SMTP_* + flags).
  Verificado: contenido del email renderizado + iteración por familia + `fitz build`.
- [x] **Panel de familia más rico** ✅ 2026-08-28. Sección nueva "Precisión por
  destreza" (`aciertos / vistas` por skill como ProgressBars coloreadas: verde
  ≥80%, ámbar ≥60%, azul si necesita práctica). Usa `mastery.seen/hits` que ya
  existían pero el panel nunca leía. Muestra dónde el chico es certero vs dónde
  falla (el rating Elo no lo dice directo). Verificado en browser.

### 🛠️ Admin / cuenta / emails (pedido del autor 2026-09-22, post-"Aprendé")

Contexto: login por **email** (no hay usuario aparte). Infra de email lista: `smtp.send`
del core + Resend (sender `no-reply@mathelp.prothos.com.ar`, ver `config.fitz` +
`mailer.fitz`). Los emails transaccionales NO dependen de MATHELP_WEEKLY_REPORT.
Decisiones: bienvenida **localizada por `family.locale`**; admin gateado por
**`MATHELP_ADMIN_EMAILS`** (env, coma-separado). Orden A→B→C, un lote cada uno.

**Fase A — Emails al registrarse** (helper compartido `mailer.send_email` + hook
`spawn(...)` best-effort en `registro_post`)
- [ ] A1. Aviso al dueño (MATHELP_ADMIN_EMAILS) con datos del registro (email, familia, locale).
- [ ] A2. Bienvenida al usuario, localizada, con pasos (crear perfiles, PIN de adulto, jugar/Aprendé).

**Fase B — Recuperación / gestión de acceso** (tabla nueva de tokens, migración 0021)
- [ ] B1. Recuperar contraseña: form → email con link+token (expira, single-use) → nueva clave; no revelar si el email existe.
- [ ] B2. Cambiar clave / email desde la cuenta (hoy no existe).
- [ ] B3. (opcional) Verificación de email al registrarse (mismo mecanismo de token).
- Nota: "usuario" = email; si lo olvidan del todo, no hay identificador alterno (ofrecer contacto de soporte).

**Fase C — Administración del sitio (super-admin)**
- [ ] C1. Gate por `MATHELP_ADMIN_EMAILS` → link "Administración" en el menú + proteger TODAS las rutas /admin (no solo ocultar).
- [ ] C2. Dashboard: contadores (familias, perfiles, sesiones, registros/día) + tabla de últimos registros (StatCard/BarChart).
- [ ] C3. Uso/engagement: DAU/WAU, juegos más jugados, retención, destrezas más flojas a nivel global.
- [ ] C4. (opcional) Moderación: ver/suspender/borrar cuentas.

**Fase D — Extras a evaluar** (seguridad/privacidad/crecimiento)
- [ ] Rate limiting en login y registro. [ ] Borrar cuenta + exportar datos (privacidad de menores).
- [ ] Página privacidad/términos + link en el registro. [ ] Formulario de contacto → email.
- [ ] Recordatorio diario de practicar (PWA push). [ ] Invitar a otra familia (referral). [ ] Avisos de hitos/errores al dueño.

### ✅ Calidad

- [x] **Ampliar el harness E2E** ✅ 2026-08-28. 4 tests nuevos con asserts en
  `harness.mjs`: `testAuth` (registro deja sesión + ruta protegida + email
  duplicado da error + login OK + password mala falla), `testEditProfile` (crear
  grado 4 → editar a grado 10 → la card refleja el cambio), `testGradeGating` (un
  perfil de grado 4 ve los juegos de secundaria bloqueados), `testPanel` (tras
  jugar, /panel monta con la sección de precisión). Usan contextos aislados para
  probar login sin sesión. `/estadistica` sumado al smoke. Harness verde entero.

### 🐛 Dogfooding (transversal, no un ítem)

Cada feature nueva destapa/endurece bugs del core de Fitz. Se anota en
`docs/norte-mathelp.md` del repo de fitz cuando aparece.

## Avance

### 🎓 Feedback al errar con explicación — Tanda 1 (Cuatro operaciones)

- **2026-08-28** — Patrón establecido + primer juego. Al errar, debajo del "era X"
  aparece una línea `.q-expl` con el PASO: la cuenta completa (`8 × 7 = 56`), y en
  la división el inverso (`56 ÷ 7 = 8 (porque 7 × 8 = 56)`). Cubre **Quiz.fitzv**
  (Contrarreloj / Práctica / Desafío) para las 4 operaciones básicas
  (add/sub/mul/div); potencias/ecuaciones/secundaria caen al "era X" simple (`""`).
  - Arquitectura: campo de estado `last_expl` seteado en `event answer()` con
    `explicar(locale, ex)` (función pura, testeada), threadeado en paralelo a
    `last_answer` por `quiz_screen` → sub-screens → `feedback_banner`.
  - i18n: `expl.div` (es/en); las otras 3 ops son ecuación pura (sin texto).
  - `tests/explicacion.fitz` (6 tests) + E2E en browser real (las 4 ops renderizan,
    0 errores de página).
  - **Falta (próximas tandas)**: Escalera (arith, ya pasa `""`), Porcentaje,
    Historia, Geometría/Volumen (fórmula), Enteros, Estimar, Series.

### 🎓 Feedback al errar con explicación — Tanda 2 (Fracciones + Problemas)

- **2026-08-28** — Dos juegos de alto valor pedagógico (donde el "cómo se llega"
  pesa más que en las operaciones sueltas).
  - **Fracciones** (`Fracciones.fitzv` + `gen_frac.fitz` + `frac_view.fitz`): en
    secundaria (modo `op`), el `FracItem` trae un campo `expl` con la derivación —
    suma/resta a común denominador (`1/2 + 6/7 = 7/14 + 12/14 = 19/14`), producto
    cruzado (`1/2 × 1/3 = 1/6`), con reducción sólo si aplica. En primaria (modo
    `identify`, leer la barra) queda `""` (nada que desarrollar).
  - **Problemas/Kiosco** (`Kiosco.fitzv` + `kiosco_view.fitz`): `expl_kiosco(locale,
    k)` mapea cada tipo de UNA operación a su cuenta: total/ahorro (×), suma (+),
    vuelto/falta/comparar (−), reparto/cuantos/unitario/velocidad (÷), edad (+),
    cuadras (×2), promedio ((a+b+c)÷3), porcentaje (×÷100), y la **fracción de un
    monto** (`3/4 de 12 = 12 ÷ 4 × 3 = 9`, el ejemplo del backlog). Los multi-paso
    (descuento/oferta/combo/iva/interés/regla3/rendimiento/ecuación/trabajo/
    desc_compuesto/evento) devuelven `""` por ahora → "era X" simple.
  - Sin claves i18n nuevas (ecuaciones puras). `tests/explicacion_kiosco.fitz` (7) +
    2 en `tests/fracciones.fitz`. E2E browser real: ambos renderizan, 0 errores.
### 🎓 Feedback al errar con explicación — Tanda 3 (el resto de los juegos)

- **2026-08-28** — Cierra 6 juegos más con el mismo patrón (`last_expl` en estado
  + función `explicar_*` pura + render `.q-expl`):
  - **Escalera** (`Escalera.fitzv` + `escalera_view`): reusa `explicar` de gen_arith
    (multiplicación, `2 × 2 = 4`).
  - **Enteros** (`enteros_view` + `Enteros.fitzv`): `explicar_enteros` con signos
    (`(-3) + 8 = 5`).
  - **Kiosco multi-paso** (`kiosco_view`): completa los 11 tipos secundarios que
    faltaban — descuento/iva/interés/oferta/combo/regla3/rendimiento/ecuación/
    trabajo/desc_compuesto/evento, con derivación de 2 cuentas encadenadas con
    " → " (`3.200 × 10 ÷ 100 = 320 → 3.200 − 320 = 2.880`).
  - **Geometría** (`geo_view` + `Geometria.fitzv`): la FÓRMULA por figura
    (`4 × 14 = 56` cuadrado, `2 × (a+b)` rect perím., `a × b ÷ 2` triángulo, etc.).
  - **Volumen** (`vol_view` + `Volumen.fitzv`): la fórmula del cuerpo (cubo lado³,
    prisma a×b×c, cilindro π≈3, compuesto).
  - **Porcentaje** (`pct_view` + `Porcentaje.fitzv`): `explicar_pct` — `n × p ÷ 100`
    (la lección), con 2º paso para descuento/iva/recargo y sucesivos con notación %.
  - Sin claves i18n nuevas. Tests: `explicacion_forma.fitz` (9 geo+vol) +
    `explicacion_pct.fitz` (5) + los 6 multi-paso en `explicacion_kiosco.fitz`.
    Suite completa 767/767. E2E browser real (5 juegos, 0 errores).
  - **Excluidos por diseño**: **Historia** es intencionalmente gentil para
    pre-lectores ("¡Probá otra!" sin revelar la respuesta) — mostrar la ecuación
    rompería ese diseño. **Estimar** (redondeo) y **Series** (patrón) no tienen una
    "cuenta" única que mostrar (la respuesta es un rango / una regla a inferir).
