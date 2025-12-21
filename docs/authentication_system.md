# MinouChat Authentication System

## Overview

MinouChat uses **Clerk** for authentication, providing secure user management with social login support (Google SSO). This replaced the previous bcrypt/JWT-based system for better security and easier maintenance.

**Last Updated**: December 2025

---

## Features

### Authentication Methods
- Email/password authentication
- Google SSO (OAuth 2.0)
- Other social providers (configurable in Clerk dashboard)

### Session Management
- JWT tokens with 60-second TTL (Clerk default)
- Proactive session refresh every 45 seconds
- Automatic retry on 401 with fresh token
- Bearer token priority over cookies

### User Management
- Automatic user sync from Clerk
- Profile information (name, email, avatar)
- Database user record linked via `clerk_id`

---

## Architecture

```
Browser                    Backend                     Clerk
   │                          │                          │
   │  1. Sign in via Clerk    │                          │
   │ ────────────────────────────────────────────────>   │
   │                          │                          │
   │  2. JWT token (60s TTL)  │                          │
   │ <────────────────────────────────────────────────   │
   │                          │                          │
   │  3. API request + Bearer │                          │
   │ ───────────────────────> │                          │
   │                          │  4. Verify JWT (JWKS)    │
   │                          │ ───────────────────────> │
   │                          │                          │
   │                          │  5. Claims (sub, email)  │
   │                          │ <─────────────────────── │
   │                          │                          │
   │  6. Response             │                          │
   │ <─────────────────────── │                          │
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clerk_id TEXT UNIQUE NOT NULL,      -- Clerk user ID (user_xxx)
    username TEXT NOT NULL,
    email TEXT,
    avatar_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

---

## API Endpoints

### Authentication Routes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | Clerk sign-in page |
| `/auth/register` | GET | Clerk sign-up page |
| `/auth/logout` | GET | Logout and clear session |
| `/auth/sync` | POST | Sync Clerk user to database |

### Protected Routes
All routes except landing page require authentication:
- `/dashboard` - User dashboard
- `/chat` - Chat interface
- `/personas` - Character management
- `/settings` - User settings
- `/documents` - Document management

---

## Core Functions

### Backend (clerk_auth.py)

```python
from src.miachat.api.core.clerk_auth import (
    require_clerk_auth,
    get_current_user_from_session,
    get_clerk_session_claims,
)

# Require authentication (FastAPI dependency)
@app.get("/protected")
async def protected_route(user = Depends(require_clerk_auth)):
    return {"message": f"Hello {user.username}"}

# Optional authentication
@app.get("/optional")
async def optional_auth(request: Request, db = Depends(get_db)):
    user = await get_current_user_from_session(request, db)
    if user:
        return {"logged_in": True, "user": user.username}
    return {"logged_in": False}
```

### Frontend (authFetch)

```javascript
// Authenticated fetch with automatic token refresh
async function authFetch(url, options = {}) {
    await clerkReadyPromise;

    // Get fresh token from Clerk SDK
    const token = await window.Clerk.session?.getToken();
    if (token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, options);

    // Retry on 401 with fresh token
    if (response.status === 401 && !options._retried) {
        await window.Clerk.session?.touch();
        return authFetch(url, { ...options, _retried: true });
    }

    return response;
}
```

---

## Token Handling

### The 60-Second Challenge

Clerk uses short-lived JWT tokens (60-second TTL) for security. This requires:

1. **Proactive Refresh**: Session touch every 45 seconds
2. **Retry Logic**: Automatic retry on 401 with fresh token
3. **Bearer Priority**: Backend prefers Bearer token over stale cookies

### Implementation

```javascript
// Proactive refresh (frontend)
setInterval(async () => {
    if (window.Clerk?.session) {
        await window.Clerk.session.touch();
    }
}, 45000);  // Every 45 seconds
```

```python
# Backend token verification with leeway
claims = jwt.decode(
    session_token,
    signing_key.key,
    algorithms=["RS256"],
    leeway=30  # 30 seconds tolerance
)
```

---

## Configuration

### Environment Variables

```bash
# Required
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

### Clerk Dashboard Settings

1. **Allowed Origins**: `http://localhost:8080`, your production domain
2. **Redirect URLs**:
   - Sign-in: `/dashboard`
   - Sign-up: `/dashboard`
3. **Social Connections**: Enable Google OAuth

---

## Security Features

### JWT Verification
- JWKS-based signature verification
- Token expiry validation with 30s leeway
- Issuer and audience validation

### Request Security
- Bearer token takes priority over cookies
- Fresh tokens required for sensitive operations
- Automatic session invalidation on logout

### Error Handling
- Specific error codes: `token_expired`, `invalid_token`, `no_session`
- `X-Auth-Error` header for frontend handling
- Graceful redirect to login on auth failure

---

## Troubleshooting

### 401 Errors After ~60 Seconds

**Cause**: Clerk's 60-second token TTL expired.

**Solution**: Ensure proactive refresh is running:
```javascript
// Check browser console for:
"Session refreshed proactively"  // Every 45s
```

### 403 Forbidden from Clerk API

**Cause**: Missing User-Agent header in backend API calls.

**Solution**: Include User-Agent in Clerk API requests:
```python
headers = {
    "Authorization": f"Bearer {CLERK_SECRET_KEY}",
    "User-Agent": "MinouChat/1.0",
}
```

### User Shows Generated Username

**Cause**: Clerk API call failed during user sync.

**Fix**:
```bash
docker exec minouchat-app python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/memories.db')
conn.execute(\"UPDATE users SET username='RealName' WHERE clerk_id='user_xxx'\")
conn.commit()
"
```

---

## Migration from Old Auth

The previous system used:
- bcrypt password hashing
- Custom JWT tokens
- Session middleware

All functionality has been migrated to Clerk. The old `auth.py` functions remain for backward compatibility but delegate to `clerk_auth.py`.

---

*For Clerk setup instructions, see [CLERK_SETUP.md](CLERK_SETUP.md)*
*For general troubleshooting, see [CLAUDE.md](../CLAUDE.md)*
