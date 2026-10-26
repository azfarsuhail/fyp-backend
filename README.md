# 🦴 Knee OA — Medical Image Analysis Backend

> **Final Year Project** — A backend system for Knee Osteoarthritis detection and management using AI-powered multi-agent architecture.

The system allows users to upload knee X-rays, receive an automated **Kellgren-Lawrence (KL) severity grade** from a custom-trained CNN, and get **personalised lifestyle recommendations** plus a structured **medication catalog** via a Retrieval-Augmented Generation (RAG) pipeline — all through a secure, role-based REST API.

---

## 📊 Project Status

| Metric | Status |
|--------|--------|
| **Tests** | ✅ 145/145 Passing (100%) |
| **Code Quality** | ✅ A- (90/100) |
| **Security** | ✅ Hardened |
| **Production Ready** | ✅ Yes |

---

## 🔒 Security Features (Latest)

### ✅ Implemented Security Measures
- **JWT Authentication** with bcrypt password hashing
- **RBAC** (Patient, GP, Admin) with role-based endpoint access
- **Rate Limiting** (5 login attempts/minute, 5 register/hour, 3 forgot-password/hour per IP)
- **Password Validation** (8+ chars, uppercase, lowercase, numbers, special chars)
- **Password Reset Flow** (secure JWT-based forgot/reset password with email)
- **OTP Password Reset** (June 2026) — Secure 6-digit OTP code via email with 5-minute expiration, bcrypt hashing, and brute-force protection (3-attempt lockout)
- **Security Headers** (X-Frame-Options, CSP, X-XSS-Protection, etc.)
- **CORS Configuration** (configurable allowed origins)
- **Environment-based Secrets** (SECRET_KEY from .env)
- **Admin Registration Blocked** (manual creation only)
- **Profile Change Logging** (audit trail for all updates)
- **Gatekeeper Validation** (CLIP zero-shot image authenticity check)
- **Global Exception Handlers** (prevents stack trace leakage)
- **Async HTTP Client** (httpx for non-blocking S3 downloads)

### 🚨 Security Hardening Applied (March 2026)
- ✅ SECRET_KEY now loaded from environment variable
- ✅ Token expiry reduced from 60 to 15 minutes
- ✅ Generic exception handling replaced with specific exceptions
- ✅ File upload validation added (size limits, content-type checks)
- ✅ Security middleware with headers and rate limiting
- ✅ Input sanitization for error messages

### 🚨 Security Hardening Applied (June 2026)
- ✅ **Event Loop Protection**: Replaced synchronous `requests.get()` with `httpx.AsyncClient()` in diagnostic pipeline
- ✅ **Expanded Rate Limiting**: Added `/register` (5/hour) and `/forgot-password` (3/hour) endpoints
- ✅ **Global Exception Handlers**: Three handlers prevent stack trace leakage and ensure consistent error formatting
- ✅ **Middleware Consolidation**: `RateLimitAuthMiddleware` handles all auth endpoints uniformly
- ✅ **IP Proxy Forwarding**: Real client IP extraction from `X-Forwarded-For` header for accurate rate limiting

### 🏗️ Infrastructure & Deployment (April 2026)
- ✅ **NGINX Reverse Proxy**: Rate limiting (10r/s, burst=20), proxy headers (X-Forwarded-For, X-Real-IP)
- ✅ **SSL/TLS**: Let's Encrypt configuration (docker-compose ready)
- ✅ **Cloud Hosting**: AWS EC2 c6a.xlarge (4 vCPU, 16GB RAM)
- ✅ **CI/CD**: GitHub Actions automated Docker build with semver tagging (v1.0.0)
- ✅ **Multi-Stage Dockerfile**: Builder + runtime stages, non-root user (appuser)
- ✅ **Resource Limits**: 3.5 CPU, 14GB memory reservation (2 CPU, 4GB)
- ✅ **Health Checks**: NGINX depends on API health (urllib-based)

