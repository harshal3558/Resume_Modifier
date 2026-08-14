from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document

from resume_mod.config import get_settings
# from resume_mode.llm import EmbeddingGateway
from resume_mod.ingestion import (
    DocumentLoader,
    DocumentProcessor,
)


LOGGER = logging.getLogger(
    "helpdesk_agent.retrieval"
)


class VectorStore:

    def __init__(
        self,
        persist_directory: Path | None = None,
        collection_name: str | None = None,
    ):

        settings = get_settings()

        self.persist_directory = (
            persist_directory
            or settings.chroma_dir
        )

        self.collection_name = (
            collection_name
            or settings.chroma_collection
        )

        self.embedding_gateway = (
            EmbeddingGateway()
        )

        self._store = None

        LOGGER.info(
            "Initializing vector store."
        )

        # --------------------------------------------------
        # Step 1: Load embedding model
        # --------------------------------------------------

        LOGGER.info(
            "Loading embedding model."
        )

        self.embeddings = (
            self.embedding_gateway
            .get_embeddings()
        )

        LOGGER.info(
            "Embedding model loaded successfully."
        )

        # --------------------------------------------------
        # Step 2: Initialize Chroma
        # --------------------------------------------------

        self._initialize_store()

        # --------------------------------------------------
        # Step 3: Automatically ingest if empty
        # --------------------------------------------------

        self._ensure_knowledge_base()

    # ------------------------------------------------------
    # Chroma initialization
    # ------------------------------------------------------

    def _initialize_store(self):

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        chroma_db_file = (
            self.persist_directory
            / "chroma.sqlite3"
        )

        if chroma_db_file.exists():

            LOGGER.info(
                "Chroma database found at: %s",
                chroma_db_file,
            )

        else:

            LOGGER.info(
                "Chroma database does not exist."
            )

            LOGGER.info(
                "Creating new Chroma database."
            )

        self._create_store()

    # ------------------------------------------------------
    # Create Chroma collection
    # ------------------------------------------------------

    def _create_store(self):

        if self._store is not None:

            return self._store

        from langchain_chroma import Chroma

        self._store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(
                self.persist_directory
            ),
        )

        LOGGER.info(
            "Initialized Chroma collection=%s",
            self.collection_name,
        )

        return self._store

    # ------------------------------------------------------
    # Get Chroma store
    # ------------------------------------------------------

    def _get_store(self):

        if self._store is None:

            self._create_store()

        return self._store

    # ------------------------------------------------------
    # Automatic knowledge-base initialization
    # ------------------------------------------------------

    def _ensure_knowledge_base(self):

        document_count = self.count()

        # ----------------------------------------------
        # Knowledge base already exists
        # ----------------------------------------------

        if document_count > 0:

            LOGGER.info(
                "Chroma knowledge base already contains "
                "%d document chunks.",
                document_count,
            )

            LOGGER.info(
                "Skipping document ingestion."
            )

            return

        # ----------------------------------------------
        # Knowledge base is empty
        # ----------------------------------------------

        LOGGER.warning(
            "Chroma knowledge base is empty."
        )

        LOGGER.info(
            "Starting automatic document ingestion."
        )

        self._ingest_documents()

    # ------------------------------------------------------
    # Automatic ingestion
    # ------------------------------------------------------

    def _ingest_documents(self):

        loader = DocumentLoader()

        processor = DocumentProcessor()

        LOGGER.info(
            "Loading documents."
        )

        documents = loader.load()

        if not documents:

            LOGGER.warning(
                "No documents found for ingestion."
            )

            return

        LOGGER.info(
            "Loaded %d documents.",
            len(documents),
        )

        LOGGER.info(
            "Splitting documents into chunks."
        )

        chunks = processor.process(
            documents
        )

        if not chunks:

            LOGGER.warning(
                "No chunks created from documents."
            )

            return

        LOGGER.info(
            "Created %d document chunks.",
            len(chunks),
        )

        LOGGER.info(
            "Generating embeddings and storing "
            "documents in Chroma."
        )

        self.add_documents(
            chunks
        )

        LOGGER.info(
            "Automatic document ingestion completed."
        )

    # ------------------------------------------------------
    # Add documents
    # ------------------------------------------------------

    def add_documents(
        self,
        documents: list[Document],
    ) -> None:

        if not documents:

            LOGGER.warning(
                "No documents supplied to vector store."
            )

            return

        store = self._get_store()

        LOGGER.info(
            "Adding %d document chunks to Chroma.",
            len(documents),
        )

        store.add_documents(
            documents
        )

        LOGGER.info(
            "Added %d chunks to Chroma.",
            len(documents),
        )

        LOGGER.info(
            "Chroma now contains %d document chunks.",
            self.count(),
        )

    # ------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int | None = None,
    ) -> list[Document]:

        settings = get_settings()

        k = (
            k
            if k is not None
            else settings.retrieval_k
        )

        store = self._get_store()

        document_count = self.count()

        if document_count == 0:

            LOGGER.warning(
                "Cannot retrieve documents because "
                "the Chroma knowledge base is empty."
            )

            return []

        documents = (
            store.similarity_search(
                query,
                k=k,
            )
        )

        LOGGER.info(
            "Retrieved %d documents for query.",
            len(documents),
        )

        return documents

    # ------------------------------------------------------
    # Retriever
    # ------------------------------------------------------

    def as_retriever(
        self,
        k: int | None = None,
    ):

        settings = get_settings()

        k = (
            k
            if k is not None
            else settings.retrieval_k
        )

        store = self._get_store()

        return store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k,
            },
        )

    # ------------------------------------------------------
    # Count chunks
    # ------------------------------------------------------

    def count(self) -> int:

        store = self._get_store()

        return store._collection.count()