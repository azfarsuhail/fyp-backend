# Changelog

## 2026-04-21 - API Contract Verification and Diagnostic Pipeline Fix

Status: Complete
Impact: Backend API reliability, documentation synchronization
Backward Compatibility: Fully compatible

---

## Overview

This maintenance update validated that the documented frontend/backend API contract matches the implemented FastAPI routes and fixed an efficiency issue in the diagnostic pipeline.

## What Was Verified

- Router registration in `app/main.py` for:
  - `/api/v1/auth`
  - `/api/v1/upload`
  - `/api/v1/diagnostic`
  - `/api/v1/recommendation`
  - `/api/v1/profile`
  - `/api/v1/videos`
  - `/api/v1/mobile`
  - `/api/v1/admin`
- Endpoint-level alignment with documented contracts in project and frontend context docs.
- API route behavior through targeted test suite execution.

## Test Validation

Command executed:

```bash
.venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_upload.py tests/test_diagnostic.py tests/test_recommendation.py tests/test_profile.py tests/test_video.py tests/test_mobile_sync.py tests/test_health.py
```

Result:

- 105 tests passed
- 0 failures
- 0 route connectivity regressions detected

## Code Fix Applied

### Diagnostic Pipeline Duplicate Inference Removed

File changed: `app/api/v1/diagnostic.py`

Issue:
- `predict_kl_grade(image_bytes)` was invoked twice in sequence inside `POST /api/v1/diagnostic/analyze`.

Fix:
- Removed the duplicated CNN inference block so the model executes once per analyze request.

Outcome:
- Reduced redundant compute in diagnostic flow.
- No API contract changes.
- No breaking changes to response payloads.

## Documentation Updates

- Updated `PROJECT_CONTEXT.md` with:
  - API contract verification status.
  - April 21 maintenance summary.
  - Current status note for verified route connectivity.
  - Cleanup of duplicated Diagnostic Agent subsection.
- Added this changelog file for traceable maintenance history.
