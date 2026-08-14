"""
runner.py
=========
Full Resume Modification Pipeline

Flow (matches README):
  1. User provides resume path + job description
  2. SearchEngine retrieves relevant chunks from ChromaDB
  3. RRF Reranker re-ranks the chunks
  4. System + user prompt is built
  5. LLMRollback tries up to 10 models (Groq → Gemini) for the response
  6. generate_pdf writes the tailored resume to disk
  7. JobProducer pushes the completed job to Redis (optional)
  8. Acknowledgement printed to stdout
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger("resume_mod.runner")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(
    job_description: str,
    context_chunks: list[str],
) -> str:
    """
    Construct the full LLM prompt from the job description and
    retrieved resume context chunks.
    """

    context_block = "\n\n".join(
        f"[Chunk {i + 1}]\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    )

    system_instruction = (
        "You are an expert resume writer and career coach. "
        "Your task is to rewrite and tailor the resume content below "
        "so that it strongly matches the given job description. "
        "Keep the content truthful and professional. "
        "Use action verbs and quantifiable achievements where possible. "
        "Output ONLY the final resume text — no commentary, no headings "
        "like 'Here is the revised resume'."
    )

    prompt = (
        f"{system_instruction}\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description.strip()}\n\n"
        f"=== RESUME CONTENT (retrieved sections) ===\n{context_block}\n\n"
        f"=== TAILORED RESUME ==="
    )

    return prompt


def _rrf_rerank(
    results: list,
    k: int = 60,
) -> list:
    """
    Apply Reciprocal Rank Fusion to a single ranked list.
    Returns documents sorted by RRF score (best first).
    """
    from collections import defaultdict

    scores: dict[int, float] = defaultdict(float)

    for rank, _ in enumerate(results, start=1):
        scores[rank] += 1.0 / (k + rank)

    ranked_indices = sorted(
        scores.keys(),
        key=lambda idx: scores[idx],
        reverse=True,
    )

    return [results[idx - 1] for idx in ranked_indices]


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    job_description: str,
    resume_filename: str = "tailored_resume",
    retrieval_k: int = 8,
    use_queue: bool = True,
) -> str:
    """
    Run the complete resume modification pipeline.

    Parameters
    ----------
    job_description : str
        The target job description to tailor the resume against.
    resume_filename : str
        Base filename for the output PDF (extension added automatically).
    retrieval_k : int
        Number of chunks to retrieve from ChromaDB.
    use_queue : bool
        Whether to push the completed job to Redis.
        Set False if Redis is not available.

    Returns
    -------
    str
        Absolute path to the generated PDF.
    """

    # ── Step 1: Validate input ──────────────────────────────────────────
    if not job_description or not job_description.strip():
        raise ValueError("Job description must not be empty.")

    LOGGER.info("=" * 60)
    LOGGER.info("🚀 Resume Modification Pipeline Started")
    LOGGER.info("=" * 60)
    LOGGER.info("Job description (first 120 chars): %s …",
                job_description[:120])

    # ── Step 2: Retrieve relevant resume chunks ─────────────────────────
    LOGGER.info("[1/6] Searching vector store for relevant resume chunks …")

    from resume_mod.retrieval.search import SearchEngine

    search_engine = SearchEngine()
    raw_results = search_engine.search(
        query=job_description,
        k=retrieval_k,
    )

    if not raw_results:
        LOGGER.warning(
            "No resume chunks retrieved — "
            "make sure your resume has been ingested into ChromaDB."
        )
        context_chunks: list[str] = []
    else:
        LOGGER.info("Retrieved %d chunks.", len(raw_results))
        context_chunks = [doc.page_content for doc in raw_results]

    # ── Step 3: Rerank with RRF ─────────────────────────────────────────
    LOGGER.info("[2/6] Reranking with Reciprocal Rank Fusion …")

    reranked_chunks = _rrf_rerank(context_chunks) if context_chunks else []

    LOGGER.info("Reranked %d chunks.", len(reranked_chunks))

    # ── Step 4: Build prompt ────────────────────────────────────────────
    LOGGER.info("[3/6] Building LLM prompt …")

    prompt = _build_prompt(
        job_description=job_description,
        context_chunks=reranked_chunks,
    )

    LOGGER.info("Prompt length: %d characters.", len(prompt))

    # ── Step 5: LLM Rollback — try up to 10 models ─────────────────────
    LOGGER.info("[4/6] Invoking LLM (with automatic rollback) …")

    # runner.py is at src/resume_mod/runner.py
    # parents[0]=src/resume_mod, parents[1]=src, parents[2]=project_root
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Ensure documents dir exists so ingestion doesn't crash on first run
    (project_root / "data" / "documents").mkdir(parents=True, exist_ok=True)

    from llm_rollback import get_llm_response

    llm_output: str = get_llm_response(prompt)

    LOGGER.info(
        "LLM response received (%d characters).",
        len(llm_output),
    )

    # ── Step 6: Generate PDF ────────────────────────────────────────────
    LOGGER.info("[5/6] Generating PDF …")

    from resume_mod.pdf_generator.pdf_generator import generate_pdf

    output_path: str = generate_pdf(
        filename=resume_filename,
        text=llm_output,
    )

    LOGGER.info("✅ PDF generated at: %s", output_path)

    # ── Step 7: Push completed job to Redis queue (optional) ────────────
    if use_queue:
        LOGGER.info("[6/6] Pushing job to Redis memory queue …")
        try:
            from resume_mod.memory.producer import JobProducer

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
                "Redis queue unavailable — skipping. (%s)",
                exc,
            )
    else:
        LOGGER.info("[6/6] Redis queue skipped (use_queue=False).")

    # ── Step 8: Acknowledgement ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅  Resume modification complete!")
    print(f"📄  Output PDF : {output_path}")
    print("=" * 60 + "\n")

    return output_path
