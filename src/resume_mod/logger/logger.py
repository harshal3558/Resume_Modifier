from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


class LoggerConfig:

    def __init__(self):

        self.project_root = (
            Path(__file__)
            .resolve()
            .parents[3]
        )

        self.log_dir = (
            self.project_root / "logs"
        )

        self.log_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%H-%M-%S_%d-%m-%Y"
        )

        self.log_file = (
            self.log_dir / f"{timestamp}.log"
        )


class Logger:

    def __init__(
        self,
        config: LoggerConfig | None = None
    ):

        self.config = (
            config
            or LoggerConfig()
        )

        self._configure()

    def _configure(self):

        root_logger = logging.getLogger()

        root_logger.setLevel(
            logging.DEBUG
        )

        formatter = logging.Formatter(
            "%(asctime)s - "
            "%(name)s - "
            "%(levelname)s - "
            "%(message)s"
        )

        # Console handler
        console_exists = any(
            getattr(
                handler,
                "_study_agent_console",
                False
            )
            for handler in root_logger.handlers
        )

        if not console_exists:

            console_handler = (
                logging.StreamHandler()
            )

            console_handler.setLevel(
                logging.INFO
            )

            console_handler.setFormatter(
                formatter
            )

            console_handler._study_agent_console = True

            root_logger.addHandler(
                console_handler
            )

        # File handler
        file_exists = any(
            getattr(
                handler,
                "_study_agent_file",
                False
            )
            for handler in root_logger.handlers
        )

        if not file_exists:

            file_handler = logging.FileHandler(
                self.config.log_file,
                encoding="utf-8"
            )

            file_handler.setLevel(
                logging.DEBUG
            )

            file_handler.setFormatter(
                formatter
            )

            file_handler._study_agent_file = True

            root_logger.addHandler(
                file_handler
            )

        # Third-party logging
        logging.getLogger(
            "httpcore"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "httpx"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "huggingface_hub"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "sentence_transformers"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "transformers"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "chromadb"
        ).setLevel(logging.WARNING)

        logging.getLogger(
            "urllib3"
        ).setLevel(logging.WARNING)


_logger = Logger()

LOGGER = logging.getLogger(
    "study_agent"
)