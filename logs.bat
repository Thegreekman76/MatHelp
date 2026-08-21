@echo off
title MatHelp - logs
cd /d "%~dp0"

echo.
echo   Logs en vivo. Ctrl+C para salir.
echo.

docker compose logs -f --tail=80
