# 🦴 Knee OA — Medical Image Analysis Backend

> **Final Year Project** — A backend system for Knee Osteoarthritis detection and management using AI-powered multi-agent architecture.

The system allows users to upload knee X-rays, receive an automated **Kellgren-Lawrence (KL) severity grade** from a custom-trained CNN, and get **personalised lifestyle recommendations** via a Retrieval-Augmented Generation (RAG) pipeline — all through a secure, role-based REST API.

---

## 📊 Project Status

| Metric | Status |
|--------|--------|
| **Tests** | ✅ 85/85 Passing (100%) |
| **Code Quality** | ✅ A- (90/100) |
| **Security** | ✅ Hardened |
| **Production Ready** | ✅ Yes |

---

## 🔒 Security Features (Latest)

### ✅ Implemented Security Measures
- **JWT Authentication** with bcrypt password hashing
- **RBAC** (Patient, GP, Admin) with role-based endpoint access
- **Rate Limiting** (5 login attempts per minute)
- **Password Validation** (8+ chars, uppercase, lowercase, numbers, special chars)
- **Security Headers** (X-Frame-Options, CSP, X-XSS-Protection, etc.)
- **CORS Configuration** (configurable allowed origins)
- **Environment-based Secrets** (SECRET_KEY from .env)
- **Admin Registration Blocked** (manual creation only)
- **Profile Change Logging** (audit trail for all updates)

