from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
from datetime import datetime


def generate_response_pdf(
    form_title,
    form_description,
    response_data,
    submitted_at=None
):
    """
    Generate a professional PDF containing one form response.

    Returns:
        BytesIO object containing the generated PDF.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "FormTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=8
    )

    description_style = ParagraphStyle(
        "Description",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        spaceAfter=18
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=8,
        spaceAfter=10
    )

    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        leading=12
    )

    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    story = []

    # ---------------------------------------------------------
    # TITLE
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            escape_text(form_title),
            title_style
        )
    )

    if form_description:
        story.append(
            Paragraph(
                escape_text(form_description),
                description_style
            )
        )

    # ---------------------------------------------------------
    # RESPONSE INFORMATION
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "Response Details",
            section_style
        )
    )

    info_data = [
        [
            Paragraph("<b>Submitted At</b>", label_style),
            Paragraph(
                escape_text(
                    submitted_at
                    if submitted_at
                    else datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
                value_style
            )
        ]
    ]

    info_table = Table(
        info_data,
        colWidths=[45 * mm, 125 * mm]
    )

    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.lightgrey),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(info_table)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # FORM RESPONSE
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "Submitted Information",
            section_style
        )
    )

    table_data = [
        [
            Paragraph("<b>Field</b>", label_style),
            Paragraph("<b>Response</b>", label_style)
        ]
    ]

    for field_name, value in response_data.items():

        if value is None:
            value = ""

        if isinstance(value, bool):
            value = "Yes" if value else "No"

        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)

        field_label = str(field_name).replace("_", " ").title()
        value_text = str(value)

        table_data.append(
            [
                Paragraph(
                    escape_text(field_label),
                    label_style
                ),
                Paragraph(
                    escape_text(value_text),
                    value_style
                )
            ]
        )

    response_table = Table(
        table_data,
        colWidths=[55 * mm, 115 * mm],
        repeatRows=1
    )

    response_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),

            ("BOX", (0, 0), (-1, -1), 0.6, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.grey),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )

    story.append(response_table)

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "Generated by FormFlow-AI",
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
        )
    )

    # ---------------------------------------------------------
    # BUILD PDF
    # ---------------------------------------------------------

    document.build(story)

    buffer.seek(0)

    return buffer


def escape_text(text):
    """
    Safely escape special characters for ReportLab Paragraphs.
    """

    text = str(text)

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return text