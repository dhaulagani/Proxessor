@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0proxessor.exe" (
    "%~dp0proxessor.exe" run %*
) else if exist "%~dp0rust\target\release\proxessor.exe" (
    "%~dp0rust\target\release\proxessor.exe" run %*
) else (
    python -m src.proxessor.cli.main run %*
)
pause
