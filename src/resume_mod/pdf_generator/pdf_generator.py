from __future__ import annotations

from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = BASE_DIR / "data" / "updated_pdfs"





def generate_pdf(
    filename: str,
    text: str,
) -> str:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = Path(filename).name

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    output_path = OUTPUT_DIR / filename

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    body_style = styles["BodyText"]
    body_style.alignment = TA_LEFT
    body_style.fontSize = 11
    body_style.leading = 16

    story = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()

        if paragraph:
            paragraph = (
                paragraph
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            story.append(
                Paragraph(
                    paragraph,
                    body_style,
                )
            )

            story.append(
                Spacer(1, 6)
            )

    document.build(story)

    return str(output_path)



# filename = "omkar_.pdf"

# text = """
# Omkar 

# Python Developer

# Skills:
# Python
# LangChain
# ChromaDB
# Machine Learning

# Experience:
# Developed an AI-powered resume processing system
# using Python, LangChain, embeddings, and ChromaDB.

# Education:
# Bachelor of Engineering in Computer Science.
# """

# pdf_path = generate_pdf(
#     filename=filename,
#     text=text,
# )

# print(f"PDF generated successfully: {pdf_path}")