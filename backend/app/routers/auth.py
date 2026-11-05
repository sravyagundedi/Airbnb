from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenRefreshRequest,
    TokenResponse, UserResponse
)
from app.security import (
    hash_password, verify_password, make_access_token, make_refresh_token,
    decode_token, current_user
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists."
        )

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name,
        role=req.role or "planner",
        budget_ceiling=req.budget_ceiling or 150,
        dietary_tags=req.dietary_tags or [],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = make_access_token(user.id, user.role)
    refresh_token = make_refresh_token(user.id, user.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = make_access_token(user.id, user.role)
    refresh_token = make_refresh_token(user.id, user.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = make_access_token(user.id, user.role)
    new_refresh = make_refresh_token(user.id, user.role)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=30 * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(current_user)):
    return user
