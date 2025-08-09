"""Block-only merging for Cast (preserves YAML, syncs content)."""

import difflib
import re
from typing import Any

import yaml


def extract_content_blocks(content: str) -> tuple[str, str]:
    """Extract YAML frontmatter and body separately.
    
    Args:
        content: Full markdown content
        
    Returns:
        (yaml_section, body_content)
    """
    # Be robust to CRLF frontmatter and normalize once
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    if not content.startswith("---\n"):
        return "", content
    
    # Find the closing ---
    end_match = re.search(r"\n---\n", content[4:])
    if not end_match:
        return "", content
    
    yaml_section = content[:end_match.end() + 4]  # Include closing ---
    body_content = content[end_match.end() + 4:]
    
    return yaml_section, body_content


def merge_content_only(
    base_content: str,
    src_content: str,
    dst_content: str,
    preserve_dst_yaml: bool = True,
) -> tuple[str, list[str]]:
    """Merge only the content blocks, preserving YAML.
    
    Args:
        base_content: Baseline content
        src_content: Source content
        dst_content: Destination content
        preserve_dst_yaml: If True, keep destination YAML unchanged
        
    Returns:
        (merged_content, list_of_conflicts)
    """
    # Extract YAML and body from each version
    base_yaml, base_body = extract_content_blocks(base_content)
    src_yaml, src_body = extract_content_blocks(src_content)
    dst_yaml, dst_body = extract_content_blocks(dst_content)
    
    conflicts = []
    
    # Merge only the body content
    merged_body, body_conflicts = merge_body_content(base_body, src_body, dst_body)
    conflicts.extend(body_conflicts)
    
    # Preserve destination YAML (or source if specified)
    if preserve_dst_yaml:
        final_yaml = dst_yaml
    else:
        final_yaml = src_yaml
    
    # Combine YAML and merged body
    if final_yaml:
        merged_content = final_yaml + merged_body
    else:
        merged_content = merged_body
    
    return merged_content, conflicts


def merge_body_content(
    base_body: str,
    src_body: str,
    dst_body: str,
) -> tuple[str, list[str]]:
    """Merge body content using true 3-way merge.
    
    Args:
        base_body: Baseline body content
        src_body: Source body content
        dst_body: Destination body content
        
    Returns:
        (merged_body, conflicts)
    """
    # If contents are identical, no merge needed
    if src_body == dst_body:
        return src_body, []
    
    # If only source changed
    if dst_body == base_body:
        return src_body, []
    
    # If only destination changed
    if src_body == base_body:
        return dst_body, []
    
    # Both changed - use proper 3-way merge
    from cast.merge_simple import smart_three_way_merge
    
    merged_body, conflicts = smart_three_way_merge(base_body, src_body, dst_body)
    
    return merged_body, conflicts


def split_by_headings(text: str) -> list[tuple[str, str]]:
    """Split text into (heading, content) blocks.
    
    Args:
        text: Body text to split
        
    Returns:
        List of (heading, content) tuples
    """
    blocks = []
    current_heading = ""
    current_content = []
    
    for line in text.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            # Save previous block
            if current_heading or current_content:
                blocks.append((current_heading, "\n".join(current_content)))
            
            # Start new block
            current_heading = line
            current_content = []
        else:
            current_content.append(line)
    
    # Save last block
    if current_heading or current_content:
        blocks.append((current_heading, "\n".join(current_content)))
    
    return blocks


def get_all_headings(
    src_blocks: list[tuple[str, str]],
    dst_blocks: list[tuple[str, str]],
) -> list[str]:
    """Get ordered list of all unique headings."""
    headings = []
    seen = set()
    
    # Add source headings first (preserve order)
    for heading, _ in src_blocks:
        if heading not in seen:
            headings.append(heading)
            seen.add(heading)
    
    # Add any destination-only headings
    for heading, _ in dst_blocks:
        if heading not in seen:
            headings.append(heading)
            seen.add(heading)
    
    return headings


def get_block_content(blocks: list[tuple[str, str]], heading: str) -> str:
    """Get content for a specific heading."""
    for h, content in blocks:
        if h == heading:
            return content
    return ""


def create_conflict_block(src: str, base: str, dst: str) -> str:
    """Create a conflict block with markers."""
    return f"""<<<<<<< SOURCE
{src}
=======
{dst}
>>>>>>> DESTINATION"""


def reconstruct_body(blocks: list[tuple[str, str]]) -> str:
    """Reconstruct body from blocks."""
    lines = []
    
    for heading, content in blocks:
        if heading:
            lines.append(heading)
        if content:
            lines.append(content)
    
    return "\n".join(lines)


def should_sync_file(
    src_index_entry: dict[str, Any],
    dst_index_entry: dict[str, Any] | None,
    src_vault_name: str,
    dst_vault_name: str,
) -> bool:
    """Check if a file should be synced between vaults.
    
    Args:
        src_index_entry: Source file index entry
        dst_index_entry: Destination file index entry (may be None)
        src_vault_name: Name of source vault
        dst_vault_name: Name of destination vault
        
    Returns:
        True if file should be synced
    """
    from cast.cast_vaults import should_sync_to_vault
    
    # Get cast-vaults from source
    cast_vaults = src_index_entry.get("cast_vaults", [])
    
    # Check if destination vault is in the list
    return should_sync_to_vault(cast_vaults, src_vault_name, dst_vault_name)