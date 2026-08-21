@echo off
title MatHelp - detener
cd /d "%~dp0"

echo.
echo   Apagando MatHelp...
echo.

docker compose down

echo.
echo   [ok] Contenedores detenidos. Los datos quedan guardados.
echo        Para volver a levantarlo: start.bat
echo        Para borrar la base:      reset.bat
echo.
pause
