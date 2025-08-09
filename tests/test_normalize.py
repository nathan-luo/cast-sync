"""Tests for content normalization."""

import pytest

from cast.normalize import (
    compute_normalized_digest,
    ensure_trailing_newline,
    normalize_content,
    normalize_line_endings,
    normalize_yaml_frontmatter,
    trim_trailing_spaces,
)


def test_normalize_line_endings():
    """Test line ending normalization."""
    assert normalize_line_endings("hello\r\nworld") == "hello\nworld"
    assert normalize_line_endings("hello\rworld") == "hello\nworld"
    assert normalize_line_endings("hello\nworld") == "hello\nworld"


def test_trim_trailing_spaces():
    """Test trailing space removal."""
    assert trim_trailing_spaces("hello  \nworld  ") == "hello\nworld"
    assert trim_trailing_spaces("  leading") == "  leading"


def test_ensure_trailing_newline():
    """Test trailing newline enforcement."""
    assert ensure_trailing_newline("hello") == "hello\n"
    assert ensure_trailing_newline("hello\n") == "hello\n"
    assert ensure_trailing_newline("") == ""


def test_normalize_yaml_frontmatter():
    """Test YAML frontmatter normalization."""
    content = """---
updated: 2025-01-01
title: Test
cast-id: abc-123
---
Body content"""
    
    normalized, fm_dict = normalize_yaml_frontmatter(content)
    
    # Check ephemeral key removed
    assert "updated" not in normalized
    
    # Check keys are sorted
    assert fm_dict is not None
    assert "updated" not in fm_dict
    assert fm_dict["title"] == "Test"
    assert fm_dict["cast-id"] == "abc-123"


def test_normalize_content():
    """Test full content normalization."""
    content = """---
title: Test
updated: now
---
Hello world  \r\n"""
    
    normalized = normalize_content(content)
    
    # Should have normalized line endings, removed trailing spaces,
    # removed ephemeral keys, and ensured trailing newline
    assert "\r" not in normalized
    assert "updated" not in normalized
    assert normalized.endswith("\n")
    assert "  \n" not in normalized


def test_compute_normalized_digest():
    """Test digest computation."""
    content1 = """---
title: Test
updated: 2025-01-01
---
Hello world"""
    
    content2 = """---
updated: 2025-01-02
title: Test
---
Hello world"""
    
    # Different updated values but same normalized content
    digest1 = compute_normalized_digest(content1)
    digest2 = compute_normalized_digest(content2)
    
    assert digest1 == digest2
    assert digest1.startswith("sha256:")


def test_digest_deterministic():
    """Test that digest is deterministic."""
    content = """---
title: Test
tags: [a, b, c]
---
Body content"""
    
    digest1 = compute_normalized_digest(content)
    digest2 = compute_normalized_digest(content)
    
    assert digest1 == digest2