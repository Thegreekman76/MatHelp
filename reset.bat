@echo off
setlocal
title MatHelp - reset
cd /d "%~dp0"

echo.
echo   CUIDADO: esto borra la base de datos completa.
echo   Se pierden perfiles, partidas y progreso.
echo.
set /p RTA="   Escribi BORRAR para confirmar: "

if /i not "%RTA%"=="BORRAR" (
    echo.
    echo   Cancelado. No se toco nada.
    echo.
    pause
    exit /b 0
)

echo.
echo   Borrando contenedores y volumen...
docker compose down -v

echo.
echo   [ok] Todo limpio. Al correr start.bat se recrea el esquema
echo        desde migrations/0001_init.sql
echo.
pause
endlocal