### ☁️ S3 Storage & Access (June 2026)
- ✅ **Private S3 Objects**: Uploaded images and video assets are stored private in S3. The database stores the S3 object key (e.g., `xrays/abc123.png`) rather than a public URL.
- ✅ **Presigned URLs**: API endpoints now return short-lived presigned URLs for clients to download objects. This improves security and auditability — objects remain private in the bucket and access is granted only via temporary URLs.
- ✅ **IAM Guidance**: The service requires an IAM role or credentials with `s3:PutObject`, `s3:GetObject`, and `s3:GeneratePresignedUrl` (via `s3:GetObject`) permissions for the bucket. Update `S3_BUCKET_NAME`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` in your `.env` or use instance profiles.

---

## 👥 User Roles

The system supports three distinct user roles with different capabilities:

### **Patient**
- Upload knee X-ray images for diagnostic analysis
- View personal diagnostic reports with KL grades
- Access personalized lifestyle recommendations
- Browse exercise video library
- Manage personal profile (name, age, pain level, mobility, etc.)
- View exercise videos tailored to their condition

### **General Practitioner (GP)**
- **Assign patients** to their clinical panel
- **Upload X-rays** for assigned patients
- **View patient diagnostic reports** and history
- **Check patient profile change history** (audit trail)
- **Generate treatment plans** based on KL grade and patient context
- Access exercise videos for patient education
- Manage their own profile

### **Admin** (Separate Portal)
- View comprehensive analytics dashboard
- Manage medication catalog
- View system-wide statistics
- Access is restricted to a separate admin portal (not in main UI)

---

## 📐 System Architecture

```mermaid
flowchart LR
    client["Mobile App<br/>(Client)"]

    subgraph proxy["NGINX Reverse Proxy"]
        direction TB
        nginx["SSL/TLS Termination (Let's Encrypt)<br/>HTTP → HTTPS redirect<br/>Rate Limiting on /api/ (10r/s, burst=20)<br/>Proxy Headers (X-Forwarded-For, X-Real-IP)"]
        static["Static landing page<br/>+ APK download"]
    end

    subgraph app["FastAPI Application Layer"]
        direction TB
        middleware["Middleware<br/>CORS · Security Headers (CSP, X-Frame-Options, etc.)<br/>Auth Rate Limiting"]

        subgraph routers["API Routers — /api/v1"]
            direction TB
            auth["Auth<br/>/auth/*"]
            upload["Upload<br/>/upload/"]
            diagnostic["Diagnostic<br/>/diagnostic/*"]
            recommendation["Recommendation<br/>/recommendation/"]
            profile["Profile<br/>/profile/*"]
            video["Video Library<br/>/videos/*"]
            medications["Medications<br/>/medications/ · /admin/medications/"]
            mobile["Mobile Sync<br/>/mobile/*"]
            analytics["Admin Analytics<br/>/admin/analytics/*"]
        end

        core["Core: JWT Auth + RBAC + DB Session"]
        middleware --> routers --> core
    end

    subgraph agents["AI Agents"]
        direction TB
        gatekeeper["Gatekeeper Agent<br/>CLIP zero-shot<br/>(openai/clip-vit-base-patch32)"]
        diagAgent["Diagnostic Agent<br/>CNN.keras (TensorFlow)"]
        recAgent["Recommendation Agent<br/>Parametric RAG"]
        vectors["Sentence-Transformers<br/>(all-MiniLM-L6-v2)<br/>+ vector store files"]
        recAgent --> vectors
    end

    neon[("Neon DB<br/>PostgreSQL + SQLAlchemy")]
    s3[("AWS S3<br/>X-rays + Videos<br/>(private, presigned URLs)")]
    resend["Resend<br/>(email)"]

    client -->|"HTTPS / JSON"| nginx
    nginx -->|"/api/, /redoc,<br/>/openapi.json, /.well-known/"| middleware

    core --> neon
    upload & video & diagnostic --> s3
    auth -->|"reset link / OTP"| resend
    diagnostic --> gatekeeper & diagAgent & recAgent
    recommendation --> recAgent
    recAgent -->|"videos + medications<br/>by KL grade"| neon
```

### Request Middleware Order

Starlette runs the last-added middleware first, so every request passes through the layers in this order (see `app/main.py`):

```mermaid
flowchart LR
    request(["Request<br/>(from NGINX)"])
    cors["CORSMiddleware<br/>answers OPTIONS preflight"]
    rate{"RateLimitAuthMiddleware<br/>POST login, register,<br/>forgot-password, request-otp:<br/>over the limit for this client IP?"}
    limited(["429 Too Many Requests<br/>+ Retry-After"])
    headers["SecurityHeadersMiddleware"]
    router["Router + dependencies<br/>get_current_user · RoleChecker"]
    response(["Response with X-Frame-Options, CSP,<br/>X-Content-Type-Options, Referrer-Policy"])

    request --> cors --> rate
    rate -->|yes| limited
    rate -->|no| headers --> router
    router -->|"response passes back through<br/>SecurityHeadersMiddleware"| response
```

The client IP comes from the first `X-Forwarded-For` entry set by NGINX, or the socket address when the API is called directly.

### Deployment Topology

```mermaid
flowchart LR
    users["Mobile App / Browser"]

    subgraph host["AWS EC2 host — docker compose"]
        direction LR
        subgraph nginxBox["knee_oa_nginx (nginx:alpine)"]
            nginx["Port 80 → 301 to HTTPS<br/>Port 443 TLS (Let's Encrypt)<br/>Serves static/ + APK download"]
        end
        subgraph apiBox["knee_oa_api (Dockerfile runtime stage)"]
            api["uvicorn app.main:app on :8000<br/>Non-root appuser<br/>Limits 3.5 CPU / 14G · 1 NVIDIA GPU"]
        end
        nginx -->|"proxy_pass http://api:8000"| api
        nginx -.->|"depends_on: service_healthy<br/>(GET /health)"| api
    end

    neon[("Neon DB")]
    s3[("AWS S3")]
    resend["Resend"]

    users -->|"HTTPS"| nginx
    api --> neon
    api --> s3
    api --> resend
