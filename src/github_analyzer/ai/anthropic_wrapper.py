# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Anthropic API wrapper with timeout and retry logic
"""

import logging
import time
from typing import Any, Dict, List, Optional

import anthropic
from anthropic import APIConnectionError, APITimeoutError
from anthropic.types import MessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class AnthropicWrapper:
    """Wrapper for Anthropic API with timeout and retry logic"""

    def __init__(
        self,
        api_key: str,
        default_timeout: int = 180,  # 3 minutes default (was 30 seconds - too short!)
        max_retries: int = 3,
    ):
        """Initialize wrapper with timeout settings"""
        self.api_key = api_key
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # Create client with timeout
        logger.info(f"🔧 Creating Anthropic client with timeout: {default_timeout}s")
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=default_timeout,  # Global timeout for all requests
        )
        logger.info(
            f"✅ Anthropic client created with timeout: {self.client._client._timeout}"
        )

        # Expose the messages API
        self.messages = self

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError)),
    )
    def create_message(
        self,
        model: str,
        messages: List[MessageParam],
        max_tokens: int = 1024,
        temperature: float = 0.1,  # Lowered for deterministic output
        system: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> anthropic.types.Message:
        """Create message with timeout and retry logic

        🏗️ GLASS HOUSE PROTOCOL - Full transparency in API calls
        """

        start_time = time.time()
        timeout_to_use = timeout or self.default_timeout

        try:
            # 🏗️ GLASS HOUSE - Log everything
            logger.info("=" * 60)
            logger.info("🏗️ ANTHROPIC WRAPPER - API CALL STARTING")
            logger.info(f"🤖 Model: {model}")
            logger.info(f"⏱️ Timeout: {timeout_to_use}s")
            logger.info(f"🎯 Max Tokens: {max_tokens}")
            logger.info(f"🌡️ Temperature: {temperature}")
            logger.info(f"📩 Messages Count: {len(messages) if messages else 0}")
            logger.info(f"📝 System Prompt Length: {len(system) if system else 0}")
            logger.info("=" * 60)

            # Make the API call with explicit timeout
            response = self.client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or anthropic.NOT_GIVEN,
                timeout=timeout_to_use,  # Per-request timeout
            )

            elapsed = time.time() - start_time

            # 🏗️ GLASS HOUSE - Log success
            logger.info("✅ API CALL SUCCESSFUL")
            logger.info(f"⏱️ Elapsed Time: {elapsed:.2f}s")
            if hasattr(response, "content") and response.content:
                logger.info(
                    f"📤 Response Length: {len(response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0]))} chars"
                )

            # Log token usage if available
            if hasattr(response, "usage"):
                total_tokens = (
                    response.usage.input_tokens + response.usage.output_tokens
                )
                logger.info(
                    f"🎯 Token Usage: {response.usage.input_tokens} in + {response.usage.output_tokens} out = {total_tokens} total"
                )
                # Note: We don't add total_tokens to response to maintain type safety
                # The analyzer accesses tokens directly from response.usage

            logger.info("=" * 60)

            return response

        except APITimeoutError as e:
            elapsed = time.time() - start_time
            logger.error("=" * 60)
            logger.error("⚠️ ANTHROPIC WRAPPER - TIMEOUT ERROR")
            logger.error(f"⏱️ Elapsed: {elapsed:.2f}s")
            logger.error(f"📝 Error: {str(e)}")
            logger.error("=" * 60)
            raise

        except APIConnectionError as e:
            logger.error("=" * 60)
            logger.error("❌ ANTHROPIC WRAPPER - CONNECTION ERROR")
            logger.error(f"📝 Error: {str(e)}")
            logger.error("=" * 60)
            raise

        except Exception as e:
            logger.error("=" * 60)
            logger.error("🔥 ANTHROPIC WRAPPER - UNEXPECTED ERROR")
            logger.error(f"📝 Error Type: {type(e).__name__}")
            logger.error(f"📝 Error: {str(e)}")
            import traceback

            logger.error(f"📝 Stack Trace:\n{traceback.format_exc()}")
            logger.error("=" * 60)
            raise

    def create_message_safe(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.1,  # Lowered for deterministic output
        system: Optional[str] = None,
        timeout: Optional[int] = None,
        fallback_response: Optional[str] = None,
    ) -> Optional[anthropic.types.Message]:
        """Create message with fallback on failure"""

        try:
            return self.create_message(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                timeout=timeout,
            )
        except Exception as e:
            logger.error(f"Failed after retries: {str(e)}")

            if fallback_response:
                # Return a mock response with fallback content
                class MockMessage:
                    def __init__(self, content: str) -> None:
                        self.content = [
                            anthropic.types.TextBlock(type="text", text=content)
                        ]

                return MockMessage(fallback_response)  # type: ignore[return-value]

            return None

    def create(self, **kwargs: Any) -> anthropic.types.Message:
        """Alias for create_message to match Anthropic API interface

        🏗️ GLASS HOUSE PROTOCOL - Direct passthrough with full logging
        """
        logger.info("🌉 WRAPPER: create() called, forwarding to create_message()")

        # Map standard Anthropic parameters to our create_message parameters
        # The standard API uses 'messages' but our create_message expects 'messages' too
        # Just pass through all kwargs directly
        return self.create_message(**kwargs)


# Singleton instance
_wrapper_instance: Optional[AnthropicWrapper] = None


def get_anthropic_wrapper(api_key: str, timeout: int = 30) -> AnthropicWrapper:
    """Get or create the Anthropic wrapper instance"""
    global _wrapper_instance

    if _wrapper_instance is None:
        _wrapper_instance = AnthropicWrapper(api_key, timeout)

    return _wrapper_instance
