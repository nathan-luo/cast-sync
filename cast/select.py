"""File selection and filtering for Cast."""

import fnmatch
from pathlib import Path

import pathspec


def create_pathspec(patterns: list[str]) -> pathspec.PathSpec:
    """Create a PathSpec from glob patterns."""
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def select_files(
    root: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[Path]:
    """Select files matching include patterns and not matching exclude patterns.
    
    Args:
        root: Root directory to search
        include_patterns: Glob patterns to include
        exclude_patterns: Glob patterns to exclude
        
    Returns:
        List of matching file paths
    """
    if include_patterns is None:
        include_patterns = ["**/*"]
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    # Create pathspecs
    include_spec = create_pathspec(include_patterns)
    exclude_spec = create_pathspec(exclude_patterns)
    
    selected = []
    
    # Walk the directory tree
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        
        # Get relative path
        rel_path = path.relative_to(root)
        rel_str = str(rel_path)
        
        # Check include patterns
        if not include_spec.match_file(rel_str):
            continue
        
        # Check exclude patterns
        if exclude_spec.match_file(rel_str):
            continue
        
        selected.append(path)
    
    return sorted(selected)


def select_by_rule(
    index_data: dict[str, dict],
    rule: dict,
) -> dict[str, dict]:
    """Select index entries based on sync rule criteria.
    
    Args:
        index_data: Full index data (cast-id -> entry)
        rule: Selection rule with criteria
        
    Returns:
        Filtered index data
    """
    selected = {}
    
    select_criteria = rule.get("select", {})
    
    # Path patterns
    if "paths_any" in select_criteria:
        path_patterns = select_criteria["paths_any"]
        path_spec = create_pathspec(path_patterns)
    else:
        path_spec = None
    
    # Type filter
    types_filter = select_criteria.get("types", None)
    
    # Category filter  
    categories_filter = select_criteria.get("categories", None)
    
    # Tag filter
    tags_any = select_criteria.get("tags_any", None)
    tags_all = select_criteria.get("tags_all", None)
    
    for cast_id, entry in index_data.items():
        # Check path pattern
        if path_spec and not path_spec.match_file(entry["path"]):
            continue
        
        # Check type
        if types_filter and entry.get("cast_type") not in types_filter:
            continue
        
        # Check category
        if categories_filter and entry.get("category") not in categories_filter:
            continue
        
        # Check tags_any (at least one tag must match)
        if tags_any:
            entry_tags = set(entry.get("tags", []))
            if not entry_tags.intersection(tags_any):
                continue
        
        # Check tags_all (all specified tags must be present)
        if tags_all:
            entry_tags = set(entry.get("tags", []))
            if not set(tags_all).issubset(entry_tags):
                continue
        
        selected[cast_id] = entry
    
    return selected


def is_hub_file(file_path: Path, index_entry: dict | None = None) -> bool:
    """Check if a file is a hub (folder note).
    
    Args:
        file_path: Path to the file
        index_entry: Optional index entry for the file
        
    Returns:
        True if file is a hub
    """
    # Check by type in index
    if index_entry and index_entry.get("cast_type") == "Hub":
        return True
    
    # Check by naming convention (folder name == file name)
    if file_path.stem == file_path.parent.name:
        return True
    
    return False


def filter_hubs(
    index_data: dict[str, dict],
    include_hubs: bool = False,
) -> dict[str, dict]:
    """Filter hub files from index data.
    
    Args:
        index_data: Full index data
        include_hubs: Whether to include hub files
        
    Returns:
        Filtered index data
    """
    if include_hubs:
        return index_data
    
    filtered = {}
    
    for cast_id, entry in index_data.items():
        # Skip hubs
        if entry.get("cast_type") == "Hub":
            continue
        
        # Check naming convention
        path = Path(entry["path"])
        if path.stem == path.parent.name:
            continue
        
        filtered[cast_id] = entry
    
    return filtered