<#
Starts the offline stack, wires the Android emulator to it, and opens the Expo app on web.

  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1           # full start + Expo web
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -Build   # rebuild the API image after code changes
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -NoApp   # backend only, no Expo
  powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -AdbOnly  # after an emulator restart

First run: starts Docker Desktop if needed, creates .env.offline with random secrets, builds
the API image and installs the app's npm packages (needs internet once), then creates the
default admin / GP / patient accounts. Later runs need no internet.

The Expo app is expected next to this repo (..\FYP_MIA-KneeOA-App-); override with -AppDir.

See docs/docker/OFFLINE_SETUP.md.
#>
param([switch]$AdbOnly, [switch]$Build, [switch]$NoApp, [string]$AppDir = (Join-Path $PSScriptRoot "..\FYP_MIA-KneeOA-App-"))

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
# --env-file: compose interpolation reads the offline env, never the production .env
$compose = @("compose", "--env-file", ".env.offline", "-f", "docker-compose.offline.yml")

# Injected into Expo's process (beats the app's tracked .env, which points at production) and
# mirrored to the app's .env.local for Expo runs started by hand. Every URL variable is set so
# none of .env's production values can be picked.
$appEnv = [ordered]@{
    EXPO_PUBLIC_API_ENV          = "development"
    EXPO_PUBLIC_API_BASE_URL_DEV = "http://localhost"
    EXPO_PUBLIC_API_BASE_URL     = "http://localhost"
    EXPO_PUBLIC_BACKEND_URL      = "http://localhost"
}

function Start-DockerEngine {
    # "Continue": in Windows PowerShell 5.1, redirecting a native command's stderr under
    # "Stop" turns any stderr line into a terminating error.
    $ErrorActionPreference = "Continue"
    docker info *> $null
    if ($LASTEXITCODE -eq 0) { return }

    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $desktop)) { throw "Docker is not running and Docker Desktop was not found at $desktop" }
    Write-Host "[docker] Starting Docker Desktop..." -ForegroundColor Cyan
    Start-Process $desktop
    $deadline = (Get-Date).AddMinutes(5)
    do {
        Start-Sleep -Seconds 3
        docker info *> $null
    } while ($LASTEXITCODE -ne 0 -and (Get-Date) -lt $deadline)
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop did not come up within 5 minutes" }
}

function Start-ExpoWeb {
    if (-not (Test-Path (Join-Path $AppDir "package.json"))) {
        Write-Warning "Expo app not found at $AppDir - skipping (pass -AppDir <path>)."
        return
    }
    Push-Location $AppDir
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "[expo] Installing npm packages (first run only)..." -ForegroundColor Cyan
            & npm.cmd install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed in $AppDir" }
        }
        # Older app code (e.g. upstream main) drops any http:// URL and silently falls back to
        # https://kneeoa.online - stop here instead of running against production.
        if (-not (Select-String -Path "src\config\apiConfig.js" -Pattern "isAllowedUrl" -Quiet)) {
            throw "The app in $AppDir only accepts https:// API URLs, so it would use https://kneeoa.online. Check out its feat/offline-local-backend branch (run.ps1 does this), or pass -NoApp."
        }
        $lines = @("# Written by fyp-backend\start-offline.ps1 on every run - edits are overwritten.",
                   "# Points the app at the offline stack (NGINX on :80) instead of https://kneeoa.online.")
        foreach ($k in $appEnv.Keys) {
            Set-Item "env:$k" $appEnv[$k]
            $lines += "$k=$($appEnv[$k])"
        }
        [System.IO.File]::WriteAllText((Join-Path $AppDir ".env.local"), ($lines -join "`n") + "`n", (New-Object System.Text.UTF8Encoding $false))
        Write-Host "[expo] API base URL: $($appEnv.EXPO_PUBLIC_API_BASE_URL_DEV) (env injected + .env.local)" -ForegroundColor Green
        Write-Host "[expo] Starting web app on http://localhost:8081 (Ctrl+C to stop; the stack keeps running)" -ForegroundColor Cyan
        # Blocks while Metro runs; --clear so a previous production bundle's inlined URL is not reused
        & npx.cmd expo start --web --clear
    } finally {
        Pop-Location
    }
}

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

Start-DockerEngine

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
Write-Host ""
Write-Host "Stop the stack: docker compose -f docker-compose.offline.yml down"

if (-not $NoApp) { Start-ExpoWeb }
