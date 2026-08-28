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

_(se va completando)_
