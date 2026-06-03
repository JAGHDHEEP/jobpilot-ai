"""Authentication use-cases: register, login, refresh, logout."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    refresh_expiry,
    verify_password,
)
from app.models.profile import Profile
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenPair


async def register(db: AsyncSession, email: str, password: str, full_name: str) -> User:
    exists = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if exists:
        raise ConflictError("An account with this email already exists.")
    user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id))   # auto-create empty profile
    await db.flush()
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.")
    if not user.is_active:
        raise AuthError("Account is disabled.")
    return user


async def issue_tokens(db: AsyncSession, user: User) -> TokenPair:
    access = create_access_token(str(user.id), user.role.value)
    raw_refresh, refresh_hash = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=refresh_hash, expires_at=refresh_expiry(),
        created_at=datetime.now(timezone.utc),
    ))
    await db.flush()
    return TokenPair(access_token=access, refresh_token=raw_refresh)


async def rotate_refresh(db: AsyncSession, raw_refresh: str) -> TokenPair:
    token_hash = hash_token(raw_refresh)
    row = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )).scalar_one_or_none()
    if not row or not row.is_valid:
        raise AuthError("Invalid or expired refresh token.")
    row.revoked_at = datetime.now(timezone.utc)          # rotate (single-use)
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one()
    await db.flush()
    return await issue_tokens(db, user)


async def revoke_all(db: AsyncSession, user_id: str) -> None:
    rows = (await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id,
                                   RefreshToken.revoked_at.is_(None))
    )).scalars().all()
    now = datetime.now(timezone.utc)
    for r in rows:
        r.revoked_at = now
    await db.flush()
