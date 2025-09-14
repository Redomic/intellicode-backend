from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.schemas.auth import UserLogin, UserRegister, Token
from app.models.user import User, UserCreate
from app.crud.user import UserCRUD
from app.core.security import create_access_token, verify_token
from app.core.config import settings
from app.db.database import get_db

router = APIRouter(tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if not payload:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if not email:
        raise credentials_exception
    
    db = get_db()
    user_crud = UserCRUD(db)
    user = user_crud.get_user_by_email(email)
    
    if not user:
        raise credentials_exception
    
    return User(**user.dict())

@router.post("/register")
async def register(user_data: UserRegister):
    """Register a new user account."""
    db = get_db()
    user_crud = UserCRUD(db)
    
    # Check if user already exists
    if user_crud.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_create = UserCreate(**user_data.dict())
    new_user = user_crud.create_user(user_create)
    
    return {
        "message": "User registered successfully",
        "user_id": new_user.key
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user and return JWT access token."""
    db = get_db()
    user_crud = UserCRUD(db)
    
    # Authenticate user
    user = user_crud.authenticate_user(user_data.email, user_data.password)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/token", response_model=Token)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint for third-party integrations."""
    db = get_db()
    user_crud = UserCRUD(db)
    
    user = user_crud.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user
