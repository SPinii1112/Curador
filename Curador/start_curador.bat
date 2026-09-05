@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_windows.ps1"
if errorlevel 1 (
  echo.
  echo Curador no pudo iniciarse. Copia el mensaje de error de arriba.
  pause
)
