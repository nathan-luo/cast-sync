"""Index management for Cast vaults."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cast.config import VaultConfig
from cast.ids import get_cast_id, extract_frontmatter
from cast.normalize import compute_normalized_digest
from cast.select import select_files


class Index:
    """Vault index manager."""
    
    def __init__(self, vault_root: Path):
        """Initialize index for a vault."""
        self.vault_root = vault_root
        self.index_path = vault_root / ".cast" / "index.json"
        self.data: dict[str, dict[str, Any]] = {}
        
    def load(self) -> None:
        """Load index from disk."""
        if self.index_path.exists():
            with open(self.index_path) as f:
                self.data = json.load(f)
    
    def save(self) -> None:
        """Save index to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write atomically
        temp_path = self.index_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(self.data, f, indent=2, sort_keys=True)
        temp_path.replace(self.index_path)
    
    def get_entry(self, cast_id: str) -> dict[str, Any] | None:
        """Get index entry by cast-id."""
        return self.data.get(cast_id)
    
    def add_entry(self, cast_id: str, entry: dict[str, Any]) -> None:
        """Add or update an index entry."""
        self.data[cast_id] = entry
    
    def remove_entry(self, cast_id: str) -> None:
        """Remove an index entry."""
        self.data.pop(cast_id, None)
    
    def find_by_path(self, path: Path) -> tuple[str, dict[str, Any]] | None:
        """Find entry by file path."""
        rel_path = path.relative_to(self.vault_root)
        
        for cast_id, entry in self.data.items():
            if Path(entry["path"]) == rel_path:
                return cast_id, entry
        
        return None


def index_file(file_path: Path, vault_root: Path, config: VaultConfig) -> dict[str, Any] | None:
    """Index a single markdown file.
    
    Returns:
        Index entry or None if file should be skipped
    """
    # Read content
    content = file_path.read_text(encoding="utf-8")
    
    # Extract metadata
    fm_dict, _, body = extract_frontmatter(content)
    if fm_dict is None:
        fm_dict = {}
    
    # For multi-vault sync, we index all files with cast-id
    # The cast-vaults field is optional and used for filtering
    
    # Get or create cast-id
    cast_id = get_cast_id(file_path)
    if not cast_id:
        # Skip files without cast-id for now
        # Could auto-add here if needed
        return None
    else:
        # Check if cast-id needs to be reordered to first position
        from cast.ids import ensure_cast_id_first
        reordered_content = ensure_cast_id_first(content)
        if reordered_content != content:
            # Write back the reordered content
            file_path.write_text(reordered_content, encoding="utf-8")
            content = reordered_content
            fm_dict, _, body = extract_frontmatter(content)
    
    # Compute normalized digest (of body only, not YAML)
    body_digest = compute_normalized_digest(body, body_only=True)
    
    # Get file stats
    stat = file_path.stat()
    
    # Build entry
    entry = {
        "title": file_path.stem,  # Title from filename
        "path": str(file_path.relative_to(vault_root)),
        "digest": body_digest,  # Digest of body only
        "cast_type": fm_dict.get("cast-type", ""),  # Cast document type
        "cast_vaults": fm_dict.get("cast-vaults", []),  # Store cast-vaults
        "cast_version": fm_dict.get("cast-version", "1"),  # Cast protocol version
        "category": fm_dict.get("category", ""),  # Local field
        "tags": fm_dict.get("tags", []),  # Local field
        "updated": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "size": stat.st_size,
    }
    
    return {cast_id: entry}


def build_index(vault_root: Path, rebuild: bool = False) -> dict[str, dict[str, Any]]:
    """Build or update the vault index.
    
    Args:
        vault_root: Root directory of the vault
        rebuild: Force full rebuild instead of incremental
        
    Returns:
        The complete index data
    """
    # Load config
    try:
        config = VaultConfig.load(vault_root)
    except FileNotFoundError:
        config = VaultConfig.create_default(vault_root)
    
    # Load existing index
    index = Index(vault_root)
    if not rebuild:
        index.load()
    
    # Track seen files for cleanup
    seen_ids = set()
    
    # Find all markdown files
    files = select_files(
        vault_root,
        include_patterns=config.include_patterns,
        exclude_patterns=config.exclude_patterns,
    )
    
    for file_path in files:
        if file_path.suffix != ".md":
            continue
        
        # Check if we need to reindex
        if not rebuild:
            existing = index.find_by_path(file_path)
            if existing:
                cast_id, entry = existing
                stat = file_path.stat()
                
                # Skip if unchanged (mtime and size match)
                if (entry.get("size") == stat.st_size and
                    entry.get("updated") == datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")):
                    seen_ids.add(cast_id)
                    continue
        
        # Index the file
        result = index_file(file_path, vault_root, config)
        if result:
            cast_id = list(result.keys())[0]
            entry = list(result.values())[0]
            index.add_entry(cast_id, entry)
            seen_ids.add(cast_id)
    
    # Remove entries for deleted files
    if not rebuild:
        deleted_ids = set(index.data.keys()) - seen_ids
        for cast_id in deleted_ids:
            index.remove_entry(cast_id)
    
    # Save index
    index.save()
    
    return index.data


def validate_index(vault_root: Path) -> list[dict[str, Any]]:
    """Validate index consistency.
    
    Returns:
        List of validation issues found
    """
    issues = []
    
    # Load index
    index = Index(vault_root)
    index.load()
    
    # Load config once
    config = VaultConfig.load(vault_root)
    
    # Check each entry
    for cast_id, entry in index.data.items():
        file_path = vault_root / entry["path"]
        
        # Check file exists
        if not file_path.exists():
            issues.append({
                "type": "missing_file",
                "cast_id": cast_id,
                "path": entry["path"],
            })
            continue
        
        # Check cast-id matches
        actual_id = get_cast_id(file_path)
        if actual_id != cast_id:
            issues.append({
                "type": "id_mismatch",
                "cast_id": cast_id,
                "actual_id": actual_id,
                "path": entry["path"],
            })
        
        # Check digest matches (body-only, same as index_file)
        content = file_path.read_text(encoding="utf-8")
        from cast.ids import extract_frontmatter
        _, _, body = extract_frontmatter(content)
        actual_digest = compute_normalized_digest(body, body_only=True)
        
        if actual_digest != entry["digest"]:
            issues.append({
                "type": "digest_mismatch",
                "cast_id": cast_id,
                "path": entry["path"],
                "expected": entry["digest"],
                "actual": actual_digest,
            })
    
    return issues