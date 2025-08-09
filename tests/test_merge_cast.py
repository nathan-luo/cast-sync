"""Tests for Cast-aware content merging."""

import pytest

from cast.merge_cast import (
    CAST_FIELDS,
    extract_yaml_and_body,
    merge_cast_content,
    merge_body_blocks,
)


def test_cast_fields_defined():
    """Test that cast fields are properly defined."""
    assert "cast-id" in CAST_FIELDS
    assert "cast-vaults" in CAST_FIELDS
    assert "cast-type" in CAST_FIELDS
    assert "cast-version" in CAST_FIELDS
    assert "cast-codebases" in CAST_FIELDS
    
    # Non-cast fields should not be included
    assert "tags" not in CAST_FIELDS
    assert "category" not in CAST_FIELDS


def test_extract_yaml_and_body():
    """Test extraction of YAML dict and body."""
    content = """---
cast-id: abc-123
cast-type: original
tags: [local, test]
---
# Content

Body text"""
    
    yaml_dict, yaml_text, body = extract_yaml_and_body(content)
    
    assert yaml_dict is not None
    assert yaml_dict["cast-id"] == "abc-123"
    assert yaml_dict["cast-type"] == "original"
    assert yaml_dict["tags"] == ["local", "test"]
    
    assert body.startswith("# Content")
    assert "Body text" in body


def test_merge_cast_content_preserves_local_fields():
    """Test that merge syncs cast-* fields but preserves local fields."""
    base = """---
cast-id: abc-123
cast-type: sync
cast-vaults:
  - vault1 (cast)
tags: [original]
---
# Section 1

Base content"""
    
    src = """---
cast-id: abc-123
cast-type: original
cast-version: 1
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [source-tag]
category: source-cat
---
# Section 1

Updated content from source"""
    
    dst = """---
cast-id: abc-123
cast-type: sync
cast-vaults:
  - vault1 (cast)
tags: [dest-tag, local]
category: dest-cat
custom_field: destination-only
---
# Section 1

Base content"""
    
    merged, conflicts = merge_cast_content(base, src, dst)
    
    # Parse merged YAML
    yaml_dict, _, merged_body = extract_yaml_and_body(merged)
    
    # Cast fields should come from source
    assert yaml_dict["cast-id"] == "abc-123"
    assert yaml_dict["cast-type"] == "original"  # From source
    assert yaml_dict["cast-version"] == "1"  # From source
    assert "vault2 (sync)" in yaml_dict["cast-vaults"]  # From source
    
    # Local fields should come from destination
    assert yaml_dict["tags"] == ["dest-tag", "local"]  # From dest
    assert yaml_dict["category"] == "dest-cat"  # From dest
    assert yaml_dict["custom_field"] == "destination-only"  # From dest
    
    # Body should be from source
    assert "Updated content from source" in merged_body


def test_merge_body_no_conflict():
    """Test body merging without conflicts."""
    base = "# Section\nOriginal"
    src = "# Section\nModified"
    dst = "# Section\nOriginal\n\n# New Section\nAdded"
    
    merged, conflicts = merge_body_blocks(base, src, dst)
    
    assert len(conflicts) == 0
    assert "Modified" in merged
    assert "New Section" in merged


def test_merge_body_with_conflict():
    """Test body merging with conflicts."""
    base = "# Section\nOriginal"
    src = "# Section\nSource change"
    dst = "# Section\nDest change"
    
    merged, conflicts = merge_body_blocks(base, src, dst)
    
    assert len(conflicts) == 1
    assert "<<<<<<< SOURCE" in merged
    assert "Source change" in merged
    assert "Dest change" in merged
    assert ">>>>>>> DESTINATION" in merged


def test_merge_cast_fields_ordering():
    """Test that cast-* fields appear first in merged YAML."""
    base = """---
tags: [test]
cast-id: abc-123
---
Content"""
    
    src = """---
category: source
cast-id: abc-123
cast-type: original
cast-version: 1
tags: [source]
---
Content"""
    
    dst = """---
tags: [dest]
custom: value
cast-id: abc-123
---
Content"""
    
    merged, _ = merge_cast_content(base, src, dst)
    
    # Cast fields should appear before other fields
    lines = merged.split('\n')
    
    # Find the YAML section
    yaml_lines = []
    in_yaml = False
    for line in lines:
        if line == "---":
            if not in_yaml:
                in_yaml = True
            else:
                break
        elif in_yaml:
            yaml_lines.append(line)
    
    # Check that cast- fields come first
    cast_seen = False
    non_cast_seen = False
    
    for line in yaml_lines:
        if line.strip():
            if line.startswith('cast-'):
                cast_seen = True
                # Should not have seen non-cast fields yet
                assert not non_cast_seen, "Cast fields should come before non-cast fields"
            elif ':' in line and not line.startswith(' '):
                non_cast_seen = True