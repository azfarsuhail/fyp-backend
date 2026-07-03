# tester.html Nginx Integration Fix

## Problem Identified
The page was hardcoded to connect to `http://localhost:8000/api/v1`, but when served through nginx, API requests need to go through nginx's proxy at `/api/v1` instead.

## Nginx Configuration Analysis

### How Nginx Works
```
User Browser → Nginx (port 80/443)
    ├─ Static Files (/) → /usr/share/nginx/html/
    └─ API Requests (/api/*) → Proxy → API Container (port 8000)
```

### The Issue
- **Direct access** (localhost:8000): API calls to `http://localhost:8000/api/v1` work
- **Through nginx** (localhost): API calls to `http://localhost:8000/api/v1` fail because:
  - Static files are served from nginx, not the API container
  - Browser tries to reach API directly, bypassing nginx proxy
  - CORS issues and network configuration problems

## Solution Applied

### Smart API URL Detection
```javascript
// Detect if running through nginx (production) or directly (development)
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = isProduction ? "/api/v1" : "http://localhost:8000/api/v1";

// Helper function to build API URL
function apiURL(endpoint) {
    if (API_BASE.startsWith('http')) {
        return `${API_BASE}${endpoint}`;
    } else {
        return API_BASE.replace(/\/+$/, '') + endpoint;
    }
}
```

### How It Works

#### Development Mode (localhost:8000)
```
Browser → http://localhost:8000/tester.html
API Calls → http://localhost:8000/api/v1/...
Direct connection to API container ✅
```

#### Production Mode (nginx)
```
Browser → http://localhost/tester.html (served by nginx)
API Calls → /api/v1/... (relative path)
Nginx proxies to API container ✅
```

## Updated API Calls

All fetch calls now use `apiURL()` helper:

| Endpoint | Old Format | New Format |
|----------|-----------|------------|
| Login | `${API_BASE}/auth/login` | `apiURL('/auth/login')` |
| Register | `${API_BASE}/auth/register` | `apiURL('/auth/register')` |
| Forgot Password | `${API_BASE}/auth/forgot-password` | `apiURL('/auth/forgot-password')` |
| Verify OTP | `${API_BASE}/auth/verify-otp` | `apiURL('/auth/verify-otp')` |
| Reset Password | `${API_BASE}/auth/reset-password` | `apiURL('/auth/reset-password')` |
| Profile GET | `${API_BASE}/profile/me` | `apiURL('/profile/me')` |
| Profile PUT | `${API_BASE}/profile/me` | `apiURL('/profile/me')` |
| Change Password | `${API_BASE}/profile/change-password` | `apiURL('/profile/change-password')` |
| Analyze | `${API_BASE}/diagnostic/analyze` | `apiURL('/diagnostic/analyze')` |
| Reports | `${API_BASE}/diagnostic/reports` | `apiURL('/diagnostic/reports')` |
| Videos | `${API_BASE}/videos` | `apiURL('/videos')` |
| Admin Analytics | `${API_BASE}/admin/analytics/dashboard` | `apiURL('/admin/analytics/dashboard')` |

## Testing Instructions

### Test 1: Direct API Access (Development)
```bash
# Open tester.html directly in browser
file:///home/ubuntu/fyp-backend/static/tester.html
# Or serve with local server
python3 -m http.server 8080
# Access: http://localhost:8080/tester.html
# API calls should go to http://localhost:8000/api/v1
```

### Test 2: Through Nginx (Production-like)
```bash
# Access through nginx
http://localhost/tester.html
# API calls should go through nginx to /api/v1
```

### Test 3: Verify API Connection
```bash
# Check nginx is proxying correctly
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost/api/v1/profile/me

# Check API directly
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/profile/me
```

## Browser Console Debugging

### Check API Base URL
```javascript
// In browser console
console.log('API_BASE:', API_BASE);
console.log('isProduction:', isProduction);
console.log('apiURL("/test"):', apiURL('/test'));
```

### Expected Output

**Development Mode:**
```
API_BASE: "http://localhost:8000/api/v1"
isProduction: false
apiURL("/test"): "http://localhost:8000/api/v1/test"
```

**Production Mode (through nginx):**
```
API_BASE: "/api/v1"
isProduction: true
apiURL("/test"): "/api/v1/test"
```

## Files Modified
- `/home/ubuntu/fyp-backend/static/tester.html` (1028 lines)

## Nginx Configuration
The nginx configuration at `/home/ubuntu/fyp-backend/nginx/nginx.conf` handles:
- Static file serving from `/usr/share/nginx/html`
- API proxy to `http://api:8000` at `/api/` path
- Rate limiting (10r/s, burst=20)
- Security headers

## CORS Considerations

### Development
- API serves at `http://localhost:8000`
- Frontend serves at `http://localhost:8080` (or file://)
- CORS may need to be configured in FastAPI

### Production (nginx)
- Both frontend and API appear to come from same origin (`/`)
- No CORS issues since nginx handles proxying
- All requests go through same domain

## Success Indicators
✅ Page loads through nginx  
✅ Login works through nginx  
✅ API calls succeed (check browser console)  
✅ No CORS errors  
✅ Profile updates work  
✅ Image analysis works  
✅ Video library loads  
✅ Admin dashboard works (for admin users)

## Troubleshooting

### "Failed to fetch" Error
1. Check if API is running: `docker compose ps`
2. Check nginx logs: `docker logs knee_oa_nginx`
3. Check API logs: `docker logs knee_oa_api`
4. Verify nginx is proxying: `curl http://localhost/api/v1/health`

### CORS Errors
1. Ensure you're accessing through nginx, not directly
2. Check ALLOWED_ORIGINS in .env file
3. For development, add `http://localhost:8080` to ALLOWED_ORIGINS

### API Returns 404
1. Check endpoint path is correct
2. Verify nginx proxy configuration
3. Test API directly: `curl http://localhost:8000/api/v1/health`

### Token Issues
1. Check localStorage: `console.log(localStorage.getItem('oa_token'))`
2. Token should be present after login
3. Token expires after 15 minutes
