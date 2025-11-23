# TAMS Admin UI

React-based admin interface for the TAMS API.

## Features

- User management with role-based access control
- List and manage sources
- List and manage flows
- List and manage segments
- Login with role-based authentication

## Development

```bash
npm start
```

The app will open at http://localhost:3000

## Environment Variables

Set `REACT_APP_API_URL` to point to your TAMS API instance (default: http://docker1:8000)

For local development, you can create a `.env` file in the `ui/` directory:
```
REACT_APP_API_URL=http://docker1:8000
```

## Default Users

- admin (role: admin, password: vastdata)
- editor (role: editor, password: vastdata)
- viewer (role: viewer, password: vastdata)
