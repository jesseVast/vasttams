# Authentication Middleware Fixed

## Summary

Fixed authentication middleware integration to properly authenticate API requests and enable JWT-based authentication for the React UI.

## Issues Fixed

### 1. Authentication Middleware Not Registered
**Problem:** The `AuthMiddleware` class was defined but not registered with FastAPI, so authentication wasn't running on requests.

**Fix:** Added authentication middleware to `src/vasttams/main.py`:
```python
# Add authentication middleware
from .auth.core import AuthManager
from .auth.providers.jwt import JWTProvider
from .auth.providers.basic import BasicAuthProvider

_auth_manager = AuthManager()
_auth_manager.add_provider(JWTProvider())
vast_db = get_vast_db()
if vast_db:
    _auth_manager.add_provider(BasicAuthProvider(vast_store=vast_db))

from .auth.middleware import AuthMiddleware
auth_middleware = AuthMiddleware(_auth_manager, require_auth=False)
app.middleware("http")(auth_middleware)
```

### 2. Incorrect Import Path
**Problem:** `src/vasttams/auth/middleware.py` was importing `from ..models import UserRole` which failed with `ModuleNotFoundError: No module named 'vasttams.models'`.

**Fix:** Changed import to `from .models import UserRole` in `src/vasttams/auth/middleware.py`.

### 3. API Response Format
**Problem:** UI was expecting `response.data.data` but API returns data directly.

**Fix:** Updated `ui/src/services/api.ts` to use `response.data` instead of `response.data.data`.

## How It Works

1. **Request Flow:**
   - Request comes in → CORS middleware → Auth middleware → Telemetry middleware → Router
   - Auth middleware extracts JWT from `Authorization: Bearer <token>` header
   - JWT is validated and user session is created
   - User role is extracted from JWT payload

2. **Authentication:**
   - `POST /auth/login` returns JWT with user info and role
   - Subsequent requests send `Authorization: Bearer <token>` header
   - Auth middleware validates JWT and creates user session
   - RBAC checks enforce role-based permissions

3. **Endpoints:**
   - Public endpoints (skip auth): `/docs`, `/redoc`, `/openapi.json`, `/health`, `/metrics`
   - Protected endpoints require JWT in Authorization header

## Testing

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"vastdata"}'
```

### List Users (with JWT)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"vastdata"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

curl http://localhost:8000/users \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
[
  {
    "user_id": "uuid",
    "username": "admin",
    "role": "admin",
    "created_at": "2025-10-28T...",
    "updated_at": "2025-10-28T..."
  },
  ...
]
```

## Status

✅ Authentication middleware registered
✅ JWT authentication working
✅ Users endpoint returns data
✅ CORS configured for React UI
✅ RBAC enforced on all endpoints
✅ Ready for UI integration

The React UI can now login, get a JWT token, and make authenticated requests to the TAMS API.

