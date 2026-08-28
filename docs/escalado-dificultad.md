# Escalado de dificultad por grado — auditoría y plan

Estado del escalado de dificultad por grado (1-7 primaria, 8-13 secundaria) en
todos los juegos, y el plan de corrección. Se va marcando el avance acá.

## Diagnóstico (auditoría 2026-08-27)

Raíz común: cada juego usa `grade` para elegir una **banda de nivel [piso..techo]**
(escala fija 1-5); el `idx` recorre la banda dentro de la ronda. Dos fallas:

1. **Los techos topan en 5 y los pisos en 3, con cortes en `grade<=8`/`else`** →
   toda la secundaria alta colapsa a la misma banda 3-5 (9°-13°, a veces 6°-13°,
   mecánicamente idénticos).
2. **Las magnitudes numéricas están cableadas por NIVEL, no por grado** (los
   `g.int(...)` son fijos) → un 13° recibe los mismos números que un 8° en el
   mismo nivel.

El único que escala bien en secundaria es **Problemas** (arreglado 2026-08-27,
con `esc_kiosco` que escala montos por grado + niveles N6-N9). Finanzas y
Funciones también escalan (piso/techo monótonos).

## Estrategia de corrección

- **(A) Escalar magnitudes por grado dentro de cada nivel** — el mayor palanca,
  transversal: helper `esc_<juego>(grade)` que agranda los `g.int(...)` para
  grados altos (como `esc_kiosco` de Problemas).
- **(B) Extender/rebandear piso-techo** para diferenciar 10-13.
- **(C) Contenido nuevo de secundaria** en los peores casos (Historia, Fracciones,
  Escalera).
- **(D) Bugs puntuales**.

Cada cambio: `fitz check` + `fitz test` verdes + (donde aplique) muestreo real en
browser. Sin romper tests existentes. Primaria se toca lo mínimo (el reclamo es
de secundaria).

## Checklist

### 🔴 Rojos (no escalan / planos en secundaria)

- [x] **Motor 4-ops (Contrarreloj / V/F / Completá / Escalera)** — `gen_arith.fitz`
  - [x] `mul_max`: rampa en secundaria (15/20/25 por tramo 8-9/10-11/12-13) → destraba Escalera + división
  - [~] `add_max`: ya tenía 3 pasos en secundaria (200/500/999) — suficiente por ahora
- [x] **Historia** — `gen_historia.fitz`: niveles 6 (multiplicación grande) y 7 (reparto/división) para secundaria + rebandeo + objetos adultos (libros/monedas/láminas/puntos) + i18n `hist.reparto`. Ya no es "2×6" narrado para un 6° de secundaria. _(Follow-up: multi-paso y % narrados, más objetos.)_
- [x] **Fracciones** — `gen_frac.fitz`: denominadores más finos por grado (12/16/20). **+ OPERACIONES** (Tanda 2): en secundaria (grade≥8) el modo pasa a "op" — suma/resta/multiplicación de fracciones con resultado reducido y distractores plausibles (errores típicos + resultados de otras operaciones). Vista nueva `frac_op_html` (fracciones apiladas). El componente no cambió (compara strings). Verificado en browser: un 6° de secundaria hace "2/5 + 5/7 = 39/35".

### 🟠 Flojos (meseta grande en secundaria alta 9/10-13)

- [x] **Geometría** — `gen_geo.fitz`: `esc_geo` escala dimensiones ×1/2/3/4 por tramo (7/8-9/10-11/12-13). SVG normaliza, figura no se desborda.
- [x] **Volumen** — `gen_vol.fitz`: `esc_vol` ×2 en 11-13 (gentil por ser cúbico).
- [x] **Porcentaje** — `gen_pct.fitz`: `esc_pct` escala el monto ×1/2/3/5 preservando el múltiplo (respuesta entera).
- [x] **Estimar** — `gen_estimar.fitz`: `esc_est` escala los operandos a estimar ×1/2/3 (niveles 3-5, los de secundaria).
- [x] **Series** — `gen_series.fitz`: arreglada la regresión de 8° (banda 3-3 → 3-4) + rebandeo (11-13 arranca en nivel 4). Primaria intacta.
- [x] **Memoria** — `gen_memoria.fitz`: nivel 6 nuevo para 11-13 (expresiones de dos cifras / dos pasos / división grande).
- [x] **Ordenar** — `gen_ordenar.fitz`: niveles 6 (mezcla de formatos: naturales+decimales+fracciones) y 7 (mezcla CON negativos) para 11-13 + 7 cartas. Rebandeo.
- [x] **Enteros** — `gen_enteros.fitz`: rebandeo del piso (12-13 arranca en multiplicación de signos). Recta ±15 fija impide escalar magnitud sin romper la vista.
- [ ] **Hora** — `gen_hora.fitz`: 7-13 iguales (defendible: "cualquier minuto" es la skill final). Baja prioridad, quizá dejar como está.

### 🟡 Con reservas (concept-driven; tweaks de piso aplicados) — CERRADO

Los tres especiales son concept-driven (los niveles ya escalan concepto: cuadrado→
raíz→notación científica, lineal→cuadrática→sistema, etc.). Escalar magnitud los haría
absurdos (12⁵ como opción múltiple). Se aplicó un tweak de piso para diferenciar el
último año:

- [x] **Potencias** — 12-13 arrancan en raíces (piso 3), no en cuadrados.
- [~] **Ecuaciones** — ya tenía piso 3 para 12-13; se deja (aceptable).
- [x] **Trigonometría** — 13 arranca en "Pitágoras hallar cateto" (piso 3).

