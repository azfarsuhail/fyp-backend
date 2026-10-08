# Offline Setup (Local Postgres + MinIO, CPU only)

Runs the whole backend on one Windows PC with **no internet at runtime**:
local PostgreSQL instead of Neon, MinIO-compatible storage instead of AWS S3,
ML models baked into the image, no GPU.

| Service | Image | Host port |
|---------|-------|-----------|
| `nginx` | `nginx:alpine` | `127.0.0.1:80` (API, static pages, admin) |
| `api` | `knee_oa_api:offline` (built locally) | internal only |
| `postgres` | `postgres:16-alpine` | internal only |
| `minio` | `pgsty/silo:RELEASE.2026-09-16T00-00-00Z` | `127.0.0.1:9000` (S3 API), `127.0.0.1:9001` (console) |
| `minio-init` | same as `minio` | one-shot, creates the bucket |

> **Why `pgsty/silo`?** MinIO stopped publishing images and deleted `minio/minio`
> from Docker Hub (Sep 2026). `pgsty/silo` (formerly `pgsty/minio`) is the community
> fork: same S3 API, `MINIO_*` variables and data format. Not affiliated with MinIO, Inc.

Files: [docker-compose.offline.yml](../../docker-compose.offline.yml),
[nginx/nginx.offline.conf](../../nginx/nginx.offline.conf),
[.env.offline.example](../../.env.offline.example).

---

## 1. One-time prep (needs internet)

```bash
cp .env.offline.example .env.offline     # then replace every "change-me" value
docker compose -f docker-compose.offline.yml pull postgres minio nginx
docker compose -f docker-compose.offline.yml build api
```

The offline build is CPU-only: base `tensorflow/tensorflow:2.15.0` (build arg `BASE_IMAGE`)
and CPU torch wheels from `https://download.pytorch.org/whl/cpu` (build arg `TORCH_INDEX_URL`).
Production keeps the GPU defaults. It also downloads the HuggingFace models (`all-MiniLM-L6-v2`, `openai/clip-vit-base-patch32`)
into the image. After this step nothing else is fetched.

## Quick start: `start-offline.ps1`

After step 1, this one script does steps 2, 3 and the emulator part of step 5:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1           # start stack + init DB + adb reverse
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -AdbOnly  # re-forward ports after an emulator restart
```

It runs `docker compose up -d --wait` (blocks until the API is healthy), then `init_admin.py`
(idempotent), then `adb reverse` for ports 80 and 9000 on every connected emulator/device.
It finds `adb` on PATH or at `%LOCALAPPDATA%\Android\Sdk\platform-tools`, and skips this step
with a warning if no emulator is running.

## 2. Start (offline from here on)

```bash
docker compose -f docker-compose.offline.yml up -d
docker compose -f docker-compose.offline.yml ps          # api becomes "healthy" after ~1-3 min
```

## 3. First run only: create tables + admin

```bash
docker compose -f docker-compose.offline.yml exec api python scripts/init_admin.py
```

Creates all tables (`Base.metadata.create_all`) and the `admin` / `admin` account.
**Change the admin password after first login.**

## 4. URLs

| What | URL |
|------|-----|
| API base | `http://localhost/api/v1` |
| Health | `http://localhost/health` |
| Landing page | `http://localhost/` |
| Admin | `http://localhost/admin-login.html` |
| API tester | `http://localhost/tester.html` |
| Storage console | `http://localhost:9001` (login = `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) |

`/docs` and `/redoc` are proxied, but Swagger/ReDoc load their JS from a CDN, so they only render online.

## 5. Mobile app (same PC)

Point the app's base URL at **`http://localhost/api/v1`**.

- **Expo web:** works as is (`localhost:8081` / `localhost:19006` are in `ALLOWED_ORIGINS`).
- **Android emulator:** forward the host ports into the emulator so `localhost` works there too
  (repeat after every emulator restart):

  ```bash
  adb reverse tcp:80 tcp:80
  adb reverse tcp:9000 tcp:9000
  ```

  Don't use `10.0.2.2`: presigned image/video URLs are signed for `localhost:9000`,
  and a different host breaks the signature. Debug builds allow cleartext HTTP; a
  release build needs `usesCleartextTraffic` enabled.

## 6. How storage works

- The DB stores object **keys** (`xrays/<uuid>.png`), never URLs.
- The API talks to storage at `S3_ENDPOINT_URL=http://minio:9000`.
- Presigned URLs are signed for `S3_PUBLIC_ENDPOINT_URL=http://localhost:9000`.
  Presigning makes no network call, so the API container never needs to reach that host.
- The diagnostic pipeline reads images directly (`download_bytes_from_s3`) instead of over a presigned URL.
- With both variables unset, the code uses AWS S3 exactly as before.

## 7. Not available offline

- **Email** (OTP / password reset via Resend): skipped when `RESEND_API_KEY` is unset.
  Users can't reset passwords; an admin can re-create the account.
- **Landing page styling** (`index.html` uses Tailwind/Font Awesome/AOS CDNs): it renders unstyled.
  The admin dashboard's Chart.js is vendored in `static/vendor/`, so its charts work.

## 8. Operations

```bash
# Logs
docker compose -f docker-compose.offline.yml logs -f api

# Stop (data kept in volumes pgdata / miniodata)
docker compose -f docker-compose.offline.yml down

# Wipe everything (DB + objects)
docker compose -f docker-compose.offline.yml down -v

# psql
docker compose -f docker-compose.offline.yml exec postgres psql -U kneeoa knee_oa

# Backup DB
docker compose -f docker-compose.offline.yml exec postgres pg_dump -U kneeoa knee_oa > backup.sql

# Run tests (SQLite + mocks, no services needed)
docker run --rm -v "$PWD:/code" knee_oa_api:offline pytest -q
```

Code changes need `docker compose -f docker-compose.offline.yml up -d --build api`.
The image doesn't bind-mount the source.
