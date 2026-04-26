@echo off
REM Clawstack Maintenance Batch
SET scriptPath=%~dp0\clawstack_janitor.ps1
echo [Maintenance] Executing PowerShell Janitor...
Powershell -ExecutionPolicy Bypass -File "%scriptPath%"
pause
