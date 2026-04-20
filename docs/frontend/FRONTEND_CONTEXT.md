# Knee OA Frontend - Project Context

## Overview

This is an Expo React Native frontend for a Knee Osteoarthritis (Knee OA) medical image analysis app. The app supports patient login, questionnaire intake, X-ray upload and analysis, report viewing, and evidence-based recommendations.

The frontend is designed as an **offline-first mobile app** with local SQLite persistence and **bidirectional backend synchronization** through a FastAPI API.

## Tech Stack

- Expo SDK 54
- React 19
- React Native 0.81
- React Navigation stack navigation
- expo-linear-gradient for the visual system
- **expo-sqlite** for local persistence (offline-first)
- react-native-gesture-handler, react-native-safe-area-context, react-native-screens

## Current Folder Structure

The project has been organized into a standard Expo layout:

- `src/screens/` - screen-level UI and navigation flows
- `src/components/` - reusable UI pieces
- `src/services/` - API, SQLite, and sync logic
- `src/config/` - theme and design tokens
- `docs/` - project documentation and context
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
- `src/services/api.js` - Backend API calls (login, upload, analysis, sync)
- `src/services/database.js` - Local SQLite operations (CRUD for all tables)
- `src/services/sync.js` - Synchronization logic (push/pull sync, offline handling)

### Config
- `src/config/theme.js` - Theme tokens and styling

## App Entry

- `index.js` registers the root app with Expo.
- `App.js` defines the stack navigator and routes.
- Initial route: `Splash`
- Navigation flow: `Splash` → `Login` → `Questionnaire` → `Home` → `ImageCapture` → `Result` → `Recommendations`

## Screen Responsibilities

### Splash Screen
- Displays branding and loading animation.
- Automatically navigates to `Login` after a short delay.
- No backend calls.

### Login Screen ✅ UPDATED (April 21, 2026)
- Collects email and password.
- Calls backend login endpoint through `loginUser`.
- Stores JWT token in the API service via `setAuthToken`.
- Persists the user locally via SQLite `saveUser`.
- **NEW**: Pulls cloud data via `fetchLatestFromCloud()` (mobile sync)
- **NEW**: Saves pulled data to local SQLite tables
- Falls back to demo credentials if backend is unavailable.

### Questionnaire Screen
- Collects clinical intake data such as age, sex, pain level, mobility, history, and medication.
- Saves questionnaire response locally in SQLite.
- Updates the backend profile with relevant fields using `updateProfile`.
- Derives backend-ready values such as mobility level and current meds.
- Passes clinical profile context to the next screen.
- **NEW**: Questionnaire automatically logged to sync_log for cloud push

### Home Screen
- Main dashboard with quick actions and recent activity UI.
- Passes route context to downstream screens.
- Clears auth token on logout.
- **NEW**: Displays sync status (data counts, last sync time)
- Mostly UI-driven, but part of the authenticated flow.

### Image Capture Screen
- Mock UI for selecting an image source.
- Uploads the image to the backend using `uploadXrayImage`.
- Sends the returned `image_id` to `analyzeUploadedXray`.
- Saves scan result locally in SQLite.
- **NEW**: Scan logged to sync_log for cloud push
- Navigates to `Result` with analysis payload and clinical context.

### Result Screen
- Displays the reported KL grade, summary, and disclaimer.
- Receives the backend analysis payload from the image flow.
- Routes to `Recommendations` with grade and profile context.

### Recommendations Screen
- Calls backend recommendation and video library endpoints.
- Renders structured recommendations and exercise videos.
- **NEW**: Caches video data locally for offline viewing

---

## Mobile Sync Architecture (April 21, 2026) ✅ IMPLEMENTED

### Overview
The mobile app implements **bidirectional sync** with offline-first design:
- **Pull Sync**: Fetch user's cloud data after login
- **Push Sync**: Upload pending local changes every 5 minutes (when online)
- **Offline Support**: All operations work offline; sync queues locally

### Database Schema (SQLite Local)

```javascript
// User profile
users: {
    id, server_id, email, full_name, role, token, profile_data, 
    created_at, updated_at, synced
}

// Health assessment
questionnaire_responses: {
    id, user_id, age, gender, weight, height, pain_level, pain_location,
    pain_duration, mobility_score, can_bend_fully, can_climb_stairs,
    can_walk_30min, previous_injuries, surgeries, medications, 
    family_history, additional_notes, completed_at, synced
}

// X-ray scans
scan_history: {
    id, user_id, image_uri, image_type, view_type, knee_side,
    kl_grade, risk_score, analysis_result, annotations, 
    scanned_at, synced
}

// Treatment recommendations
recommendations: {
    id, user_id, scan_id, recommendation_text, exercises, 
    lifestyle_tips, generated_at, synced
}

// Exercise videos
video_references: {
    id, title, description, video_url, thumbnail_url, category,
    difficulty, duration_seconds, target_kl_grades, cached_locally
}

// Sync audit trail
sync_log: {
    id, table_name, record_id, action (insert|update|delete),
    status (pending|synced|failed), attempted_at, completed_at, 
    error_message
}
```

### Sync Service (`src/services/sync.js`) ✅ IMPLEMENTED

**Periodic Push Sync** - Every 5 minutes:
```javascript
performSync() {
    // Check if online
    // Get all pending items from sync_log
    // For each pending: call syncDataToCloud()
    // Mark as synced or failed
}
```

**Features**:
- ✅ Periodic sync (every 5 minutes)
- ✅ Offline detection and deferred sync
- ✅ Error logging and retry capability
- ✅ Automatic sync on app resume

### API Service (`src/services/api.js`) ✅ UPDATED

