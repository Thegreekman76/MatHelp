@echo off
setlocal
title MatHelp - E2E de browser
cd /d "%~dp0"

echo.
echo   MatHelp - E2E de browser real (puppeteer)
echo   -----------------------------------------
echo   Chequea que los juegos no parpadeen ni tiren errores JS.
echo   Requiere: node.js + Chrome + el server andando (start.bat) en :3000
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo   [X] Falta node.js. Instalalo de https://nodejs.org
    echo.
    pause
    exit /b 1
)

REM --- 1. server andando? ------------------------------------------------
curl -s -o nul http://localhost:3000/ >nul 2>&1
if errorlevel 1 (
    echo   [X] El server no responde en http://localhost:3000
    echo       Corre start.bat primero (en otra ventana) y volve a intentar.
    echo.
    pause
    exit /b 1
)
echo   [ok] Server respondiendo

REM --- 2. puppeteer-core instalado? -------------------------------------
if not exist "tools\browser\node_modules\puppeteer-core" (
    echo   Instalando puppeteer-core (una sola vez)...
    pushd "tools\browser"
    call npm install --silent
    popd
)
echo   [ok] puppeteer-core listo

REM --- 3. correr el harness --------------------------------------------
echo.
node "tools\browser\harness.mjs"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
    echo   ========================================
    echo     Browser E2E VERDE
    echo   ========================================
) else (
    echo   [X] Fallaron chequeos (RC=%RC%). Mira el detalle arriba.
)
echo.
pause
exit /b %RC%
