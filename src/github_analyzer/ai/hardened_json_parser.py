# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
HardenedJSONParser - Phase 2 of Operation Containment Field

Robust JSON parser utility designed to handle malformed JSON responses from AI models.
Implements aggressive pattern matching and repair techniques to salvage valid data
from corrupted JSON structures.
"""

import json
import re
from typing import Any, Callable, Dict, List, Match, Optional, Tuple, Union

from ..utils.logging import get_logger

logger = get_logger(__name__)


class HardenedJSONParser:
    """
    Robust JSON parser that attempts to repair common AI-generated JSON errors.

    This parser uses a multi-stage approach:
    1. Extract JSON block from mixed content
    2. Apply regex-based repairs for common errors
    3. Validate structure against expected schema
    4. Provide detailed error reporting for unrecoverable errors
    """

    # Common JSON repair patterns
    REPAIR_PATTERNS: List[Tuple[str, Union[str, Callable[[Match[str]], str]]]] = [
        # Fix trailing commas before closing brackets/braces
        (r",\s*([}\]])", r"\1"),
        # Fix single quotes to double quotes (but preserve quotes inside strings)
        (r"(?<!\\)'([^']*?)(?<!\\)'", r'"\1"'),
        # Fix unquoted keys (simple cases)
        (r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":'),
        # Remove extra commas
        (r",+", r","),
        # Fix common escape issues
        (r'\\(?!["\\/bfnrt])', r"\\\\"),
        # Remove trailing content after final brace
        (r"\}[^}]*$", r"}"),
        # Fix missing quotes around string values (conservative approach)
        (
            r':\s*([^",\[\]{}]+?)(?=\s*[,}\]])',
            lambda m: (
                f': "{m.group(1).strip()}"'
                if not m.group(1).strip().isdigit()
                and m.group(1).strip().lower() not in ["true", "false", "null"]
                and m.group(1).strip() not in ["True", "False", "None"]
                else m.group(0)
            ),
        ),
    ]

    def __init__(self) -> None:
        """Initialize the hardened JSON parser."""
        self.repair_attempts = 0
        self.last_error: Optional[str] = None

    def parse(
        self, response_text: str, expected_keys: Optional[List[str]] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parse JSON from response text with aggressive error recovery.

        Args:
            response_text: Raw response text that may contain JSON
            expected_keys: Optional list of keys that must be present in valid JSON

        Returns:
            Tuple of (parsed_dict, error_message)
            If successful: (dict, "")
            If failed: (None, error_description)
        """
        self.repair_attempts = 0
        self.last_error = None

        logger.debug(
            f"Attempting to parse JSON from response of {len(response_text)} characters"
        )

        # Step 1: Extract JSON block
        json_text = self._extract_json_block(response_text)
        if not json_text:
            return None, "No JSON block found in response"

        logger.debug(f"Extracted JSON block of {len(json_text)} characters")

        # Step 2: Try direct parsing first
        result = self._try_parse(json_text)
        if result:
            if self._validate_structure(result, expected_keys):
                logger.info("JSON parsed successfully without repairs")
                return result, ""
            else:
                logger.warning("JSON parsed but failed structure validation")

        # Step 3: Apply repairs and retry
        repaired_json = self._apply_repairs(json_text)
        result = self._try_parse(repaired_json)
        if result:
            if self._validate_structure(result, expected_keys):
                logger.info(
                    f"JSON parsed successfully after {self.repair_attempts} repairs"
                )
                return result, ""
            else:
                logger.warning("Repaired JSON parsed but failed structure validation")

        # Step 4: Last resort - aggressive extraction
        logger.warning("Standard repairs failed, attempting aggressive extraction")
        result = self._aggressive_extract(response_text, expected_keys)
        if result:
            logger.info("JSON extracted using aggressive parsing")
            return result, ""

        # Step 5: Complete failure
        error_msg = f"Failed to parse JSON after {self.repair_attempts} repair attempts. Last error: {self.last_error}"
        logger.error(error_msg)
        return None, error_msg

    def _extract_json_block(self, text: str) -> Optional[str]:
        """Extract JSON block from mixed content, handling truncation."""
        # Find the first opening brace
        start_pos = text.find("{")
        if start_pos == -1:
            return None

        # Count braces to find the matching closing brace
        brace_count = 0
        end_pos = start_pos
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start_pos:], start_pos):
            # Handle string content properly
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            # Only count braces outside of strings
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break

        # If braces aren't balanced, we have truncated JSON
        if brace_count > 0:
            logger.warning(
                f"Detected truncated JSON with {brace_count} unclosed braces"
            )
            # Try to repair by adding closing braces
            json_block = text[start_pos:]

            # Clean up any incomplete values at the end
            # Remove incomplete string values
            if '"' in json_block:
                last_quote = json_block.rfind('"')
                # Check if this quote is closing a value
                if last_quote > 0:
                    # Look for the start of this string value
                    search_start = max(
                        0, last_quote - 1000
                    )  # Search back up to 1000 chars
                    substr = json_block[search_start:last_quote]
                    if substr.count('"') % 2 == 1:  # Odd number means unclosed string
                        # Find the last complete element
                        last_complete = max(
                            json_block.rfind('",'),
                            json_block.rfind('"}'),
                            json_block.rfind('"]'),
                            json_block.rfind('" }'),
                            json_block.rfind('" ]'),
                        )
                        if last_complete > 0:
                            json_block = json_block[: last_complete + 2]

            # Add missing closing brackets and braces
            bracket_diff = json_block.count("[") - json_block.count("]")
            json_block += "]" * bracket_diff
            json_block += "}" * brace_count

            logger.info(
                f"Repaired truncated JSON by adding {bracket_diff} ] and {brace_count} }}"
            )
            return json_block

        if brace_count == 0:
            json_block = text[start_pos:end_pos]
            # Basic validation that brackets are balanced
            if json_block.count("[") == json_block.count("]"):
                return json_block

        return None

    def _try_parse(self, json_text: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON text, capturing errors."""
        try:
            result = json.loads(json_text)
            if isinstance(result, dict):
                return result
            else:
                self.last_error = f"Expected dict but got {type(result).__name__}"
                return None
        except json.JSONDecodeError as e:
            self.last_error = f"JSONDecodeError: {e}"
            logger.debug(f"JSON parse failed: {e}")
            return None
        except Exception as e:
            self.last_error = f"Unexpected error: {e}"
            logger.debug(f"Unexpected JSON parse error: {e}")
            return None

    def _apply_repairs(self, json_text: str) -> str:
        """Apply regex-based repairs to fix common JSON issues."""
        repaired = json_text

        for pattern, replacement in self.REPAIR_PATTERNS:
            try:
                if callable(replacement):
                    # Handle lambda replacements
                    repaired = re.sub(pattern, replacement, repaired)
                else:
                    repaired = re.sub(pattern, replacement, repaired)
                self.repair_attempts += 1
            except Exception as e:
                logger.debug(f"Repair pattern failed: {e}")
                continue

        # Additional manual repairs
        repaired = self._manual_repairs(repaired)

        return repaired

    def _manual_repairs(self, json_text: str) -> str:
        """Apply manual repairs for specific known issues."""
        # Remove any text before the opening brace
        json_text = re.sub(r"^[^{]*", "", json_text)

        # Remove any text after the final closing brace
        json_text = re.sub(r"\}[^}]*$", "}", json_text)

        # Fix boolean values (case-sensitive)
        json_text = re.sub(r":\s*True\b", ": true", json_text)
        json_text = re.sub(r":\s*False\b", ": false", json_text)
        json_text = re.sub(r":\s*None\b", ": null", json_text)

        # Fix array syntax issues
        json_text = re.sub(r"\[\s*,", "[", json_text)  # Remove leading comma in arrays
        json_text = re.sub(r",\s*\]", "]", json_text)  # Remove trailing comma in arrays

        self.repair_attempts += 1
        return json_text

    def _validate_structure(
        self, data: Dict[str, Any], expected_keys: Optional[List[str]]
    ) -> bool:
        """Validate that parsed JSON has expected structure."""
        if not expected_keys:
            return True

        # Only require critical keys, allow extra keys
        critical_keys = ["summary"]  # Only require summary as critical
        missing_critical = [key for key in critical_keys if key not in data]
        if missing_critical:
            logger.debug(f"Missing critical keys: {missing_critical}")
            return False

        # Check if we have some expected keys (not all required)
        found_keys = [key for key in expected_keys if key in data]
        logger.debug(
            f"Structure validation: found {len(found_keys)} out of {len(expected_keys)} expected keys: {found_keys}"
        )
        logger.debug(f"Available keys in data: {list(data.keys())}")

        if len(found_keys) >= 3:  # Need at least 3 out of 5 expected keys
            return True

        logger.debug(
            f"Validation failed: Only found {len(found_keys)} out of {len(expected_keys)} expected keys: {found_keys}"
        )
        return False

    def _aggressive_extract(
        self, text: str, expected_keys: Optional[List[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Last resort: Extract key-value pairs using aggressive pattern matching.

        This method tries to salvage any useful data even from severely malformed JSON.
        """
        logger.debug("Attempting aggressive extraction")

        extracted = {}

        # Try to extract common fields using regex
        field_patterns = {
            "summary": r'"summary"\s*:\s*"([^"]*)"',
            "observed_patterns": r'"observed_patterns"\s*:\s*(\[.*?\])',
            "limitations": r'"limitations"\s*:\s*(\[.*?\])',
            "context_notes": r'"context_notes"\s*:\s*"([^"]*)"',
            "upgrade_benefit": r'"upgrade_benefit"\s*:\s*"([^"]*)"',
        }

        for field, pattern in field_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    if field in ["observed_patterns", "limitations"]:
                        # Try to parse array
                        array_text = match.group(1)
                        # More aggressive array repair
                        array_text = re.sub(
                            r",\s*\]", "]", array_text
                        )  # Fix trailing commas
                        array_text = re.sub(
                            r":\s*True\b", ": true", array_text
                        )  # Fix booleans
                        array_text = re.sub(r":\s*False\b", ": false", array_text)
                        array_text = re.sub(r":\s*None\b", ": null", array_text)
                        array_text = re.sub(
                            r"'([^']*)'", r'"\1"', array_text
                        )  # Fix quotes
                        extracted[field] = json.loads(array_text)
                    else:
                        extracted[field] = match.group(1)
                except Exception as e:
                    logger.debug(f"Failed to extract {field}: {e}")
                    # Provide fallback values for arrays
                    if field == "observed_patterns":
                        extracted[field] = []
                    elif field == "limitations":
                        extracted[field] = ["Data extraction incomplete"]
                    continue

        # If we found any data, return it
        if extracted:
            # Fill in missing required fields with defaults
            if "summary" not in extracted:
                extracted["summary"] = "Analysis completed with limited data extraction"
            if "observed_patterns" not in extracted:
                extracted["observed_patterns"] = []
            if "limitations" not in extracted:
                extracted["limitations"] = ["Data extraction was incomplete"]
            if "context_notes" not in extracted:
                extracted["context_notes"] = "Extracted from malformed response"
            if "upgrade_benefit" not in extracted:
                extracted["upgrade_benefit"] = (
                    "Professional analysis provides detailed insights"
                )

            return extracted

        return None


def create_hardened_parser() -> HardenedJSONParser:
    """Factory function to create a hardened JSON parser instance."""
    return HardenedJSONParser()
