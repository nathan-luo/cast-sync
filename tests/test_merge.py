"""Tests for MKD-aware merging."""

import pytest

from cast.merge_mkd import (
    merge_dependencies,
    merge_yaml,
    merge_body_blocks,
    parse_dependency,
    perform_mkd_merge,
    split_regions,
)


def test_split_regions():
    """Test splitting content into regions."""
    content = """---
title: Test
---
# Introduction

Body content

# Dependencies
- ref:Other Page
- child:Sub Page

# End"""
    
    regions = split_regions(content)
    
    assert regions.frontmatter is not None
    assert regions.frontmatter["title"] == "Test"
    assert "# Introduction" in regions.body
    assert regions.dependencies is not None
    assert len(regions.dependencies) == 2
    assert regions.has_end_marker


def test_parse_dependency():
    """Test dependency parsing."""
    role, target, depth, tags = parse_dependency("- ref:Other Page")
    assert role == "ref"
    assert target == "Other Page"
    assert depth == 0
    assert tags == []
    
    role2, target2, depth2, tags2 = parse_dependency("  - child:Sub Page {tag1, tag2}")
    assert role2 == "child"
    assert target2 == "Sub Page"
    assert tags2 == ["tag1", "tag2"]


def test_merge_yaml_tags():
    """Test YAML tag merging (set union)."""
    base = {"tags": ["a", "b"]}
    src = {"tags": ["a", "b", "c"]}
    dst = {"tags": ["a", "d"]}
    
    merged, conflicts = merge_yaml(base, src, dst)
    
    assert set(merged["tags"]) == {"a", "b", "c", "d"}
    assert len(conflicts) == 0


def test_merge_yaml_type_conflict():
    """Test YAML type/category conflicts."""
    base = {"type": "Note", "category": "draft"}
    src = {"type": "Spec", "category": "draft"}
    dst = {"type": "Note", "category": "final"}
    
    merged, conflicts = merge_yaml(base, src, dst)
    
    # Type conflict
    assert "type" in str(conflicts)
    # Category changed but no conflict (scalar last-writer-wins)
    assert merged["category"] in ["draft", "final"]


def test_merge_dependencies_union():
    """Test dependency merging (union)."""
    base = ["- ref:Page A", "- ref:Page B"]
    src = ["- ref:Page A", "- ref:Page B", "- ref:Page C"]
    dst = ["- ref:Page A", "- ref:Page D"]
    
    merged, conflicts = merge_dependencies(base, src, dst)
    
    # Should have union: A, C, D (B was removed by dst)
    targets = []
    for dep in merged:
        _, target, _, _ = parse_dependency(dep)
        targets.append(target)
    
    assert "Page A" in targets
    assert "Page C" in targets
    assert "Page D" in targets
    assert "Page B" not in targets  # Removed in dst


def test_merge_body_blocks():
    """Test heading-block merging."""
    base = """# Section 1
Original content

# Section 2
Base content"""
    
    src = """# Section 1
Modified by source

# Section 2
Base content"""
    
    dst = """# Section 1
Original content

# Section 2
Modified by dest

# Section 3
New in dest"""
    
    merged, conflicts = merge_body_blocks(base, src, dst)
    
    # Section 1: conflict (both changed)
    # Section 2: dst wins (only dst changed)
    # Section 3: included (new in dst)
    
    assert "Modified by dest" in merged
    assert "Section 3" in merged
    assert len(conflicts) > 0  # Section 1 conflict


def test_perform_mkd_merge_no_conflict():
    """Test full merge without conflicts."""
    base = """---
title: Test
tags: [a, b]
---
# Content

Original body"""
    
    src = """---
title: Test
tags: [a, b, c]
---
# Content

Modified body"""
    
    dst = """---
title: Test
tags: [a, b]
---
# Content

Original body

# New Section

Added in dest"""
    
    merged, conflicts = perform_mkd_merge(base, src, dst)
    
    assert len(conflicts) == 0
    assert "tags:" in merged
    assert "c" in merged  # Tag from src
    assert "Modified body" in merged  # Body from src
    assert "New Section" in merged  # Section from dst