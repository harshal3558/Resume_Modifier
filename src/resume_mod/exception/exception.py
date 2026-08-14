"""
exception/exception.py
======================
Custom exception with rich error context (file + line number).
"""

import logging
import sys
# from src.logger import logging

LOGGER = logging.getLogger("resume_mod.exception")


def error_message_detail(error: Exception, error_detail: sys) -> str:
    """Extract file name and line number from the traceback."""

    _, _, exc_tb = error_detail.exc_info()

    file_name = "Unknown"
    line_number = 0

    if exc_tb is not None:
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

    error_message = (
        f"Error occurred in script [{file_name}] "
        f"at line [{line_number}]: {error}"
    )

    return error_message


class CustomException(Exception):
    """
    Drop-in replacement for Exception with automatic context capture.

    Usage
    -----
    try:
        ...
    except Exception as e:
        raise CustomException(e, sys) from e
    """

    def __init__(self, error_message: Exception | str, error_detail: sys) -> None:
        super().__init__(error_message)
        self.error_message = error_message_detail(
            error_message,
            error_detail=error_detail,
        )

    def __str__(self) -> str:
        return self.error_message