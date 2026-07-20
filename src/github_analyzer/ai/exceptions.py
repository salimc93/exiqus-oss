# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Custom exceptions for AI analysis operations.

Part of Operation Containment Field - ensuring invalid data never propagates.
"""


class UnparsableAIResponseError(Exception):
    """
    Raised when AI response cannot be parsed into valid JSON after all retry attempts.

    This exception ensures that malformed AI responses are never silently accepted,
    maintaining data integrity throughout the system.
    """

    def __init__(self, message: str, last_response: str = "", attempts: int = 0):
        """
        Initialize the exception with details about the parsing failure.

        Args:
            message: Error description
            last_response: The last AI response that failed to parse
            attempts: Number of attempts made before giving up
        """
        self.last_response = last_response
        self.attempts = attempts
        super().__init__(message)
