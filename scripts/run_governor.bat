@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%
echo Starting Proxessor Process Governor...
python -m src.proxessor.cli.main run %*
pause
