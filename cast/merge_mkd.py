"""MKD-aware 3-way merge for Cast."""

import difflib
import re
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class MergeRegions:
    """Regions of a markdown file for merging."""
    
    frontmatter: dict[str, Any] | None = None
    frontmatter_text: str = ""
    body: str = ""
    dependencies: list[str] | None = None
    has_end_marker: bool = False


def split_regions(content: str) -> MergeRegions:
    """Split markdown content into mergeable regions."""
    regions = MergeRegions()
    
    # Be robust to CRLF frontmatter and normalize once
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    # Extract frontmatter
    if content.startswith("---\n"):
        end_match = re.search(r"\n---\n", content[4:])
        if end_match:
            fm_text = content[4:end_match.start() + 4]
            regions.frontmatter_text = fm_text
            
            try:
                regions.frontmatter = yaml.safe_load(fm_text) or {}
            except yaml.YAMLError:
                regions.frontmatter = None
            
            content = content[end_match.end() + 4:]
    
    # Look for Dependencies section
    deps_match = re.search(r"^# Dependencies\n(.*?)(?=^# End|$)", content, re.MULTILINE | re.DOTALL)
    
    if deps_match:
        deps_text = deps_match.group(1)
        regions.dependencies = [
            line.strip() 
            for line in deps_text.split("\n") 
            if line.strip() and line.strip().startswith("-")
        ]
        
        # Extract body (before dependencies)
        regions.body = content[:deps_match.start()]
        
        # Check for End marker
        if re.search(r"^# End\s*$", content[deps_match.end():], re.MULTILINE):
            regions.has_end_marker = True
    else:
        # No dependencies section
        regions.body = content
        
        # Still check for End marker
        if re.search(r"^# End\s*$", content, re.MULTILINE):
            regions.has_end_marker = True
            # Remove End marker from body
            regions.body = re.sub(r"^# End\s*$", "", regions.body, flags=re.MULTILINE).rstrip()
    
    return regions


