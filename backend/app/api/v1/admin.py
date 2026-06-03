"""Admin dashboard routes (RBAC: admin only)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import AdminUser, DBSession
from app.models.application import Application
from app.models.job import Job
from app.models.system import AIUsage, AuditLog
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


class SystemMetrics(BaseModel):
    users: int
    jobs: int
    applications: int
    ai_calls: int
    ai_cost_usd: float


@router.get("/metrics", response_model=SystemMetrics)
async def metrics(_: AdminUser, db: DBSession) -> SystemMetrics:
    async def count(model) -> int:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())

    cost = (await db.execute(select(func.coalesce(func.sum(AIUsage.cost_usd), 0)))).scalar_one()
    return SystemMetrics(
        users=await count(User), jobs=await count(Job),
        applications=await count(Application), ai_calls=await count(AIUsage),
        ai_cost_usd=float(cost),
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(_: AdminUser, db: DBSession, limit: int = 100) -> list[UserOut]:
    rows = (await db.execute(select(User).order_by(User.created_at.desc()).limit(limit))) \
        .scalars().all()
    return [UserOut.model_validate(u, from_attributes=True) for u in rows]


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate(user_id: str, _: AdminUser, db: DBSession) -> UserOut:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    user.is_active = False
    await db.commit()
    return UserOut.model_validate(user, from_attributes=True)


class AIUsageRow(BaseModel):
    provider: str
    model: str
    operation: str
    calls: int
    total_cost: float


@router.get("/ai-usage", response_model=list[AIUsageRow])
async def ai_usage(_: AdminUser, db: DBSession) -> list[AIUsageRow]:
    rows = (await db.execute(
        select(AIUsage.provider, AIUsage.model, AIUsage.operation,
               func.count().label("calls"), func.coalesce(func.sum(AIUsage.cost_usd), 0))
        .group_by(AIUsage.provider, AIUsage.model, AIUsage.operation)
    )).all()
    return [AIUsageRow(provider=p, model=m, operation=o, calls=c, total_cost=float(cost))
            for p, m, o, c, cost in rows]


class AuditRow(BaseModel):
    action: str
    target_type: str | None
    target_id: str | None
    created_at: str


@router.get("/audit", response_model=list[AuditRow])
async def audit(_: AdminUser, db: DBSession, limit: int = 100) -> list[AuditRow]:
    rows = (await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))).scalars().all()
    return [AuditRow(action=r.action, target_type=r.target_type, target_id=r.target_id,
                     created_at=r.created_at.isoformat()) for r in rows]
