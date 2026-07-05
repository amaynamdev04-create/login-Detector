"""Simple Markdown to PDF converter using ReportLab.

This produces a readable, plain formatted PDF suitable for printing/presentation.
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import sys


def convert(md_path: str, pdf_path: str) -> None:
    with open(md_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin
    normal_size = 10

    c.setFont("Helvetica", normal_size)

    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            size = max(12, 20 - (level - 1) * 2)
            font = "Helvetica-Bold"
            wrapped = simpleSplit(text, font, size, width - 2 * margin)
            for part in wrapped:
                y -= size + 6
                if y < margin:
                    c.showPage()
                    y = height - margin
                    c.setFont(font, size)
                c.setFont(font, size)
                c.drawString(margin, y, part)
            c.setFont("Helvetica", normal_size)
            y -= 6
        elif line.strip() == "":
            y -= normal_size + 2
        else:
            wrapped = simpleSplit(line, "Helvetica", normal_size, width - 2 * margin)
            for part in wrapped:
                y -= normal_size + 2
                if y < margin:
                    c.showPage()
                    y = height - margin
                    c.setFont("Helvetica", normal_size)
                c.drawString(margin, y, part)

    c.save()


if __name__ == "__main__":
    md = "PROJECT_DOCS.md"
    pdf = "PROJECT_DOCS.pdf"
    if len(sys.argv) >= 2:
        md = sys.argv[1]
    if len(sys.argv) >= 3:
        pdf = sys.argv[2]
    convert(md, pdf)
    print(f"Wrote {pdf}")
