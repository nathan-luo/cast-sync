"""Sync planning for Cast."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cast.config import GlobalConfig, VaultConfig
from cast.index import Index
from cast.normalize import compute_normalized_digest
from cast.objects import ObjectStore
from cast.peers import PeerState, get_common_baseline
from cast.select import select_by_rule


class ActionType(Enum):
    """Types of sync actions."""
    
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    MERGE = "MERGE"
    CONFLICT = "CONFLICT"
    SKIP = "SKIP"
    RENAME = "RENAME"
    DELETE = "DELETE"


@dataclass
class SyncAction:
    """A planned sync action."""
    
    cast_id: str
    action_type: ActionType
    source_path: Path | None = None
    dest_path: Path | None = None
    source_digest: str | None = None
    dest_digest: str | None = None
    base_digest: str | None = None
    reason: str = ""
    mode: str = "broadcast"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "cast_id": self.cast_id,
            "type": self.action_type.value,
            "source_path": str(self.source_path) if self.source_path else None,
            "dest_path": str(self.dest_path) if self.dest_path else None,
            "source_digest": self.source_digest,
            "dest_digest": self.dest_digest,
            "base_digest": self.base_digest,
            "reason": self.reason,
            "mode": self.mode,
        }


def detect_action(
    cast_id: str,
    src_entry: dict[str, Any] | None,
    dst_entry: dict[str, Any] | None,
    src_peer: PeerState,
    dst_peer: PeerState,
    mode: str,
    src_vault_path: Path | None = None,
    dst_vault_path: Path | None = None,
) -> SyncAction:
    """Detect the appropriate sync action for a file.
    
    Args:
        cast_id: File identifier
        src_entry: Source index entry
        dst_entry: Destination index entry
        src_peer: Source's peer state for destination
        dst_peer: Destination's peer state for source
        mode: Sync mode (broadcast, bidirectional, mirror)
        src_vault_path: Source vault root path (for reading actual content)
        dst_vault_path: Destination vault root path (for reading actual content)
        
    Returns:
        SyncAction to perform
    """
    # File doesn't exist in destination
    if not dst_entry:
        return SyncAction(
            cast_id=cast_id,
            action_type=ActionType.CREATE,
            source_path=Path(src_entry["path"]) if src_entry else None,
            source_digest=src_entry["digest"] if src_entry else None,
            reason="File does not exist in destination",
            mode=mode,
        )
    
    # File exists in both
    src_digest = src_entry["digest"] if src_entry else None
    dst_digest = dst_entry["digest"] if dst_entry else None
    
    # Check if already in sync (body content is identical)
    if src_digest == dst_digest:
        return SyncAction(
            cast_id=cast_id,
            action_type=ActionType.SKIP,
            source_path=Path(src_entry["path"]) if src_entry else None,
            dest_path=Path(dst_entry["path"]) if dst_entry else None,
            reason="Files are identical",
            mode=mode,
        )
    
    # Get baseline
    base_digest = get_common_baseline(src_peer, dst_peer, cast_id)
    
    # For more accurate conflict detection, we need to check if only local fields changed
    # This is especially important in broadcast mode where destination shouldn't have body changes
    def has_body_changed(vault_path: Path, entry: dict[str, Any], base_digest: str | None) -> bool:
        """Check if body content actually changed vs just local fields."""
        if not base_digest or not vault_path:
            return True  # Conservative: assume changed if no baseline
        
        # The digest in the index is already body-only, so we can directly compare
        return entry["digest"] != base_digest
    
    # Mode-specific logic
    if mode == "mirror":
        # Always overwrite in mirror mode
        return SyncAction(
            cast_id=cast_id,
            action_type=ActionType.UPDATE,
            source_path=Path(src_entry["path"]) if src_entry else None,
            dest_path=Path(dst_entry["path"]) if dst_entry else None,
            source_digest=src_digest,
            dest_digest=dst_digest,
            reason="Mirror mode - force overwrite",
            mode=mode,
        )
    
    elif mode == "broadcast":
        # Check if destination body content changed since baseline
        dst_body_changed = has_body_changed(dst_vault_path, dst_entry, base_digest)
        
        if base_digest and dst_body_changed:
            # Destination body changed - conflict
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.CONFLICT,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                source_digest=src_digest,
                dest_digest=dst_digest,
                base_digest=base_digest,
                reason="Destination modified since last sync (broadcast mode)",
                mode=mode,
            )
        else:
            # Safe to update (dst only has local field changes or no changes)
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.UPDATE,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                source_digest=src_digest,
                dest_digest=dst_digest,
                reason="Broadcast update",
                mode=mode,
            )
    
    elif mode == "bidirectional":
        # Check what changed
        src_changed = base_digest and src_digest != base_digest
        dst_changed = base_digest and dst_digest != base_digest
        
        if not base_digest:
            # No baseline - try to detect if one is just an append of the other
            # This handles the common case where files are edited independently but compatibly
            if src_vault_path and dst_vault_path:
                src_file = src_vault_path / src_entry["path"]
                dst_file = dst_vault_path / dst_entry["path"]
                
                if src_file.exists() and dst_file.exists():
                    src_content = src_file.read_text(encoding="utf-8")
                    dst_content = dst_file.read_text(encoding="utf-8")
                    
                    # Extract just the body for comparison
                    from cast.ids import extract_frontmatter
                    _, _, src_body = extract_frontmatter(src_content)
                    _, _, dst_body = extract_frontmatter(dst_content)
                    
                    # Check if one is a prefix of the other (simple append case)
                    src_body_stripped = src_body.strip()
                    dst_body_stripped = dst_body.strip()
                    
                    if src_body_stripped.startswith(dst_body_stripped):
                        # Source has appended to dest - use source
                        return SyncAction(
                            cast_id=cast_id,
                            action_type=ActionType.UPDATE,
                            source_path=Path(src_entry["path"]) if src_entry else None,
                            dest_path=Path(dst_entry["path"]) if dst_entry else None,
                            source_digest=src_digest,
                            dest_digest=dst_digest,
                            reason="Source appears to be destination + additions",
                            mode=mode,
                        )
                    elif dst_body_stripped.startswith(src_body_stripped):
                        # Dest has appended to source - skip (will sync other direction)
                        return SyncAction(
                            cast_id=cast_id,
                            action_type=ActionType.SKIP,
                            source_path=Path(src_entry["path"]) if src_entry else None,
                            dest_path=Path(dst_entry["path"]) if dst_entry else None,
                            reason="Destination appears to be source + additions",
                            mode=mode,
                        )
            
            # Can't auto-resolve - conflict
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.CONFLICT,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                source_digest=src_digest,
                dest_digest=dst_digest,
                reason="No common baseline and changes incompatible",
                mode=mode,
            )
        
        elif src_changed and not dst_changed:
            # Only source changed
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.UPDATE,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                source_digest=src_digest,
                dest_digest=dst_digest,
                base_digest=base_digest,
                reason="Source changed, destination unchanged",
                mode=mode,
            )
        
        elif dst_changed and not src_changed:
            # Only destination changed - skip
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.SKIP,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                reason="Destination changed, source unchanged",
                mode=mode,
            )
        
        elif src_changed and dst_changed:
            # Both changed - merge
            return SyncAction(
                cast_id=cast_id,
                action_type=ActionType.MERGE,
                source_path=Path(src_entry["path"]) if src_entry else None,
                dest_path=Path(dst_entry["path"]) if dst_entry else None,
                source_digest=src_digest,
                dest_digest=dst_digest,
                base_digest=base_digest,
                reason="Both sides changed - 3-way merge",
                mode=mode,
            )
    
    # Default to skip
    return SyncAction(
        cast_id=cast_id,
        action_type=ActionType.SKIP,
        reason="Unknown sync scenario",
        mode=mode,
    )


def create_plan(
    source: str,
    dest: str,
    rule_id: str | None = None,
) -> dict[str, Any]:
    """Create a sync plan between two vaults.
    
    Args:
        source: Source vault ID from global config
        dest: Destination vault ID from global config
        rule_id: Specific rule to use (optional)
        
    Returns:
        Plan dictionary with actions and metadata
    """
    # Resolve vault paths from IDs
    global_config = GlobalConfig.load()
    
    src_path = global_config.get_vault_path(source)
    if not src_path or not src_path.exists():
        raise ValueError(f"Source vault '{source}' not found in global config or path doesn't exist")
    
    dst_path = global_config.get_vault_path(dest)
    if not dst_path or not dst_path.exists():
        raise ValueError(f"Destination vault '{dest}' not found in global config or path doesn't exist")
    
    # Auto-index both vaults to ensure up-to-date
    from cast.index import build_index
    build_index(src_path, rebuild=False)
    build_index(dst_path, rebuild=False)
    
    # Load configurations
    src_config = VaultConfig.load(src_path)
    dst_config = VaultConfig.load(dst_path)
    
    # Load indices
    src_index = Index(src_path)
    src_index.load()
    
    dst_index = Index(dst_path)
    dst_index.load()
    
    # Load peer states
    src_peer = PeerState(src_path, dst_config.vault_id)
    src_peer.load()
    
    dst_peer = PeerState(dst_path, src_config.vault_id)
    dst_peer.load()
    
    # If a rule is specified, filter source index by rule.select
    scan_index = src_index.data
    if rule_id:
        rule = next((r for r in src_config.sync_rules if r.id == rule_id), None)
        if not rule:
            raise ValueError(f"Rule '{rule_id}' not found in {src_config.config_path}")
        from cast.select import select_by_rule
        scan_index = select_by_rule(scan_index, {"select": rule.select})
    
    # Plan actions based on cast-vaults field
    actions = []
    
    # Check all files in source index
    for cast_id, src_entry in scan_index.items():
        # Check if this file should sync to destination vault
        cast_vaults = src_entry.get("cast_vaults", [])
        from cast.cast_vaults import parse_cast_vaults, should_sync_to_vault, VaultRole
        
        # Skip quickly if dest isn't listed / direction not allowed
        if not should_sync_to_vault(cast_vaults, src_config.vault_id, dst_config.vault_id):
            continue
        
        roles = dict(parse_cast_vaults(cast_vaults))
        src_role = roles.get(src_config.vault_id)
        dst_role = roles.get(dst_config.vault_id)
        if not src_role or not dst_role:
            continue  # must have both ends declared
        
        # Map roles to a mode
        if src_role == VaultRole.CAST and dst_role == VaultRole.SYNC:
            dest_mode = "broadcast"
        else:
            # SYNC→CAST or SYNC→SYNC
            dest_mode = "bidirectional"
        
        # Skip if file doesn't sync to this destination
        if not dest_mode:
            continue
        
        dst_entry = dst_index.get_entry(cast_id)
        
        action = detect_action(
            cast_id=cast_id,
            src_entry=src_entry,
            dst_entry=dst_entry,
            src_peer=src_peer,
            dst_peer=dst_peer,
            mode=dest_mode,
            src_vault_path=src_path,
            dst_vault_path=dst_path,
        )
        
        actions.append(action)
    
    # Build plan
    plan = {
        "source": {
            "vault_id": src_config.vault_id,
            "path": str(src_path),
        },
        "dest": {
            "vault_id": dst_config.vault_id,
            "path": str(dst_path),
        },
        "actions": [a.to_dict() for a in actions],
        "summary": {
            "total": len(actions),
            "create": sum(1 for a in actions if a.action_type == ActionType.CREATE),
            "update": sum(1 for a in actions if a.action_type == ActionType.UPDATE),
            "merge": sum(1 for a in actions if a.action_type == ActionType.MERGE),
            "conflict": sum(1 for a in actions if a.action_type == ActionType.CONFLICT),
            "skip": sum(1 for a in actions if a.action_type == ActionType.SKIP),
        },
    }
    
    return plan