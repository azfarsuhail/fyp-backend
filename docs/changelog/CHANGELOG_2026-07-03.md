# Changelog - 2026-07-03

## 🎯 Major Features

### GP Workspace Implementation
- **[ADDED]** Complete GP Workspace clinical hub in `tester.html`
- **[ADDED]** Patient assignment system with dropdown selection
- **[ADDED]** Patient profile history lookup with filtered timeline
- **[ADDED]** Diagnostic upload tool for GPs to upload X-rays for patients
- **[ADDED]** Patient diagnostic report viewer with accordion display
- **[ADDED]** Treatment plan generator for GPs (KL grade, pain level, mobility level)

### GP-Patient Relationship Management
- **[ADDED]** `primary_gp_id` column to `User` model (SQLAlchemy)
- **[ADDED]** `POST /profile/patients/assign/{patient_id}` endpoint (GP role required)
- **[ADDED]** `GET /profile/patients/mine` endpoint (GP role required)
- **[ADDED]** `GET /profile/patients/search?email=...` endpoint (GP role required)
- **[ADDED]** Patient dropdown selectors in all GP Workspace sections
- **[ADDED]** Auto-sync between dropdown selection and manual input fields

## 🐛 Bug Fixes

### Critical Fixes
- **[FIXED]** 'Invalid Date' display in historical reports
  - Added `created_at: datetime` to `ReportOut` Pydantic schema
  - Updated frontend date parsing with fallback: `r.created_at ? new Date(r.created_at).toLocaleDateString(...) : 'Unknown Date'`
- **[FIXED]** Broken GP API routing in frontend
  - Corrected all GP endpoints to include `/profile` prefix
  - Fixed `gp-search-btn`, `assignPatientToMe`, and `gp-lookup-btn` functions
- **[FIXED]** Double-encoded JSON strings in current_meds history logs
  - Added parsing logic to handle both single and double-encoded JSON
  - Implemented array comparison to filter false positives
- **[FIXED]** "Use This Patient ID" hallucinated button
  - Completely replaced with "Assign to Me" button
  - Fixed button to call `assignPatientToMe()` function

### UI/UX Fixes
- **[FIXED]** History timeline showing password_hash changes
  - Filtered out all `password_hash` field logs
- **[FIXED]** History timeline showing current_meds false positives
  - Implemented JSON parsing and sorted array comparison
  - Only shows actual medication changes
- **[FIXED]** Mobile responsiveness issues
  - Added media query for sidebar (collapses on mobile)
  - Fixed grid layouts for profile, stats, and video cards
  - Adjusted padding and margins for smaller screens

## 🚀 Improvements

### User Experience
- **[IMPROVED]** GP Workspace as primary tab for GP users
  - GP Workspace now loads automatically on GP login
  - Removed "Analyze Image" and "Reports" tabs for GPs
  - GPs only see Profile and Video Library tabs
- **[IMPROVED]** Patient dropdown selection in all GP sections
  - Upload X-ray, Reports, and History sections all have patient dropdowns
  - Dropdowns auto-populate from assigned patients list
  - Manual input fields remain available as fallback
- **[IMPROVED]** Clinical workflow efficiency
  - GPs can now manage entire patient panel from one workspace
  - One-click patient selection instead of manual ID entry
  - Integrated report viewing and history lookup

### Code Quality
- **[IMPROVED]** Frontend code organization
  - Removed duplicate GP functions
  - Consolidated event handlers
  - Added clear function documentation
- **[IMPROVED]** Backend API structure
  - Added proper role-based access control for all GP endpoints
  - Implemented patient validation before assignment
  - Added error handling for non-patient users

## 🗑️ Removals

### Deprecated Features
- **[REMOVED]** Admin dashboard tabs from main UI
  - Admin functionality moved to separate portal
  - GPs no longer see admin-related buttons
- **[REMOVED]** "Analyze Image" tab for GP users
  - Replaced with dedicated "Upload X-ray for Patient" tool in GP Workspace
- **[REMOVED]** "Reports" tab for GP users
  - Replaced with "Patient Diagnostic Reports" section in GP Workspace

## 📦 Database Changes

### Schema Updates
- **[ADDED]** `primary_gp_id` column to `USER` table
  - Type: `INTEGER`, Nullable
  - Foreign Key: References `USER.user_id`
  - Purpose: Links patients to their assigned GP
- **[MIGRATION]** Applied `2026_07_03_ddaa5d75d15f_add_primary_gp_id_to_user.py`
  - Migration command: `docker exec knee_oa_api alembic upgrade head`

## 📱 Mobile Integration Notes

### New Endpoints for Mobile App
Mobile developers should be aware of these new GP-specific endpoints:

1. **Patient Search**: `GET /api/v1/profile/patients/search?email={email}`
   - Returns list of matching patients with `user_id`, `full_name`, `email`
   - Requires GP authentication

2. **Patient Assignment**: `POST /api/v1/profile/patients/assign/{patient_id}`
   - Assigns a patient to the current GP
   - Returns updated patient profile
   - Requires GP authentication

3. **My Patients**: `GET /api/v1/profile/patients/mine`
   - Returns all patients assigned to the current GP
   - Returns list with `user_id`, `full_name`, `email`
   - Requires GP authentication

### Structured Data Formats
All recommendation endpoints now return structured JSON arrays:
- `lifestyle_plan`: Array of `LifestyleItem` objects
- `warnings`: Array of `Warning` objects
- `medications`: Array of `Medication` objects
- `exercise_video_urls`: Array of S3 URL strings

Mobile apps should parse these arrays instead of relying on legacy text fields.

---

**Date**: 2026-07-03  
**Version**: 1.0.0  
**Status**: Production Ready ✅
