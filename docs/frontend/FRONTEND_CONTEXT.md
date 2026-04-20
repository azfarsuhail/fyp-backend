# Knee OA Frontend - Project Context

## Overview

This is an Expo React Native frontend for a Knee Osteoarthritis (Knee OA) medical image analysis app. The app supports patient login, questionnaire intake, X-ray upload and analysis, report viewing, and evidence-based recommendations.

The frontend is designed as an offline-first mobile app with local SQLite persistence and backend synchronization through a FastAPI API.

## Tech Stack

- Expo SDK 54
- React 19
- React Native 0.81
- React Navigation stack navigation
- expo-linear-gradient for the visual system
- expo-sqlite for local persistence
- react-native-gesture-handler, react-native-safe-area-context, react-native-screens

## Current Folder Structure

The project has been organized into a standard Expo layout:

- `src/screens/` - screen-level UI and navigation flows
- `src/components/` - reusable UI pieces
- `src/services/` - API, SQLite, and sync logic
- `src/config/` - theme and design tokens
- root files - app entry, configuration, docs, and package metadata

## Current Source Layout

### Screens
- `src/screens/SplashScreen.js`
- `src/screens/LoginScreen.js`
- `src/screens/HomeScreen.js`
- `src/screens/QuestionnaireScreen.js`
- `src/screens/ImageCaptureScreen.js`
- `src/screens/ResultScreen.js`
- `src/screens/RecommendationsScreen.js`

### Components
- `src/components/ProgressBar.js`
- `src/components/DisclaimerBanner.js`

### Services
- `src/services/api.js`
- `src/services/database.js`
- `src/services/sync.js`

### Config
- `src/config/theme.js`

## App Entry

- `index.js` registers the root app with Expo.
- `App.js` defines the stack navigator and routes.
- Initial route: `Splash`
- Navigation flow: `Splash` -> `Login` -> `Questionnaire` -> `Home` -> `ImageCapture` -> `Result` -> `Recommendations`

## Screen Responsibilities

### Splash Screen
- Displays branding and loading animation.
- Automatically navigates to `Login` after a short delay.
- No backend calls.

### Login Screen
- Collects email and password.
- Calls backend login endpoint through `loginUser`.
- Stores JWT token in the API service via `setAuthToken`.
- Persists the user locally via SQLite `saveUser`.
- Falls back to demo credentials if backend is unavailable.

### Questionnaire Screen
- Collects clinical intake data such as age, sex, pain level, mobility, history, and medication.
- Saves questionnaire response locally in SQLite.
- Updates the backend profile with relevant fields using `updateProfile`.
- Derives backend-ready values such as mobility level and current meds.
- Passes clinical profile context to the next screen.

### Home Screen
- Main dashboard with quick actions and recent activity UI.
- Passes route context to downstream screens.
- Clears auth token on logout.
- Mostly UI-driven, but part of the authenticated flow.

### Image Capture Screen
- Mock UI for selecting an image source.
- Uploads the image to the backend using `uploadXrayImage`.
- Sends the returned `image_id` to `analyzeUploadedXray`.
- Saves scan result locally in SQLite.
- Navigates to `Result` with analysis payload and clinical context.

### Result Screen
- Displays the reported KL grade, summary, and disclaimer.
- Receives the backend analysis payload from the image flow.
- Routes to `Recommendations` with grade and profile context.

### Recommendations Screen
- Calls backend recommendation and video library endpoints.
- Renders structured recommendations and exercise videos.
- Falls back to the analysis recommendation if the backend response is sparse.

## Backend Integration

The frontend is wired to the FastAPI backend described in `BACKEND_CONTEXT.md` and `openapi.json`.

### Base URL
- Configured through `EXPO_PUBLIC_BACKEND_URL` in `.env.local`
- Example value: `http://localhost:8000`

