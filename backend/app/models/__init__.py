"""Import all models so Alembic / metadata sees them."""
from app.db.base import Base
from app.models.application import Application, ApplicationEvent
from app.models.document import Document
from app.models.enums import (
    ApplicationStatus,
    DocKind,
    EmploymentType,
    JobSource,
    RemoteType,
    SkillCategory,
    UserRole,
)
from app.models.job import Job, JobMatch, Recommendation
from app.models.profile import (
    Achievement,
    Certification,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from app.models.system import AIUsage, AuditLog, Feedback
from app.models.user import OAuthAccount, RefreshToken, User

__all__ = [
    "Base", "User", "OAuthAccount", "RefreshToken", "Profile", "Education", "Experience",
    "Project", "Skill", "Certification", "Achievement", "Document", "Job", "JobMatch",
    "Recommendation", "Application", "ApplicationEvent", "AIUsage", "AuditLog", "Feedback",
    "UserRole", "ApplicationStatus", "JobSource", "EmploymentType", "RemoteType", "DocKind",
    "SkillCategory",
]