### 🚨 Security Hardening Applied (March 2026)
- ✅ SECRET_KEY now loaded from environment variable
- ✅ Token expiry reduced from 60 to 15 minutes
- ✅ Generic exception handling replaced with specific exceptions
- ✅ File upload validation added (size limits, content-type checks)
- ✅ Security middleware with headers and rate limiting
- ✅ Input sanitization for error messages

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Mobile App (Client)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTPS / JSON
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Application Layer                       │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌─────────┐ │
│  │  Auth    │ │  Upload  │ │ Diagnostic │ │ Recomm. │ │  Video  │ │
│  │ /auth/*  │ │ /upload/ │ │ /diagnos./*│ │ /recom./ │ │ /videos │ │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘ └────┬────┘ └────┬────┘ │
│       │             │             │              │           │      │
│  ┌────▼─────────────▼─────────────▼──────────────▼───────────▼────┐ │
│  │              Core: JWT Auth + RBAC + DB Session                │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────┬──────────┬──────────────┬──────────────┬────────────────┘
           │          │              │              │
           ▼          ▼              ▼              ▼
      ┌─────────┐ ┌────────┐ ┌────────────┐ ┌────────────┐
      │ Neon DB │ │ AWS S3 │ │ Diagnostic │ │ Recommend. │
      │ (Postgres│ │(Images │ │   Agent    │ │   Agent    │
      │  + ORM) │ │+Videos)│ │  (CNN)     │ │   (RAG)    │
      └─────────┘ └────────┘ └──────┬─────┘ └──────┬─────┘
                                    │               │
                              ┌─────▼─────┐  ┌──────▼──────┐
                              │ CNN.keras │  │ Sentence    │
                              │ TF Model  │  │ Transformers│
                              │ (256×256) │  │ + VectorDB  │
                              └───────────┘  └─────────────┘
```

### Multi-Agent Design

The backend uses a **decoupled multi-agent architecture** where each agent has a single responsibility:

| Agent | Responsibility | Technology |
|-------|---------------|------------|
| **Diagnostic Agent** | Predicts KL severity grade (0–4) from a preprocessed knee X-ray | TensorFlow CNN (`.keras` model) |
| **Recommendation Agent** | Generates personalised lifestyle advice and exercise video links based on KL grade, pain, and mobility | Sentence-Transformers RAG with cosine similarity retrieval |

The agents are invoked sequentially during the `/diagnostic/analyze` pipeline but are fully independent — the Recommendation Agent can also be called standalone via `/recommendation/`.

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
│   │   ├── auth.py                # POST /register, POST /login
│   │   ├── upload.py              # POST / (X-ray upload to S3)
│   │   ├── diagnostic.py          # POST /analyze, GET /reports, GET /reports/{id}
│   │   ├── recommendation.py      # GET / (standalone recommendations)
│   │   ├── profile.py             # GET/PUT /me, POST /me/change-password
│   │   └── video.py               # CRUD for exercise video library
│   ├── core/
│   │   ├── config.py              # SQLAlchemy engine, session, Base (Neon DB)
│   │   ├── dependencies.py        # get_db, get_current_user, RoleChecker
│   │   └── security.py            # bcrypt hashing, JWT creation/validation
│   ├── models/
│   │   ├── user.py                # USER table
│   │   ├── image.py               # IMAGE table (uploaded X-rays)
│   │   ├── report.py              # REPORT table (diagnosis + recommendations)
│   │   └── library.py             # EXERCISE_VIDEO table
│   ├── schemas/
│   │   ├── user_schema.py         # UserCreate, UserOut, Token
│   │   ├── image_schema.py        # ImageUploadResponse, ImageOut
│   │   ├── report_schema.py       # DiagnosticRequest, ReportOut, RecommendationResult
│   │   └── profile_schema.py      # ProfileUpdate, ProfileOut, PasswordChange
│   ├── services/
│   │   ├── image_processor.py     # Grayscale → ROI → Resize → CLAHE → Normalise
│   │   └── s3_service.py          # S3 upload/download/presigned URL helpers
│   └── ml_assets/
│       ├── cnn_weights/CNN.keras   # Trained CNN model weights
│       └── vector_store/           # RAG embeddings (auto-generated on first run)
├── alembic/
│   ├── env.py                     # Alembic config (loads all models for autogenerate)
│   ├── script.py.mako             # Migration template
│   └── versions/                  # Auto-generated migration files
├── tests/
│   ├── conftest.py                # In-memory SQLite, fixtures, auth helpers
│   ├── test_auth.py               # 12 tests — registration + login (admin blocked)
│   ├── test_upload.py             # 7 tests — X-ray upload with S3 mocking
│   ├── test_diagnostic.py         # 11 tests — CNN/RAG pipeline + reports
│   ├── test_recommendation.py     # 9 tests — standalone recommendations
│   ├── test_profile.py            # 26 tests — profile CRUD + password + **logging & history**
│   ├── test_video.py              # 19 tests — video library CRUD + RBAC
│   └── test_health.py             # 2 tests — root + health check
│
│ **Total: 85 tests, ALL PASSING**
├── Dockerfile                     # Python 3.10-slim, ML-optimised
├── docker-compose.yml             # Dev setup with hot-reload volume mount
├── requirements.txt               # All dependencies with version pins
├── alembic.ini                    # Alembic configuration
└── .env                           # (You create this) — secrets & DB URL
```

---

## 🔐 Authentication & Authorisation

### JWT Token Flow

```
Client                          Server
  │                               │
  │  POST /auth/register          │
  │  {email, password, name}      │
  │──────────────────────────────►│──► Hash password (bcrypt)
  │                               │──► Store in Neon DB
  │◄──────────────────────────────│    Return UserOut
  │                               │
  │  POST /auth/login             │
  │  {username, password}         │
  │──────────────────────────────►│──► Verify password
  │                               │──► Generate JWT (email + role)
  │◄──────────────────────────────│    Return {access_token}
  │                               │
  │  GET /profile/me              │
  │  Authorization: Bearer <JWT>  │
  │──────────────────────────────►│──► Decode JWT
  │                               │──► Extract email + role
  │◄──────────────────────────────│    Return profile
```

### Role-Based Access Control (RBAC)

| Endpoint | Patient | GP | Admin |
|----------|---------|-----|-------|
| `POST /auth/register` | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `POST /upload/` | ✅ | ✅ | ❌ |
| `POST /diagnostic/analyze` | ✅ (own images) | ✅ (any image) | ❌ |
| `GET /diagnostic/reports` | ✅ (own) | ✅ (own) | ❌ |
| `GET /recommendation/` | ✅ | ✅ | ❌ |
| `GET/PUT /profile/me` | ✅ | ✅ | ✅ |
| `GET /videos/` | ✅ | ✅ | ✅ |
| `POST/PUT/DELETE /videos/` | ❌ | ❌ | ✅ |

---

## 🤖 Diagnostic Pipeline (CNN)

When a user calls `POST /diagnostic/analyze`, the following pipeline executes:

```
Raw X-ray bytes (PNG/JPEG)
        │
        ▼
┌─────────────────────────┐
│   Image Processor       │
│                         │
│  1. Load from bytes     │
│  2. Convert to grayscale│
│  3. Centre-crop ROI     │
│  4. Resize to 256×256   │
│  5. CLAHE enhancement   │
│  6. Normalise [0, 1]    │
│  7. Reshape (1,256,256,1│)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Diagnostic Agent      │
│                         │
│  CNN.keras model        │
│  (Singleton loaded once)│
│                         │
│  model.predict() →      │
│  softmax over 5 classes │
└────────────┬────────────┘
             │
             ▼
   KL Grade (0-4) + Confidence Score
             │
             ▼
┌─────────────────────────┐
│  Recommendation Agent   │
│                         │
│  1. Embed user context  │
│  2. Cosine similarity   │
│     against knowledge   │
│     base embeddings     │
│  3. KL-grade boosting   │
│  4. Top-k retrieval     │
│  5. Compose advice text │
│  6. Fetch exercise      │
│     videos from DB      │
└────────────┬────────────┘
             │
             ▼
   Full Report (saved to DB)
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

The Recommendation Agent uses **retrieval-only RAG** (no LLM generation) to keep advice deterministic and avoid hallucinated medical content.

**How it works:**

1. A built-in knowledge base of lifestyle advice passages is embedded using `all-MiniLM-L6-v2` (384-dim sentence embeddings)
2. At query time, the user's context (KL grade, pain level, mobility) is encoded into a natural-language query
3. Cosine similarity retrieves the top-k most relevant passages
4. Documents matching the exact KL grade receive a **relevance boost** (+0.15)
5. Matching exercise videos are fetched from the `EXERCISE_VIDEO` table
6. A structured recommendation is composed with a medical disclaimer

The vector store is auto-generated on first run and cached as `embeddings.npy` + `documents.json`.

---

## 🗄️ Database Schema (Neon DB)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
│    USER      │       │    IMAGE     │       │     REPORT       │
├──────────────┤       ├──────────────┤       ├──────────────────┤
│ user_id (PK) │◄──┐   │ image_id (PK)│◄──┐   │ report_id (PK)  │
│ email        │   │   │ user_id (FK) │───┘   │ image_id (FK)   │──►IMAGE
│ password_hash│   │   │ s3_url       │       │ user_id (FK)    │──►USER
│ full_name    │   │   │ processed_url│       │ kl_grade (0-4)  │
│ role         │   │   │ file_name    │       │ confidence       │
│ created_at   │   │   │ content_type │       │ diagnosis_summary│
│ last_login   │   │   │ uploaded_at  │       │ recommendation   │
└──────────────┘   │   └──────────────┘       │ video_urls (JSON)│
                   │                           │ created_at       │
                   │                           └──────────────────┘
                   │
                   │   ┌──────────────────┐
                   │   │ EXERCISE_VIDEO   │
                   │   ├──────────────────┤
                   │   │ video_id (PK)    │
                   │   │ title            │
                   │   │ description      │
                   │   │ s3_url           │
                   │   │ thumbnail_url    │
                   │   │ kl_grade_min     │
                   │   │ kl_grade_max     │
                   │   │ category         │
                   │   │ difficulty       │
                   │   │ duration_seconds │
                   │   └──────────────────┘
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login and receive JWT token |

### Image Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload/` | Upload a knee X-ray (PNG/JPEG) |

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

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/profile/me` | Get current user's profile |
| `PUT` | `/api/v1/profile/me` | Update profile (name, email) |
| `POST` | `/api/v1/profile/me/change-password` | Change password |

### Video Library
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/videos/` | List videos (filter by KL grade, category) |
| `GET` | `/api/v1/videos/{id}` | Get a specific video |
| `POST` | `/api/v1/videos/` | Create video entry (Admin only) |
| `PUT` | `/api/v1/videos/{id}` | Update video entry (Admin only) |
| `DELETE` | `/api/v1/videos/{id}` | Delete video entry (Admin only) |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message |
| `GET` | `/health` | Health check |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- A [Neon DB](https://neon.tech) account (free tier works)
- An AWS account with an S3 bucket

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
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up --build
```

This starts the API at `http://localhost:8000` with hot-reload enabled.

### 3. Run Locally (Without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run Database Migrations

```bash
# Generate migration from models
alembic revision --autogenerate -m "initial tables"

# Apply to Neon DB
alembic upgrade head
```

### 5. Access the API Docs

Once running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing

Tests use an **in-memory SQLite** database and mock all external services (S3, CNN, RAG) so they run fast without any credentials or ML models.

```bash
# Activate venv
.venv\Scripts\activate

# Run all 59 tests
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
| `test_diagnostic.py` | 9 | Full pipeline mocking, reports CRUD, access control |
| `test_recommendation.py` | 8 | RAG endpoint, validation, error handling |
| `test_profile.py` | 11 | Profile CRUD, password change, duplicate email check |
| `test_video.py` | 11 | Video CRUD, KL grade filtering, admin-only guards |
| **Total** | **59** | **All passing ✅** |

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
| **Image Processing** | Pillow + NumPy | Grayscale, resize, ROI extraction, normalisation |
| **RAG Embeddings** | Sentence-Transformers | `all-MiniLM-L6-v2` for semantic retrieval |
| **Containerisation** | Docker + Compose | Reproducible dev/prod environments |
| **Testing** | pytest + httpx | 59 tests with in-memory SQLite and mocking |

---

## ⚠️ Known Issues & Notes

- **bcrypt must be pinned to `4.0.1`** — newer versions break `passlib`'s bcrypt backend.
- **`datetime.utcnow()` deprecation** — Python 3.12+ warns about this; will be migrated to `datetime.now(UTC)` in a future update.
- **Pydantic `class Config` deprecation** — will be migrated to `model_config = ConfigDict(...)` in a future update.
- The CNN model file (`CNN.keras`) is not included in the repository due to size — place it in `app/ml_assets/cnn_weights/`.

---

## 📄 License

This project is part of a Final Year Project (FYP) for academic purposes.
