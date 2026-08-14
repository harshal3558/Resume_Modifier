"""
memory/producer.py
==================
JobProducer — pushes resume-modification jobs onto the MemoryQueue.
"""

from __future__ import annotations

import logging

from resume_mod.memory.memory import MemoryQueue

LOGGER = logging.getLogger("resume_mod.memory.producer")


class JobProducer:
    """
    Sends resume-modification job payloads to the Redis Stream.

    Parameters
    ----------
    queue : MemoryQueue | None
        Shared queue instance.  A new one is created if not provided.
    """

    def __init__(
        self,
        queue: MemoryQueue | None = None,
    ) -> None:
        self.queue = queue or MemoryQueue()

    def push(
        self,
        filename: str,
        job_description: str,
        output_path: str = "",
    ) -> str:
        """
        Push a resume-modification job to the queue.

        Parameters
        ----------
        filename : str
            Original resume filename (used as job identifier).
        job_description : str
            Target job description the resume should be tailored for.
        output_path : str
            Path to the generated PDF (populated after LLM processing).

        Returns
        -------
        str
            Redis message ID of the queued job.
        """
        payload = {
            "filename": filename,
            "job_description": job_description[:500],   # trim for Redis
            "output_path": output_path,
        }

        LOGGER.info(
            "Producing job for filename='%s'",
            filename,
        )

        message_id = self.queue.push_job(payload)

        LOGGER.info(
            "Job queued — message_id=%s",
            message_id,
        )

        return message_id
