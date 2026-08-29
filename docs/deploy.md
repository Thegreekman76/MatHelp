# Deploy de MatHelp — checklist

MatHelp corre como stack Docker (app Fitz + Postgres) definido en
`docker-compose.yml`. La app se compila desde el código con la imagen del
compilador Fitz (`FITZ_IMAGE` del `Dockerfile`).

## Flujo normal de deploy

```bash
# En el VPS, con el repo actualizado:
docker compose up -d --build app     # recompila la app con el código nuevo
docker compose logs -f app           # verificar que arranca
```

`--build app` es lo que recompila el binario. Sin `--build`, se reusa la imagen
vieja y los cambios de código NO entran.

## Versión del compilador

`Dockerfile` fija `ARG FITZ_IMAGE=ghcr.io/thegreekman76/fitz:vX.Y.Z` y
`ARG FLV_TAG=vA.B.C` (fitz-liveviews). Al actualizar a una versión nueva de Fitz
que arregla un check✓/build✗ o agrega un builtin usado, bumpear el `FITZ_IMAGE`
(la imagen la publica el CI de fitz al taggear) y `docker compose up -d --build app`.

Actual: `FITZ_IMAGE=ghcr.io/thegreekman76/fitz:v0.60.0`, `FLV_TAG=v0.50.0`.

## Migraciones de base de datos

Los `.sql` de `migrations/` se montan en `/docker-entrypoint-initdb.d` y corren
**solos SÓLO la primera vez** que se crea el volumen de Postgres (DB fresca).

**Sobre una DB existente** (con datos), una migración nueva NO corre sola. Hay que
aplicarla a mano:

```bash
# ejemplo con la migración de Estadística:
docker compose exec -T db psql -U mathelp -d mathelp < migrations/0017_estadistica.sql
```

Todas las migraciones son idempotentes (`IF NOT EXISTS` / `DROP + ADD` del
constraint), así que reaplicar una ya corrida no rompe nada. Alternativa
destructiva: `reset.bat` borra el volumen y re-corre todas (pierde los datos).

**Pendiente al día de hoy**: si el VPS ya tiene una DB con datos, aplicar
`migrations/0017_estadistica.sql` (juego Estadística) — sin eso, entrar a
`/estadistica` falla el INSERT de la sesión por el CHECK viejo de `sessions.mode`.

## Reporte semanal por email (opcional, APAGADO por default)

El `@cron("0 9 * * 1")` de `src/reporte.fitz` manda cada lunes 9:00 UTC un
resumen de la semana a cada familia con actividad. Está **apagado** hasta que se
configure. Para activarlo, setear en el `.env` del host (el `docker-compose.yml`
ya los pasa al contenedor con defaults):

```env
MATHELP_WEEKLY_REPORT=1
MATHELP_PUBLIC_URL=https://<tu-dominio>       # para el botón "Ver el panel" del email
# SMTP de tu proveedor (Gmail app-password, SendGrid, Amazon SES, etc.):
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=<usuario>
SMTP_PASSWORD=<password / app-password>
SMTP_FROM=MatHelp <no-reply@tu-dominio>
SMTP_TLS=starttls                              # starttls | implicit | none
```

Luego `docker compose up -d app` (sin `--build` alcanza — solo cambia el env).
El reporte NO spamea familias sin actividad y es best-effort (un fallo de SMTP de
una familia no corta las demás; se loguea `reporte.error`). Para probar el envío
antes de esperar al lunes, se puede bajar temporalmente el cron a un intervalo
corto o apuntar el SMTP a un catcher local.

## Pendiente — Product / ship-it (para cuando llegue el momento)

Fuera de scope hasta ahora (acordado): son los pasos para pasar de "corre en el
VPS" a "producto público".

- [ ] **Dominio + HTTPS**: apuntar un dominio al VPS, y un reverse-proxy (Caddy /
  Traefik / nginx) que termine TLS delante del `app:3000`. Actualizar
  `MATHELP_PUBLIC_URL` al dominio real. Caddy es el más simple (HTTPS automático
  con Let's Encrypt en 2 líneas de `Caddyfile`).
- [ ] **PWA offline pulida**: `manifest.json` + service worker para instalar en el
  celu y jugar sin conexión (los generadores son deterministas desde el seed, así
  que el juego funciona offline; la persistencia sincroniza al reconectar).
- [ ] **Landing page** pública (fuera de la app logueada): qué es MatHelp, para
  quién, capturas, y el CTA a crear cuenta.
- [ ] **JWT_SECRET de producción**: reemplazar el default por algo largo y
  aleatorio (`openssl rand -hex 32`) en el `.env` del VPS.
- [ ] **Backups de Postgres**: `pg_dump` periódico del volumen `pgdata`.
- [ ] **Observability**: los logs ya salen estructurados (JSON) por stdout del
  core de Fitz; conectar a donde se junten (Loki / un archivo rotado / el proveedor).
