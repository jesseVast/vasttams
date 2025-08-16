# 🔐 TAMS API 7.0 Authentication Testing

This document explains how to test the new authentication system independently before integrating it with the main TAMS API.

## 📁 New Files Created

```
app/auth/
├── __init__.py              # Auth package
├── core.py                  # Core interfaces
├── models.py                # Auth models
├── providers/               # Auth providers
│   ├── __init__.py
│   ├── base.py             # Base provider interface
│   ├── jwt.py              # JWT/Bearer authentication
│   ├── basic.py            # Basic authentication
│   └── url_token.py        # URL token authentication
├── middleware.py            # Auth middleware
├── dependencies.py          # Auth dependencies
└── utils.py                 # Auth utilities

test_auth.py                 # Standalone test server
test_auth_simple.py          # Simple test script
AUTH_TEST_README.md          # This file
```

## 🚀 Quick Start

### 1. Test Basic Functionality

```bash
# Test the authentication system structure
python test_auth_simple.py
```

This will verify that all providers are initialized correctly.

### 2. Start Test Server

```bash
# Start the standalone test server
python test_auth.py
```

The server will start on `http://localhost:8000`

### 3. Test Authentication Methods

#### JWT/Bearer Authentication

```bash
# Get a JWT token
curl -X POST "http://localhost:8000/auth/login/jwt" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}'

# Use the token to access protected endpoint
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer <your-token-here>"
```

#### Basic Authentication

```bash
# Test basic auth directly
curl -X GET "http://localhost:8000/protected" \
  -u admin:admin123

# Or login to get a JWT token
curl -X POST "http://localhost:8000/auth/login/basic" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

#### URL Token Authentication

```bash
# Test URL token auth
curl -X GET "http://localhost:8000/protected?access_token=test-token"
```

## 🧪 Test Users and Tokens

### Basic Authentication Users
- `admin` / `admin123`
- `user` / `user123`
- `test` / `test123`

### URL Token Authentication
- `test-token` → user: `test`
- `admin-token` → user: `admin`
- `user-token` → user: `user`

## 📋 Available Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Root endpoint | No |
| GET | `/auth/test` | Test endpoint | No |
| GET | `/protected` | Protected endpoint | Yes |
| POST | `/auth/login/basic` | Basic auth login | No |
| POST | `/auth/login/jwt` | JWT login | No |
| GET | `/auth/test/jwt` | Test JWT auth | Yes |
| GET | `/auth/test/basic` | Test Basic auth | Yes |
| GET | `/auth/test/url-token` | Test URL token auth | Yes |
| GET | `/auth/status` | Auth system status | No |
| GET | `/auth/users` | List test users | No |

## 🔍 Testing Scenarios

### 1. No Authentication
```bash
curl http://localhost:8000/
# Should return: {"message": "TAMS Auth Test API", "status": "running"}
```

### 2. Invalid Authentication
```bash
curl http://localhost:8000/protected
# Should return: 401 Unauthorized
```

### 3. Valid JWT Authentication
```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login/jwt" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' | jq -r '.access_token')

# Use token
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Valid Basic Authentication
```bash
curl -X GET "http://localhost:8000/protected" \
  -u admin:admin123
```

### 5. Valid URL Token Authentication
```bash
curl -X GET "http://localhost:8000/protected?access_token=test-token"
```

## 🔧 Configuration

The authentication system is configured with sensible defaults for testing:

- **JWT Secret**: `test-secret-key-change-in-production`
- **JWT Algorithm**: `HS256`
- **JWT Expiry**: 30 minutes
- **Basic Auth**: Enabled with test users
- **URL Token**: Enabled with test tokens

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root
2. **Port Already in Use**: Change the port in `test_auth.py`
3. **JWT Errors**: Check that the token is properly formatted
4. **Basic Auth Errors**: Verify username/password combinations

### Debug Mode

Add debug logging to see what's happening:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ✅ Success Criteria

The authentication system is working correctly if:

1. ✅ All providers initialize without errors
2. ✅ JWT tokens can be created and validated
3. ✅ Basic authentication works with test users
4. ✅ URL token authentication works with test tokens
5. ✅ Protected endpoints require authentication
6. ✅ Public endpoints are accessible without authentication
7. ✅ Invalid credentials return 401 errors

## 🔄 Next Steps

Once testing is complete:

1. **Integrate with main TAMS API** - Add auth middleware to `app/main.py`
2. **Configure production settings** - Update JWT secrets and user management
3. **Add to existing endpoints** - Protect sensitive endpoints
4. **Update documentation** - Add auth examples to main README

## 📚 API Documentation

Once the test server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These will show all available endpoints and allow interactive testing. 