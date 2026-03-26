from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generate_pdf(report_text, path="report.pdf"):
    doc = SimpleDocTemplate(path)
    styles = getSampleStyleSheet()

    elements = []

    for line in report_text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 10))

    doc.build(elements)

    return path