### API Service Behavior
- `src/services/api.js` centralizes all requests.
- It adds Authorization headers when a token exists.
- It handles JSON and non-JSON responses.
- It exposes helpers for:
  - login
  - image upload
  - diagnostic analysis
  - profile update
  - report fetch
  - recommendations
  - video library
  - mobile sync
  - health check

## Backend Contract Used by the Frontend

The frontend follows the documented backend structure:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/upload/`
- `POST /api/v1/diagnostic/analyze`
- `GET /api/v1/diagnostic/reports`
- `GET /api/v1/diagnostic/reports/{report_id}`
- `GET /api/v1/recommendation/`
- `GET /api/v1/profile/me`
- `PUT /api/v1/profile/me`
- `GET /api/v1/profile/me/history`
- `POST /api/v1/profile/me/change-password`
- `GET /api/v1/videos/`
- `GET /api/v1/videos/{video_id}`
- `GET /api/v1/mobile/sync/data`
- `GET /api/v1/mobile/sync/summary`
- `POST /api/v1/mobile/sync/export`
- `GET /api/v1/mobile/sync/status`
- `GET /health`

## Local Data Storage

SQLite is used for offline-first support and cached records.

### Local Tables Used
- users
- questionnaire_responses
- scan_history
- recommendations
- video_references
- sync_log

### Local Storage Responsibilities
- cache user profile and token-related info
- save questionnaire submissions locally
- save scan results locally
- support sync workflows when the device is online

## Design System

The app uses a dark medical-themed visual language with gradients and glassy surfaces.

### Theme Tokens
Defined in `src/config/theme.js`:
- colors
- font weights
- spacing sizes
- border radii
- shadows
- KL grade color helpers

### Shared UI
- `ProgressBar` renders multi-step questionnaire progress.
- `DisclaimerBanner` shows the medical disclaimer on diagnostic and recommendation screens.

## Current Navigation and Data Flow

1. User sees `Splash`.
2. User logs in on `Login`.
3. Questionnaire data is captured on `Questionnaire`.
4. User lands on `Home` with clinical context.
5. User opens `ImageCapture` to upload an X-ray.
6. Image is uploaded and analyzed by the backend.
7. Result appears on `Result`.
8. Recommendation details are shown on `Recommendations`.

## Environment Files

### `.env.local`
Contains the backend base URL used by the frontend:
- `EXPO_PUBLIC_BACKEND_URL`

This file is intended for local configuration and should not be treated as a shared production secret.

## Root Files Still Present

- `App.js`
- `index.js`
- `app.json`
- `package.json`
- `package-lock.json`
- `metro.config.js`
- `eas.json`
- `openapi.json`
- `README.md`
- `BACKEND_CONTEXT.md`
- `.env.local`

## Development Commands

```bash
npm install
npm start
npm run android
npm run ios
npm run web
```

## Practical Notes

- The image picker is still mocked in the UI, so the capture experience is not yet a real camera/gallery integration.
- Some screens still use fallback UI data when backend responses are incomplete.
- The app expects authenticated API access for profile, diagnostic, recommendation, and video endpoints.
- The frontend currently assumes one active logged-in user at a time.

## Maintenance Guidance

When changing this app, keep these rules consistent:

- Update `src/services/api.js` first for backend contract changes.
- Keep screen files focused on UI and navigation.
- Keep shared styles and tokens in `src/config/theme.js`.
- Keep local persistence and sync logic in `src/services/`.
- Prefer route params for passing analysis/profile context between screens.
- Preserve offline fallback behavior unless the app is explicitly converted to online-only.

## Known Gaps

- Real camera/gallery selection is not implemented yet.
- The dashboard remains mostly static UI data.
- Questionnaire data is only partially mapped to backend profile fields.
- Report history and profile history screens are not present yet.

## Summary

This frontend is an Expo mobile app for Knee OA analysis with a clean source split, local persistence, authenticated backend integration, and a navigation flow centered on login, questionnaire intake, X-ray analysis, and clinical recommendations.
