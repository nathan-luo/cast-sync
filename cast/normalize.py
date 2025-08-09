"""Content normalization and hashing for Cast."""

import hashlib
import re
from typing import Any

import yaml


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def trim_trailing_spaces(text: str) -> str:
    """Remove trailing spaces from each line."""
    lines = text.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def ensure_trailing_newline(text: str) -> str:
    """Ensure text ends with a newline."""
    if text and not text.endswith("\n"):
        return text + "\n"
    return text


def normalize_yaml_frontmatter(
    content: str, 
    ephemeral_keys: list[str] | None = None
) -> tuple[str, dict[str, Any] | None]:
    """Normalize YAML frontmatter in markdown content.
    
    Args:
        content: Markdown content with optional frontmatter
        ephemeral_keys: Keys to remove from frontmatter
        
    Returns:
        (normalized_content, frontmatter_dict)
    """
    if ephemeral_keys is None:
        ephemeral_keys = ["updated", "last_synced", "base-version"]
    
    # Be robust to CRLF frontmatter and normalize once
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    # Check for frontmatter
    if not content.startswith("---\n"):
        return content, None
    
    # Find the closing ---
    end_match = re.search(r"\n---\n", content[4:])
    if not end_match:
        return content, None
    
    fm_text = content[4:end_match.start() + 4]
    body = content[end_match.end() + 4:]
    
    # Parse YAML
    try:
        fm_dict = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        # If YAML is invalid, return as-is
        return content, None
    
    # Remove ephemeral keys
    for key in ephemeral_keys:
        fm_dict.pop(key, None)
    
    # Sort keys for deterministic output
    sorted_fm = dict(sorted(fm_dict.items()))
    
    # Reserialize YAML
    if sorted_fm:
        fm_yaml = yaml.safe_dump(sorted_fm, sort_keys=True, allow_unicode=True)
        normalized = f"---\n{fm_yaml}---\n{body}"
    else:
        # No frontmatter left after removing ephemeral keys
        normalized = body
    
    return normalized, sorted_fm


def normalize_content(
    content: str,
    ephemeral_keys: list[str] | None = None
) -> str:
    """Normalize markdown content for hashing.
    
    Applies:
    - Line ending normalization (to LF)
    - Trailing space removal
    - YAML frontmatter normalization
    - Trailing newline enforcement
    
    Args:
        content: Raw markdown content
        ephemeral_keys: Keys to remove from frontmatter
        
    Returns:
        Normalized content
    """
    # Normalize line endings first
    content = normalize_line_endings(content)
    
    # Normalize YAML frontmatter
    content, _ = normalize_yaml_frontmatter(content, ephemeral_keys)
    
    # Trim trailing spaces
    content = trim_trailing_spaces(content)
    
    # Ensure trailing newline
    content = ensure_trailing_newline(content)
    
    return content


def compute_digest(content: bytes, algorithm: str = "sha256") -> str:
    """Compute hash digest of content.
    
    Args:
        content: Content bytes to hash
        algorithm: Hash algorithm (sha256, sha512, etc.)
        
    Returns:
        Hex digest string with algorithm prefix
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    return f"{algorithm}:{hasher.hexdigest()}"


def compute_normalized_digest(
    content: str,
    ephemeral_keys: list[str] | None = None,
    algorithm: str = "sha256",
    body_only: bool = False,
) -> str:
    """Compute normalized digest of markdown content.
    
    Args:
        content: Raw markdown content (or just body if body_only)
        ephemeral_keys: Keys to remove from frontmatter
        algorithm: Hash algorithm
        body_only: If True, content is already just the body
        
    Returns:
        Digest string with algorithm prefix
    """
    if body_only:
        # Content is already just the body, normalize it directly
        normalized = normalize_line_endings(content)
        normalized = trim_trailing_spaces(normalized)
        normalized = ensure_trailing_newline(normalized)
    else:
        normalized = normalize_content(content, ephemeral_keys)
    
    content_bytes = normalized.encode("utf-8")
    return compute_digest(content_bytes, algorithm)


def verify_digest(content: str, expected_digest: str, ephemeral_keys: list[str] | None = None) -> bool:
    """Verify content matches expected digest.
    
    Args:
        content: Raw markdown content
        expected_digest: Expected digest with algorithm prefix
        ephemeral_keys: Keys to remove from frontmatter
        
    Returns:
        True if digest matches
    """
    # Extract algorithm from digest
    if ":" in expected_digest:
        algorithm, _ = expected_digest.split(":", 1)
    else:
        algorithm = "sha256"
    
    actual_digest = compute_normalized_digest(content, ephemeral_keys, algorithm)
    return actual_digest == expected_digest