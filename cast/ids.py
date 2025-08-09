"""Cast ID (UUID) management."""

import re
import uuid
from pathlib import Path
from typing import Any

import yaml


CAST_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    return bool(CAST_ID_PATTERN.match(value))


def generate_cast_id() -> str:
    """Generate a new cast-id (UUID v4)."""
    return str(uuid.uuid4())


def extract_frontmatter(content: str) -> tuple[dict[str, Any] | None, str, str]:
    """Extract YAML frontmatter from markdown content.
    
    Returns:
        (frontmatter_dict, frontmatter_text, body)
    """
    # Defensive check: ensure content is a string
    if not isinstance(content, str):
        raise TypeError(f"extract_frontmatter expects a string, got {type(content)}: {content!r}")
    
    # Be robust to CRLF frontmatter and normalize once
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    if not content.startswith("---\n"):
        return None, "", content
    
    # Find the closing ---
    end_match = re.search(r"\n---\n", content[4:])
    if not end_match:
        return None, "", content
    
    fm_text = content[4:end_match.start() + 4]
    body = content[end_match.end() + 4:]
    
    try:
        fm_dict = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None, fm_text, body
    
    return fm_dict, fm_text, body


def inject_cast_id(content: str, cast_id: str) -> str:
    """Inject a cast-id into markdown content, ensuring it's the first field."""
    fm_dict, fm_text, body = extract_frontmatter(content)
    
    if fm_dict is None:
        # No frontmatter, create one
        fm_dict = {}
    
    # Create ordered dict with cast-id first
    ordered_dict = {"cast-id": cast_id}
    
    # Add other cast-* fields in a specific order
    cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
    for field in cast_field_order:
        if field in fm_dict:
            ordered_dict[field] = fm_dict[field]
    
    # Add remaining fields (non-cast fields)
    for key, value in fm_dict.items():
        if key not in ordered_dict and not key.startswith("cast-"):
            ordered_dict[key] = value
    
    # Add any remaining cast-* fields not in our standard order
    for key, value in fm_dict.items():
        if key not in ordered_dict and key.startswith("cast-"):
            ordered_dict[key] = value
    
    # Reconstruct content
    fm_yaml = yaml.safe_dump(ordered_dict, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_yaml}---\n{body}"


def ensure_cast_id_first(content: str) -> str:
    """Ensure cast-id is the first field in YAML frontmatter."""
    # Defensive check: ensure content is a string
    if not isinstance(content, str):
        raise TypeError(f"ensure_cast_id_first expects a string, got {type(content)}: {content!r}")
    
    fm_dict, _, body = extract_frontmatter(content)
    
    if not fm_dict or "cast-id" not in fm_dict:
        return content  # No frontmatter or no cast-id, return as-is
    
    # Create ordered dict with cast-id first
    cast_id = fm_dict["cast-id"]
    ordered_dict = {"cast-id": cast_id}
    
    # Add other cast-* fields in standard order
    cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
    for field in cast_field_order:
        if field in fm_dict:
            ordered_dict[field] = fm_dict[field]
    
    # Add remaining non-cast fields
    for key, value in fm_dict.items():
        if key not in ordered_dict and not key.startswith("cast-"):
            ordered_dict[key] = value
    
    # Add any remaining cast-* fields not in standard order
    for key, value in fm_dict.items():
        if key not in ordered_dict and key.startswith("cast-"):
            ordered_dict[key] = value
    
    # Reconstruct content
    fm_yaml = yaml.safe_dump(ordered_dict, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_yaml}---\n{body}"


def get_cast_id(file_path: Path) -> str | None:
    """Extract cast-id from a markdown file."""
    if not file_path.exists() or not file_path.suffix == ".md":
        return None
    
    content = file_path.read_text(encoding="utf-8")
    fm_dict, _, _ = extract_frontmatter(content)
    
    if fm_dict and "cast-id" in fm_dict:
        cast_id = fm_dict["cast-id"]
        if is_valid_uuid(str(cast_id)):
            return str(cast_id)
    
    return None


def add_cast_id_to_file(file_path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Add a cast-id to a file if it doesn't have one.
    
    Returns:
        Dictionary with status and details
    """
    result = {
        "path": file_path,
        "status": "skipped",
        "uuid": None,
    }
    
    # Check if file already has cast-id
    existing_id = get_cast_id(file_path)
    if existing_id:
        result["status"] = "exists"
        result["uuid"] = existing_id
        return result
    
    # Generate new cast-id
    new_id = generate_cast_id()
    result["uuid"] = new_id
    
    if not dry_run:
        # Read content
        content = file_path.read_text(encoding="utf-8")
        
        # Inject cast-id
        new_content = inject_cast_id(content, new_id)
        
        # Write back atomically
        temp_path = file_path.with_suffix(".tmp")
        temp_path.write_text(new_content, encoding="utf-8")
        temp_path.replace(file_path)
        
        result["status"] = "added"
    else:
        result["status"] = "would_add"
    
    return result


def add_cast_ids(vault_root: Path, dry_run: bool = False) -> list[dict[str, Any]]:
    """Add cast-ids to all markdown files in vault.
    
    Returns:
        List of results for each file processed
    """
    from cast.config import VaultConfig
    from cast.select import select_files
    
    # Load vault config
    try:
        config = VaultConfig.load(vault_root)
    except FileNotFoundError:
        # Use defaults if no config
        config = VaultConfig.create_default(vault_root)
    
    # Find all markdown files
    files = select_files(
        vault_root,
        include_patterns=config.include_patterns,
        exclude_patterns=config.exclude_patterns,
    )
    
    results = []
    for file_path in files:
        if file_path.suffix == ".md":
            result = add_cast_id_to_file(file_path, dry_run=dry_run)
            results.append(result)
    
    return results


def find_duplicates(vault_root: Path) -> dict[str, list[Path]]:
    """Find files with duplicate cast-ids.
    
    Returns:
        Dictionary mapping cast-id to list of paths with that ID
    """
    from cast.config import VaultConfig
    from cast.select import select_files
    
    # Load vault config
    try:
        config = VaultConfig.load(vault_root)
    except FileNotFoundError:
        config = VaultConfig.create_default(vault_root)
    
    # Find all markdown files
    files = select_files(
        vault_root,
        include_patterns=config.include_patterns,
        exclude_patterns=config.exclude_patterns,
    )
    
    # Collect cast-ids
    id_to_paths: dict[str, list[Path]] = {}
    
    for file_path in files:
        if file_path.suffix == ".md":
            cast_id = get_cast_id(file_path)
            if cast_id:
                if cast_id not in id_to_paths:
                    id_to_paths[cast_id] = []
                id_to_paths[cast_id].append(file_path)
    
    # Filter to only duplicates
    duplicates = {
        cast_id: paths
        for cast_id, paths in id_to_paths.items()
        if len(paths) > 1
    }
    
    return duplicates