<#
Starts the offline stack and wires the Android emulator to it.

  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1           # full start
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -AdbOnly  # after an emulator restart

See docs/docker/OFFLINE_SETUP.md.
#>
param([switch]$AdbOnly)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$compose = @("compose", "-f", "docker-compose.offline.yml")

function Connect-Emulators {
    # adb on PATH, else the Android Studio default SDK location
    $adb = (Get-Command adb -ErrorAction SilentlyContinue).Source
    if (-not $adb) {
        $sdkAdb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
        if (Test-Path $sdkAdb) { $adb = $sdkAdb }
    }
    if (-not $adb) {
        Write-Warning "adb not found - skipping port forwarding (fine for Expo web)."
        return
    }

    # Lines like "emulator-5554<TAB>device"; skip offline/unauthorized devices
    $devices = & $adb devices | Select-String "^(\S+)\s+device$" | ForEach-Object { $_.Matches[0].Groups[1].Value }
    if (-not $devices) {
        Write-Warning "No running emulator/device. Start it, then run: .\start-offline.ps1 -AdbOnly"
        return
    }

    foreach ($d in $devices) {
        # 80 = API/NGINX, 9000 = object storage (presigned URLs are signed for localhost:9000)
        foreach ($port in 80, 9000) {
            & $adb -s $d reverse "tcp:$port" "tcp:$port" | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "adb reverse tcp:$port failed on $d" }
        }
        Write-Host "[adb] $d -> localhost:80, localhost:9000" -ForegroundColor Green
    }
}

if ($AdbOnly) {
    Connect-Emulators
    exit 0
}

if (-not (Test-Path ".env.offline")) {
    throw ".env.offline missing - copy .env.offline.example to .env.offline and set the secrets."
}

Write-Host "[docker] Starting offline stack (first API start takes 1-3 min)..." -ForegroundColor Cyan
& docker @compose up -d --wait --wait-timeout 600
if ($LASTEXITCODE -ne 0) {
    & docker @compose ps
    throw "docker compose up failed - check: docker compose -f docker-compose.offline.yml logs api"
}

# Idempotent: creates missing tables and the admin account only on first run
& docker @compose exec -T api python scripts/init_admin.py
if ($LASTEXITCODE -ne 0) { throw "init_admin.py failed" }

Connect-Emulators

Write-Host ""
Write-Host "Ready:" -ForegroundColor Green
Write-Host "  API      http://localhost/api/v1"
Write-Host "  Admin    http://localhost/admin-login.html"
Write-Host "  Storage  http://localhost:9001"
