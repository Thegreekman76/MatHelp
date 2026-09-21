#!/usr/bin/env bash
# redeploy.sh — sube a producción el último commit de MatHelp.
#
# Corré esto desde la raíz del repo (Git Bash en Windows, o cualquier shell
# POSIX). Un solo comando: pushea lo que tengas commiteado y redeploya el VPS.
#
#   ./deploy/redeploy.sh          # o:  redeploy.bat  (Windows)
#
# Qué hace:
#   1. git push del branch actual (NO commitea — eso lo hacés vos antes).
#   2. Por SSH en el VPS: git pull + rebuild/restart SOLO del container `app`
#      (la DB y el volumen NO se tocan).
#   3. Espera a que /healthz responda y muestra las últimas líneas del log.
#
# El deploy INICIAL (clone, .env, cert de Cloudflare, nginx) está en
# deploy/README.md — este script es solo para actualizaciones posteriores.
set -euo pipefail

VPS="${MATHELP_VPS:-143.110.154.156}"
REPO_DIR="/opt/mathelp/repo"
COMPOSE="docker compose -f docker-compose.prod.yml"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Avisar (no bloquear) si hay cambios sin commitear: no se van a deployar.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[!] Tenés cambios sin commitear — NO se van a deployar (solo se deploya lo pusheado)."
fi

echo "==> git push origin ${BRANCH}"
git push origin "${BRANCH}"

echo "==> redeploy en ${VPS} (branch ${BRANCH})"
ssh "${VPS}" bash -s <<EOF
set -euo pipefail
cd "${REPO_DIR}"

echo "==> git pull"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git reset --hard "origin/${BRANCH}"

echo "==> rebuild + restart app"
${COMPOSE} up -d --build app

echo "==> esperando /healthz ..."
ok=0
for i in \$(seq 1 30); do
  if curl -fsS http://127.0.0.1:8003/healthz >/dev/null 2>&1; then
    echo "    OK — /healthz responde"
    ok=1
    break
  fi
  sleep 2
done
[ "\$ok" = "1" ] || echo "    [!] /healthz no respondió en 60s — revisá los logs de abajo"

echo "==> últimas líneas del log de app:"
${COMPOSE} logs --tail 25 app
EOF

echo ""
echo "==> Listo. Público: https://mathelp.prothos.com.ar/"