```

### Multi-Agent Design

The backend uses a **decoupled multi-agent architecture** where each agent has a single responsibility:

| Agent | Responsibility | Technology |
|-------|---------------|------------|
| **Gatekeeper Agent** | Validates image authenticity, rejects OOD/garbage uploads | CLIP zero-shot classifier (openai/clip-vit-base-patch32) |
| **Diagnostic Agent** | Predicts KL severity grade (0–4) from a preprocessed knee X-ray | TensorFlow CNN (`.keras` model) |
| **Recommendation Agent** | Generates personalised lifestyle advice and exercise video links based on KL grade, pain, and mobility | Sentence-Transformers RAG with cosine similarity retrieval |

The agents are invoked sequentially during the `/diagnostic/analyze` pipeline but are fully independent — the Recommendation Agent can also be called standalone via `/recommendation/`. The Gatekeeper runs first to ensure only valid knee X-rays proceed to the diagnostic pipeline.

---

## 🗂️ Project Structure

```
knee_oa_backend/
├── app/
│   ├── main.py                    # FastAPI app entry point, router registration, CORS
│   ├── agents/
│   │   ├── diagnostic_agent.py    # CNN model loader + KL grade inference
│   │   └── recommendation_agent.py# RAG pipeline + exercise video retrieval
│   ├── api/v1/
│   │   ├── auth.py                # POST /register, POST /login, POST /forgot-password, POST /reset-password
│   │   ├── upload.py              # POST / (X-ray upload to S3)
│   │   ├── diagnostic.py          # POST /analyze, GET /reports, GET /reports/{id}
│   │   ├── recommendation.py      # GET / (standalone recommendations)
│   │   ├── profile.py             # GET/PUT /me, GET /me/history, GET /patients/{patient_id}/history, POST /me/change-password
│   │   ├── video.py               # CRUD for exercise video library (GET, POST, PUT, DELETE, upload endpoints)
│   │   ├── medications.py         # Public medication catalog + admin medication creation
│   │   ├── mobile_sync.py         # Mobile app data sync endpoints (GET /sync/data, /sync/summary, POST /sync/export, GET /sync/status)
│   │   └── admin_analytics.py     # Admin analytics endpoints (GET /analytics/dashboard, /analytics/users, /analytics/reports, /analytics/activity)
│   ├── core/
│   │   ├── config.py              # SQLAlchemy engine, session, Base (Neon DB)
│   │   ├── dependencies.py        # get_db, get_current_user, RoleChecker
│   │   └── security.py            # bcrypt hashing, JWT creation/validation, password reset tokens
│   ├── middleware/
│   │   ├── security_headers.py    # Security headers middleware (CSP, X-Frame-Options, etc.)
│   │   └── rate_limiting.py       # Rate limiting middleware for auth endpoints
│   ├── models/
│   │   ├── user.py                # USER table
│   │   ├── image.py               # IMAGE table (uploaded X-rays)
│   │   ├── report.py              # REPORT table (diagnosis + recommendations)
│   │   ├── library.py             # EXERCISE_VIDEO table
│   │   └── medication.py          # MEDICATION table
│   ├── schemas/
│   │   ├── user_schema.py         # UserCreate, UserOut, Token, ForgotPasswordRequest, ResetPasswordRequest
│   │   ├── image_schema.py        # ImageUploadResponse, ImageOut
│   │   ├── report_schema.py       # DiagnosticRequest, ReportOut
│   │   ├── recommendation_schema.py # Medication + RecommendationResult output schemas
│   │   └── profile_schema.py      # ProfileUpdate, ProfileOut, PasswordChange
│   ├── services/
│   │   ├── email.py               # Email service (Resend integration, password reset emails)
│   │   ├── image_processor.py     # RGB → Centre-crop ROI → Resize 224×224 → DenseNet preprocessing
│   │   ├── s3_service.py          # S3 upload/download/presigned URL helpers
│   │   ├── medication_service.py  # Medication catalog queries and serialization
│   │   └── mobile_sync.py         # Mobile sync data export and aggregation
│   └── ml_assets/
│       ├── cnn_weights/
│       │   └── CNN.keras           # Diagnostic CNN model (KL grading)
│       └── vector_store/           # RAG knowledge base + embeddings (built by scripts/generate_embeddings.py)
├── alembic/
│   ├── env.py                     # Alembic config (loads all models for autogenerate)
│   ├── script.py.mako             # Migration template
│   └── versions/                  # Auto-generated migration files
├── scripts/
│   ├── init_admin.py              # Initialize default admin account
│   └── cleanup_test_db.py         # Test database cleanup utility
├── tests/
│   ├── conftest.py                # In-memory SQLite, fixtures, auth helpers
│   ├── test_auth.py               # 12 tests — registration + login (admin blocked)
│   ├── test_upload.py             # 7 tests — X-ray upload with S3 mocking
│   ├── test_diagnostic.py         # 11 tests — CNN/RAG pipeline + reports
│   ├── test_recommendation.py     # 9 tests — standalone recommendations
│   ├── test_profile.py            # 26 tests — profile CRUD + password + **logging & history**
│   ├── test_video.py              # 19 tests — video library CRUD + RBAC
│   ├── test_mobile_sync.py        # 20 tests — mobile sync endpoints + data export
│   ├── test_health.py             # 2 tests — root + health check
│   └── test_password_reset.py     # 10 tests — forgot/reset password flow + token validation
│
│ **Total: 145 tests, ALL PASSING**
├── Dockerfile                     # Python 3.10-slim, ML-optimised, multi-stage build
├── docker-compose.yml             # Dev setup with hot-reload volume mount
├── docker-compose.prod.yml        # Production setup with NGINX reverse proxy
├── requirements.txt               # All dependencies with version pins
├── alembic.ini                    # Alembic configuration
├── pytest.ini                     # Pytest configuration
└── .env                           # (You create this) — secrets & DB URL
```

---

## 🔐 Authentication & Authorization

### JWT Token Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as Server (FastAPI)
    participant DB as Neon DB

    Note over C,DB: Registration
    C->>S: POST /auth/register<br/>{email, password, full_name, role}
    S->>S: Reject admin role + validate password strength
    S->>S: Hash password (bcrypt)
    S->>DB: Store user
    S-->>C: Return UserOut

    Note over C,DB: Login
    C->>S: POST /auth/login<br/>{username, password}
    S->>DB: Look up user by email
    S->>S: Verify password (bcrypt)
    S->>DB: Update last_login
    S->>S: Generate JWT (sub = email, role)
    S-->>C: Return {access_token, token_type}

    Note over C,DB: Authenticated request
    C->>S: GET /profile/me<br/>Authorization: Bearer #lt;JWT#gt;
    S->>S: Decode JWT → extract email + role
    S->>DB: Load user by email
    S-->>C: Return profile
```

