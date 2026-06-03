"""Integration tests for the auth flow."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_me_flow(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "password123", "full_name": "Alice"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "a@b.com"
    assert body["tokens"]["access_token"]

    r = await client.post("/api/v1/auth/login",
                          json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["tokens"]["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


async def test_duplicate_email_conflicts(client):
    payload = {"email": "dup@b.com", "password": "password123", "full_name": "Dup"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


async def test_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json={
        "email": "c@b.com", "password": "password123", "full_name": "C"})
    r = await client.post("/api/v1/auth/login",
                          json={"email": "c@b.com", "password": "wrongpass"})
    assert r.status_code == 401


async def test_protected_route_requires_token(client):
    assert (await client.get("/api/v1/profile")).status_code == 401


async def test_refresh_rotates_token(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "r@b.com", "password": "password123", "full_name": "R"})
    refresh = r.json()["tokens"]["refresh_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    # old refresh token is now single-use / revoked
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r3.status_code == 401
