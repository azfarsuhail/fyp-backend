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

## 1. Start: `start-offline.ps1`

One script does everything, first run included:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1           # start everything + Expo web
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -Build    # after code changes: rebuild the API image
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -NoApp    # backend only, no Expo
powershell -ExecutionPolicy Bypass -File .\start-offline.ps1 -AdbOnly  # re-forward ports after an emulator restart
```

It:

1. Starts Docker Desktop if the Docker engine isn't running (waits up to 5 min).
2. Creates `.env.offline` from `.env.offline.example` if missing, with a random secret for every
   `change-me` value (DB password, storage password, JWT `SECRET_KEY`).
3. Runs `docker compose up -d --wait`: builds `knee_oa_api:offline` if it doesn't exist yet and
   blocks until every service is healthy.
4. Runs `scripts/init_admin.py`: creates all tables and the [default accounts](#2-default-accounts).
   Idempotent, so existing accounts and data are never touched.
5. Runs `adb reverse` for ports 80 and 9000 on every connected emulator/device (`adb` from PATH or
   `%LOCALAPPDATA%\Android\Sdk\platform-tools`; skipped with a warning if none is running).
6. Opens the Expo app on web at `http://localhost:8081`, pointed at `http://localhost`: the
   `EXPO_PUBLIC_*` API URL variables are injected into Expo's process (overriding the app's
   production `.env`) and written to the app's `.env.local`, which is overwritten on every run. The app
   repo must sit next to this one (`..\FYP_MIA-KneeOA-App-`, or pass `-AppDir <path>`); its npm
   packages are installed on the first run. Ctrl+C stops Expo only; the stack keeps running.

**Internet is needed only on the very first run** (pulling `postgres` / `pgsty/silo` / `nginx`
and building the API image, ~15 min). The build is CPU-only: base `tensorflow/tensorflow:2.15.0`
(build arg `BASE_IMAGE`), CPU torch wheels from `https://download.pytorch.org/whl/cpu`
(build arg `TORCH_INDEX_URL`), and the HuggingFace models (`all-MiniLM-L6-v2`,
`openai/clip-vit-base-patch32`) baked into the image. Production keeps the GPU defaults.
After that, every start works with the network unplugged.

To pre-fetch on a machine with internet and then start offline elsewhere:

```bash
docker compose -f docker-compose.offline.yml pull postgres minio nginx
docker compose -f docker-compose.offline.yml build api
```

## 2. Default accounts

Created automatically by `start-offline.ps1` (via `scripts/init_admin.py`):

| Role | Login (email field) | Password | Notes |
|------|---------------------|----------|-------|
| Admin | `admin` | `admin` | Admin dashboard: `http://localhost/admin-login.html` |
| GP | `gp@kneeoa.online` | `gp123456` | Sees the demo patient under assigned patients |
| Patient | `patient@kneeoa.online` | `patient123` | Assigned to the demo GP; profile pre-filled (age 58, pain 5/10, moderate mobility) |

The GP and patient are created only when `SEED_DEMO_USERS=1`, which `docker-compose.offline.yml`
sets. Production never gets them. **These passwords are public: change them if the machine is
shared or reachable from a network.**

Storage console (`http://localhost:9001`): user `kneeoa-admin`, password = `MINIO_ROOT_PASSWORD`
in your `.env.offline` (random, generated on first run).

## 3. Manual start (without the script)

```bash
docker compose -f docker-compose.offline.yml up -d --wait
docker compose -f docker-compose.offline.yml exec api python scripts/init_admin.py
```

## 4. URLs

| What | URL |
|------|-----|
| API base | `http://localhost/api/v1` |
| Health | `http://localhost/health` |
| Landing page | `http://localhost/` |
| Admin | `http://localhost/admin-login.html` |
| API tester | `http://localhost/tester.html` |
| Storage console | `http://localhost:9001` (login = `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) |

| API docs | `http://localhost/docs` (Swagger UI), `http://localhost/redoc` |

Every page loads its JS, CSS, fonts and images from `static/` (`static/vendor/`, `static/images/`),
so nothing needs a CDN.

## 5. Mobile app (same PC)

Point the app's base URL at **`http://localhost/api/v1`**.

- **Expo web:** started by `start-offline.ps1`. `ALLOWED_ORIGINS` (set in
  `docker-compose.offline.yml`) covers `localhost` / `127.0.0.1` on ports 8081-8084 and 19006, so
  CORS still works when 8081 is busy and Expo moves to the next port. The app accepts a plain `http://` base URL only when
  `EXPO_PUBLIC_API_ENV=development`.
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
- **External links** on the landing page (GitHub repos) only open online.

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

# Run tests (SQLite + mocks, no services or network needed)
docker run --rm --network none -e TESTING=1 -e DATABASE_URL=sqlite:////tmp/test.db   -e SECRET_KEY=test-secret-key-at-least-32-characters-long -e AWS_ACCESS_KEY_ID=x -e AWS_SECRET_ACCESS_KEY=y   -v "$PWD/tests:/code/tests:ro" -v "$PWD/pytest.ini:/code/pytest.ini:ro"   knee_oa_api:offline python -m pytest -q -p no:cacheprovider
```

Code changes need `.\start-offline.ps1 -Build`. The image doesn't bind-mount the source.
