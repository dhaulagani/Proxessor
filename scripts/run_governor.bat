@echo off
setlocal
cd /d "%~dp0\.."
if exist "%~dp0..\proxessor.exe" (
    "%~dp0..\proxessor.exe" run %*
) else if exist "%~dp0..\rust\target\release\proxessor.exe" (
    "%~dp0..\rust\target\release\proxessor.exe" run %*
) else (
    python -m src.proxessor.cli.main run %*
)
pause