### OTP Password Reset Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as Server (FastAPI)
    participant DB as Neon DB
    participant E as Resend (email)

    Note over C,E: Request a code (rate-limited to 3 per hour per IP)
    C->>S: POST /auth/request-otp {email}
    S->>DB: Look up user by email
    opt user exists
        S->>S: Generate 6-digit code (secrets) + bcrypt hash
        S->>DB: Insert otp_verification (expires_at = now + 5 min)
        S-)E: Send OTP email (background task)
    end
    S-->>C: Generic success message (prevents email enumeration)

    Note over C,E: Verify the code and reset the password
    C->>S: POST /auth/verify-otp-and-reset<br/>{email, otp_code, new_password}
    S->>DB: Look up user by email
    S->>S: Validate new password strength
    S->>DB: Fetch latest active OTP (pending, not expired)
    alt code matches
        S->>DB: Mark verified, update password_hash,<br/>add PROFILE_LOG entry, delete user's OTP records
        S-->>C: 200 Password reset
    else no active OTP
        S-->>C: 400 Invalid or expired OTP code
    else wrong code
        S->>DB: attempts += 1 (locked at 3)
        S-->>C: 400 Attempts remaining / OTP locked
    end
```

### OTP Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending : POST /auth/request-otp<br/>is_verified = 0, attempts = 0
    Pending --> Pending : wrong code<br/>(attempts below 3)
    Pending --> Verified : correct code<br/>is_verified = 1
    Pending --> Locked : 3rd wrong code<br/>is_verified = 2
    Pending --> Expired : 5 minutes pass<br/>(ignored by active-OTP lookup)
    Verified --> [*] : password updated,<br/>OTP records deleted
    Locked --> [*]
    Expired --> [*]
```

### Role-Based Access Control (RBAC)

| Endpoint | Patient | GP | Admin |
|----------|---------|-----|-------|
| `POST /auth/register` | ✅ | ✅ | ❌ (disabled) |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `POST /auth/forgot-password` | ✅ | ✅ | ✅ |
| `POST /auth/reset-password` | ✅ | ✅ | ✅ |
| `POST /upload/` | ✅ | ✅ | ❌ |
| `POST /diagnostic/analyze` | ✅ (own images) | ✅ (any image) | ❌ |
| `GET /diagnostic/reports` | ✅ (own) | ✅ (own) | ❌ |
| `GET /diagnostic/reports/{id}` | ✅ (own) | ✅ (own) | ❌ |
| `GET /recommendation/` | ✅ | ✅ | ❌ |
| `GET /profile/me` | ✅ | ✅ | ✅ |
| `PUT /profile/me` | ✅ | ✅ | ✅ |
| `GET /profile/me/history` | ✅ | ✅ | ✅ |
| `GET /profile/patients/{patient_id}/history` | ❌ | ✅ | ✅ |
| `POST /profile/me/change-password` | ✅ | ✅ | ✅ |
| `GET /videos/` | ✅ | ✅ | ✅ |
| `GET /videos/{id}` | ✅ | ✅ | ✅ |
| `POST /videos/` | ❌ | ❌ | ✅ |
| `POST /videos/upload` | ❌ | ❌ | ✅ |
| `PUT /videos/{id}` | ❌ | ❌ | ✅ |
| `PUT /videos/{id}/upload` | ❌ | ❌ | ✅ |
| `DELETE /videos/{id}` | ❌ | ❌ | ✅ |
| `GET /mobile/sync/data` | ✅ | ✅ | ❌ |
| `GET /mobile/sync/summary` | ✅ | ✅ | ❌ |
| `POST /mobile/sync/export` | ✅ | ✅ | ❌ |
| `GET /mobile/sync/status` | ✅ | ✅ | ❌ |
| `GET /admin/analytics/dashboard` | ❌ | ❌ | ✅ |
| `GET /admin/analytics/users` | ❌ | ❌ | ✅ |
| `GET /admin/analytics/reports` | ❌ | ❌ | ✅ |
| `GET /admin/analytics/activity` | ❌ | ❌ | ✅ |

---

## 🤖 Diagnostic Pipeline (CNN)

### X-ray Upload

An X-ray must be uploaded before it can be analysed:

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as Server (FastAPI)
    participant S3 as AWS S3
    participant DB as Neon DB

    C->>S: POST /upload/ (multipart file)<br/>Authorization: Bearer #lt;JWT#gt;
    S->>S: RoleChecker (patient or gp)
    alt content type not PNG, JPEG or DICOM
        S-->>C: 400 Invalid file type
    else allowed type
        S->>S3: Put object at xrays/{uuid}.{ext} (private)
        S3-->>S: Object key
        S->>DB: Insert IMAGE row (s3_url = object key)
        S->>S: Sign presigned URL for the key
        S-->>C: 201 ImageUploadResponse (presigned s3_url)
    end
