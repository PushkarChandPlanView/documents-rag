from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db
from schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await create_user(db, request.email, request.password, first_name=request.first_name, last_name=request.last_name)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(user.id, user.email, is_admin=user.is_admin)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = await get_user_by_id(db, payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        access_token = create_access_token(user.id, user.email, is_admin=user.is_admin)
        new_refresh = create_refresh_token(user.id)
        return TokenResponse(access_token=access_token, refresh_token=new_refresh)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
