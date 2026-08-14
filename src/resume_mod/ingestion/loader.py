from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from resume_mod.config import get_settings


LOGGER = logging.getLogger(
    "helpdesk_agent.loaders"
)


class DocumentLoader:

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".txt",
        ".md",
        ".docx",
    }

    def __init__(
        self,
        documents_dir: Path | None = None,
    ):

        settings = get_settings()

        self.documents_dir = (
            documents_dir
            or settings.documents_dir
        )

    def load(self) -> list[Document]:

        if not self.documents_dir.exists():

            LOGGER.warning(
                "Documents directory does not exist: %s",
                self.documents_dir,
            )

            return []

        documents: list[Document] = []

        files = sorted(
            path
            for path in self.documents_dir.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                in self.SUPPORTED_EXTENSIONS
            )
        )

        LOGGER.info(
            "Found %d document files.",
            len(files),
        )

        for path in files:

            try:

                loaded = self._load_file(
                    path
                )

                documents.extend(
                    loaded
                )

                LOGGER.info(
                    "Loaded document: %s",
                    path.name,
                )

            except Exception:

                LOGGER.exception(
                    "Failed to load document: %s",
                    path,
                )

        LOGGER.info(
            "Loaded %d document objects.",
            len(documents),
        )

        return documents

    def _load_file(
        self,
        path: Path,
    ) -> list[Document]:

        suffix = path.suffix.lower()

        if suffix == ".pdf":

            from langchain_community.document_loaders import (
                PyPDFLoader,
            )

            loader = PyPDFLoader(
                str(path)
            )

            return loader.load()

        if suffix == ".txt":

            from langchain_community.document_loaders import (
                TextLoader,
            )

            loader = TextLoader(
                str(path),
                encoding="utf-8",
            )

            return loader.load()

        if suffix == ".md":

            from langchain_community.document_loaders import (
                UnstructuredMarkdownLoader,
            )

            loader = UnstructuredMarkdownLoader(
                str(path)
            )

            return loader.load()

        if suffix == ".docx":

            from langchain_community.document_loaders import (
                Docx2txtLoader,
            )

            loader = Docx2txtLoader(
                str(path)
            )

            return loader.load()

        raise ValueError(
            f"Unsupported file type: {suffix}"
        )


class DocumentProcessor:

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):

        settings = get_settings()

        self.chunk_size = (
            chunk_size
            if chunk_size is not None
            else settings.chunk_size
        )

        self.chunk_overlap = (
            chunk_overlap
            if chunk_overlap is not None
            else settings.chunk_overlap
        )

        self.splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    "? ",
                    "! ",
                    " ",
                    "",
                ],
            )
        )

    def process(
        self,
        documents: list[Document],
    ) -> list[Document]:

        if not documents:

            LOGGER.warning(
                "No documents to process."
            )

            return []

        chunks = (
            self.splitter.split_documents(
                documents
            )
        )

        for index, chunk in enumerate(
            chunks
        ):

            chunk.metadata = {
                **chunk.metadata,
                "chunk_id": index,
                "source": chunk.metadata.get(
                    "source",
                    "unknown",
                ),
            }

        LOGGER.info(
            "Created %d document chunks.",
            len(chunks),
        )

        return chunks