```

### Analysis Pipeline

When a user calls `POST /diagnostic/analyze`, the following pipeline executes:

```mermaid
flowchart TD
    start(["POST /diagnostic/analyze<br/>{image_id, pain_level, mobility_level}"])
    checks{"Image exists, caller may analyse it,<br/>and no report exists yet?"}
    download["Download raw X-ray bytes from S3<br/>(presigned URL + httpx.AsyncClient)"]

    gatekeeper{"Gatekeeper Agent<br/>CLIP zero-shot (image validation)<br/>Top label is 'a knee x-ray'<br/>with score > 0.5?"}

    subgraph diagnostic["Diagnostic Agent"]
        direction TB
        processor["Image Processor<br/>1. Load from bytes (EXIF orientation, RGB)<br/>2. Centre-crop square ROI<br/>3. Resize to 224×224<br/>4. DenseNet preprocess_input<br/>5. Reshape (1, 224, 224, 3)"]
        cnn["CNN.keras model<br/>(singleton, loaded once)<br/>model.predict() → softmax over 5 classes"]
        processor --> cnn
    end

    grade[/"KL Grade (0–4) + Confidence Score"/]
    processed["Upload processed image to S3<br/>(non-critical, failures ignored)"]

    subgraph recommendation["Recommendation Agent (Parametric RAG)"]
        direction TB
        filters["1. Hard filter by KL grade, pain, mobility<br/>2. Profile filters: kinesiophobia, occupation,<br/>medication conflicts, stairs"]
        rank["3. Embed user context (all-MiniLM-L6-v2)<br/>4. Cosine similarity → top-k (6) records<br/>5. Apply pain/mobility modifiers"]
        compose["6. Format lifestyle plan + KL-grade warnings<br/>7. Fetch exercise videos + medications from DB<br/>8. Compose advice text"]
        filters --> rank --> compose
    end

    fallback["Fallback: 'Recommendation service<br/>temporarily unavailable'"]
    save[("Full Report saved to DB")]
    reject(["Request rejected"])

    start --> checks
    checks -->|yes| download
    checks -->|no| reject
    download --> gatekeeper
    gatekeeper -->|valid| processor
    gatekeeper -->|invalid| reject
    cnn --> grade
    grade --> processed --> filters
    compose --> save
    recommendation -.->|on error| fallback
    fallback --> save
