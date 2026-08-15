"""
main.py
=======
CLI entry point for the Auto Resume Modifier.

Usage
-----
  python main.py --job "Software Engineer at Google"
  python main.py --job "Data Engineer" --output my_resume --no-queue
  python main.py --list-models
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything else so API keys are available
load_dotenv()

# Ensure the package and llm_rollback are importable
_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC = _PROJECT_ROOT / "src"

for _path in (_SRC, _PROJECT_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Initialise logging (sets up file + console handlers)
from resume_mod.logger.logger import Logger  # noqa: E402
Logger()

import logging  # noqa: E402
LOGGER = logging.getLogger("resume_mod.main")


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-mod",
        description=(
            "Auto Resume Modifier — tailor your resume to any job description "
            "using ChromaDB retrieval + LLM (Groq / Gemini) generation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --job "ML Engineer at OpenAI"
  python main.py --job "Backend Engineer" --output backend_resume
  python main.py --list-models
        """,
    )

    parser.add_argument(
        "--job",
        metavar="JOB_DESCRIPTION",
        type=str,
        help="Target job description to tailor the resume against.",
    )

    parser.add_argument(
        "--output",
        metavar="FILENAME",
        type=str,
        default="tailored_resume",
        help="Output PDF base filename (default: tailored_resume).",
    )

    parser.add_argument(
        "--k",
        metavar="K",
        type=int,
        default=8,
        help="Number of resume chunks to retrieve from ChromaDB (default: 8).",
    )

    parser.add_argument(
        "--no-queue",
        action="store_true",
        default=False,
        help="Skip pushing the job to the Redis memory queue.",
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        default=False,
        help="Print the LLM fallback chain and exit.",
    )

    return parser


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def _list_models() -> None:
    """Print the full LLM fallback chain with key availability."""
    from llm_rollback import LLMRollback

    gateway = LLMRollback()
    providers = gateway.available_providers()

    print("\n🔗 LLM Fallback Chain (tried in order):\n")
    print(f"{'#':<4} {'Label':<40} {'Key set?':<10}")
    print("-" * 56)

    for p in providers:
        key_status = "✅ yes" if p["key_present"] else "❌ missing"
        print(f"{p['rank']:<4} {p['label']:<40} {key_status:<10}")

    print()


def _run(args: argparse.Namespace) -> None:
    """Execute the full pipeline."""
    from resume_mod.runner import run_pipeline

    run_pipeline(
        job_description=args.job,
        resume_filename=args.output,
        retrieval_k=args.k,
        use_queue=not args.no_queue,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # ── --list-models ───────────────────────────────────────────────────
    if args.list_models:
        _list_models()
        return

    # ── Require --job for normal run ────────────────────────────────────
    if not args.job:
        parser.print_help()
        print(
            "\n❌  Error: --job is required. "
            "Provide a job description to tailor your resume.\n"
        )
        sys.exit(1)

    LOGGER.info(
        "Starting Resume Modifier | output='%s' | k=%d | queue=%s",
        args.output,
        args.k,
        not args.no_queue,
    )

    _run(args)


if __name__ == "__main__":
    main()
