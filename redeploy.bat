@echo off
REM redeploy.bat — sube a produccion el ultimo commit (wrapper de deploy/redeploy.sh).
REM Requiere Git Bash instalado (viene con Git for Windows).
cd /d "%~dp0"
bash deploy/redeploy.sh %*
