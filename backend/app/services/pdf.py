"""Render Markdown-ish resume/cover text to a PDF byte string via ReportLab."""
from __future__ import annotations

import io
import re


def markdown_to_pdf(markdown: str, title: str = "Document") -> bytes:
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, title=title,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=10,
                        spaceAfter=4, textColor="#1f2937")
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14,
                          alignment=TA_LEFT)

    story: list = []
    bullets: list = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            story.append(ListFlowable(
                [ListItem(Paragraph(b, body), leftIndent=10) for b in bullets],
                bulletType="bullet", start="•"))
            bullets = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            flush_bullets()
            story.append(Spacer(1, 4))
            continue
        line = _inline(line)
        if line.startswith("# "):
            flush_bullets()
            story.append(Paragraph(line[2:], h1))
        elif line.startswith("## "):
            flush_bullets()
            story.append(Paragraph(line[3:], h2))
        elif line.startswith(("- ", "* ")):
            bullets.append(line[2:])
        else:
            flush_bullets()
            story.append(Paragraph(line, body))
    flush_bullets()

    doc.build(story)
    return buf.getvalue()


def _inline(text: str) -> str:
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<i>\1</i>", text)
    return text
