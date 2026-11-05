import datetime
import bcrypt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db import get_db
from app.models import User, TripMember

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

RANK = {"viewer": 0, "planner": 1, "leader": 2, "admin": 3}


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def make_token(user_id: int, role: str, minutes: int, token_type: str = "access") -> str:
    exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "exp": exp
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def make_access_token(user_id: int, role: str) -> str:
    return make_token(user_id, role, minutes=settings.ACCESS_TTL_MIN, token_type="access")


def make_refresh_token(user_id: int, role: str) -> str:
    return make_token(user_id, role, minutes=settings.REFRESH_TTL_DAYS * 24 * 60, token_type="refresh")


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type; expected {expected_type}"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(token, expected_type="access")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject missing")
    user = await db.get(User, int(user_id_str))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(min_role: str):
    def dep(user: User = Depends(current_user)) -> User:
        user_rank = RANK.get(user.role, 0)
        required_rank = RANK.get(min_role, 0)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role; requires at least {min_role}"
            )
        return user
    return dep


async def get_room_role(user: User, trip_id: int, db: AsyncSession) -> str:
    """Returns the effective role of a user in a trip: admin override, or per-room membership role."""
    if user.role == "admin":
        return "admin"
    stmt = select(TripMember).where(TripMember.trip_id == trip_id, TripMember.user_id == user.id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this trip room")
    return member.role


async def auth_from_token(token: str, db: AsyncSession) -> User:
    """Used for WebSocket handshake authentication."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=4401, detail="Subject missing")
        user = await db.get(User, int(user_id_str))
        if not user:
            raise HTTPException(status_code=4401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=4401, detail="Invalid token")
