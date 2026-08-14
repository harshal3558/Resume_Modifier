from __future__ import annotations

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger("resume_mod.runner")


def _build_prompt(
    job_description: str,
    context_chunks: list[str],
) -> str:

    context_block = "\n\n".join(
        f"[Chunk {i + 1}]\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    )

    system_instruction = r"""
You are an expert resume writer, career coach, and LaTeX document designer.

Your task is to create a professional, ATS-friendly resume tailored to
the given job description using ONLY the truthful information available
in the retrieved resume content.

IMPORTANT RULES:

1. Tailor the resume strongly to the job description.
2. Do not invent companies, projects, technologies, degrees, dates,
   achievements, metrics, or other facts.
3. Use strong action verbs.
4. Use quantifiable achievements only when supported by the resume.
5. Prioritize skills and experience relevant to the job description.
6. Keep the resume concise and professional.
7. Make the final document suitable for A4.
8. Use clean professional LaTeX formatting.
9. The output MUST be complete compilable LaTeX source code.
10. The output MUST start with \documentclass.
11. The output MUST end with \end{document}.
12. Use XeLaTeX-compatible packages.
13. Do not use Markdown.
14. Do not use ```latex code fences.
15. Do not include explanations or commentary.
16. Output ONLY the complete LaTeX source.

FONT RULES:

The PDF will be compiled on Linux using XeLaTeX.

DO NOT use:
- Helvetica
- Arial
- Calibri
- Aptos
- Times New Roman
- Any font that may not exist on Linux.

Use:

\usepackage{fontspec}

and:

\setmainfont{DejaVu Sans}

DejaVu Sans is installed on the target Linux system.

Do not change the font.

Use packages such as:

\usepackage{fontspec}
\usepackage{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}

The document must compile successfully using XeLaTeX.

Resume structure:

- Candidate name
- Contact information if available
- Professional summary
- Technical skills
- Work experience
- Projects
- Education
- Certifications if available

Only include sections for which information is available.
"""

    prompt = (
        f"{system_instruction}\n\n"
        f"=== JOB DESCRIPTION ===\n"
        f"{job_description.strip()}\n\n"
        f"=== RESUME CONTENT (RETRIEVED SECTIONS) ===\n"
        f"{context_block}\n\n"
        f"=== FINAL LATEX RESUME ==="
    )

    return prompt


def _clean_latex_output(
    latex_output: str,
) -> str:
    """
    Remove Markdown code fences if the LLM accidentally returns them.
    """

    latex_output = latex_output.strip()

    if latex_output.startswith("```latex"):
        latex_output = latex_output[len("```latex"):].strip()

    elif latex_output.startswith("```tex"):
        latex_output = latex_output[len("```tex"):].strip()

    elif latex_output.startswith("```"):
        latex_output = latex_output[len("```"):].strip()

    if latex_output.endswith("```"):
        latex_output = latex_output[:-3].strip()

    return latex_output


def _validate_latex(
    latex_output: str,
) -> None:
    """
    Perform basic validation before passing LaTeX to XeLaTeX.
    """

    if not latex_output.strip():
        raise ValueError(
            "LLM returned empty LaTeX."
        )

    if "\\documentclass" not in latex_output:
        raise ValueError(
            "LLM output does not contain \\documentclass."
        )

    if "\\begin{document}" not in latex_output:
        raise ValueError(
            "LLM output does not contain \\begin{document}."
        )

    if "\\end{document}" not in latex_output:
        raise ValueError(
            "LLM output does not contain \\end{document}."
        )


def _rrf_rerank(
    results: list,
    k: int = 60,
) -> list:

    from collections import defaultdict

    scores: dict[int, float] = defaultdict(float)

    for rank, _ in enumerate(results, start=1):
        scores[rank] += 1.0 / (k + rank)

    ranked_indices = sorted(
        scores.keys(),
        key=lambda idx: scores[idx],
        reverse=True,
    )

    return [
        results[idx - 1]
        for idx in ranked_indices
    ]


def _get_job_description(
    job_description: str | None,
) -> str:
    """
    Get the job description.

    If a JD is provided programmatically, use it directly.

    Otherwise, read multiline input from the terminal until the
    user enters END on its own line.
    """

    if job_description and job_description.strip():
        return job_description.strip()

    print("\n" + "=" * 60)
    print("Enter the Job Description")
    print("=" * 60)
    print("Paste the complete job description below.")
    print("Type END on a new line when you are finished.")
    print("=" * 60 + "\n")

    lines: list[str] = []

    while True:

        try:
            line = input()

        except EOFError:
            break

        # END means the user has finished entering the JD.
        if line.strip().upper() == "END":
            break

        lines.append(line)

    job_description = "\n".join(
        lines
    ).strip()

    if not job_description:
        raise ValueError(
            "Job description must not be empty."
        )

    return job_description


def _slugify(
    value: str,
) -> str:
    """
    Convert arbitrary text into a safe filename component.

    Example:

        "Data Scientist / Machine Learning"
        ->
        "data_scientist_machine_learning"
    """

    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")


def _extract_candidate_name(
    context_chunks: list[str],
) -> str:
    """
    Try to identify the candidate name from the retrieved resume content.

    The function primarily looks at the beginning of the retrieved content
    because names are commonly present near the top of a resume.

    If a suitable name cannot be detected, return 'resume'.
    """

    if not context_chunks:
        return "resume"

    combined_text = "\n".join(
        context_chunks[:3]
    )

    lines = [
        line.strip()
        for line in combined_text.splitlines()
        if line.strip()
    ]

    # Common labels such as:
    # Name: Omkar
    # Full Name: Omkar Patil
    name_patterns = [
        r"^(?:full\s+name|candidate\s+name|name)\s*[:\-]\s*(.+)$",
        r"^(?:resume\s+of)\s+(.+)$",
    ]

    for line in lines[:20]:

        for pattern in name_patterns:

            match = re.match(
                pattern,
                line,
                flags=re.IGNORECASE,
            )

            if match:

                candidate_name = match.group(1).strip()

                candidate_name = re.sub(
                    r"[^A-Za-z\s.'-]",
                    "",
                    candidate_name,
                ).strip()

                if candidate_name:
                    return _slugify(
                        candidate_name
                    )

    # If no explicit "Name:" field exists, try the first short line.
    for line in lines[:10]:

        clean_line = re.sub(
            r"[^A-Za-z\s.'-]",
            "",
            line,
        ).strip()

        words = clean_line.split()

        if (
            1 <= len(words) <= 4
            and len(clean_line) <= 60
            and not any(
                keyword in clean_line.lower()
                for keyword in [
                    "resume",
                    "curriculum",
                    "vitae",
                    "email",
                    "phone",
                    "linkedin",
                    "github",
                    "developer",
                    "engineer",
                    "experience",
                    "education",
                    "skills",
                ]
            )
        ):
            return _slugify(
                clean_line
            )

    return "resume"


def _extract_job_title(
    job_description: str,
) -> str:
    """
    Extract a likely job title from the job description.

    Examples:

        "Data Scientist"
        "Senior Python Developer"
        "Machine Learning Engineer"
    """

    lines = [
        line.strip()
        for line in job_description.splitlines()
        if line.strip()
    ]

    # First look for common job-title labels.
    patterns = [
        r"^(?:job\s*title|position|role|designation)\s*[:\-]\s*(.+)$",
        r"^(?:hiring\s+for)\s*[:\-]?\s*(.+)$",
        r"^(?:opening|vacancy)\s*[:\-]?\s*(.+)$",
    ]

    for line in lines[:30]:

        for pattern in patterns:

            match = re.match(
                pattern,
                line,
                flags=re.IGNORECASE,
            )

            if match:

                title = match.group(1).strip()

                if len(title) <= 100:
                    return _slugify(title)

    # Look for common role keywords.
    role_keywords = [
        "data scientist",
        "data analyst",
        "machine learning engineer",
        "ml engineer",
        "ai engineer",
        "artificial intelligence engineer",
        "python developer",
        "software engineer",
        "backend developer",
        "backend engineer",
        "full stack developer",
        "full-stack developer",
        "frontend developer",
        "frontend engineer",
        "devops engineer",
        "cloud engineer",
        "data engineer",
        "research scientist",
        "research engineer",
        "business analyst",
        "product manager",
        "project manager",
        "technical lead",
        "software developer",
    ]

    description_lower = job_description.lower()

    for keyword in role_keywords:

        if keyword in description_lower:
            return _slugify(keyword)

    # Last fallback: use a generic role name.
    return "tailored_resume"


def _generate_unique_filename(
    candidate_name: str,
    job_description: str,
) -> str:
    """
    Generate a unique filename using:

        candidate name
        +
        target job title
        +
        timestamp
        +
        short UUID

    Example:

        omkar_data_scientist_20260814_203512_a81f3c.pdf
    """

    candidate_slug = _slugify(
        candidate_name
    )

    job_title_slug = _extract_job_title(
        job_description
    )

    if not candidate_slug:
        candidate_slug = "resume"

    if not job_title_slug:
        job_title_slug = "tailored_resume"

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique_id = uuid4().hex[:6]

    return (
        f"{candidate_slug}_"
        f"{job_title_slug}_"
        f"{timestamp}_"
        f"{unique_id}.pdf"
    )


def run_pipeline(
    job_description: str | None = None,
    retrieval_k: int = 8,
    use_queue: bool = False,
) -> str:

    # =========================================================
    # 1. Get Job Description
    # =========================================================

    job_description = _get_job_description(
        job_description
    )

    LOGGER.info("=" * 60)
    LOGGER.info(
        "Resume Modification Pipeline Started"
    )
    LOGGER.info("=" * 60)

    LOGGER.info(
        "Job description (first 120 chars): %s ...",
        job_description[:120],
    )

    # =========================================================
    # 2. Search Vector Store
    # =========================================================

    LOGGER.info(
        "[1/6] Searching vector store for relevant resume chunks..."
    )

    from resume_mod.retrieval.search import SearchEngine

    search_engine = SearchEngine()

    raw_results = search_engine.search(
        query=job_description,
        k=retrieval_k,
    )

    if not raw_results:

        LOGGER.warning(
            "No resume chunks retrieved. "
            "Make sure your resume has been ingested into ChromaDB."
        )

        context_chunks: list[str] = []

    else:

        LOGGER.info(
            "Retrieved %d chunks.",
            len(raw_results),
        )

        context_chunks = [
            document.page_content
            for document in raw_results
        ]

    # =========================================================
    # 3. Generate Dynamic Filename
    # =========================================================

    candidate_name = _extract_candidate_name(
        context_chunks
    )

    resume_filename = _generate_unique_filename(
        candidate_name=candidate_name,
        job_description=job_description,
    )

    LOGGER.info(
        "Candidate name detected: %s",
        candidate_name,
    )

    LOGGER.info(
        "Generated unique filename: %s",
        resume_filename,
    )

    # =========================================================
    # 4. Rerank
    # =========================================================

    LOGGER.info(
        "[2/6] Reranking with Reciprocal Rank Fusion..."
    )

    reranked_chunks = (
        _rrf_rerank(
            context_chunks
        )
        if context_chunks
        else []
    )

    LOGGER.info(
        "Reranked %d chunks.",
        len(reranked_chunks),
    )

    # =========================================================
    # 5. Build LLM Prompt
    # =========================================================

    LOGGER.info(
        "[3/6] Building LLM prompt..."
    )

    prompt = _build_prompt(
        job_description=job_description,
        context_chunks=reranked_chunks,
    )

    LOGGER.info(
        "Prompt length: %d characters.",
        len(prompt),
    )

    # =========================================================
    # 6. Invoke LLM
    # =========================================================

    LOGGER.info(
        "[4/6] Invoking LLM to generate LaTeX resume..."
    )

    project_root = Path(
        __file__
    ).resolve().parents[2]

    if str(project_root) not in sys.path:
        sys.path.insert(
            0,
            str(project_root),
        )

    (
        project_root
        / "data"
        / "documents"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    from llm_rollback import get_llm_response

    llm_output: str = get_llm_response(
        prompt
    )

    LOGGER.info(
        "LLM response received (%d characters).",
        len(llm_output),
    )

    # =========================================================
    # Clean LaTeX
    # =========================================================

    latex_text = _clean_latex_output(
        llm_output
    )

    _validate_latex(
        latex_text
    )

    LOGGER.info(
        "LaTeX validation successful."
    )

    # =========================================================
    # 7. Generate PDF using XeLaTeX
    # =========================================================

    LOGGER.info(
        "[5/6] Generating PDF using XeLaTeX..."
    )

    from resume_mod.pdf_generator import (
        generate_pdf,
        generate_pdf_from_latex,
    )

    output_path: str = generate_pdf_from_latex(
        filename=resume_filename,
        latex_text=latex_text,
    )

    LOGGER.info(
        "PDF generated at: %s",
        output_path,
    )

    # =========================================================
    # 8. Redis Queue
    # =========================================================

    if use_queue:

        LOGGER.info(
            "[6/6] Pushing job to Redis memory queue..."
        )

        try:

            from resume_mod.memory.producer import (
                JobProducer,
            )

            producer = JobProducer()

            message_id = producer.push(
                filename=resume_filename,
                job_description=job_description,
                output_path=output_path,
            )

            LOGGER.info(
                "Job queued with message_id=%s",
                message_id,
            )

        except Exception as exc:

            LOGGER.warning(
                "Redis queue unavailable - skipping. (%s)",
                exc,
            )

    else:

        LOGGER.info(
            "[6/6] Redis queue skipped."
        )

    # =========================================================
    # Final Output
    # =========================================================

    print("\n" + "=" * 60)
    print("Resume modification complete!")
    print(f"Output PDF: {output_path}")
    print(f"Filename: {resume_filename}")
    print("=" * 60 + "\n")

    return output_path


if __name__ == "__main__":

    run_pipeline(
        use_queue=False
    )