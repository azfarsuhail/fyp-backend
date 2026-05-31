# Changelog — 2026-05-31

- Added GP/Admin `GET /api/v1/profile/patients/{patient_id}/history` endpoint to view patient profile change history (restricted to `gp` and `admin`).
- Updated backend configuration (`app/core/config.py`) to support `DEBUG` and `TESTING` env flags, SQLite test mode, and `pool_pre_ping` for Postgres.
- Added unit tests for access control on the patient-history endpoint.
- Documentation updated: moved changelogs into `docs/changelog/` and updated architecture notes.
