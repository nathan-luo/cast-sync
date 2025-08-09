"""Tests for block-only content merging."""

import pytest

from cast.merge_blocks import (
    extract_content_blocks,
    merge_content_only,
    merge_body_content,
    split_by_headings,
)


def test_extract_content_blocks():
    """Test extraction of YAML and body."""
    # With YAML
    content1 = """---
title: Test
cast-vaults:
  - vault1 (cast)
---
# Content

Body text"""
    
    yaml_section, body = extract_content_blocks(content1)
    
    assert "title: Test" in yaml_section
    assert "cast-vaults:" in yaml_section
    assert yaml_section.endswith("---\n")
    assert body.startswith("# Content")
    assert "Body text" in body
    
    # Without YAML
    content2 = "# Direct Content\n\nNo frontmatter"
    yaml2, body2 = extract_content_blocks(content2)
    
    assert yaml2 == ""
    assert body2 == content2


def test_merge_content_only():
    """Test merging only body content while preserving YAML."""
    base = """---
title: Original
cast-vaults:
  - vault1 (cast)
---
# Section 1

Original content"""
    
    src = """---
title: Source Title
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
---
# Section 1

Modified content from source"""
    
    dst = """---
title: Destination Title
tags: [local, test]
cast-vaults:
  - vault1 (cast)
---
# Section 1

Original content

# Section 2

New section in destination"""
    
    # Merge with preserve_dst_yaml=True
    merged, conflicts = merge_content_only(base, src, dst, preserve_dst_yaml=True)
    
    # Destination YAML should be preserved
    assert "title: Destination Title" in merged
    assert "tags:" in merged
    
    # Source body changes should be included
    assert "Modified content from source" in merged
    
    # Destination's new section should be included
    assert "Section 2" in merged


def test_merge_body_content_no_conflict():
    """Test body merging without conflicts."""
    base = """# Section 1
Base content

# Section 2
Shared content"""
    
    src = """# Section 1
Modified by source

# Section 2
Shared content"""
    
    dst = """# Section 1
Base content

# Section 2
Shared content

# Section 3
New in destination"""
    
    merged, conflicts = merge_body_content(base, src, dst)
    
    # No conflicts expected
    assert len(conflicts) == 0
    
    # Source change applied
    assert "Modified by source" in merged
    
    # Destination addition included
    assert "Section 3" in merged
    assert "New in destination" in merged


def test_merge_body_content_with_conflict():
    """Test body merging with conflicts."""
    base = """# Section 1
Original content"""
    
    src = """# Section 1
Changed by source"""
    
    dst = """# Section 1
Changed by destination"""
    
    merged, conflicts = merge_body_content(base, src, dst)
    
    # Should have conflict
    assert len(conflicts) == 1
    assert "Section 1" in conflicts[0]
    
    # Should have conflict markers
    assert "<<<<<<< SOURCE" in merged
    assert "Changed by source" in merged
    assert "=======" in merged
    assert "Changed by destination" in merged
    assert ">>>>>>> DESTINATION" in merged


def test_split_by_headings():
    """Test splitting content by top-level headings."""
    content = """Some preface

# First Section
Content of first

## Subsection
Still in first

# Second Section
Content of second"""
    
    blocks = split_by_headings(content)
    
    assert len(blocks) == 3
    
    # Preface (no heading)
    assert blocks[0][0] == ""
    assert "Some preface" in blocks[0][1]
    
    # First section
    assert blocks[1][0] == "# First Section"
    assert "Content of first" in blocks[1][1]
    assert "## Subsection" in blocks[1][1]
    assert "Still in first" in blocks[1][1]
    
    # Second section
    assert blocks[2][0] == "# Second Section"
    assert "Content of second" in blocks[2][1]