**Pull Sync Endpoints**:
```javascript
fetchLatestFromCloud()      // GET /api/v1/mobile/sync/data
getCloudSyncSummary()       // GET /api/v1/mobile/sync/summary
getCloudSyncStatus()        // GET /api/v1/mobile/sync/status
```

**Push Sync Endpoints**:
```javascript
syncDataToCloud()           // POST /api/v1/mobile/sync/export
```

**Authentication**:
- Bearer token from login
- Automatic refresh on 401 (TODO: implement token refresh)
- Tokens expire after 15 minutes

### Database Service (`src/services/database.js`) ✅ IMPLEMENTED

**Pull Sync Save Functions** (NEW April 21, 2026):
```javascript
savePulledUserProfile(user)           // Save cloud user to local
savePulledQuestionnaire(questionnaire) // Save cloud questionnaire
savePulledScans(scans)                // Save cloud scan history
savePulledRecommendations(recs)       // Save cloud recommendations
```

**Push Sync Functions**:
```javascript
saveQuestionnaireResponse()    // Save locally, log to sync_log
saveScanResult()               // Save locally, log to sync_log
saveRecommendation()           // Save locally, log to sync_log
```

**Sync Tracking**:
```javascript
logSyncAction(table, record_id, action)  // Log to sync_log
getPendingSyncItems()                     // Get pending changes
markSynced(sync_id)                       // Mark as synced
markSyncFailed(sync_id, error)           // Mark as failed
```

---

## Sync Data Flow

### 1. Login (Pull Sync) ✅
```
User enters credentials
    ↓
loginUser() → Backend login
    ↓
setAuthToken() + saveUser() → Local storage
    ↓
fetchLatestFromCloud() → GET /api/v1/mobile/sync/data
    ↓
savePulledUserProfile/Questionnaire/Scans/Recommendations
    ↓
startPeriodicSync() → Begin 5-min sync cycle
    ↓
Navigate to Home
```

### 2. Periodic Push Sync ✅
```
Every 5 minutes (when online)
    ↓
performSync()
    ↓
getPendingSyncItems() from sync_log
    ↓
For each pending item:
    syncDataToCloud() → POST /api/v1/mobile/sync/export
        ↓
    Backend stores in PostgreSQL
        ↓
    markSynced() in sync_log
    ↓
Log results (synced count, failed count)
```

### 3. Offline Handling ✅
```
isOnline() returns false
    ↓
Skip sync cycle
    ↓
App continues working with local SQLite
    ↓
All changes logged to sync_log (status: pending)
    ↓
When online again → Sync kicks in automatically
```

---

## Implementation Status

### ✅ Implemented (Ready to Use)
- SQLite database setup with all tables
- Push sync (5-min periodic upload)
- Offline detection and handling
- Sync logging and error tracking
- API integration points

### ⚠️ Needs Integration
- **Pull sync after login** - Functions exist, needs wiring in LoginScreen
- **Token refresh** - Backend doesn't have refresh endpoint yet
- **Incremental sync** - Currently always full sync

### 📋 Future Enhancements
- Sync status UI indicator in Home screen
- Conflict resolution for concurrent edits
- Incremental sync using timestamps
- Local SQLite encryption

---

## Service API Reference

### sync.js
```javascript
performSync()           // Manually trigger sync
startPeriodicSync(ms)   // Start 5-min sync (call on app start)
stopPeriodicSync()      // Stop periodic sync
```

### api.js
```javascript
// Pull sync
fetchLatestFromCloud(timestamp)      // Fetch all user data
getCloudSyncSummary()                // Get record counts
getCloudSyncStatus()                 // Check availability

// Push sync
syncDataToCloud(payload)             // Upload pending changes

// Auth
loginUser(email, password)           // Login and get token
setAuthToken(token)                  // Store auth token
getBackendUrl()                      // Get API base URL
```

### database.js
```javascript
// Pull sync
savePulledUserProfile(user)          // Save downloaded user
savePulledQuestionnaire(data)        // Save downloaded questionnaire
savePulledScans(scans)               // Save downloaded scans
savePulledRecommendations(recs)      // Save downloaded recommendations

// Push sync
saveQuestionnaireResponse(data)      // Save and log for sync
saveScanResult(data)                 // Save and log for sync
saveRecommendation(data)             // Save and log for sync

// Sync tracking
logSyncAction(table, id, action)     // Log sync action
getPendingSyncItems()                // Get items to sync
markSynced(syncId)                   // Mark as synced
markSyncFailed(syncId, error)        // Mark as failed
```

---

## Testing Sync

### Manual Test - Pull Sync
```bash
# Login - should pull cloud data and populate local SQLite
# Check: questionnaire_responses, scan_history, recommendations tables
```

### Manual Test - Push Sync
```bash
# 1. Fill questionnaire offline
# 2. Check sync_log - should show "pending" status
# 3. Go online - should auto-sync
# 4. Check sync_log - should show "synced" status
```

### Debug Sync
```javascript
// In HomeScreen or debug screen
const db = await getDatabase();
const pending = await db.getAllAsync('SELECT * FROM sync_log WHERE status = "pending"');
console.log('Pending sync items:', pending);
```

---

## Deployment Checklist

- [x] Mobile app has SQLite database schema
- [x] Push sync logic (5-min periodic)
- [x] Offline detection
- [ ] Pull sync wired into LoginScreen
- [ ] Sync status UI in Home screen
- [ ] Token refresh implementation
- [ ] Load test with multiple users
- [ ] Test offline → online transition
- [ ] Deploy mobile app to TestFlight/Play Store

---

**Version**: 2.0  
**Last Updated**: April 21, 2026  
**Status**: ✅ Mobile sync infrastructure ready; needs LoginScreen integration
