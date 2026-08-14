from __future__ import annotations

import logging

from resume_mod.ingestion import (
    DocumentLoader,
    DocumentProcessor,
)
from resume_mod.store import (
    VectorStore,
)


LOGGER = logging.getLogger(
    "helpdesk_agent.ingestion"
)


def ingest_documents() -> None:

    loader = DocumentLoader()

    processor = DocumentProcessor()

    vector_store = VectorStore()

    documents = loader.load()

    if not documents:

        LOGGER.warning(
            "No documents found for ingestion."
        )

        return

    chunks = processor.process(
        documents
    )

    if not chunks:

        LOGGER.warning(
            "No chunks created."
        )

        return

    vector_store.add_documents(
        chunks
    )

    LOGGER.info(
        "Document ingestion completed."
    )


if __name__ == "__main__":

    ingest_documents()