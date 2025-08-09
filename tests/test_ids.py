"""Tests for Cast ID management."""

import tempfile
from pathlib import Path

import pytest

from cast.ids import (
    add_cast_id_to_file,
    extract_frontmatter,
    generate_cast_id,
    get_cast_id,
    inject_cast_id,
    is_valid_uuid,
)


def test_is_valid_uuid():
    """Test UUID validation."""
    assert is_valid_uuid("f47ac10b-58cc-4372-a567-0e02b2c3d479")
    assert is_valid_uuid("F47AC10B-58CC-4372-A567-0E02B2C3D479")
    assert not is_valid_uuid("not-a-uuid")
    assert not is_valid_uuid("f47ac10b-58cc-4372-a567")


def test_generate_cast_id():
    """Test cast-id generation."""
    id1 = generate_cast_id()
    id2 = generate_cast_id()
    
    assert is_valid_uuid(id1)
    assert is_valid_uuid(id2)
    assert id1 != id2  # Should be unique


def test_extract_frontmatter():
    """Test frontmatter extraction."""
    # With frontmatter
    content = """---
title: Test
cast-id: abc-123
---
Body content"""
    
    fm_dict, fm_text, body = extract_frontmatter(content)
    
    assert fm_dict is not None
    assert fm_dict["title"] == "Test"
    assert fm_dict["cast-id"] == "abc-123"
    assert body == "Body content"
    
    # Without frontmatter
    content2 = "Just body content"
    fm_dict2, fm_text2, body2 = extract_frontmatter(content2)
    
    assert fm_dict2 is None
    assert fm_text2 == ""
    assert body2 == "Just body content"


def test_inject_cast_id():
    """Test cast-id injection."""
    # Content without frontmatter
    content1 = "# Title\n\nBody content"
    new_id = generate_cast_id()
    result1 = inject_cast_id(content1, new_id)
    
    assert f"cast-id: {new_id}" in result1
    assert result1.startswith("---\n")
    assert "Body content" in result1
    
    # Content with existing frontmatter
    content2 = """---
title: Test
---
Body content"""
    
    result2 = inject_cast_id(content2, new_id)
    assert f"cast-id: {new_id}" in result2
    assert "title: Test" in result2


def test_get_cast_id():
    """Test cast-id extraction from file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
cast-id: f47ac10b-58cc-4372-a567-0e02b2c3d479
title: Test
---
Content""")
        temp_path = Path(f.name)
    
    try:
        cast_id = get_cast_id(temp_path)
        assert cast_id == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    finally:
        temp_path.unlink()


def test_add_cast_id_to_file():
    """Test adding cast-id to a file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test\n\nContent")
        temp_path = Path(f.name)
    
    try:
        # Add cast-id
        result = add_cast_id_to_file(temp_path)
        
        assert result["status"] == "added"
        assert is_valid_uuid(result["uuid"])
        
        # Verify it was written
        cast_id = get_cast_id(temp_path)
        assert cast_id == result["uuid"]
        
        # Try adding again - should skip
        result2 = add_cast_id_to_file(temp_path)
        assert result2["status"] == "exists"
        assert result2["uuid"] == cast_id
        
    finally:
        temp_path.unlink()


def test_add_cast_id_dry_run():
    """Test dry run mode."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test\n\nContent")
        temp_path = Path(f.name)
    
    try:
        # Dry run - should not modify file
        result = add_cast_id_to_file(temp_path, dry_run=True)
        
        assert result["status"] == "would_add"
        assert is_valid_uuid(result["uuid"])
        
        # Verify file was not modified
        cast_id = get_cast_id(temp_path)
        assert cast_id is None
        
    finally:
        temp_path.unlink()