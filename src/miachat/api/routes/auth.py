"""
FastAPI Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from typing import Optional
from sqlalchemy.orm import Session

from ..core.auth import (
    UserCreate, UserLogin, UserResponse, Token, PasswordChange,
    register_user, authenticate_user, login_user,
    get_current_user, get_current_user_optional,
    refresh_access_token, login_user_session, logout_user_session,
    get_current_user_from_session, get_password_hash
)
from ..core.templates import render_template
from ...database.config import get_db
from ...database.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])

# Security
security = HTTPBearer(auto_error=False)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Login page"""
    # Check if user is already logged in
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    
    return await render_template(request, "login")

@router.post("/login")
async def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login user and create session"""
    user = await authenticate_user(user_data.username, user_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create session
    await login_user_session(user, request)
    
    # Return success response
    return {
        "success": True,
        "message": "Login successful",
        "redirect": "/"
    }

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Registration page"""
    # Check if user is already logged in
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    
    return await render_template(request, "register")

@router.post("/register")
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user"""
    user = await register_user(user_data, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Auto-login after registration
    db_user = db.query(User).filter(User.id == user.id).first()
    await login_user_session(db_user, request)
    
    return {
        "success": True,
        "message": "Registration successful",
        "redirect": "/"
    }

@router.post("/logout")
async def logout(request: Request):
    """Logout user and clear session"""
    await logout_user_session(request)
    return {
        "success": True,
        "message": "Logout successful",
        "redirect": "/auth/login"
    }

@router.post("/change-password")
async def change_password(password_data: PasswordChange, request: Request, db: Session = Depends(get_db)):
    """Change password for logged-in user (session-based, no old password required)"""
    # Get current user from session
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Validate new password
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    # Hash and update password
    new_hash = get_password_hash(password_data.new_password)
    current_user.password_hash = new_hash
    db.commit()

    return {
        "success": True,
        "message": "Password updated successfully"
    }

# API endpoints for JWT tokens (for API clients)
@router.post("/api/login")
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT tokens (for API clients)"""
    user = await authenticate_user(user_data.username, user_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = await login_user(user)
    return {
        "success": True,
        "message": "Login successful",
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }

@router.post("/api/refresh")
async def api_refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token (for API clients)"""
    new_access_token = await refresh_access_token(refresh_token, db)
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.get("/api/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information (for API clients)"""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login
        }
    }

@router.get("/api/check")
async def check_auth(current_user: Optional[dict] = Depends(get_current_user_optional)):
    """Check if user is authenticated (for API clients)"""
    if current_user:
        return {
            "success": True,
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        }
    else:
        return {
            "success": True,
            "authenticated": False
        } 