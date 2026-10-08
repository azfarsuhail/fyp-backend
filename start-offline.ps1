<#
Starts the offline stack and wires the Android emulator to it.

  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1           # full start
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -Build   # rebuild the API image after code changes
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -AdbOnly  # after an emulator restart

First run: creates .env.offline with random secrets, builds the API image (needs internet
once), then creates the default admin / GP / patient accounts. Later runs need no internet.

See docs/docker/OFFLINE_SETUP.md.
#>
param([switch]$AdbOnly, [switch]$Build)

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
    # Each distinct "change-me..." placeholder gets its own random secret; repeats of the
    # same placeholder (e.g. the DB password inside DATABASE_URL) get the same value.
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $secrets = @{}
    $envText = [regex]::Replace((Get-Content ".env.offline.example" -Raw), "(?<=[=:])change-me[\w-]*", {
        param($m)
        if (-not $secrets.ContainsKey($m.Value)) {
            $bytes = New-Object byte[] 24
            $rng.GetBytes($bytes)
            $secrets[$m.Value] = -join ($bytes | ForEach-Object { $_.ToString("x2") })
        }
        $secrets[$m.Value]
    })
    [System.IO.File]::WriteAllText((Join-Path $PSScriptRoot ".env.offline"), $envText, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "[env] Created .env.offline with random secrets" -ForegroundColor Green
}

$upArgs = @("up", "-d", "--wait", "--wait-timeout", "600")
if ($Build) { $upArgs += "--build" }
Write-Host "[docker] Starting offline stack (first run builds the API image: ~15 min)..." -ForegroundColor Cyan
& docker @compose @upArgs
if ($LASTEXITCODE -ne 0) {
    & docker @compose ps
    throw "docker compose up failed - check: docker compose -f docker-compose.offline.yml logs api"
}

# Idempotent: creates missing tables and the default accounts only on first run
& docker @compose exec -T api python scripts/init_admin.py
if ($LASTEXITCODE -ne 0) { throw "init_admin.py failed" }

Connect-Emulators

Write-Host ""
Write-Host "Ready:" -ForegroundColor Green
Write-Host "  API      http://localhost/api/v1   (docs: http://localhost/docs)"
Write-Host "  Admin    http://localhost/admin-login.html"
Write-Host "  Storage  http://localhost:9001"
Write-Host ""
Write-Host "Default accounts (see docs/docker/OFFLINE_SETUP.md):" -ForegroundColor Green
Write-Host "  Admin    admin                 / admin"
Write-Host "  GP       gp@kneeoa.online      / gp123456"
Write-Host "  Patient  patient@kneeoa.online / patient123"
