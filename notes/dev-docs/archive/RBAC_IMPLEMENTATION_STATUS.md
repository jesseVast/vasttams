# RBAC Implementation Status

## Completed ✓

1. **Models & Schemas**
   - `UserRole` enum added (ADMIN, EDITOR, VIEWER)
   - Role fields added to `User`, `UserSession`, `AuthResult`
   - Database schema updated with role field

2. **RBAC Module**
   - Created `src/vasttams/auth/rbac.py`
   - Dependency functions: `require_admin()`, `require_editor()`, `require_viewer()`
   - Permission checking logic implemented

3. **Auth Providers**
   - JWT provider embeds/extracts role claims
   - Basic auth provider fetches role from database
   - Middleware includes role in `UserSession`

4. **UserService**
   - Created `src/vasttams/auth/user_service.py`
   - CRUD operations with password hashing (bcrypt)

5. **Management Script**
   - Created `mgmt/user_mgmt.py`
   - CLI for user management
   - Can initialize default users

6. **Datetime Updates**
   - Replaced all `datetime.utcnow()` calls
   - Added timezone imports

7. **Router Imports**
   - Added RBAC imports to all 8 router files:
     - sources/router.py ✓
     - flows/router.py ✓
     - segments/router.py ✓
     - objects/router.py ✓
     - storagebackends/router.py ✓
     - webhooks/router.py ✓
     - auth/router.py ✓
     - service/router.py ✓
     - hls/router.py ✓

8. **Sources Router**
   - RBAC added to all major endpoints:
     - GET: require_viewer
     - POST/PUT: require_editor
     - DELETE: require_admin

9. **Flows Router**
   - RBAC added to main CRUD endpoints:
     - GET: require_viewer
     - POST/PUT: require_editor
     - DELETE: require_admin

## In Progress

### Remaining Work

**Add RBAC to remaining endpoints:**

1. **Flows Router** - sub-resource endpoints (tags, description, label, flow_collection, bit_rates, read_only)
2. **Segments Router** - all endpoints
3. **Objects Router** - all endpoints
4. **Storage Backends Router** - all endpoints
5. **Webhooks Router** - all endpoints
6. **Auth Router** - all endpoints
7. **Service Router** - all endpoints
8. **HLS Router** - all endpoints

**Pattern to apply:**

```python
# GET endpoints
user_session: UserSession = Depends(require_viewer)

# POST/PUT endpoints
user_session: UserSession = Depends(require_editor)

# DELETE endpoints
user_session: UserSession = Depends(require_admin)
```

## Next Steps

1. Add RBAC to all remaining endpoints in each router
2. Create RBAC tests
3. Initialize default users using `mgmt/user_mgmt.py init-default-users`
4. Test RBAC enforcement

## Role Permissions

- **ADMIN**: Full access to all operations (read, write, delete)
- **EDITOR**: Read + write sources/flows/segments/objects (no delete)
- **VIEWER**: Read-only access to all resources

