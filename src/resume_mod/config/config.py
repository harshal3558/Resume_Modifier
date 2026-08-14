from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class ConfigError(Exception):
    """Raised when application configuration is invalid."""


@dataclass(frozen=True)
class Settings:

    project_root: Path

    data_dir: Path
    documents_dir: Path
    chroma_dir: Path
    logs_dir: Path

    chroma_collection: str

    llm_provider: str
    llm_model: str

    embedding_provider: str
    embedding_model: str

    chunk_size: int
    chunk_overlap: int
    retrieval_k: int

    max_question_length: int
    max_context_length: int

    def validate(self) -> None:

        if not self.chroma_collection.strip():
            raise ConfigError(
                "Chroma collection name cannot be empty."
            )

        if self.chunk_size <= 0:
            raise ConfigError(
                "Chunk size must be greater than zero."
            )

        if self.chunk_overlap < 0:
            raise ConfigError(
                "Chunk overlap cannot be negative."
            )

        if self.chunk_overlap >= self.chunk_size:
            raise ConfigError(
                "Chunk overlap must be smaller than chunk size."
            )

        if self.retrieval_k <= 0:
            raise ConfigError(
                "Retrieval k must be greater than zero."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:

    project_root = (
        Path(__file__)
        .resolve()
        .parents[3]
    )

    settings = Settings(

        project_root=project_root,

        data_dir=(
            project_root / "data"
        ),

        documents_dir=(
            project_root
            / "data"
            / "documents"
        ),

        chroma_dir=(
            project_root
            / "data"
            / "chroma_db"
        ),

        logs_dir=(
            project_root / "logs"
        ),

        chroma_collection=os.getenv(
            "CHROMA_COLLECTION",
            "college_knowledge",
        ),

        llm_provider=os.getenv(
            "LLM_PROVIDER",
            "openai",
        ),

        llm_model=os.getenv(
            "LLM_MODEL",
            "gpt-5.4",
        ),

        embedding_provider=os.getenv(
            "EMBEDDING_PROVIDER",
            "huggingface",
        ),

        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),

        chunk_size=int(
            os.getenv(
                "CHUNK_SIZE",
                "1000",
            )
        ),

        chunk_overlap=int(
            os.getenv(
                "CHUNK_OVERLAP",
                "150",
            )
        ),

        retrieval_k=int(
            os.getenv(
                "RETRIEVAL_K",
                "4",
            )
        ),

        max_question_length=int(
            os.getenv(
                "MAX_QUESTION_LENGTH",
                "3000",
            )
        ),

        max_context_length=int(
            os.getenv(
                "MAX_CONTEXT_LENGTH",
                "12000",
            )
        ),
    )

    settings.data_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.documents_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.chroma_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.logs_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.validate()

    return settings