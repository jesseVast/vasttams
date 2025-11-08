# Users Endpoint Added to TAMS API

## Summary

Added a `/users` endpoint to the TAMS API for user management, including CORS configuration for the React UI.

## Changes Made

### 1. Backend Changes

#### Added `/users` Endpoint
**File: `src/vasttams/auth/router.py`**

- Created `users_router = APIRouter(prefix="/users", tags=["users"])`
- Added `GET /users` - List all users (admin only)
- Added `POST /users` - Create a new user (admin only)
- Added `DELETE /users/{username}` - Delete a user (admin only)

**Endpoints:**
- `GET /users` - Returns list of users with their roles
- `POST /users` - Creates a new user with username, password, and role
- `DELETE /users/{username}` - Deletes a user by username

**Models:**
- `UserCreateRequest` - For creating users
- `UserResponse` - For API responses

#### Integrated Users Router
**File: `src/vasttams/main.py`**

- Added `users_router` import
- Registered `users_router` with FastAPI app

#### Fixed API Response Format
**File: `ui/src/services/api.ts`**

- Updated `userService.list()` to return `response.data` (not `response.data.data`)
- Updated `sourceService.list()` to return `response.data`
- Updated `flowService.list()` to return `response.data`

This matches the actual API response format where endpoints return data directly, not wrapped in a `data` object.

### 2. CORS Configuration
**File: `src/vasttams/main.py`**

Added CORS middleware to allow the React UI to make requests:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Endpoints

### Login
```
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "vastdata"
}
```

**Response:**
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "admin",
  "role": "admin"
}
```

### List Users
```
GET /users
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "user_id": "uuid",
    "username": "admin",
    "role": "admin",
    "created_at": "2025-10-27T...",
    "updated_at": "2025-10-27T..."
  }
]
```

### Create User
```
POST /users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "newuser",
  "password": "password",
  "role": "viewer"
}
```

### Delete User
```
DELETE /users/{username}
Authorization: Bearer <token>
```

## Testing

1. **Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"vastdata"}'
```

2. **List Users (with token):**
```bash
TOKEN="your_jwt_token"
curl http://localhost:8000/users \
  -H "Authorization: Bearer $TOKEN"
```

3. **Create User:**
```bash
TOKEN="your_jwt_token"
curl -X POST http://localhost:8000/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"password","role":"viewer"}'
```

4. **Delete User:**
```bash
TOKEN="your_jwt_token"
curl -X DELETE http://localhost:8000/users/newuser \
  -H "Authorization: Bearer $TOKEN"
```

## UI Integration

The React UI now:
- Can login with admin/editor/viewer credentials
- Can fetch the users list using `GET /users`
- Can create new users using `POST /users`
- Can delete users using `DELETE /users/{username}`
- Sends Authorization header with JWT token on all authenticated requests

## Status

✅ Users endpoint added
✅ CORS configured
✅ RBAC enforced (admin only for user management)
✅ UI API service updated to match response format
✅ Ready for testing

