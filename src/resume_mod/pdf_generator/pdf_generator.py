from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

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


def generate_pdf_from_latex(
    filename: str,
    latex_text: str,
) -> str:
    """
    Convert LaTeX text into a PDF using XeLaTeX.

    The generated PDF is stored in the same OUTPUT_DIR
    used by generate_pdf().
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = Path(filename).name

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    output_path = OUTPUT_DIR / filename

    xelatex = shutil.which("xelatex")

    if xelatex is None:
        raise RuntimeError(
            "xelatex was not found. "
            "Install XeLaTeX and make sure it is available in PATH."
        )

    # Create a temporary directory for .tex, .aux, .log, etc.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        tex_path = temp_dir / "document.tex"

        # Write LaTeX source
        tex_path.write_text(
            latex_text,
            encoding="utf-8",
        )

        command = [
            xelatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(temp_dir),
            str(tex_path),
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "XeLaTeX failed to generate the PDF.\n\n"
                f"stdout:\n{exc.stdout}\n\n"
                f"stderr:\n{exc.stderr}"
            ) from exc

        generated_pdf = temp_dir / "document.pdf"

        if not generated_pdf.exists():
            raise RuntimeError(
                "XeLaTeX completed but the PDF was not created."
            )

        # Move final PDF to your existing output directory.
        shutil.copy2(
            generated_pdf,
            output_path,
        )

    return str(output_path)



# filename = "omkar_latex.pdf"

# latex_text = r"""
# \documentclass[11pt,a4paper]{article}

# \usepackage{fontspec}
# \usepackage{geometry}
# \usepackage{enumitem}

# \geometry{
#     top=20mm,
#     bottom=20mm,
#     left=20mm,
#     right=20mm
# }

# \setmainfont{DejaVu Sans}

# \begin{document}

# \begin{center}
#     {\LARGE \textbf{Omkar}}

#     \vspace{4mm}

#     {\large Python Developer}
# \end{center}

# \section*{Skills}

# \begin{itemize}[noitemsep]
#     \item Python
#     \item LangChain
#     \item ChromaDB
#     \item Machine Learning
# \end{itemize}

# \section*{Experience}

# Developed an AI-powered resume processing system
# using Python, LangChain, embeddings, and ChromaDB.

# \section*{Education}

# Bachelor of Engineering in Computer Science.

# \end{document}
# """

# pdf_path = generate_pdf_from_latex(
#     filename=filename,
#     latex_text=latex_text,
# )

# print(f"LaTeX PDF generated successfully: {pdf_path}")