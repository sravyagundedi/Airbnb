import datetime
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenRefreshRequest,
    TokenResponse, UserResponse, UserUpdateRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.security import (
    hash_password, verify_password, make_access_token, make_refresh_token,
    decode_token, current_user
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# In-memory reset code store: email -> (code, expires_at)
RESET_CODES = {}



@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    clean_email = req.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists."
        )

    user = User(
        email=clean_email,
        password_hash=hash_password(req.password),
        display_name=req.display_name.strip(),
        role=req.role or "planner",
        budget_ceiling=req.budget_ceiling if req.budget_ceiling is not None else 150,
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
    clean_email = req.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials or register a new account."
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


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    if req.display_name is not None:
        user.display_name = req.display_name.strip()
    if req.budget_ceiling is not None:
        user.budget_ceiling = req.budget_ceiling
    if req.dietary_tags is not None:
        user.dietary_tags = req.dietary_tags

    if req.new_password:
        if not req.current_password or not verify_password(req.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed. Please enter your correct current password."
            )
        user.password_hash = hash_password(req.new_password)

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    clean_email = req.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account registered with this email address."
        )

    code = f"{secrets.randbelow(900000) + 100000}"  # 6-digit code
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    RESET_CODES[clean_email] = (code, expires)

    return {
        "message": "Password reset code generated successfully.",
        "email": clean_email,
        "reset_code": code,
        "expires_in_minutes": 15
    }


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    clean_email = req.email.strip().lower()
    entry = RESET_CODES.get(clean_email)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active password reset request found for this email. Please request a code first."
        )

    code, expires = entry
    if datetime.datetime.utcnow() > expires:
        RESET_CODES.pop(clean_email, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new code."
        )

    if req.reset_code.strip() != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code. Please check and try again."
        )

    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = hash_password(req.new_password)
    await db.commit()
    RESET_CODES.pop(clean_email, None)

    return {"message": "Password has been successfully reset. You may now sign in with your new password."}

