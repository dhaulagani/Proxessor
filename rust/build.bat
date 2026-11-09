@echo off
setlocal
cd /d "%~dp0"
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
echo Building Proxessor Native Rust release binary...
cargo build --release
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)
echo Build successful! Binary located at target\release\proxessor.exe
pause
