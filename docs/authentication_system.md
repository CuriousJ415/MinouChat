# MiaChat Authentication System

## Overview

The MiaChat authentication system provides secure user registration, login, and session management. It's built using FastAPI and integrates with SQLAlchemy ORM for database operations.

## Features

### ✅ Completed Features

1. **User Registration**
   - Username and email validation
   - Password hashing with bcrypt
   - Duplicate username/email prevention
   - Automatic login after registration

2. **User Authentication**
   - Login with username or email
   - Secure password verification
   - Session-based authentication for web pages
   - JWT token authentication for API clients

3. **Session Management**
   - FastAPI session middleware integration
   - Database-backed user sessions
   - Configurable session expiration
   - Automatic session cleanup

4. **Route Protection**
   - FastAPI dependency injection for authentication
   - Automatic redirects for unauthenticated users
   - Template context injection for user data

5. **User Interface**
   - Modern login/register forms
   - Responsive navigation with user status
   - User dashboard with logout functionality
   - Bootstrap-based responsive design

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

## API Endpoints

### Web Authentication Routes
- `GET /auth/login` - Login page
- `POST /auth/login` - Login form submission (session-based)
- `GET /auth/register` - Registration page
- `POST /auth/register` - Registration form submission
- `POST /auth/logout` - Logout user

### API Authentication Routes (JWT-based)
- `POST /auth/api/login` - API login (returns JWT tokens)
- `POST /auth/api/refresh` - Refresh JWT access token
- `GET /auth/api/me` - Get current user info (JWT protected)
- `GET /auth/api/check` - Check authentication status

### Protected Routes
- `GET /` - Main dashboard (requires authentication)
- `GET /chat` - Chat interface (requires authentication)
- `GET /characters` - Character management (requires authentication)
- `GET /settings` - User settings (requires authentication)
- `GET /config` - Configuration page (requires authentication)
- `GET /personality` - Personality management (requires authentication)

## Core Functions

### User Management
```python
from src.miachat.api.core.auth import register_user, authenticate_user, get_current_user_from_session

# Register a new user
user = await register_user(user_data, db)

# Authenticate a user
user = await authenticate_user(username, password, db)

# Get current authenticated user from session
current_user = await get_current_user_from_session(request, db)
```

### Session Management
```python
from src.miachat.api.core.auth import login_user_session, logout_user_session

# Login user and create session
await login_user_session(user, request)

# Logout user
await logout_user_session(request)
```

### Route Protection
```python
from fastapi import Depends
from src.miachat.api.core.auth import require_session_auth

@app.get("/protected")
async def protected_route(request: Request, user = Depends(require_session_auth)):
    return {"message": f"Hello {user.username}"}
```

## Security Features

1. **Password Security**
   - Passwords are hashed using bcrypt
   - Secure password verification
   - Minimum password length validation

2. **Session Security**
   - FastAPI session middleware with secure cookies
   - Database-backed user sessions
   - Automatic cleanup of expired sessions
   - CSRF protection ready

3. **JWT Token Security**
   - Secure JWT tokens for API authentication
   - Configurable token expiration
   - Refresh token mechanism
   - Token validation and verification

4. **Input Validation**
   - Username/email uniqueness validation
   - Email format validation using Pydantic
   - Password strength requirements
   - SQL injection prevention through SQLAlchemy ORM

## Usage Examples

### Protecting Web Routes
```python
from fastapi import Depends, Request
from src.miachat.api.core.auth import get_current_user_from_session

@app.get("/dashboard")
async def dashboard(request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "dashboard", user=current_user)
```

### Template Access
```html
{% if user %}
    <p>Welcome, {{ user.username }}!</p>
    <a href="#" onclick="logout()">Logout</a>
{% else %}
    <a href="/auth/login">Login</a>
    <a href="/auth/register">Register</a>
{% endif %}
```

### API Authentication
```javascript
// Login and get JWT tokens
fetch('/auth/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'user',
        password: 'password'
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
    }
});

// Use JWT token for API calls
fetch('/auth/api/me', {
    headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
})
.then(response => response.json())
.then(data => console.log('User info:', data));
```

## Configuration

The authentication system uses the following FastAPI configuration:

```python
# Session middleware configuration
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here"  # Change in production
)

# JWT configuration
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

## Testing

The authentication system has been tested with:
- ✅ User registration
- ✅ User authentication (session-based)
- ✅ JWT token authentication
- ✅ Password validation
- ✅ Session management
- ✅ Route protection
- ✅ Database operations
- ✅ Template rendering with user context

## Getting Started

1. **Start the application**: `python run.py`
2. **Visit**: `http://localhost:8080`
3. **Register a new account** at `/auth/register`
4. **Login** at `/auth/login`
5. **Access protected pages** when authenticated

## Architecture

The authentication system follows FastAPI best practices:

- **Dependency Injection**: Uses FastAPI's dependency injection for database sessions and authentication
- **Session Middleware**: Leverages Starlette's session middleware for web authentication
- **JWT Tokens**: Provides JWT-based authentication for API clients
- **SQLAlchemy ORM**: Uses SQLAlchemy for database operations
- **Pydantic Models**: Uses Pydantic for data validation and serialization 