```

### Kellgren-Lawrence Grading Scale

| Grade | Severity | Description |
|-------|----------|-------------|
| 0 | Normal | No radiographic features of OA |
| 1 | Doubtful | Minute osteophytes, doubtful significance |
| 2 | Minimal | Definite osteophytes, possible joint-space narrowing |
| 3 | Moderate | Moderate osteophytes, definite narrowing, some sclerosis |
| 4 | Severe | Large osteophytes, marked narrowing, severe sclerosis |

---

## 💡 Recommendation Agent (RAG)

The Recommendation Agent uses **parametric, retrieval-only RAG** (no LLM generation) to keep advice deterministic and avoid hallucinated medical content. The knowledge base is a table of structured advice records (category, action, frequency, duration, intensity, evidence level), and the agent returns those records as typed JSON rather than generated text.

**How it works:**

1. Records are hard-filtered by KL grade range, pain threshold, and mobility requirement
2. Profile filters then remove records that conflict with the patient's kinesiophobia, occupation type, current medications, or stair access — all before ranking, so ranking always has the full candidate set
3. The user's context (KL grade, pain level, mobility) is encoded into a natural-language query with `all-MiniLM-L6-v2` (384-dim sentence embeddings)
4. Cosine similarity against the surviving records' embeddings selects the top-k (6) most relevant records
5. Pain and mobility modifiers adjust intensity and frequency, and grade-specific warnings are attached
6. Matching exercise videos and medications are fetched from the `EXERCISE_VIDEO` and `MEDICATION` tables by KL grade range
7. A text summary with a medical disclaimer is composed for backward compatibility

The vector store is committed under `app/ml_assets/vector_store/` as `parametric_knowledge.json` + `parametric_embeddings.npy`. If you change the knowledge base, regenerate the embeddings with `python scripts/generate_embeddings.py` — the agent raises an error on first use if the two files are missing or their record counts differ.

---

## 🗄️ Database Schema (Neon DB)

```mermaid
erDiagram
    USER ||--o{ IMAGE : uploads
    USER ||--o{ REPORT : owns
    IMAGE ||--o| REPORT : "analysed into"
    USER ||--o{ PROFILE_LOG : "change history"
    USER ||--o{ OTP_VERIFICATION : "password reset"

    USER {
        int user_id PK
        string email UK
        string password_hash
        string full_name
        string role "patient, gp, admin"
        int age
        int pain_level "0-10"
        string mobility_level
        boolean has_support
        string kinesiophobia
        string occupation_type
        boolean has_stairs
        string current_meds "JSON array"
        string sleep_quality
        datetime created_at
        datetime last_login
        int primary_gp_id "GP user_id, no FK"
    }

    IMAGE {
        int image_id PK
        int user_id FK
        string s3_url "S3 object key"
        string processed_s3_url
        string file_name
        string content_type
        datetime uploaded_at
    }

    REPORT {
        int report_id PK
        int image_id FK
        int user_id FK
        int kl_grade "0-4"
        float confidence
        text diagnosis_summary
        text recommendation
        text lifestyle_plan "JSON"
        text warnings "JSON"
        text medications "JSON"
        text exercise_video_urls "JSON"
        datetime created_at
    }

    PROFILE_LOG {
        int log_id PK
        int user_id FK
        string field_name
        text old_value
        text new_value
        datetime changed_at
    }

    OTP_VERIFICATION {
        int id PK
        int user_id FK
        string code_hash "bcrypt"
        datetime expires_at
        int attempts
        int is_verified "0 pending, 1 verified, 2 expired or locked"
    }

    EXERCISE_VIDEO {
        int video_id PK
        string title
        text description
        string s3_url
        string thumbnail_url
        int kl_grade_min
        int kl_grade_max
        string category
        string difficulty
        int duration_seconds
    }

    MEDICATION {
        int id PK
        string name
        string dosage
        string frequency
        text instructions
        text contraindications
        int kl_grade_min "0-4"
        int kl_grade_max "0-4"
    }
```

> `EXERCISE_VIDEO` and `MEDICATION` have no foreign keys; the Recommendation Agent matches them to a report by KL grade range (`kl_grade_min ≤ grade ≤ kl_grade_max`).

### Table Descriptions

#### USER Table
- **Core Fields**: `user_id` (PK), `email` (unique), `password_hash`, `full_name`, `role` (patient/gp/admin)
- **Patient Context (Original)**: `age`, `pain_level` (0-10), `mobility_level` (limited/moderate/good), `has_support` (boolean)
- **Patient Context (April 2026)**: `kinesiophobia` (low/moderate/high), `occupation_type` (sedentary/light_manual/heavy_manual), `has_stairs` (boolean), `current_meds` (JSON array as string), `sleep_quality` (poor/fair/good)
- **Timestamps**: `created_at`, `last_login`
- **Relationships**: One-to-many with `IMAGE`, `REPORT`, `PROFILE_LOG`

#### PROFILE_LOG Table ⭐ NEW (April 2026)
- `log_id` (PK), `user_id` (FK)
- `field_name` - Name of the field that changed
- `old_value` - Previous value (NULL if new field)
- `new_value` - New value (NULL if field removed)
- `changed_at` - Timestamp of change
- **Purpose**: Full audit trail for all profile updates
- **Indexed by**: `user_id`, `changed_at`

#### IMAGE Table
- `image_id` (PK), `user_id` (FK)
- `s3_url` - Original image URL
- `processed_s3_url` - Processed image URL (if applicable)
- `file_name`, `content_type`, `uploaded_at`
- **Relationship**: Belongs to one user

#### REPORT Table
- `report_id` (PK), `image_id` (FK), `user_id` (FK)
- **Diagnostic Fields**: `kl_grade` (0-4), `confidence` (float), `diagnosis_summary` (text)
- **Recommendation Fields**: `recommendation` (text), `lifestyle_plan` (JSON), `warnings` (JSON), `exercise_video_urls` (JSON)
- `created_at` - Timestamp
- **Relationship**: Links to one image and one user

#### EXERCISE_VIDEO Table
- `video_id` (PK)
- `title`, `description`, `s3_url`, `thumbnail_url`
- `kl_grade_min`, `kl_grade_max` - Range filter for KL grades
- `category` (strengthening/flexibility/low-impact)
- `difficulty` (beginner/intermediate/advanced)
- `duration_seconds`
- **Purpose**: Exercise video library for recommendations

#### MEDICATION Table
- `id` (PK)
- `name`, `dosage`, `frequency`, `instructions`, `contraindications`
- `kl_grade_min`, `kl_grade_max` - Validated KL range for recommendation filtering
- **Purpose**: Structured medication catalog used by the recommendation engine and admin dashboard

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user (Patient, GP only; Admin disabled) |
| `POST` | `/api/v1/auth/login` | Login and receive JWT token (rate-limited: 5 attempts/minute) |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset email (rate-limited: 3 attempts/hour) |
| `POST` | `/api/v1/auth/reset-password` | Reset password with JWT token (validates strength) |

### Image Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload/` | Upload a knee X-ray (PNG/JPEG) with Gatekeeper validation |

### Diagnostic
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/diagnostic/analyze` | Run full CNN + RAG pipeline on an image |
| `GET` | `/api/v1/diagnostic/reports` | List all reports for current user |
| `GET` | `/api/v1/diagnostic/reports/{id}` | Get a specific report |

### Recommendation
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/recommendation/` | Get standalone recommendations by KL grade |

### Medication Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/medications/` | Get the public structured medication catalog for recommendation filtering |
| `POST` | `/api/v1/admin/medications/` | Create a medication record (Admin only, bearer token required) |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/profile/me` | Get current user's profile |
| `PUT` | `/api/v1/profile/me` | Update profile (name, email, age, pain_level, mobility_level, kinesiophobia, occupation_type, has_stairs, current_meds, sleep_quality) |
| `GET` | `/api/v1/profile/me/history` | Get profile change history (audit trail) |
| `GET` | `/api/v1/profile/patients/{patient_id}/history` | Get another user's profile history (GP/Admin only) |
| `POST` | `/api/v1/profile/me/change-password` | Change password |

### Video Library
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/videos/` | List videos (filter by KL grade, category) |
| `GET` | `/api/v1/videos/{id}` | Get a specific video |
| `POST` | `/api/v1/videos/` | Create video metadata entry (Admin only) |
| `POST` | `/api/v1/videos/upload` | Upload video file to S3 (Admin only) |
| `PUT` | `/api/v1/videos/{id}` | Update video metadata (Admin only) |
| `PUT` | `/api/v1/videos/{id}/upload` | Update video file (Admin only) |
| `DELETE` | `/api/v1/videos/{id}` | Delete video entry (Admin only) |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message |
| `GET` | `/health` | Health check |

### Admin Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/analytics/dashboard` | Dashboard statistics (Admin only) - Total users, users by role, new users, images/reports, KL distribution, recent reports |
| `GET` | `/api/v1/admin/analytics/users` | Get user list with filters (Admin only) - Filter by role, date range, activity status |
| `GET` | `/api/v1/admin/analytics/reports` | Get diagnostic reports with filters (Admin only) - Filter by KL grade, date range, confidence threshold |
| `GET` | `/api/v1/admin/analytics/activity` | Get activity metrics (Admin only) - Daily/weekly/monthly trends, user engagement, upload statistics |

### Mobile Sync
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/mobile/sync/data` | Sync full user data (images, reports, history) |
| `GET` | `/api/v1/mobile/sync/summary` | Get sync summary (counts only) |
| `POST` | `/api/v1/mobile/sync/export` | Export user data to JSON file |
| `GET` | `/api/v1/mobile/sync/status` | Get sync status and availability |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- A [Neon DB](https://neon.tech) account (free tier works)
- An AWS account with an S3 bucket
- Git (for cloning and version tagging)

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd knee_oa_backend
```

Create a `.env` file in the project root:

```env
# Database (Neon DB)
DATABASE_URL=postgresql://your_user:your_password@your_neon_host/your_db?sslmode=require

# JWT Secret (change this!)
SECRET_KEY=your-super-secret-key-change-this

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=eu-west-1
S3_BUCKET_NAME=knee-oa-uploads

# CORS Configuration (optional)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
ALLOW_DEV_ORIGINS=http://127.0.0.1:3000
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up --build
```

This starts:
- **NGINX Proxy** on port 80 (rate-limited, security headers)
- **FastAPI Backend** on port 8000 (internal)
- API accessible at `http://localhost` with hot-reload enabled

### 3. Run Locally (Without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run Database Migrations (Local Development)

```bash
# Generate migration from models
alembic revision --autogenerate -m "initial tables"

# Apply to Neon DB
alembic upgrade head
```

### 5. Initialize Admin Account

```bash
python scripts/init_admin.py
```

### 6. Access the API Docs

Once running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Admin Dashboard**: [http://localhost/admin-dashboard.html](http://localhost/admin-dashboard.html)

### 5. Deploy to Production (Docker)

When deploying via Docker, database migrations must be run **from the host machine** after the container starts:

```bash
# Start the container
docker-compose up -d

# Run migrations from host machine
docker exec -it knee_oa_api alembic upgrade head

# Verify migration status
docker exec -it knee_oa_api alembic current
```

**Important**: The `alembic` command must be executed inside the running container using `docker exec`. Do not attempt to run migrations from the host machine without entering the container first.

### 6. Build & Push to Docker Hub (CI/CD)

For automated builds, push a version tag:

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

This triggers GitHub Actions to:
1. Build the Docker image
2. Tag with semver (e.g., `1.0.0`)
3. Push to Docker Hub (`${DOCKERHUB_USERNAME}/knee-oa-api`)

For continuous deployment on main branch:
```bash
git push origin main
```

This tags the image as `latest`.

```mermaid
flowchart TD
    push(["Push to main<br/>or tag v*.*.*"])

    subgraph testJob["Job: test (ubuntu-latest)"]
        direction TB
        t1["Checkout + Python 3.11"] --> t2["Set test env<br/>(SQLite DATABASE_URL, TESTING=1)"]
        t2 --> t3["pip install -r requirements.txt"] --> t4{"pytest tests/<br/>passes?"}
    end

    subgraph buildJob["Job: build (needs: test)"]
        direction TB
        b1["Checkout + free runner disk space"] --> b2["Set up Buildx + log in to Docker Hub"]
        b2 --> b3["Docker metadata: choose tags"] --> b4["Build runtime stage + push"]
    end

    push --> t1
    t4 -->|no| stopped(["Workflow fails, no image pushed"])
    t4 -->|yes| b1
    b4 -->|"push to main"| latest["knee-oa-api:latest"]
    b4 -->|"tag v1.2.3"| semver["knee-oa-api:1.2.3"]
```

To push to `main` without running this workflow (e.g. documentation-only changes), include `[skip ci]` in the head commit message.

---

## 🧪 Testing

Tests use an **in-memory SQLite** database and mock all external services (S3, CNN, RAG) so they run fast without any credentials or ML models.

```bash
# Activate venv
.venv\Scripts\activate

# Run all 105 tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_auth.py -v

# Run with coverage (install pytest-cov first)
pytest tests/ --cov=app --cov-report=term-missing
```

### Test Summary

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_health.py` | 2 | Root + health endpoints |
| `test_auth.py` | 11 | Registration, login, validation, duplicate emails |
| `test_upload.py` | 7 | File upload, type validation, S3 mocking, RBAC |
| `test_diagnostic.py` | 11 | Full pipeline mocking, reports CRUD, access control |
| `test_recommendation.py` | 9 | RAG endpoint, validation, error handling |
| `test_profile.py` | 26 | Profile CRUD, password change, duplicate email check, **logging & history** |
| `test_video.py` | 19 | Video CRUD, KL grade filtering, admin-only guards |
| `test_mobile_sync.py` | 20 | Mobile sync endpoints, data export, RBAC |
| **Total** | **105** | **All passing ✅** |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI | Async REST API with auto-generated OpenAPI docs |
| **Database** | Neon DB (PostgreSQL) | Serverless, auto-scaling relational database |
| **ORM** | SQLAlchemy 2.0 | Database models and queries |
| **Migrations** | Alembic | Schema versioning and auto-generation |
| **Auth** | JWT + bcrypt | Stateless token auth with password hashing |
| **Storage** | AWS S3 + boto3 | X-ray images and exercise video hosting |
| **ML Inference** | TensorFlow (CPU) | CNN model for KL grade prediction |
| **Image Validation** | CLIP (openai/clip-vit-base-patch32) | Zero-shot gatekeeper for OOD detection |
| **Image Processing** | Pillow + NumPy | EXIF orientation, RGB conversion, centre-crop ROI, resize, DenseNet preprocessing |
| **RAG Embeddings** | Sentence-Transformers | `all-MiniLM-L6-v2` for semantic retrieval |
| **Containerisation** | Docker + Compose | Reproducible dev/prod environments |
| **Reverse Proxy** | NGINX | Rate limiting, security headers, SSL termination |
| **CI/CD** | GitHub Actions | Automated Docker builds with semver tagging |
| **Testing** | pytest + httpx | 105 tests with in-memory SQLite and mocking |

---

## ⚠️ Known Issues & Notes

### 🚨 Critical Bug Fix: TensorFlow XLA Compiler Crash (2026-06-16)

**Issue**: Container crashes during TensorFlow inference with `ptxas 12.3.103 has a bug` error.

**Root Cause**: The `tensorflow:2.15.0-gpu` base image ships with a broken NVIDIA compiler (`ptxas` version 12.3.103) that computes math incorrectly. TensorFlow's XLA optimizer has a hardcoded kill-switch for this version.

**Solution**: A "Search and Destroy" command in the Dockerfile's RUNTIME stage replaces the broken binary with a patched version installed via pip.

**⚠️ DO NOT REMOVE**: The following Dockerfile command is **critical** and must not be removed or modified:

```dockerfile
RUN PATCHED_PTXAS=$(find /opt/venv -name ptxas -type f | head -n 1) && \
    rm -f /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/bin/ptxas
```

**Impact if Removed**: Complete container crashes during diagnostic model inference.

**Full Details**: See [ADR-001: TensorFlow XLA ptxas Compiler Bug Fix](docs/architecture/ADR-001-TensorFlow-XLA-ptxas-Fix.md)

---

### Other Known Issues

- **bcrypt must be pinned to `4.0.1`** — newer versions break `passlib`'s bcrypt backend.
- **`datetime.utcnow()` deprecation** — Python 3.12+ warns about this; will be migrated to `datetime.now(UTC)` in a future update.
- **Pydantic `class Config` deprecation** — will be migrated to `model_config = ConfigDict(...)` in a future update.
- The CNN model file (`CNN.keras`) is not included in the repository due to size — place it in `app/ml_assets/cnn_weights/`.
- The CLIP gatekeeper uses the pretrained `openai/clip-vit-base-patch32` model from HuggingFace (automatically downloaded on first use).
- **NGINX Rate Limiting**: Default is 10 requests/second with burst of 20 — adjust in `nginx.conf` if needed.
- **Docker Resource Limits**: API container is limited to 3.5 CPU and 14GB memory — adjust in `docker-compose.yml` based on your instance specs.

---

## 📄 License

This project is part of a Final Year Project (FYP) for academic purposes.

---

## 📚 Documentation

Comprehensive documentation is now organized in the [`docs/`](docs/) folder:

### 🏛️ Architecture Decision Records
- [ADR-001: TensorFlow XLA Compiler Bug Fix](docs/architecture/ADR-001-TensorFlow-XLA-ptxas-Fix.md) - Critical runtime bug fix documentation

### 🔒 Security
- [Security Audit](docs/security/SECURITY_AUDIT.md) - Vulnerability assessment
- [Security Fixes](docs/security/SECURITY_FIXES.md) - Implementation guide
- [Applied Fixes](docs/security/SECURITY_APPLIED.md) - Current security status

### 🐳 Docker & Deployment
- [Docker Audit](docs/docker/DOCKER_AUDIT.md) - Configuration review
- [Quick Reference](docs/docker/DOCKER_QUICKREF.md) - Commands & best practices

### 📱 Mobile Integration
- [Mobile API Integration Guide](docs/mobile/API_INTEGRATION_GUIDE.md) - Complete API reference for mobile developers (authentication, OTP reset, sync, diagnostics)
- [Mobile Sync Guide](docs/mobile/MOBILE_SYNC_GUIDE.md) - Offline-first architecture guide

### 📦 Git & Version Control
- [Git Guide](docs/git/GIT_GUIDE.md) - Workflow & security checklist

### 📊 Code Quality
- [Code Quality Report](docs/code-quality/CODE_QUALITY_REPORT.md) - Audit & metrics

**Documentation Index**: [docs/README.md](docs/README.md)

---

## 🎨 Admin Dashboard

Access the admin analytics dashboard at:
- **Login**: `http://localhost:8000/admin-login.html`
- **Dashboard**: `http://localhost:8000/admin-dashboard.html`
- **Medications**: `http://localhost:8000/admin-medications-upload.html`

**Features**:
- 📊 Real-time analytics charts (KL grades, user growth, confidence)
- 👥 User statistics and role distribution
- 📈 Activity monitoring and recent reports
- 💚 System health monitoring
- 💊 Medication catalog management page for admins
- 🔐 Admin-only access (RBAC protected)

**Default Credentials**:
- Email: `admin`
- Password: `admin`
- ⚠️ **Change password after first login!**

---

## 📱 Mobile App Integration

The backend provides comprehensive mobile sync capabilities:

### API Endpoints
- `GET /api/v1/mobile/sync/data` - Get all user-specific data
- `GET /api/v1/mobile/sync/summary` - Get data count summary
- `POST /api/v1/mobile/sync/export` - Export user data as JSON
- `GET /api/v1/mobile/sync/status` - Get sync status

### Medication Management
- `GET /api/v1/medications/` - Public medication catalog for the recommendation engine
- `POST /api/v1/admin/medications/` - Admin-only medication creation with bearer token auth

### What Gets Synced
- ✅ User profile (age, pain_level, mobility_level, has_support)
- ✅ User's X-ray images (metadata + S3 URLs)
- ✅ User's diagnostic reports (KL grades, recommendations)
- ✅ User's profile change history (audit trail)
- ✅ Structured medication catalog for recommendation filtering

### What Does NOT Get Synced
- ❌ Other users' data
- ❌ Exercise video library (downloaded separately)
- ❌ System configurations

**Implementation Guide**: [docs/mobile/MOBILE_SYNC_GUIDE.md](docs/mobile/MOBILE_SYNC_GUIDE.md)

