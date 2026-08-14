"""
memory/worker.py
================
JobWorker — reads resume jobs from the MemoryQueue and processes them
via a user-supplied callback.
"""

from __future__ import annotations

import logging
from typing import Callable

from resume_mod.memory.memory import MemoryQueue

LOGGER = logging.getLogger("resume_mod.memory.worker")


class JobWorker:
    """
    Background worker that listens on the Redis Stream and calls
    a callback for every job it receives.

    Parameters
    ----------
    queue : MemoryQueue | None
        Shared queue instance.  A new one is created if not provided.
    callback : Callable[[str, dict], None] | None
        Function invoked for each job.
        Signature: callback(message_id: str, payload: dict)
    """

    def __init__(
        self,
        queue: MemoryQueue | None = None,
        callback: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.queue = queue or MemoryQueue()
        self.callback = callback or self._default_callback

    # ------------------------------------------------------------------
    # Default callback — just logs the job
    # ------------------------------------------------------------------

    @staticmethod
    def _default_callback(message_id: str, payload: dict) -> None:
        LOGGER.info(
            "📦 Job received [%s] → filename='%s'",
            message_id,
            payload.get("filename", "unknown"),
        )

    # ------------------------------------------------------------------
    # Blocking event loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Block and process jobs from the queue indefinitely.

        Stop with KeyboardInterrupt (Ctrl+C).
        """
        LOGGER.info(
            "🟢 Worker started — listening on stream '%s' …",
            self.queue.stream_name,
        )

        last_id = "$"   # only receive messages that arrive from now on

        while True:
            try:
                jobs = self.queue.read_jobs(
                    last_id=last_id,
                    count=1,
                    block_ms=0,         # block indefinitely until a job arrives
                )

                for message_id, payload in jobs:
                    LOGGER.info(
                        "Processing job [%s] — filename='%s'",
                        message_id,
                        payload.get("filename"),
                    )

                    try:
                        self.callback(message_id, payload)
                        LOGGER.info(
                            "✅ Job [%s] completed.",
                            message_id,
                        )
                    except Exception as exc:
                        LOGGER.error(
                            "❌ Job [%s] failed — %s",
                            message_id,
                            exc,
                        )

                    # Advance cursor so we don't re-process this message
                    last_id = message_id

            except KeyboardInterrupt:
                LOGGER.info("🛑 Worker stopped manually.")
                break

            except Exception as exc:
                LOGGER.error(
                    "Stream read error — %s. Retrying …",
                    exc,
                )
