@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Instala Node.js 22.12 o posterior y vuelve a abrir este archivo.
  pause
  exit /b 1
)
if not exist "apps\web\node_modules\.bin\vite.cmd" (
  call npm --prefix apps/web ci
  if errorlevel 1 goto :error
)
echo Vista previa: http://127.0.0.1:4173/#portada
call npm --prefix apps/web run dev:local
if errorlevel 1 goto :error
exit /b 0

:error
echo No se pudo iniciar la vista previa. Revisa el mensaje anterior.
pause
exit /b 1
