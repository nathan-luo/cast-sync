"""Cast-aware merging that syncs cast-* fields and body content."""

import re
from typing import Any

import yaml


# Cast fields that should be synced across vaults
CAST_FIELDS = {
    "cast-id",
    "cast-vaults", 
    "cast-type",
    "cast-version",
    "cast-codebases",
}


def extract_yaml_and_body(content: str) -> tuple[dict[str, Any] | None, str, str]:
    """Extract YAML frontmatter and body from markdown content.
    
    Returns:
        (yaml_dict, yaml_text, body)
    """
    # Be robust to CRLF frontmatter and normalize once
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    if not content.startswith("---\n"):
        return None, "", content
    
    # Find the closing ---
    end_match = re.search(r"\n---\n", content[4:])
    if not end_match:
        return None, "", content
    
    yaml_text = content[4:end_match.start() + 4]
    body = content[end_match.end() + 4:]
    
    try:
        yaml_dict = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return None, yaml_text, body
    
    return yaml_dict, yaml_text, body


def merge_cast_content(
    base_content: str,
    src_content: str,
    dst_content: str,
) -> tuple[str, list[str]]:
    """Merge Cast content: sync cast-* fields and body, preserve local fields.
    
    Args:
        base_content: Baseline content
        src_content: Source content
        dst_content: Destination content
        
    Returns:
        (merged_content, list_of_conflicts)
    """
    # Extract YAML and body from each version
    base_yaml, _, base_body = extract_yaml_and_body(base_content)
    src_yaml, _, src_body = extract_yaml_and_body(src_content)
    dst_yaml, _, dst_body = extract_yaml_and_body(dst_content)
    
    if base_yaml is None:
        base_yaml = {}
    if src_yaml is None:
        src_yaml = {}
    if dst_yaml is None:
        dst_yaml = {}
    
    conflicts = []
    
    # Merge YAML: cast-* fields from source, local fields from destination
    merged_yaml = {}
    
    # Start with destination's local fields
    for key, value in dst_yaml.items():
        if not key.startswith("cast-"):
            merged_yaml[key] = value
    
    # Add/update cast-* fields from source
    for key in CAST_FIELDS:
        if key in src_yaml:
            merged_yaml[key] = src_yaml[key]
    
    # Merge body content
    merged_body, body_conflicts = merge_body_blocks(base_body, src_body, dst_body)
    conflicts.extend(body_conflicts)
    
    # Reconstruct content
    if merged_yaml:
        # Order keys: cast-id first, then other cast-* fields, then others
        ordered_yaml = {}
        
        # Ensure cast-id is first
        if "cast-id" in merged_yaml:
            ordered_yaml["cast-id"] = merged_yaml["cast-id"]
        
        # Add other cast fields in standard order
        cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
        for field in cast_field_order:
            if field in merged_yaml:
                ordered_yaml[field] = merged_yaml[field]
        
        # Add any remaining cast-* fields
        for key in CAST_FIELDS:
            if key in merged_yaml and key not in ordered_yaml:
                ordered_yaml[key] = merged_yaml[key]
        
        # Add non-cast fields
        for key, value in merged_yaml.items():
            if not key.startswith('cast-'):
                ordered_yaml[key] = value
        
        yaml_text = yaml.safe_dump(ordered_yaml, sort_keys=False, allow_unicode=True)
        merged_content = f"---\n{yaml_text}---\n{merged_body}"
    else:
        merged_content = merged_body
    
    return merged_content, conflicts


def merge_body_blocks(
    base_body: str,
    src_body: str,
    dst_body: str,
) -> tuple[str, list[str]]:
    """Merge body content using heading-aware diff.
    
    Args:
        base_body: Baseline body
        src_body: Source body
        dst_body: Destination body
        
    Returns:
        (merged_body, conflicts)
    """
    conflicts = []
    
    # Simple cases
    if src_body == dst_body:
        return src_body, []
    
    if dst_body == base_body:
        return src_body, []
    
    if src_body == base_body:
        return dst_body, []
    
    # Both changed - split by headings for granular merge
    base_blocks = split_by_headings(base_body)
    src_blocks = split_by_headings(src_body)
    dst_blocks = split_by_headings(dst_body)
    
    merged_blocks = []
    all_headings = get_all_headings(src_blocks, dst_blocks)
    
    for heading in all_headings:
        base_block = get_block_content(base_blocks, heading)
        src_block = get_block_content(src_blocks, heading)
        dst_block = get_block_content(dst_blocks, heading)
        
        if src_block == dst_block:
            merged_blocks.append((heading, src_block))
        elif src_block == base_block:
            merged_blocks.append((heading, dst_block))
        elif dst_block == base_block:
            merged_blocks.append((heading, src_block))
        else:
            # Conflict
            conflict_text = f"""<<<<<<< SOURCE
{src_block}
=======
{dst_block}
>>>>>>> DESTINATION"""
            merged_blocks.append((heading, conflict_text))
            conflicts.append(f"Conflict in: {heading or 'preface'}")
    
    # Reconstruct body
    lines = []
    for heading, content in merged_blocks:
        if heading:
            lines.append(heading)
        if content:
            lines.append(content)
    
    return '\n'.join(lines), conflicts


def split_by_headings(text: str) -> list[tuple[str, str]]:
    """Split text by top-level headings."""
    blocks = []
    current_heading = ""
    current_content = []
    
    for line in text.split('\n'):
        if line.startswith('# ') and not line.startswith('## '):
            # Save previous block
            if current_heading or current_content:
                blocks.append((current_heading, '\n'.join(current_content)))
            # Start new block
            current_heading = line
            current_content = []
        else:
            current_content.append(line)
    
    # Save last block
    if current_heading or current_content:
        blocks.append((current_heading, '\n'.join(current_content)))
    
    return blocks


def get_all_headings(
    src_blocks: list[tuple[str, str]], 
    dst_blocks: list[tuple[str, str]]
) -> list[str]:
    """Get all unique headings preserving order."""
    headings = []
    seen = set()
    
    for heading, _ in src_blocks:
        if heading not in seen:
            headings.append(heading)
            seen.add(heading)
    
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


def should_sync_file(
    src_entry: dict[str, Any],
    dst_entry: dict[str, Any] | None,
    src_vault: str,
    dst_vault: str,
) -> bool:
    """Check if file should sync between vaults based on cast-vaults.
    
    Args:
        src_entry: Source file index entry
        dst_entry: Destination file index entry (may be None)
        src_vault: Source vault name
        dst_vault: Destination vault name
        
    Returns:
        True if file should sync
    """
    from cast.cast_vaults import should_sync_to_vault
    
    # Get cast-vaults from source
    cast_vaults = src_entry.get("cast_vaults", [])
    
    # Check if destination vault is listed
    return should_sync_to_vault(cast_vaults, src_vault, dst_vault)


def get_title_from_path(file_path: str) -> str:
    """Extract title from file path (filename without extension)."""
    from pathlib import Path
    return Path(file_path).stem