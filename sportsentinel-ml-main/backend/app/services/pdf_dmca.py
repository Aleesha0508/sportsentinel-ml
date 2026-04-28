import os
from datetime import datetime
from textwrap import wrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PDF_DIR = "generated_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


def draw_wrapped_text(c, text, x, y, width=90, line_height=14):
    for paragraph in str(text).split("\n"):
        if not paragraph.strip():
            y -= line_height
            continue

        for line in wrap(paragraph, width=width):
            c.drawString(x, y, line)
            y -= line_height

            if y < 60:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = A4[1] - 50

    return y


def create_dmca_pdf(violation_id: str, violation: dict, notice_text: str) -> str:
    filename = f"dmca_notice_{violation_id}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "DMCA TAKEDOWN NOTICE")
    y -= 35

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "To:")
    y -= 16

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"{violation.get('platform', 'Platform')} Copyright / Legal Team")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Subject: DMCA Takedown Request")
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "1. Identification of Copyrighted Work")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        f"Original Asset Title: {violation.get('matched_title', 'N/A')}\n"
        f"Matched Asset ID: {violation.get('matched_asset_id', 'N/A')}",
        50,
        y,
    )
    y -= 15

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "2. Identification of Infringing Material")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        f"Platform: {violation.get('platform', 'N/A')}\n"
        f"Source URL: {violation.get('source_url', 'N/A')}\n"
        f"Evidence Path: {violation.get('query_storage_path', 'N/A')}\n"
        f"Query Filename: {violation.get('query_filename', 'N/A')}",
        50,
        y,
    )
    y -= 15

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "3. Evidence and Detection Details")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        f"Violation Type: {violation.get('violation_type', 'N/A')}\n"
        f"Confidence Score: {violation.get('confidence', 'N/A')}\n"
        f"Similarity Score: {violation.get('similarity_score', 'N/A')}\n"
        f"Explanation: {violation.get('explanation', 'N/A')}",
        50,
        y,
    )
    y -= 15

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "4. Good Faith Statement")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        "I have a good faith belief that the disputed use of the copyrighted material "
        "described above is not authorized by the copyright owner, its agent, or the law.",
        50,
        y,
    )
    y -= 15

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "5. Accuracy and Authority Statement")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        "I state, under penalty of perjury, that the information in this notice is accurate "
        "and that I am authorized to act on behalf of the owner of the exclusive rights "
        "that are allegedly infringed.",
        50,
        y,
    )
    y -= 15

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "6. Requested Action")
    y -= 18

    c.setFont("Helvetica", 10)
    y = draw_wrapped_text(
        c,
        "Please remove or disable access to the infringing material identified above as soon as possible.",
        50,
        y,
    )
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Digital Signature:")
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(50, y, "SportsSentinel Authorized Representative")
    y -= 15
    c.drawString(50, y, "SportsSentinel Media Protection System")

    c.save()
    return filepath