@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%CD%
start "" python -m src.proxessor.cli.main gui %*
