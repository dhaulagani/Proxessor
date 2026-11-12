# Proxessor Single Executable Build Script
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build_single_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Building Proxessor Single Executable Packages   " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Compile Rust Native Core Single Exe
Write-Host "[1/2] Compiling Rust Core (LTO, strip, opt-level=3)..." -ForegroundColor Yellow
cargo build --release --manifest-path rust/Cargo.toml
if ($LASTEXITCODE -ne 0) {
    Write-Error "Rust compilation failed!"
    exit 1
}

New-Item -ItemType Directory -Path "dist" -Force | Out-Null
Copy-Item "rust\target\release\proxessor.exe" "dist\proxessor-core.exe" -Force
Copy-Item "rust\target\release\proxessor.exe" "proxessor.exe" -Force

# 2. Compile Desktop GUI Single Exe (PyInstaller)
Write-Host "[2/2] Compiling Standalone Desktop GUI (PyInstaller --onefile --noconsole)..." -ForegroundColor Yellow
$PythonExe = "C:\Users\Gani\AppData\Local\Programs\Python\Python313\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python.exe"
}

& $PythonExe -m PyInstaller --clean --onefile --noconsole `
    --name "Proxessor-GUI" `
    --add-data "config;config" `
    --add-binary "proxessor.exe;." `
    --distpath "dist" `
    --workpath "build\pyinstaller" `
    run_gui.py

Write-Host "==================================================" -ForegroundColor Green
Write-Host " Single Executable Build Completed!               " -ForegroundColor Green
Write-Host " - Core Engine CLI : dist\proxessor-core.exe       " -ForegroundColor Green
Write-Host " - Desktop GUI App : dist\Proxessor-GUI.exe        " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
