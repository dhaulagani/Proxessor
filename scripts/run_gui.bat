@echo off
setlocal
cd /d "%~dp0\.."

set "PY_EXE=C:\Users\Gani\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
if not exist "%PY_EXE%" (
    if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe" (
        set "PY_EXE=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe"
    ) else (
        set "PY_EXE=pythonw.exe"
    )
)

start "" "%PY_EXE%" "%~dp0..\run_gui.py" %*
exit
