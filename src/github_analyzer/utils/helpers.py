# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Helper functions and utilities for Exiqus.

This module provides common utility functions used throughout
the application for data processing, validation, and formatting.
"""

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique ID with optional prefix.

    Args:
        prefix: Optional prefix for the ID

    Returns:
        Unique ID string
    """
    random_part = secrets.token_urlsafe(16)[:16]  # 16 chars
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


def validate_github_url(url: str, allow_subdirectory: bool = True) -> bool:
    """
    Validate if a URL is a valid GitHub repository URL.

    Args:
        url: URL to validate
        allow_subdirectory: Whether to accept URLs with subdirectory paths

    Returns:
        True if valid GitHub repository URL, False otherwise
    """
    if allow_subdirectory:
        # Use new parser that handles subdirectories
        parsed_info = parse_github_url_with_subdirectory(url)
        return parsed_info is not None

    # Original strict validation (for backward compatibility)
    try:
        # Parse URL
        parsed = urlparse(url)

        # Must be HTTP/HTTPS and GitHub domain
        if parsed.scheme not in ["http", "https"] or parsed.netloc != "github.com":
            return False

        # Extract path components
        path_parts = [part for part in parsed.path.split("/") if part]

        # Must have exactly 2 parts: owner/repo
        if len(path_parts) != 2:
            return False

        owner, repo = path_parts

        # Validate owner and repo names (GitHub naming rules)
        github_name_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$"

        if not re.match(github_name_pattern, owner) or not re.match(
            github_name_pattern, repo
        ):
            return False

        # Length limits (GitHub limits)
        if len(owner) > 39 or len(repo) > 100:
            return False

        return True

    except Exception:
        return False


def parse_github_url_with_subdirectory(url: str) -> Optional[Dict[str, str]]:
    """
    Parse GitHub URL and extract repository info and subdirectory path.

    Handles both standard repository URLs and nested subdirectory URLs.
    Examples:
    - https://github.com/owner/repo -> base_url, no subdirectory
    - https://github.com/owner/repo/tree/main/examples/blog -> base_url + subdirectory

    Args:
        url: GitHub URL (can include subdirectory paths)

    Returns:
        Dictionary with 'base_url', 'owner', 'repo', 'subdirectory' keys, or None
    """
    try:
        # Parse URL
        parsed = urlparse(url)

        # Must be GitHub (accept both http and https)
        if parsed.scheme not in ["http", "https"] or parsed.netloc != "github.com":
            return None

        # Extract path components
        path_parts = [part for part in parsed.path.split("/") if part]

        # Need at least owner/repo
        if len(path_parts) < 2:
            return None

        owner, repo = path_parts[0], path_parts[1]

        # Validate owner and repo names
        github_name_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$"
        if not re.match(github_name_pattern, owner) or not re.match(
            github_name_pattern, repo
        ):
            return None

        # Build base repository URL
        base_url = f"https://github.com/{owner}/{repo}"

        # Check for subdirectory path
        subdirectory = None
        if len(path_parts) > 2:
            # Common patterns: /tree/branch/path, /blob/branch/path
            if path_parts[2] in ["tree", "blob"] and len(path_parts) > 4:
                # Skip tree/blob and branch, take the rest as subdirectory
                subdirectory = "/".join(path_parts[4:])
            elif path_parts[2] not in [
                "issues",
                "pulls",
                "actions",
                "wiki",
                "settings",
            ]:
                # If it's not a GitHub UI path, might be direct subdirectory
                subdirectory = "/".join(path_parts[2:])

        return {
            "base_url": base_url,
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
            "subdirectory": subdirectory or "",
        }
    except Exception:
        return None


def extract_repo_info(url: str) -> Optional[Dict[str, str]]:
    """
    Extract owner and repository name from GitHub URL.

    Args:
        url: GitHub repository URL

    Returns:
        Dictionary with 'owner' and 'repo' keys, or None if invalid
    """
    # Try new parser first for backward compatibility
    parsed_info = parse_github_url_with_subdirectory(url)
    if parsed_info:
        return {
            "owner": parsed_info["owner"],
            "repo": parsed_info["repo"],
            "full_name": parsed_info["full_name"],
        }
    return None


def sanitize_repo_name(name: str) -> str:
    """
    Sanitize repository name for safe use in filenames, etc.

    Args:
        name: Repository name to sanitize

    Returns:
        Sanitized name safe for filenames
    """
    # Replace problematic characters with underscores
    sanitized = re.sub(r"[^\w\-_.]", "_", name)

    # Remove multiple consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Trim underscores from ends
    sanitized = sanitized.strip("_")

    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_repo"

    return sanitized


def calculate_cost(
    input_tokens: int, output_tokens: int, model: Optional[str] = None
) -> float:
    """
    Calculate the cost of an AI API call.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: AI model used. Defaults to the configured model.

    Returns:
        Cost in USD
    """
    from ..ai.cost_tracker import CostTracker
    from ..core.tier_config import get_configured_model

    model = model or get_configured_model()
    pricing = CostTracker.MODEL_PRICING.get(model, CostTracker.UNKNOWN_MODEL_PRICING)

    # CostTracker prices per 1000 tokens.
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]

    return input_cost + output_cost


def _format_header(result: Dict[str, Any]) -> List[str]:
    """Format the header section of the analysis result."""
    lines = []
    if "repository_url" in result:
        lines.append(f"[Analysis] Analysis Result for {result['repository_url']}")
    else:
        lines.append("[Analysis] Repository Analysis Result")
    lines.append("=" * 60)
    return lines


