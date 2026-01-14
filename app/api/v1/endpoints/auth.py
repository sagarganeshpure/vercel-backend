from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Any
import logging

from app.schemas.user import UserCreate, User, UserLogin, Token, TokenRefresh, UserProfileUpdate
from app.db.models.user import User as DBUser
from app.core import security
from app.core.config import settings
from app.api.deps import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(DBUser).filter(DBUser.email == email).first()
    if not user:
        logger.warning(f"Login attempt with non-existent email: {email}")
        return False
    if not user.is_active:
        logger.warning(f"Login attempt with inactive user: {email}")
        return False
    if not security.verify_password(password, user.hashed_password):
        logger.warning(f"Login attempt with incorrect password for email: {email}")
        return False
    return user

@router.post("/login", response_model=Token)
async def login(
    *,
    db: Session = Depends(get_db),
    login_data: UserLogin
) -> Any:
    """
    User login with email and password to get access token and refresh token
    """
    try:
        user = authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token (short-lived)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )
        
        # Create refresh token (long-lived)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = security.create_refresh_token(
            subject=user.email, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(*, db: Session = Depends(get_db), user_in: UserCreate) -> Any:
    """
    Register a new user.
    """
    try:
        logger.info(f"Registration attempt for email: {user_in.email}, username: {user_in.username}, role: {user_in.role}")
        # Check if email already exists
        db_user = db.query(DBUser).filter(DBUser.email == user_in.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists."
            )
        
        # Check if username already exists
        db_user = db.query(DBUser).filter(DBUser.username == user_in.username).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The username is already taken."
            )
        
        # Hash the password using security module
        hashed_password = security.get_password_hash(user_in.password)
        
        # Create new user
        db_user = DBUser(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_password,
            role=user_in.role,
            is_active=True
        )
        
        # Add to database
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except IntegrityError as e:
        # Handle database integrity errors (unique constraints, etc.)
        db.rollback()
        logger.error(f"Database integrity error during registration: {str(e)}")
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        if "email" in error_msg.lower() or "UNIQUE constraint failed: users.email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists."
            )
        elif "username" in error_msg.lower() or "UNIQUE constraint failed: users.username" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The username is already taken."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed due to a database constraint violation."
            )
    except SQLAlchemyError as e:
        # Handle other database errors
        db.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Database error during registration: {error_msg}")
        # Provide more specific error message
        if "no such table" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database tables not initialized. Please contact administrator."
            )
        elif "UNIQUE constraint" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email or username already exists."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {error_msg}"
            )
    except Exception as e:
        # Handle any other unexpected errors
        db.rollback()
        error_msg = str(e)
        logger.error(f"Unexpected error during registration: {error_msg}", exc_info=True)
        # Check if it's a validation error
        if "validation" in error_msg.lower() or "pattern" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {error_msg}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {error_msg}"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    *,
    db: Session = Depends(get_db),
    token_data: TokenRefresh
) -> Any:
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = security.verify_token(token_data.refresh_token, is_refresh=True)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token type is refresh
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user email from token
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists and is active
    user = db.query(DBUser).filter(DBUser.email == email).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    
    # Optionally create a new refresh token (rotate refresh token)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = security.create_refresh_token(
        subject=user.email, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=User)
def get_me(current_user: DBUser = Depends(get_current_user)) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.put("/profile", response_model=User)
def update_profile(
    *,
    db: Session = Depends(get_db),
    profile_update: UserProfileUpdate,
    current_user: DBUser = Depends(get_current_user)
) -> Any:
    """
    Update user profile information (username, email, profile image).
    """
    update_data = profile_update.model_dump(exclude_unset=True)
    
    # Check if email is being updated and if it's already taken
    if 'email' in update_data and update_data['email'] != current_user.email:
        existing_user = db.query(DBUser).filter(DBUser.email == update_data['email']).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists."
            )
    
    # Check if username is being updated and if it's already taken
    if 'username' in update_data and update_data['username'] != current_user.username:
        existing_user = db.query(DBUser).filter(DBUser.username == update_data['username']).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The username is already taken."
            )
    
    # Update user fields
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user
