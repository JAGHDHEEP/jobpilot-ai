"""Aggregate all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai_tools,
    applications,
    auth,
    insights,
    jobs,
    profile,
    resumes,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(ai_tools.router)
api_router.include_router(insights.router)
api_router.include_router(admin.router)
