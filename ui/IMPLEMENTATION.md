# TAMS UI Implementation

## Overview

React-based admin interface for the TAMS API with role-based authentication.

## Project Structure

```
ui/
├── src/
│   ├── components/
│   │   └── Layout.tsx          # Main layout with sidebar
│   ├── pages/
│   │   ├── Login.tsx          # Login page
│   │   ├── Dashboard.tsx     # Dashboard
│   │   ├── Users.tsx          # User management
│   │   ├── Sources.tsx        # Sources listing
│   │   ├── Flows.tsx          # Flows listing
│   │   └── Segments.tsx       # Segments listing
│   ├── services/
│   │   └── api.ts             # API service layer
│   ├── types.ts               # TypeScript type definitions
│   ├── App.tsx                # Main app component
│   └── index.tsx              # Entry point
├── .env                        # Environment variables
└── README.md                   # Documentation
```

## Features

### 1. Authentication
- Login with username/password
- Role-based access control
- Protected routes
- JWT token management

### 2. User Management
- List users in table format
- Create new users
- Delete users
- Role assignment (admin, editor, viewer)
- Role badges with color coding

### 3. Sources Management
- List all sources
- Display source metadata
- Filter by format

### 4. Flows Management
- List all flows
- Display flow metadata
- Link to source

### 5. Segments Management
- List segments for a specific flow
- Filter by flow ID
- Display timerange information

## Technology Stack

- **React** - UI framework
- **TypeScript** - Type safety
- **Material-UI** - UI components
- **React Router** - Navigation
- **Axios** - HTTP client

## Getting Started

1. Install dependencies:
```bash
cd ui
npm install
```

2. Start the development server:
```bash
npm start
```

3. Access the UI at http://localhost:3000

## API Integration

The UI expects the TAMS API to be running at http://localhost:8000 (configurable via .env).

### Authentication Endpoint

The UI needs a login endpoint at `/auth/login` that accepts:
```json
{
  "username": "admin",
  "password": "vastdata"
}
```

And returns:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "admin",
  "role": "admin"
}
```

### User Management Endpoints (to be implemented)

- `GET /users` - List all users
- `POST /users` - Create a user
- `DELETE /users/{username}` - Delete a user
- `PUT /users/{username}/role` - Update user role

## Default Users

The TAMS API creates these users on startup:
- **admin** (role: admin, password: vastdata)
- **editor** (role: editor, password: vastdata)
- **viewer** (role: viewer, password: vastdata)

## Next Steps

1. Implement user management API endpoints
2. Add edit functionality for sources and flows
3. Add create/delete functionality
4. Add filtering and search
5. Add pagination for large datasets
6. Add role-based UI restrictions

