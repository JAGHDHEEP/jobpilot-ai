"""OAuth2 code exchange + user upsert for Google / GitHub."""
from __future__ import annotations

import httpx
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.profile import Profile
from app.models.user import OAuthAccount, User

_PROVIDERS = {
    "google": {
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
    },
    "github": {
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
    },
}


def _creds(provider: str) -> tuple[str | None, str | None]:
    if provider == "google":
        return settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET
    if provider == "github":
        return settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET
    return None, None


async def exchange_and_upsert(db: AsyncSession, provider: str, code: str,
                              request: Request) -> User:
    if provider not in _PROVIDERS:
        raise AppError(f"Unsupported OAuth provider: {provider}", code="bad_provider")
    client_id, client_secret = _creds(provider)
    if not client_id or not client_secret:
        raise AppError(f"{provider} OAuth is not configured.", code="oauth_unconfigured")

    cfg = _PROVIDERS[provider]
    redirect = f"{settings.OAUTH_REDIRECT_BASE}{settings.API_V1_PREFIX}/auth/oauth/{provider}/callback"
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            cfg["token_url"],
            data={"client_id": client_id, "client_secret": client_secret, "code": code,
                  "redirect_uri": redirect, "grant_type": "authorization_code"},
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        access = token_resp.json().get("access_token")
        if not access:
            raise AppError("OAuth token exchange failed.", code="oauth_failed")
        info = (await client.get(cfg["userinfo_url"],
                                 headers={"Authorization": f"Bearer {access}"})).json()

    provider_uid = str(info.get("id") or info.get("sub"))
    email = info.get("email") or f"{provider}_{provider_uid}@users.noreply"
    full_name = info.get("name") or info.get("login") or email.split("@")[0]

    link = (await db.execute(
        select(OAuthAccount).where(OAuthAccount.provider == provider,
                                   OAuthAccount.provider_uid == provider_uid)
    )).scalar_one_or_none()
    if link:
        return (await db.execute(select(User).where(User.id == link.user_id))).scalar_one()

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        user = User(email=email, full_name=full_name, is_verified=True)
        db.add(user)
        await db.flush()
        db.add(Profile(user_id=user.id))
    from datetime import datetime, timezone
    db.add(OAuthAccount(user_id=user.id, provider=provider, provider_uid=provider_uid,
                        created_at=datetime.now(timezone.utc)))
    await db.flush()
    return user
