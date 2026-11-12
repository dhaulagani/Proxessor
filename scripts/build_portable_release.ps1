# Proxessor Portable Release Build Script
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build_portable_release.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Building Proxessor Windows Portable Release" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Run Cargo Tests
Write-Host "[1/5] Running Rust test suite..." -ForegroundColor Yellow
cargo test --manifest-path rust/Cargo.toml
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cargo test suite failed!"
    exit 1
}

# 2. Build Release Binary
Write-Host "[2/5] Compiling optimized release binary (LTO + opt-level=3)..." -ForegroundColor Yellow
cargo build --release --manifest-path rust/Cargo.toml
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cargo build failed!"
    exit 1
}

$DistDir = Join-Path $Root "dist\proxessor-v1.0.0-windows-x64-portable"
$ZipFile = Join-Path $Root "dist\proxessor-v1.0.0-windows-x64-portable.zip"
$ShaFile = "$ZipFile.sha256"

# 3. Assemble Portable Directory
Write-Host "[3/5] Assembling portable release artifacts in $DistDir..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path (Join-Path $DistDir "config") -Force | Out-Null

Copy-Item (Join-Path $Root "rust\target\release\proxessor.exe") $DistDir -Force
Copy-Item (Join-Path $Root "config\default_rules.json") (Join-Path $DistDir "config") -Force
Copy-Item (Join-Path $Root "LICENSE") $DistDir -Force

# 4. Create Zip Archive
Write-Host "[4/5] Creating zip package..." -ForegroundColor Yellow
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
Compress-Archive -Path "$DistDir\*" -DestinationPath $ZipFile -CompressionLevel Optimal

# 5. Compute SHA256 Checksum
Write-Host "[5/5] Generating SHA256 checksum..." -ForegroundColor Yellow
$Hash = (Get-FileHash $ZipFile -Algorithm SHA256).Hash
Set-Content -Path $ShaFile -Value "$Hash  $([System.IO.Path]::GetFileName($ZipFile))" -Encoding ascii

Write-Host "==================================================" -ForegroundColor Green
Write-Host " Portable release build completed successfully!   " -ForegroundColor Green
Write-Host " Zip Archive : $ZipFile" -ForegroundColor Green
Write-Host " SHA256      : $Hash" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
