@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%
echo Running Proxessor test suite...
python -m pytest tests/ -v
pause
