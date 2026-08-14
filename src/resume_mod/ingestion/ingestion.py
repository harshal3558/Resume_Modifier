"""
ingestion/ingestion.py
======================
Standalone ingest_documents() helper.
Loads documents from disk, chunks them, and stores in ChromaDB.

Note: VectorStore is imported lazily inside ingest_documents() to
avoid the circular dependency:
  store.py → ingestion → ingestion.py → store  (circular)
"""

from __future__ import annotations

import logging

from resume_mod.ingestion.loader import (
    DocumentLoader,
    DocumentProcessor,
)

LOGGER = logging.getLogger("resume_mod.ingestion")


def ingest_documents() -> None:
    """
    Full ingestion pipeline:
      1. Load all supported files from the documents_dir
      2. Split into chunks
      3. Embed and store in ChromaDB
    """
    # Lazy import to break circular dependency with store
    from resume_mod.store import VectorStore  # noqa: PLC0415

    loader = DocumentLoader()
    processor = DocumentProcessor()
    vector_store = VectorStore()

    documents = loader.load()

    if not documents:
        LOGGER.warning("No documents found for ingestion.")
        return

    chunks = processor.process(documents)

    if not chunks:
        LOGGER.warning("No chunks created.")
        return

    vector_store.add_documents(chunks)

    LOGGER.info("Document ingestion completed successfully.")


if __name__ == "__main__":
    ingest_documents()