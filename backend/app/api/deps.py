"""Shared FastAPI dependencies: DB session, auth, RBAC."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, PermissionError_
from app.core.security import JWTError, decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise AuthError("Missing authentication credentials.")
    try:
        payload = decode_token(creds.credentials)
    except JWTError as exc:
        raise AuthError("Invalid or expired token.") from exc
    if payload.get("type") != "access":
        raise AuthError("Invalid token type.")
    user_id = payload.get("sub")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("User not found or inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.admin:
        raise PermissionError_("Admin privileges required.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
