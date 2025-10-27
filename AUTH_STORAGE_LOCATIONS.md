# Authentication Storage Locations

## Summary

Authentication information is **stored in VAST database tables** with schemas defined in the codebase, though currently the **auth providers use in-memory fallback credentials** by default.

## Database Storage (Defined but Not Currently Used)

### Tables Defined in Schemas

Schemas are defined in `app/service/schemas.py`:

1. **`users` table**
   - Fields: `id`, `username`, `email`, `password_hash`, `created`, `updated`
   - Stores user accounts for Basic Auth
   - Password stored as bcrypt hash

2. **`api_tokens` table**
   - Fields: `id`, `user_id`, `token_hash`, `expires_at`, `created`
   - Stores API tokens for URL Token Auth
   - Token stored as hash

3. **`refresh_tokens` table**
   - Fields: `id`, `user_id`, `token_hash`, `expires_at`, `created`
   - Stores refresh tokens for JWT Bearer Auth
   - Used for token refresh flow

4. **`auth_logs` table**
   - Fields: `id`, `user_id`, `event_type`, `ip_address`, `user_agent`, `created`
   - Logs authentication events
   - Audit trail for security

## Current Implementation Status

### Auth Providers

**File**: `app/auth/providers/`

All three providers (`basic.py`, `jwt.py`, `url_token.py`) accept a `vast_store` parameter but currently:

1. **Use fallback credentials by default** (in-memory)
2. **Database integration code exists** but is not active
3. **VAST store parameter is optional**

Example from `basic.py`:
```python
def __init__(self, vast_store=None, fallback_users: dict = None):
    self.vast_store = vast_store  # Optional database
    
    # Fallback in-memory users for development/testing
    self.fallback_users = fallback_users or {
        "admin": "$2b$12$P1HfguryTOezJ3aSyiwYfOLiJQCbmeEmOSdogJBrsCIYP3L8/Lfeq",
        "user": "$2b$12$v7SDbmZvU1hZ1Pk4IXjezu5T6Yg1w3sSAy/ICOS/Ug5Il1lGKNvpi",
        "test": "$2b$12$EXIdqzfdI8pJrUdJagN4qeeMNoeZda/niFkdtCMBh0ROP2qL5tVZS"
    }
```

## Where Data Actually Lives

### Currently Active: In-Memory (Fallback)

**Basic Auth**: Fallback users in `app/auth/providers/basic.py`
- `admin` / `admin123`
- `user` / `user123`
- `test` / `test123`

**URL Token Auth**: Fallback tokens in `app/auth/providers/url_token.py`
- `test-token` → test user
- `admin-token` → admin user
- `user-token` → regular user

**JWT Auth**: No storage needed (stateless tokens)

### Available but Not Used: VAST Database

The database tables exist in the schema (`app/service/schemas.py`) and would be initialized by `app/common/storage/table_initializer.py`, but:

1. **Tables are registered in schemas**
2. **Not currently queried by auth providers**
3. **Auth providers would need `vast_store` passed to use them**

## To Activate Database Storage

To use VAST database for auth storage:

1. **Pass vast_store to auth providers**:
   ```python
   from app.core.dependencies import get_vast_db
   vast_db = get_vast_db()
   
   basic_provider = BasicAuthProvider(vast_store=vast_db)
   url_token_provider = URLTokenProvider(vast_store=vast_db)
   ```

2. **Ensure tables are created**:
   - Tables are defined in `app/service/schemas.py`
   - Registered in `app/common/storage/schemas.py`
   - Should be created by table initializer

3. **Update provider code** to query database when `vast_store` is provided

## Schema Location Summary

| Auth Data | Schema Location | Table Name | Current Storage |
|-----------|----------------|------------|-----------------|
| User accounts | `app/service/schemas.py:50` | `users` | In-memory fallback |
| API tokens | `app/service/schemas.py:62` | `api_tokens` | In-memory fallback |
| Refresh tokens | `app/service/schemas.py:73` | `refresh_tokens` | In-memory fallback |
| Auth logs | `app/service/schemas.py:84` | `auth_logs` | Not used |

## Notes

- Database schemas are **defined** but not currently **used**
- Auth providers **support database** but **default to in-memory**
- Fallback credentials are for **development/testing only**
- Production should pass `vast_store` to providers to use database storage

