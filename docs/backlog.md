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

- [ ] **Feedback al errar con explicación** (máximo valor de aprendizaje). Hoy al
  fallar solo muestra "era X". Sumar el PASO: cómo se llega al resultado
  ("3/4 de 12 = 12 ÷ 4 × 3 = 9"). Por tipo de ejercicio / por juego.
- [ ] **Repaso inteligente afinado** — priorizar por skill más flojo + spaced
  repetition (base ya está con el Elo + due_at).
- [ ] **Más contenido** — decimales, probabilidad, estadística con gráficos,
  ecuaciones con recta/parábola, "pizza" SVG para fracciones. (Elegir 1-2.)

### 👨‍👩‍👧 Familia / retención

- [ ] **Reporte semanal por email a los padres** — `smtp.send` nativo del core de
  Fitz. "Esta semana Aurora hizo 45 ejercicios, mejoró en división". @cron semanal.
- [ ] **Panel de familia más rico** — gráficos de progreso por chico, por skill.

### ✅ Calidad

- [ ] **Ampliar el harness E2E** — cubrir auth, perfiles, forms, y el escalado por
  grado. Eventualmente screenshots de regresión visual en CI.

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