### 🐛 Bugs / puntuales — RESUELTO

- [x] **`grade_teclado` código muerto** — NO era un bug de correctitud: el teclado de
  Completá SÍ tiene la tecla ± (`con_signo`/`kp_signo`) y la secundaria puede tipear
  negativos. La función era dead code (el ± la reemplazó). **Removida** (función + test
  + import).
- [x] **`difficulty_for` satura en 5** — es **por diseño**: la escala Elo es 1-5, no se
  puede "distinguir" más allá del máximo. No hay fix; no toca el ejercicio, solo el peso
  del scoring. Se deja.

### ⚪ Sin cambios (defendible)

- **Hora** — `gen_hora.fitz`: 7-13 iguales, pero "leer cualquier minuto" ES la skill terminal del juego. Meseta justificable por el dominio. Se deja.

### 🟢 Ya escalan bien (no tocar)

- [x] **Problemas** (arreglado 2026-08-27)
- [x] **Finanzas** (piso/techo monótono 11-13)
- [x] **Funciones** (piso/techo monótono 11-13)

## Avance

### 2026-08-27 — Tanda 1 (11 juegos)

Enfoque: **escalar magnitudes por grado dentro de cada nivel** (el mayor palanca)
+ rebandeo/niveles nuevos donde hacía falta. Primaria tocada lo mínimo. Todo con
`fitz check` + `fitz test` (165) verdes + smoke de los 21 juegos en browser a grado
13 sin errores + muestreo visual de contenido.

- **Motor** (`gen_arith.fitz`): `mul_max` con rampa 15/20/25 en secundaria → Escalera
  y división ya no son idénticas 8°-13°.
- **Geometría / Volumen / Porcentaje / Estimar**: helper `esc_*(grade)` escala las
  magnitudes por tramo de años (dimensiones, montos, operandos a estimar).
- **Enteros**: rebandeo del piso (12-13 arranca en multiplicación de signos).
- **Series**: arreglada la regresión de 8° (banda 3-3 → 3-4) + rebandeo (11-13 → nivel 4).
- **Ordenar**: niveles 6 (mezcla de formatos) y 7 (mezcla con negativos) + 7 cartas.
- **Memoria**: nivel 6 (dos cifras / dos pasos / división grande) para 11-13.
- **Fracciones**: denominadores más finos por grado (hasta 20 en 6° sec) + rampa.
- **Historia**: niveles 6 (mult grande) y 7 (reparto/división) + objetos adultos
  (libros/monedas/láminas/puntos) + i18n `hist.reparto`. Verificado en browser: un
  6° de secundaria recibe "14 cajas de 11 puntos" y "120 libros entre 10 amigos",
  no "2 × 6 globos".

**Diferido** (follow-up): multi-paso y % narrados en Historia, magnitud dentro de los
especiales (potencias/ecuaciones/trig), y los bugs puntuales (`grade_teclado`,
`difficulty_for`). Hora se deja (defendible).

### 2026-08-27 — Tanda 2 (Fracciones con operaciones)

`gen_frac.fitz` gana el modo "op" para secundaria (grade≥8): dos fracciones + una
operación (+, −, ×), resultado REDUCIDO (helper `gcd`), distractores por error típico
(sumar num y den) + resultados de las otras operaciones + corrimientos. La vista
(`frac_op_html`) muestra la operación con fracciones apiladas en vez de la barra; el
componente `Fracciones.fitzv` NO cambió (compara strings). i18n `frac.pregunta_op` +
CSS `.frac-op`. Test `frac_op_secundaria` recomputa la operación desde el prompt. 166
tests verdes + verificado en browser a grado 13.

**Diferido restante**: multi-paso/% narrados en Historia, magnitud en los especiales,
bugs puntuales.

### 2026-08-27 — Tanda 3 (cierre)

- **Especiales**: tweaks de piso (potencias 12-13 arrancan en raíces, trig 13 en
  Pitágoras hallar cateto) para diferenciar el último año. Ecuaciones ya estaba bien.
  El fix de magnitud NO aplica (concept-driven; los niveles ya escalan concepto).
- **`grade_teclado`**: removido (dead code — el teclado de Completá tiene ± para
  secundaria, no era un bug de correctitud).
- **`difficulty_for`**: se deja (satura en 5 por diseño de la escala Elo 1-5).

**Estado**: el reclamo original (la secundaria recibía ejercicios de primaria) está
**cubierto en los 20 juegos**.

### 2026-08-27 — Tanda 4 (Historia multi-paso + porcentaje)

`gen_historia.fitz` gana niveles 8 (multi-paso: `a·b + c`, "cajas de X más sueltos") y
9 (porcentaje narrado: `el b% de a`) + rebandeo de secundaria (g8-9 → mult grande +
reparto, g10-11 → + multi-paso, g12-13 → + porcentaje). Campo `c` nuevo en `HistItem`
(el multi-paso usa tres números). i18n `hist.multi`/`hist.porcentaje` + objetos adultos.
**Bug encontrado y arreglado**: el loop de distractores usaba `for c in shuf`, pisando
el campo `c` → el `c` devuelto era un distractor, no el del multi-paso. Renombrado a
`cd`. 165 tests verdes + verificado en browser (reparto → multi-paso → porcentaje).

Con esto Historia queda completa; no queda deuda de escalado abierta.
