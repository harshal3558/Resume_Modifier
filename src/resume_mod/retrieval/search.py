from __future__ import annotations

import logging
from langchain_core.documents import Document
from resume_mod.store.store import VectorStore


LOGGER = logging.getLogger("resume_mod.retrieval.search")


class SearchEngine:

    def __init__(self) -> None:
        self.vector_store = VectorStore()

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        if not query or not query.strip():
            LOGGER.warning("Empty search query received.")
            return []

        query = query.strip()

        LOGGER.info(
            "Searching for query=%s with k=%d",
            query,
            k,
        )

        documents = self.vector_store.similarity_search(
            query=query,
            k=k,
        )

        LOGGER.info(
            "Retrieved %d similar chunks.",
            len(documents),
        )

        return documents

