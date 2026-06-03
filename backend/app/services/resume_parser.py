"""Resume parsing engine: extract text from PDF/DOCX and build a master profile."""
from __future__ import annotations

import io
import re

from app.ai.factory import get_llm, parse_json_response
from app.ai.matching import keyword_set
from app.ai.prompts import RESUME_PARSE_SYSTEM
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.document import ParsedProfile

log = get_logger()

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")

_SKILL_VOCAB = {
    "python", "java", "javascript", "typescript", "react", "nextjs", "node", "nodejs",
    "fastapi", "django", "flask", "spring", "express", "sql", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "docker", "kubernetes", "aws", "azure", "gcp",
    "terraform", "ansible", "git", "github", "gitlab", "jenkins", "ci/cd", "graphql", "rest",
    "grpc", "kafka", "rabbitmq", "spark", "hadoop", "airflow", "pytorch", "tensorflow",
    "scikit-learn", "pandas", "numpy", "go", "golang", "rust", "c++", "c#", ".net", "php",
    "ruby", "rails", "html", "css", "tailwind", "sass", "celery", "linux", "bash", "kotlin",
    "swift", "flutter", "android", "ios", "selenium", "pytest", "jest", "cypress",
    "machine learning", "deep learning", "nlp", "llm", "rag", "prompt engineering",
}


def extract_text(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_pdf(content)
    if name.endswith(".docx"):
        return _extract_docx(content)
    raise AppError("Unsupported file type. Upload a PDF or DOCX.", code="unsupported_file")


def _extract_pdf(content: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text as pdf_extract
        return pdf_extract(io.BytesIO(content)) or ""
    except Exception as exc:  # pragma: no cover
        log.warning("pdf_parse_failed", error=str(exc))
        return ""


def _extract_docx(content: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:  # pragma: no cover
        log.warning("docx_parse_failed", error=str(exc))
        return ""


def heuristic_skills(text: str) -> list[str]:
    low = text.lower()
    found = {s for s in _SKILL_VOCAB if s in low}
    # also catch single-token skills via the tokenizer
    tokens = keyword_set(text)
    found |= {s for s in _SKILL_VOCAB if " " not in s and s in tokens}
    return sorted(found)


async def parse_resume(filename: str, content: bytes) -> tuple[str, ParsedProfile]:
    """Return (raw_text, structured profile). LLM-structured with heuristic fallback."""
    text = extract_text(filename, content)
    if not text.strip():
        raise AppError("Could not extract text from the document.", code="empty_document")

    llm = get_llm()
    structured: dict = {}
    try:
        resp = await llm.complete(
            system=RESUME_PARSE_SYSTEM,
            user=text[:12000],
            json_mode=True,
            temperature=0.0,
            max_tokens=2000,
        )
        structured = parse_json_response(resp)
    except Exception as exc:  # pragma: no cover
        log.warning("llm_parse_failed_fallback_heuristic", error=str(exc))

    # Merge with heuristics — never lose obviously present data.
    skills = sorted(set(structured.get("skills") or []) | set(heuristic_skills(text)))
    emails = _EMAIL_RE.findall(text)
    phones = _PHONE_RE.findall(text)

    profile = ParsedProfile(
        full_name=structured.get("full_name"),
        email=structured.get("email") or (emails[0] if emails else None),
        phone=structured.get("phone") or (phones[0].strip() if phones else None),
        location=structured.get("location"),
        summary=structured.get("summary"),
        skills=skills,
        experiences=structured.get("experiences") or [],
        educations=structured.get("educations") or [],
        projects=structured.get("projects") or [],
        certifications=structured.get("certifications") or [],
        keywords=structured.get("keywords") or skills,
    )
    return text, profile
