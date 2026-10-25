"""Offline PDF guide generation."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#18332e")
FOREST = colors.HexColor("#1d6554")
MINT = colors.HexColor("#e7f0e9")
MUTED = colors.HexColor("#64756d")


def _safe(value: Any) -> str:
    return escape(str(value))


def _header_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(FOREST)
    canvas.rect(0, height - 0.22 * inch, width, 0.22 * inch, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#dfe6df"))
    canvas.line(doc.leftMargin, 0.55 * inch, width - doc.rightMargin, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.36 * inch, "PERSONALIZED TRAVEL ITINERARY PLANNER")
    canvas.drawRightString(width - doc.rightMargin, 0.36 * inch, f"{doc.page}")
    canvas.restoreState()


def build_itinerary_pdf(trip: dict[str, Any]) -> bytes:
    """Return a standalone PDF itinerary guide as bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.78 * inch,
        title=f"{trip.get('destination', 'Trip')} itinerary",
        author="Personalized Travel Itinerary Planner",
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle("TripTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=INK, alignment=TA_CENTER, spaceAfter=5)
    subtitle_style = ParagraphStyle("TripSubtitle", parent=base["Normal"], fontSize=10, leading=15, textColor=MUTED, alignment=TA_CENTER)
    day_style = ParagraphStyle("DayHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=INK, spaceBefore=10, spaceAfter=7)
    slot_style = ParagraphStyle("Slot", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=FOREST)
    body_style = ParagraphStyle("BodySmall", parent=base["Normal"], fontSize=9, leading=13, textColor=INK)
    detail_style = ParagraphStyle("Detail", parent=base["Normal"], fontSize=8, leading=11, textColor=MUTED)
    section_style = ParagraphStyle("SectionHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=8, spaceAfter=8)

    story = [Spacer(1, 0.16 * inch), Paragraph("YOUR TRIP, AT A GLANCE", subtitle_style), Spacer(1, 5), Paragraph(_safe(trip.get("destination", "Trip")), title_style)]
    story += [Paragraph(f"{_safe(trip.get('country', ''))} &nbsp;·&nbsp; {_safe(trip.get('start_date', ''))} to {_safe(trip.get('end_date', ''))} &nbsp;·&nbsp; {_safe(trip.get('days', ''))} days", subtitle_style), Spacer(1, 13)]
    summary_data = [["TRAVEL PARTY", "PACE", "BUDGET", "INTERESTS"], [
        _safe(trip.get("party", "")), _safe(trip.get("pace", "")), _safe(trip.get("budget", "")), _safe(", ".join(trip.get("interests", [])) or "Open discovery")
    ]]
    summary = Table(summary_data, colWidths=[1.55 * inch, 1.25 * inch, 1.15 * inch, 2.1 * inch])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MINT), ("TEXTCOLOR", (0, 0), (-1, 0), FOREST),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"), ("FONTSIZE", (0, 1), (-1, 1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe6df")),
    ]))
    story.extend([summary, Spacer(1, 14), HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dfe6df")), Spacer(1, 6)])

    currency = _safe(trip.get("currency", "USD"))
    for day in trip.get("itinerary", []):
        content = [Paragraph(_safe(day.get("title", f"Day {day.get('day', '')}")), day_style)]
        rows = [["TIME", "PLAN", "AREA", "EST. COST"]]
        for activity in day.get("activities", []):
            plan = f"<b>{_safe(activity.get('name', 'Activity'))}</b><br/><font color='#64756d'>{_safe(activity.get('description', ''))}</font>"
            cost = float(activity.get("cost_local", 0))
            rows.append([
                Paragraph(_safe(activity.get("slot", "")), slot_style),
                Paragraph(plan, body_style),
                Paragraph(_safe(activity.get("area", "")), detail_style),
                Paragraph(f"{currency} {cost:,.2f}<br/><font color='#64756d'>${float(activity.get('cost_usd', 0)):,.2f} USD</font>", body_style),
            ])
        table = Table(rows, colWidths=[1.16 * inch, 3.0 * inch, 1.05 * inch, 1.0 * inch], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dfe6df")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9f6")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        content.append(table)
        story.extend([KeepTogether(content), Spacer(1, 8)])

    story.extend([PageBreak(), Paragraph("Offline-ready checklist", section_style), Paragraph("Before you leave, keep these essentials available both on your phone and offline.", detail_style), Spacer(1, 10)])
    checklist = [
        "[ ] Save the local emergency number and your accommodation address.",
        "[ ] Share your itinerary and check-in plan with a trusted contact.",
        "[ ] Keep travel insurance details, passport copies, and key documents accessible offline.",
        "[ ] Confirm local transport options and any timed-entry reservations.",
        "[ ] Check current weather, opening hours, and official travel advisories before departure.",
    ]
    for item in checklist:
        story.extend([Paragraph(_safe(item), body_style), Spacer(1, 8)])
    story.extend([Spacer(1, 14), HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dfe6df")), Spacer(1, 8)])
    story.append(Paragraph("Budget note", section_style))
    story.append(Paragraph("Activity and meal costs are planning estimates, not live prices. Transport, lodging, taxes, and currency movement may change your final spend. Verify local details before travel.", body_style))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
