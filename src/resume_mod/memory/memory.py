"""
memory/memory.py
================
MemoryQueue — thin wrapper around a Redis Stream.

Acts as the shared backbone between JobProducer and JobWorker.
"""

from __future__ import annotations

import logging
import os

LOGGER = logging.getLogger("resume_mod.memory")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_NAME = os.getenv("REDIS_STREAM", "resume_jobs_stream")


class MemoryQueue:
    """
    Wraps a Redis Stream to provide a simple job queue.

    Parameters
    ----------
    stream_name : str
        Redis stream key name (defaults to REDIS_STREAM env var).
    host : str
        Redis host (defaults to REDIS_HOST env var or 'localhost').
    port : int
        Redis port (defaults to REDIS_PORT env var or 6379).
    """

    def __init__(
        self,
        stream_name: str = STREAM_NAME,
        host: str = REDIS_HOST,
        port: int = REDIS_PORT,
    ) -> None:
        self.stream_name = stream_name
        self._host = host
        self._port = port
        self._client = None

    # ------------------------------------------------------------------
    # Lazy Redis connection
    # ------------------------------------------------------------------

    def _get_client(self):
        """Return a live Redis client, connecting lazily on first use."""
        if self._client is None:
            try:
                import redis

                self._client = redis.Redis(
                    host=self._host,
                    port=self._port,
                    decode_responses=True,
                )
                # Ping to verify the connection is alive
                self._client.ping()
                LOGGER.info(
                    "Connected to Redis at %s:%s",
                    self._host,
                    self._port,
                )
            except Exception as exc:
                LOGGER.error(
                    "Could not connect to Redis — %s",
                    exc,
                )
                raise

        return self._client

    # ------------------------------------------------------------------
    # Push a job payload onto the stream
    # ------------------------------------------------------------------

    def push_job(self, payload: dict) -> str:
        """
        Add a dict payload to the Redis stream.

        Returns
        -------
        str
            The auto-generated Redis message ID.
        """
        client = self._get_client()
        message_id: str = client.xadd(
            self.stream_name,
            payload,
            id="*",
        )
        LOGGER.info(
            "Pushed job to stream '%s' with id=%s",
            self.stream_name,
            message_id,
        )
        return message_id

    # ------------------------------------------------------------------
    # Read pending jobs from the stream
    # ------------------------------------------------------------------

    def read_jobs(
        self,
        last_id: str = "$",
        count: int = 1,
        block_ms: int = 0,
    ) -> list[tuple[str, dict]]:
        """
        Read new messages from the stream.

        Parameters
        ----------
        last_id : str
            Stream cursor. '$' = only new messages (blocking tail).
        count : int
            Max messages to fetch at once.
        block_ms : int
            Milliseconds to block waiting for a message (0 = forever).

        Returns
        -------
        list of (message_id, payload_dict) tuples
        """
        client = self._get_client()
        response = client.xread(
            {self.stream_name: last_id},
            count=count,
            block=block_ms,
        )
        results: list[tuple[str, dict]] = []
        if response:
            for _stream, messages in response:
                for message_id, data in messages:
                    results.append((message_id, data))
        return results
