@echo off
echo Starting Proxessor Process Governor...
python -m src.proxessor.cli.main run %*
pause
