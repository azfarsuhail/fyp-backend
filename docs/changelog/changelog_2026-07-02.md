# Changelog - 2026-07-02

## Overview
Systemic backend remediation focused on removing event-loop blocking work, reducing database round-trips, fixing resource lifecycle issues, and hardening shared state for concurrent requests.

## Changes

### 1. Event Loop Unblocking
**Status:** Complete

**What Changed:**
- Moved synchronous CPU-heavy diagnostic work out of the async request path in `app/api/v1/diagnostic.py`
- Wrapped CLIP-based image validation, TensorFlow inference, and recommendation generation in `run_in_threadpool()`
- Kept the public API unchanged

**Why:**
- Prevents the FastAPI event loop from being blocked by image validation, model inference, and semantic ranking
- Improves concurrency under load

**Files Modified:**
- `app/api/v1/diagnostic.py`

### 2. Database Fetch Optimization
**Status:** Complete

**What Changed:**
- Replaced multi-query fetch patterns with eager loading using `joinedload()`
- Reduced repeated user-to-related-entity lookups in mobile sync, report retrieval, and profile history endpoints

**Why:**
- Cuts avoidable round-trips to the database
- Lowers latency and reduces connection pool pressure

**Files Modified:**
- `app/services/mobile_sync.py`
- `app/api/v1/diagnostic.py`
- `app/api/v1/profile.py`

### 3. Resource Lifecycle Hardening
**Status:** Complete

**What Changed:**
- Replaced the module-level S3 client pattern with a client factory and explicit close handling
- Added rollback-on-failure handling around database commits in auth and OTP flows
- Replaced a raw SQLite connection with a context manager in mobile sync export logic

**Why:**
- Prevents leaked sockets, file handles, and incomplete transactions
- Improves connection pool health and failure recovery

**Files Modified:**
- `app/services/s3_service.py`
- `app/services/otp_service.py`
- `app/api/v1/auth.py`
- `app/services/mobile_sync.py`

### 4. Thread-Safe Shared State
**Status:** Complete

**What Changed:**
- Added locking around lazy singleton initialization for the diagnostic model and validation agent
- Added locking around recommendation model and knowledge-base loading
- Added locking around the in-memory auth rate limiter counters

**Why:**
- Prevents race conditions during first-load initialization
- Avoids lost updates in request counters under concurrent traffic

**Files Modified:**
- `app/agents/diagnostic_agent.py`
- `app/agents/validation_agent.py`
- `app/agents/recommendation_agent.py`
- `app/core/security_middleware.py`

## Safety Notes
- No API signatures were changed.
- The rate limiter is still in-memory and process-local; it is thread-safe now, but not shared across multiple worker processes.
- S3 clients are now explicitly closed after use, which is safer for long-running workers.

## Validation
- Syntax checks passed for all edited files.
- Changes were applied incrementally by task to keep the remediation bounded and reversible.
