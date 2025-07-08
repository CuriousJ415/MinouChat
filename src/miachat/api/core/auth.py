"""
FastAPI Authentication System
Handles user authentication, registration, and JWT token management
"""
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Union
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

# Security configuration
SECRET_KEY = "your-secret-key-here-change-in-production"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str  # Can be username or email
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> Optional[User]:
    """Get the current user if authenticated, None otherwise"""
    if credentials is None:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            return None
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

async def register_user(user_data: UserCreate, db: Session = Depends(get_db)) -> Optional[UserResponse]:
    """Register a new user"""
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        return None
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        created_at=db_user.created_at,
        last_login=db_user.last_login
    )

async def authenticate_user(username: str, password: str, db: Session = Depends(get_db)) -> Optional[User]:
    """Authenticate a user with username/email and password"""
    # Try to find user by username or email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

async def login_user(user: User) -> Token:
    """Create access and refresh tokens for a user"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token
    )

async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)) -> Optional[str]:
    """Refresh an access token using a refresh token"""
    payload = verify_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return None
    
    username = payload.get("sub")
    if username is None:
        return None
    
    # Verify user still exists
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    
    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return access_token

def require_auth():
    """Dependency to require authentication for routes"""
    return get_current_user

def optional_auth():
    """Dependency for optional authentication"""
    return get_current_user_optional

# Session-based authentication for web pages
async def get_current_user_from_session(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get the current user from session for web pages"""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user

async def require_session_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Require session authentication for web pages"""
    user = await get_current_user_from_session(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"Location": "/auth/login"}
        )
    return user

async def login_user_session(user: User, request: Request):
    """Login user and store in session"""
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return True

async def logout_user_session(request: Request):
    """Logout user and clear session"""
    request.session.clear()
    return True 