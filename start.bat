@echo off
setlocal enabledelayedexpansion
title MatHelp - iniciando

echo.
echo   MatHelp - Matematica que se comparte
echo   ------------------------------------
echo.

cd /d "%~dp0"

REM --- 1. Docker esta corriendo? -----------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
    echo   [X] Docker no responde.
    echo.
    echo       Abri Docker Desktop, espera a que diga "Engine running"
    echo       y volve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)
echo   [ok] Docker esta corriendo

REM --- 2. Archivo .env ----------------------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo   [ok] .env creado desde .env.example
    ) else (
        echo   [!] No hay .env ni .env.example - se usan los valores por defecto
    )
) else (
    echo   [ok] .env encontrado
)

REM --- 3. Puerto ----------------------------------------------------------
set "MATHELP_PORT=3000"
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="MATHELP_PORT" set "MATHELP_PORT=%%B"
    )
)
echo   [ok] Puerto: !MATHELP_PORT!

REM --- 4. Levantar --------------------------------------------------------
echo.
echo   Construyendo y levantando los contenedores...
echo   (la primera vez tarda unos minutos: compila el binario nativo)
echo.

docker compose up -d --build
if errorlevel 1 (
    echo.
    echo   [X] Fallo el build.
    echo.
    echo       Cosas para mirar:
    echo.
    echo       - Si fallo al bajar "ghcr.io/thegreekman76/fitz", proba el
    echo         fallback que compila Fitz desde el codigo fuente:
    echo           docker compose -f docker-compose.yml -f docker-compose.source.yml up -d --build
    echo.
    echo       - Si fallo al clonar fitz-liveviews, revisa tu conexion.
    echo.
    echo       - El detalle completo del error esta arriba de este mensaje.
    echo.
    pause
    exit /b 1
)

REM --- 5. Esperar a que responda -----------------------------------------
echo.
echo   Esperando a que MatHelp responda...
set /a INTENTOS=0
:esperar
set /a INTENTOS+=1
curl -s -o nul -w "" http://localhost:!MATHELP_PORT!/ >nul 2>&1
if not errorlevel 1 goto listo
if !INTENTOS! geq 45 goto timeout
timeout /t 2 /nobreak >nul
goto esperar

:timeout
echo.
echo   [!] No respondio despues de 90 segundos.
echo       Mira los logs con:  logs.bat
echo.
pause
exit /b 1

:listo
echo.
echo   ========================================
echo     MatHelp esta andando
echo     http://localhost:!MATHELP_PORT!
echo   ========================================
echo.
echo   Para verlo en el celular (misma red WiFi):
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%J in ("%%I") do echo     http://%%J:!MATHELP_PORT!
)
echo.
echo   logs.bat   ver los logs en vivo
echo   stop.bat   apagar todo
echo   reset.bat  borrar la base y empezar de cero
echo.

start "" "http://localhost:!MATHELP_PORT!"

endlocal
