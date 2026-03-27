"""
PDF report generator using ReportLab.

Produces a styled PDF with:
- Cover page (title, location, risk score, date)
- Section headers and body text
- Risk flags and warnings as colored callout boxes
- Footer with page numbers
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable


# ── Color palette ─────────────────────────────────────────────────────────────
DARK_NAVY = colors.HexColor("#0f172a")
MID_NAVY = colors.HexColor("#1e293b")
SLATE = colors.HexColor("#475569")
LIGHT_GRAY = colors.HexColor("#f1f5f9")
BORDER_GRAY = colors.HexColor("#e2e8f0")
ACCENT = colors.HexColor("#6366f1")   # indigo
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GREEN = colors.HexColor("#16a34a")
RED_BG = colors.HexColor("#fef2f2")
AMBER_BG = colors.HexColor("#fffbeb")
GREEN_BG = colors.HexColor("#f0fdf4")
WHITE = colors.white


def risk_color(score: int):
    if score <= 3:
        return GREEN, GREEN_BG
    elif score <= 6:
        return AMBER, AMBER_BG
    else:
        return RED, RED_BG


def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontName="Helvetica",
        fontSize=13,
        textColor=colors.HexColor("#94a3b8"),
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=DARK_NAVY,
        spaceBefore=14,
        spaceAfter=6,
        borderPadding=(0, 0, 4, 0),
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        textColor=SLATE,
        leading=15,
        spaceAfter=4,
    )
    styles["flag"] = ParagraphStyle(
        "flag",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=RED,
    )
    styles["warning"] = ParagraphStyle(
        "warning",
        fontName="Helvetica",
        fontSize=9,
        textColor=AMBER,
    )
    styles["label"] = ParagraphStyle(
        "label",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=SLATE,
    )
    styles["small"] = ParagraphStyle(
        "small",
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#94a3b8"),
        alignment=TA_CENTER,
    )
    return styles


class NumberedCanvas:
    """Add page numbers to footer."""
    pass


def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header line
    canvas.setStrokeColor(BORDER_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, h - 1.5 * cm, w - 2 * cm, h - 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE)
    canvas.drawString(2 * cm, h - 1.2 * cm, "GEO DUE DILIGENCE AI")
    canvas.drawRightString(w - 2 * cm, h - 1.2 * cm, datetime.now().strftime("%d %B %Y"))
    # Footer line
    canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)
    canvas.drawCentredString(w / 2, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _clean_markdown(text: str) -> str:
    """Convert basic markdown to plain text for ReportLab."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"^#{1,3}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    return text


def generate_pdf(report_data: dict, path: str = "report.pdf") -> str:
    """
    Generate a styled PDF from the structured report dict.
    Returns the output path.
    """
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    styles = make_styles()
    doc = BaseDocTemplate(
        path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    # Page templates
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="main", frames=[frame], onPage=_header_footer),
    ])

    story = []

    # ── Cover section ─────────────────────────────────────────────────────────
    risk_score = report_data.get("risk_score", 5)
    location = report_data.get("location", {})
    flags = report_data.get("flags", [])
    warnings_list = report_data.get("warnings", [])

    r_color, r_bg = risk_color(risk_score)
    risk_label = "LOW RISK" if risk_score <= 3 else ("MEDIUM RISK" if risk_score <= 6 else "HIGH RISK")

    # Cover block (dark background table)
    cover_data = [
        [Paragraph("🧠 GEO DUE DILIGENCE AI", ParagraphStyle(
            "ct", fontName="Helvetica-Bold", fontSize=22, textColor=WHITE, alignment=TA_CENTER
        ))],
        [Paragraph(
            f"{location.get('city', 'Unknown')}, {location.get('country', '')}",
            ParagraphStyle("cs", fontName="Helvetica", fontSize=13,
                           textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER)
        )],
        [Paragraph(
            f"{location.get('latitude', '')}°N &nbsp; {location.get('longitude', '')}°E",
            ParagraphStyle("cc", fontName="Helvetica", fontSize=10,
                           textColor=colors.HexColor("#64748b"), alignment=TA_CENTER)
        )],
        [Paragraph(
            f"Risk Score: {risk_score}/10  —  {risk_label}",
            ParagraphStyle("cr", fontName="Helvetica-Bold", fontSize=14,
                           textColor=r_color, alignment=TA_CENTER)
        )],
        [Paragraph(
            datetime.now().strftime("Report generated: %d %B %Y"),
            ParagraphStyle("cd", fontName="Helvetica", fontSize=9,
                           textColor=colors.HexColor("#64748b"), alignment=TA_CENTER)
        )],
    ]
    cover_table = Table(cover_data, colWidths=[doc.width])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
        ("BOX", (0, 0), (-1, -1), 1, ACCENT),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING", (0, 0), (-1, 0), 24),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 24),
        ("TOPPADDING", (0, 1), (-1, -2), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -2), 6),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Flags & Warnings ──────────────────────────────────────────────────────
    if flags or warnings_list:
        story.append(Paragraph("Risk Flags & Warnings", styles["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
        story.append(Spacer(1, 4))

        if flags:
            flag_rows = [[Paragraph("⚠ " + f, styles["flag"])] for f in flags]
            flag_table = Table(flag_rows, colWidths=[doc.width])
            flag_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), RED_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [RED_BG, colors.HexColor("#fde8e8")]),
            ]))
            story.append(flag_table)
            story.append(Spacer(1, 6))

        if warnings_list:
            warn_rows = [[Paragraph("• " + w, styles["warning"])] for w in warnings_list]
            warn_table = Table(warn_rows, colWidths=[doc.width])
            warn_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), AMBER_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(warn_table)
            story.append(Spacer(1, 6))

    # ── Report sections ───────────────────────────────────────────────────────
    section_titles = {
        "location_overview": "Location Overview",
        "executive_summary": "Executive Summary",
        "environmental_analysis": "Environmental Analysis",
        "technical_analysis": "Technical Analysis",
        "risk_assessment": "Risk Assessment",
        "planning_context": "Planning Context",
        "recommendation": "Recommendation",
        "report": "Report",
    }

    sections = report_data.get("sections", {})
    for key, content in sections.items():
        if not content:
            continue
        title = section_titles.get(key, key.replace("_", " ").title())
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(title, styles["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
        story.append(Spacer(1, 4))

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue
            clean = _clean_markdown(line)
            story.append(Paragraph(clean, styles["body"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    return path