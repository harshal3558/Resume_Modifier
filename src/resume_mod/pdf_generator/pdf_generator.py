from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


BASE_DIR = Path(__file__).resolve().parents[3]

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "updated_pdfs"
)


def generate_pdf(
    filename: str,
    text: str,
) -> str:
    """
    Generate a PDF using ReportLab.

    The generated PDF is stored inside:

        data/updated_pdfs/
    """

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

    document.build(
        story
    )

    return str(output_path)


def generate_pdf_from_latex(
    filename: str,
    latex_text: str,
) -> str:
    """
    Generate a PDF from LaTeX using XeLaTeX.

    The resulting PDF is stored in:

        data/updated_pdfs/

    Temporary LaTeX files such as .aux, .log and .out
    are automatically removed.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = Path(filename).name

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    output_path = OUTPUT_DIR / filename

    # ---------------------------------------------------------
    # Find XeLaTeX
    # ---------------------------------------------------------

    xelatex = shutil.which(
        "xelatex"
    )

    if xelatex is None:

        raise RuntimeError(
            "xelatex was not found in PATH.\n\n"
            "Install it using:\n"
            "sudo apt update\n"
            "sudo apt install texlive-xetex "
            "texlive-latex-extra "
            "texlive-fonts-recommended"
        )

    # ---------------------------------------------------------
    # Temporary compilation directory
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir = Path(
            temp_dir
        )

        tex_path = (
            temp_dir
            / "document.tex"
        )

        pdf_path = (
            temp_dir
            / "document.pdf"
        )

        log_path = (
            temp_dir
            / "document.log"
        )

        # -----------------------------------------------------
        # Write LaTeX source
        # -----------------------------------------------------

        tex_path.write_text(
            latex_text,
            encoding="utf-8",
        )

        # -----------------------------------------------------
        # XeLaTeX command
        # -----------------------------------------------------

        command = [
            xelatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-output-directory",
            str(temp_dir),
            str(tex_path),
        ]

        # -----------------------------------------------------
        # Compile twice
        # -----------------------------------------------------

        for attempt in range(2):

            try:

                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )

            except subprocess.CalledProcessError as exc:

                log_content = ""

                if log_path.exists():

                    try:
                        log_content = (
                            log_path.read_text(
                                encoding="utf-8",
                                errors="replace",
                            )
                        )

                    except Exception:
                        log_content = ""

                raise RuntimeError(
                    "XeLaTeX failed to generate the PDF.\n\n"
                    f"Command:\n"
                    f"{' '.join(command)}\n\n"
                    f"stdout:\n"
                    f"{exc.stdout}\n\n"
                    f"stderr:\n"
                    f"{exc.stderr}\n\n"
                    f"LaTeX log:\n"
                    f"{log_content[-10000:]}"
                ) from exc

        # -----------------------------------------------------
        # Verify PDF
        # -----------------------------------------------------

        if not pdf_path.exists():

            raise RuntimeError(
                "XeLaTeX completed successfully, "
                "but the PDF file was not created."
            )

        # -----------------------------------------------------
        # Copy final PDF
        # -----------------------------------------------------

        shutil.copy2(
            pdf_path,
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