def _format_assessment_section(result: Dict[str, Any]) -> List[str]:
    """Format assessment type and confidence information."""
    lines = []
    if "assessment_type" in result:
        lines.append(f"[Analysis] Assessment Type: {result['assessment_type']}")
    else:
        # Legacy support removed - all assessments are evidence-based
        lines.append("[Analysis] Assessment: Evidence-based analysis")

    if "confidence" in result:
        lines.append(f"[Target] Confidence: {result['confidence']}%")
    return lines


def _format_summary_section(result: Dict[str, Any]) -> List[str]:
    """Format summary and key signal information."""
    lines = []
    if "summary" in result:
        lines.append("\n[Note] Summary:")
        lines.append(f"   {result['summary']}")

    if "key_signal" in result:
        lines.append("\n[Key] Key Signal:")
        lines.append(f"   {result['key_signal']}")
    return lines


def _format_strengths_concerns_section(result: Dict[str, Any]) -> List[str]:
    """Format strengths and concerns sections."""
    lines = []

    # Strengths
    if "strengths" in result and result["strengths"]:
        lines.append("\n[OK] Strengths:")
        for strength in result["strengths"]:
            lines.append(f"   • {strength}")

    # Concerns/Yellow flags
    concerns_key = "yellow_flags" if "yellow_flags" in result else "concerns"
    if concerns_key in result and result[concerns_key]:
        lines.append("\n[Warning]  Areas of Concern:")
        for concern in result[concerns_key]:
            lines.append(f"   • {concern}")

    # Context fit
    if "context_fit" in result:
        lines.append("\n[Target] Context Suitability:")
        for context, suitable in result["context_fit"].items():
            emoji = "[OK]" if suitable else "[X]"
            lines.append(f"   {emoji} {context.title()}")

    return lines


def _format_metadata_section(result: Dict[str, Any]) -> List[str]:
    """Format metadata information."""
    lines = []
    if "generated_by" in result:
        lines.append(f"\n[Bot] Analysis Method: {result['generated_by']}")

    if "cost" in result:
        lines.append(f"[Cost] Cost: ${result['cost']:.6f}")

    if "analysis_time" in result:
        lines.append(f"[Time]  Time: {result['analysis_time']:.2f}s")

    return lines


def format_analysis_result(result: Dict[str, Any]) -> str:
    """
    Format analysis result for human-readable display.

    Args:
        result: Analysis result dictionary

    Returns:
        Formatted string representation
    """
    if not result:
        return "No analysis result available"

    lines = []

    # Build formatted output using helper functions
    lines.extend(_format_header(result))
    lines.extend(_format_assessment_section(result))
    lines.extend(_format_summary_section(result))
    lines.extend(_format_strengths_concerns_section(result))
    lines.extend(_format_metadata_section(result))

    return "\n".join(lines)


def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Safely parse JSON with fallback.

    Args:
        data: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON data or default value
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely serialize to JSON with fallback.

    Args:
        data: Data to serialize
        default: Default JSON string if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, indent=2)
    except (TypeError, ValueError):
        return default


def normalize_datetime(dt: Union[str, datetime]) -> datetime:
    """
    Normalize datetime to UTC timezone-aware datetime.

    Args:
        dt: Datetime string or datetime object

    Returns:
        UTC timezone-aware datetime
    """
    if isinstance(dt, str):
        # Try to parse ISO format
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            # Fallback to current time
            dt = datetime.now(timezone.utc)

    if isinstance(dt, datetime):
        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

    return dt


def calculate_days_between(
    start: Union[str, datetime], end: Optional[Union[str, datetime]] = None
) -> int:
    """
    Calculate days between two dates.

    Args:
        start: Start date
        end: End date (defaults to now)

    Returns:
        Number of days between dates
    """
    if end is None:
        end = datetime.now(timezone.utc)

    start_dt = normalize_datetime(start)
    end_dt = normalize_datetime(end)

    return (end_dt - start_dt).days


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def parse_github_languages(languages: Dict[str, int]) -> Dict[str, float]:
    """
    Parse GitHub languages data to percentages.

    Args:
        languages: Language data from GitHub API (name -> bytes)

    Returns:
        Language percentages (name -> percentage)
    """
    if not languages:
        return {}

    total_bytes = sum(languages.values())
    if total_bytes == 0:
        return {}

    return {
        lang: round((bytes_count / total_bytes) * 100, 1)
        for lang, bytes_count in languages.items()
    }


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Filename

    Returns:
        File extension (without dot) or empty string
    """
    return Path(filename).suffix.lstrip(".")


def is_documentation_file(filename: str) -> bool:
    """
    Check if filename appears to be documentation.

    Args:
        filename: Filename to check

    Returns:
        True if appears to be documentation
    """
    filename_lower = filename.lower()

    # Common documentation files
    doc_files = {
        "readme",
        "readme.md",
        "readme.txt",
        "readme.rst",
        "contributing",
        "contributing.md",
        "changelog",
        "changelog.md",
        "license",
        "license.md",
        "license.txt",
        "authors",
        "authors.md",
        "install",
        "install.md",
        "usage",
        "usage.md",
    }

    # Documentation directories
    doc_dirs = {"docs/", "doc/", "documentation/"}

    return (
        filename_lower in doc_files
        or any(filename_lower.startswith(doc_dir) for doc_dir in doc_dirs)
        or filename_lower.endswith(".md")
    )


def is_test_file(filename: str) -> bool:
    """
    Check if filename appears to be a test file.

    Args:
        filename: Filename to check

    Returns:
        True if appears to be a test file
    """
    filename_lower = filename.lower()

    return (
        "test" in filename_lower
        or "spec" in filename_lower
        or filename_lower.startswith("test_")
        or filename_lower.endswith("_test.py")
        or filename_lower.endswith(".test.js")
        or filename_lower.endswith(".spec.js")
    )
