@echo off
setlocal
title TRAVEL PLANNER V5.9
cd /d "%~dp0"
set "PWSH=%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe"
if not exist "%PWSH%" (
  for /f "delims=" %%I in ('where pwsh.exe 2^>nul') do if not defined FOUND set "FOUND=%%I"
  if defined FOUND set "PWSH=%FOUND%"
)
if not exist "%PWSH%" (echo PowerShell 7 introuvable. & pause & exit /b 1)
if not exist "%~dp0server.ps1" (echo server.ps1 introuvable. & pause & exit /b 1)
echo Demarrage de Travel Planner V5.9...
start "Travel Planner V5.9 - Serveur" "%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0server.ps1"
timeout /t 4 /nobreak >nul
start "" "http://localhost:8787/"
