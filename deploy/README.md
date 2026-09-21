# Deploy — MatHelp en el VPS (Ubuntu + Cloudflare)

Paso a paso para deployar MatHelp en el VPS `143.110.154.156`, donde ya
corren `citai`, `syndesi` y `fitzwatch`. Cada app vive en la raíz de su
propio host y bindea un puerto loopback; nginx del host hace el `proxy_pass`.

## Topología

```
Cloudflare (DNS + edge TLS, proxy ON)
        ↓ HTTPS
[VPS:443] nginx host
        ↓ proxy_pass http://127.0.0.1:8003
        ↓
[Docker] mathelp-app  (binario Fitz nativo SSR, expone 127.0.0.1:8003 → :3000 interno)
[Docker] mathelp-db   (Postgres 16, solo accesible dentro de mathelp_network)
```

| Pieza | Valor |
|---|---|
| Dominio | `mathelp.prothos.com.ar` |
| Puerto host (loopback) | `127.0.0.1:8003` (citai=8000, syndesi=8001, fitzwatch=8002) |
| Workdir VPS | `/opt/mathelp/` |
| Repo VPS | `/opt/mathelp/repo/` |
| Red Docker | `mathelp_network` (bridge, dedicada) |
| Volumen DB | `mathelp_pgdata` |
| TLS | Cloudflare Origin Certificate dedicado |
| Nginx site | symlink a `/opt/mathelp/repo/deploy/nginx/mathelp.conf` |

MatHelp es **SSR puro**: el backend Fitz sirve TODO (HTML + WebSockets +
estáticos vía `static_dir="public"`). nginx solo hace de reverse-proxy.

---

## 1. Cloudflare — DNS + Origin Certificate  *(manual, en el dashboard)*

1. **DNS**: prothos.com.ar → DNS → agregar registro:
   - Type: `A`
   - Name: `mathelp`
   - IPv4: `143.110.154.156`
   - Proxy: **ON** (nube naranja)
   - TTL: Auto

2. **Origin Certificate** (TLS entre Cloudflare y el VPS):
   - SSL/TLS → Origin Server → *Create Certificate*
   - Hostnames: `mathelp.prothos.com.ar`
   - Key type: RSA 2048, Validity: 15 años
   - Guardá los dos blobs (**cert** y **key**) — los pegás al VPS en el paso 3.

3. **SSL/TLS mode**: confirmá que prothos.com.ar está en **Full (strict)**.

---

## 2. VPS — directorios y certificados

```bash
ssh root@143.110.154.156

# Estructura paralela a /opt/fitzwatch/
mkdir -p /opt/mathelp/ssl-certificates

# Pegá el cert de Cloudflare (paso 1.2)
nano /opt/mathelp/ssl-certificates/mathelp.prothos.com.ar.pem
# Pegá la key
nano /opt/mathelp/ssl-certificates/mathelp.prothos.com.ar.key

chmod 644 /opt/mathelp/ssl-certificates/mathelp.prothos.com.ar.pem
chmod 600 /opt/mathelp/ssl-certificates/mathelp.prothos.com.ar.key
```

---

## 3. VPS — clonar el repo y crear el `.env` de producción

```bash
cd /opt/mathelp
git clone https://github.com/Thegreekman76/MatHelp.git repo
cd repo

# Crear el .env (NO se commitea). Generá secrets fuertes:
cat > .env <<EOF
POSTGRES_USER=mathelp
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=mathelp
JWT_SECRET=$(openssl rand -hex 32)
MATHELP_DEFAULT_LOCALE=es-AR
MATHELP_PUBLIC_URL=https://mathelp.prothos.com.ar
MATHELP_WEEKLY_REPORT=0
EOF

chmod 600 .env
```

> **Reporte semanal por email:** queda **apagado** (`MATHELP_WEEKLY_REPORT=0`).
> Este VPS (DigitalOcean) **bloquea SMTP outbound** (587/465), así que
> `smtp.send` no saldría. Para activarlo hay que refactorizar `reporte.fitz`
> a un proveedor HTTP (Resend), igual que hizo fitzwatch. No es blocker.

---

## 4. VPS — levantar el stack Docker

```bash
cd /opt/mathelp/repo
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f app   # verificar boot OK
```

Las 19 migraciones de `migrations/` corren solas la primera vez que se crea
el volumen `mathelp_pgdata` (orden por nombre, `0001_init.sql` primero).

---

## 5. VPS — instalar el nginx site

```bash
# Symlink al conf versionado en el repo (patrón de fitzwatch).
ln -s /opt/mathelp/repo/deploy/nginx/mathelp.conf /etc/nginx/sites-available/mathelp.conf
ln -s /etc/nginx/sites-available/mathelp.conf     /etc/nginx/sites-enabled/mathelp.conf

nginx -t                 # validar sintaxis (necesita el cert del paso 2)
systemctl reload nginx   # sin downtime para las otras apps
```

---

## 6. Verificación

```bash
# Healthcheck local del binario (loopback)
curl http://127.0.0.1:8003/healthz          # → {"status":"ok"}

# Healthcheck público vía nginx + Cloudflare
curl https://mathelp.prothos.com.ar/healthz  # → {"status":"ok"}

# Home (debería devolver HTML)
curl -I https://mathelp.prothos.com.ar/
```

Abrí `https://mathelp.prothos.com.ar/` en el browser, creá una cuenta, un
perfil, y jugá una partida (verifica que el WebSocket del cronómetro conecta).

---

## Updates posteriores

Desde tu máquina, con el cambio ya commiteado:

```bash
./deploy/redeploy.sh        # Linux/macOS/Git Bash
redeploy.bat                # Windows
```

Hace `git push` del branch actual, y por SSH: `git pull` + rebuild/restart
del container `app` (la DB y el volumen no se tocan) + espera el `/healthz`.

Si tocaste `deploy/nginx/mathelp.conf`, además:

```bash
ssh root@143.110.154.156 'nginx -t && systemctl reload nginx'
```

---

## Rollback

```bash
ssh root@143.110.154.156
cd /opt/mathelp/repo
git log --oneline -10
git reset --hard <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build app
```

## Troubleshooting

| Síntoma | Causa probable |
|---|---|
| `502` desde Cloudflare | El container `mathelp-app` no levantó. `docker compose -f docker-compose.prod.yml logs app`. |
| `526` desde Cloudflare | El Origin Cert no validó. Revisá `/opt/mathelp/ssl-certificates/`. |
| `521` desde Cloudflare | nginx no escucha en 443. `nginx -t && systemctl status nginx`. |
| El juego no arranca / WS no conecta | Falta el `location /live/` con headers `Upgrade`/`Connection`. Revisá `mathelp.conf`. |
| La DB arranca vacía / cambió schema | El volumen `mathelp_pgdata` ya existía. Las migraciones solo corren en volumen nuevo. |