def merge_yaml(
    base: dict[str, Any] | None,
    src: dict[str, Any] | None, 
    dst: dict[str, Any] | None,
    src_mtime: float | None = None,
    dst_mtime: float | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Merge YAML frontmatter using MKD rules.
    
    Returns:
        (merged_dict, list_of_conflicts)
    """
    if base is None:
        base = {}
    if src is None:
        src = {}
    if dst is None:
        dst = {}
    
    merged = {}
    conflicts = []
    
    # Get all keys
    all_keys = set(base.keys()) | set(src.keys()) | set(dst.keys())
    
    for key in all_keys:
        base_val = base.get(key)
        src_val = src.get(key)
        dst_val = dst.get(key)
        
        # Special handling for specific fields
        if key == "tags":
            # Set union for tags
            tags = set()
            if isinstance(src_val, list):
                tags.update(src_val)
            if isinstance(dst_val, list):
                tags.update(dst_val)
            merged[key] = sorted(list(tags))
            
        elif key in ["category", "type"]:
            # Must match
            if src_val != dst_val and src_val is not None and dst_val is not None:
                conflicts.append(f"{key}: '{src_val}' vs '{dst_val}'")
                merged[key] = src_val  # Default to source
            else:
                merged[key] = src_val or dst_val
                
        elif isinstance(base_val, dict) or isinstance(src_val, dict) or isinstance(dst_val, dict):
            # Shallow merge for maps
            map_base = base_val if isinstance(base_val, dict) else {}
            map_src = src_val if isinstance(src_val, dict) else {}
            map_dst = dst_val if isinstance(dst_val, dict) else {}
            
            map_merged = {}
            map_keys = set(map_base.keys()) | set(map_src.keys()) | set(map_dst.keys())
            
            for map_key in map_keys:
                base_map_val = map_base.get(map_key)
                src_map_val = map_src.get(map_key)
                dst_map_val = map_dst.get(map_key)
                
                if src_map_val == dst_map_val:
                    map_merged[map_key] = src_map_val
                elif src_map_val == base_map_val:
                    map_merged[map_key] = dst_map_val
                elif dst_map_val == base_map_val:
                    map_merged[map_key] = src_map_val
                else:
                    # Conflict
                    conflicts.append(f"{key}.{map_key}: conflict")
                    map_merged[map_key] = src_map_val  # Default to source
            
            if map_merged:
                merged[key] = map_merged
                
        else:
            # Scalar values - last writer wins
            if src_val == dst_val:
                merged[key] = src_val
            elif src_val == base_val:
                merged[key] = dst_val
            elif dst_val == base_val:
                merged[key] = src_val
            else:
                # Both changed - use mtime if available
                if src_mtime and dst_mtime:
                    merged[key] = src_val if src_mtime >= dst_mtime else dst_val
                else:
                    merged[key] = src_val  # Default to source
    
    return merged, conflicts


def parse_dependency(dep_line: str) -> tuple[str, str, int, list[str]]:
    """Parse a dependency line into components.
    
    Returns:
        (role, target, depth, tag_selectors)
    """
    # Remove leading dash and whitespace
    dep_line = dep_line.lstrip("- ").strip()
    
    # Extract depth (number of leading spaces/indents)
    depth_match = re.match(r"^(\s*)", dep_line)
    depth = len(depth_match.group(1)) if depth_match else 0
    
    # Parse role and target
    # Format: role:Target Title {tags}
    match = re.match(r"^(\w+):\s*(.+?)(?:\s*\{([^}]+)\})?$", dep_line.strip())
    
    if match:
        role = match.group(1)
        target = match.group(2).strip()
        tags_str = match.group(3)
        
        tags = []
        if tags_str:
            tags = [t.strip() for t in tags_str.split(",")]
        
        return role, target, depth, tags
    
    # Fallback - treat as simple reference
    return "ref", dep_line.strip(), depth, []


def merge_dependencies(
    base: list[str] | None,
    src: list[str] | None,
    dst: list[str] | None,
) -> tuple[list[str], list[str]]:
    """Merge dependencies lists.
    
    Returns:
        (merged_list, conflicts)
    """
    if base is None:
        base = []
    if src is None:
        src = []
    if dst is None:
        dst = []
    
    # Parse all dependencies
    base_deps = {parse_dependency(d): d for d in base}
    src_deps = {parse_dependency(d): d for d in src}
    dst_deps = {parse_dependency(d): d for d in dst}
    
    merged_deps = {}
    conflicts = []
    
    # Get all unique dependencies
    all_deps = set(base_deps.keys()) | set(src_deps.keys()) | set(dst_deps.keys())
    
    for dep_tuple in all_deps:
        role, target, depth, tags = dep_tuple
        
        in_base = dep_tuple in base_deps
        in_src = dep_tuple in src_deps
        in_dst = dep_tuple in dst_deps
        
        # Determine what to do
        if in_src and in_dst:
            # Both have it - check for conflicts
            src_parsed = parse_dependency(src_deps[dep_tuple])
            dst_parsed = parse_dependency(dst_deps[dep_tuple])
            
            if src_parsed[0] != dst_parsed[0]:  # Different roles
                conflicts.append(f"Dependency role conflict for {target}")
                merged_deps[dep_tuple] = src_deps[dep_tuple]
            else:
                # Use max depth
                max_depth = max(src_parsed[2], dst_parsed[2])
                merged_deps[dep_tuple] = f"{'  ' * max_depth}- {role}:{target}"
                
        elif in_src and not in_dst:
            if in_base:
                # Removed in dst, keep removed
                pass
            else:
                # Added in src
                merged_deps[dep_tuple] = src_deps[dep_tuple]
                
        elif in_dst and not in_src:
            if in_base:
                # Removed in src, keep removed
                pass
            else:
                # Added in dst
                merged_deps[dep_tuple] = dst_deps[dep_tuple]
    
    # Sort dependencies by role, target, depth
    sorted_deps = sorted(merged_deps.keys(), key=lambda x: (x[0], x[1].lower(), x[2]))
    merged_list = [merged_deps[d] for d in sorted_deps]
    
    return merged_list, conflicts


def merge_body_blocks(
    base: str,
    src: str,
    dst: str,
) -> tuple[str, list[str]]:
    """Merge body content using heading-block diff3.
    
    Returns:
        (merged_body, conflicts)
    """
    conflicts = []
    
    # Split by top-level headings
    def split_by_headings(text: str) -> list[tuple[str, str]]:
        """Split text into (heading, content) blocks."""
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
    
    base_blocks = split_by_headings(base)
    src_blocks = split_by_headings(src)
    dst_blocks = split_by_headings(dst)
    
    # Create lookup maps
    base_map = {heading: content for heading, content in base_blocks}
    src_map = {heading: content for heading, content in src_blocks}
    dst_map = {heading: content for heading, content in dst_blocks}
    
    # Get all headings
    all_headings = []
    seen = set()
    
    # Preserve order: src headings first, then dst additions
    for heading, _ in src_blocks:
        if heading and heading not in seen:
            all_headings.append(heading)
            seen.add(heading)
    
    for heading, _ in dst_blocks:
        if heading and heading not in seen:
            all_headings.append(heading)
            seen.add(heading)
    
    # Merge each block
    merged_blocks = []
    
    for heading in all_headings:
        base_content = base_map.get(heading, "")
        src_content = src_map.get(heading, "")
        dst_content = dst_map.get(heading, "")
        
        if src_content == dst_content:
            # No conflict
            merged_blocks.append((heading, src_content))
            
        elif src_content == base_content:
            # Only dst changed
            merged_blocks.append((heading, dst_content))
            
        elif dst_content == base_content:
            # Only src changed
            merged_blocks.append((heading, src_content))
            
        else:
            # Both changed - try diff3
            merger = difflib.Differ()
            
            # For now, create conflict markers
            conflict_text = f"<<<<<<< SRC\n{src_content}\n||||||| BASE\n{base_content}\n=======\n{dst_content}\n>>>>>>> DST"
            merged_blocks.append((heading, conflict_text))
            conflicts.append(f"Block conflict in: {heading or 'preface'}")
    
    # Reconstruct body
    merged_lines = []
    for heading, content in merged_blocks:
        if heading:
            merged_lines.append(heading)
        if content:
            merged_lines.append(content)
    
    return "\n".join(merged_lines), conflicts


def perform_mkd_merge(
    base_content: str,
    src_content: str,
    dst_content: str,
    src_mtime: float | None = None,
    dst_mtime: float | None = None,
    ephemeral_keys: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Perform full MKD-aware 3-way merge.
    
    Returns:
        (merged_content, list_of_conflicts)
    """
    # Split into regions
    base_regions = split_regions(base_content)
    src_regions = split_regions(src_content)
    dst_regions = split_regions(dst_content)
    
    all_conflicts = []
    
    # Merge YAML
    merged_yaml, yaml_conflicts = merge_yaml(
        base_regions.frontmatter,
        src_regions.frontmatter,
        dst_regions.frontmatter,
        src_mtime,
        dst_mtime,
    )
    all_conflicts.extend(yaml_conflicts)
    
    # Remove ephemeral keys
    if ephemeral_keys:
        for key in ephemeral_keys:
            merged_yaml.pop(key, None)
    
    # Merge dependencies
    merged_deps, deps_conflicts = merge_dependencies(
        base_regions.dependencies,
        src_regions.dependencies,
        dst_regions.dependencies,
    )
    all_conflicts.extend(deps_conflicts)
    
    # Merge body
    merged_body, body_conflicts = merge_body_blocks(
        base_regions.body,
        src_regions.body,
        dst_regions.body,
    )
    all_conflicts.extend(body_conflicts)
    
    # Reconstruct content
    parts = []
    
    # Add frontmatter
    if merged_yaml:
        yaml_text = yaml.safe_dump(merged_yaml, sort_keys=True, allow_unicode=True)
        parts.append(f"---\n{yaml_text}---")
    
    # Add body
    if merged_body:
        parts.append(merged_body)
    
    # Add dependencies
    if merged_deps:
        parts.append("# Dependencies")
        for dep in merged_deps:
            parts.append(dep)
    
    # Add End marker if needed
    if src_regions.has_end_marker or dst_regions.has_end_marker:
        parts.append("# End")
    
    merged_content = "\n".join(parts)
    
    return merged_content, all_conflicts