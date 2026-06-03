"""Auth + OAuth routes."""
from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.schemas.auth import (
    AuthResult,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import Message
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResult, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession) -> AuthResult:
    user = await auth_service.register(db, body.email, body.password, body.full_name)
    tokens = await auth_service.issue_tokens(db, user)
    await db.commit()
    return AuthResult(user=UserOut.model_validate(user, from_attributes=True), tokens=tokens)


@router.post("/login", response_model=AuthResult)
async def login(body: LoginRequest, db: DBSession) -> AuthResult:
    user = await auth_service.authenticate(db, body.email, body.password)
    tokens = await auth_service.issue_tokens(db, user)
    await db.commit()
    return AuthResult(user=UserOut.model_validate(user, from_attributes=True), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DBSession) -> TokenPair:
    tokens = await auth_service.rotate_refresh(db, body.refresh_token)
    await db.commit()
    return tokens


@router.post("/logout", response_model=Message)
async def logout(user: CurrentUser, db: DBSession) -> Message:
    await auth_service.revoke_all(db, str(user.id))
    await db.commit()
    return Message(message="Logged out from all sessions.")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)


# ---- OAuth2 (authorization-code flow). Wires Google/GitHub when configured. ----
@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str) -> dict:
    """Return the provider authorization URL for the SPA to redirect to."""
    redirect = f"{settings.OAUTH_REDIRECT_BASE}{settings.API_V1_PREFIX}/auth/oauth/{provider}/callback"
    urls = {
        "google": (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect}"
            "&response_type=code&scope=openid%20email%20profile"
        ),
        "github": (
            "https://github.com/login/oauth/authorize"
            f"?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={redirect}&scope=user:email"
        ),
    }
    return {"authorization_url": urls.get(provider, ""), "configured": bool(urls.get(provider))}


@router.get("/oauth/{provider}/callback", response_model=AuthResult)
async def oauth_callback(provider: str, code: str, request: Request, db: DBSession) -> AuthResult:
    """Exchange the code, upsert the user, and issue tokens.

    Token exchange uses Authlib/httpx against the provider; see services.oauth for the
    provider-specific exchange wiring (kept out of the router for testability).
    """
    from app.services.oauth import exchange_and_upsert
    user = await exchange_and_upsert(db, provider, code, request)
    tokens = await auth_service.issue_tokens(db, user)
    await db.commit()
    return AuthResult(user=UserOut.model_validate(user, from_attributes=True), tokens=tokens)
