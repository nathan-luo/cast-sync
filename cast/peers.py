"""Peer state management for Cast."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class PeerState:
    """Manages sync state with a peer vault."""
    
    def __init__(self, vault_root: Path, peer_id: str):
        """Initialize peer state manager."""
        self.vault_root = vault_root
        self.peer_id = peer_id
        self.state_path = vault_root / ".cast" / "peers" / f"{peer_id}.json"
        self.data: dict[str, Any] = {
            "peer_id": peer_id,
            "last_sync": None,
            "files": {},
        }
    
    def load(self) -> None:
        """Load peer state from disk."""
        if self.state_path.exists():
            with open(self.state_path) as f:
                self.data = json.load(f)
    
    def save(self) -> None:
        """Save peer state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write atomically
        temp_path = self.state_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(self.data, f, indent=2, sort_keys=True)
        temp_path.replace(self.state_path)
    
    def get_file_state(self, cast_id: str) -> dict[str, Any] | None:
        """Get sync state for a file."""
        return self.data["files"].get(cast_id)
    
    def update_file_state(
        self,
        cast_id: str,
        base_obj: str | None = None,
        source_digest: str | None = None,
        dest_digest: str | None = None,
        dest_path: str | None = None,
        last_result: str | None = None,
    ) -> None:
        """Update sync state for a file."""
        if cast_id not in self.data["files"]:
            self.data["files"][cast_id] = {}
        
        state = self.data["files"][cast_id]
        
        if base_obj is not None:
            state["base_obj"] = base_obj
        
        if source_digest is not None:
            state["source_digest"] = source_digest
        
        if dest_digest is not None:
            state["dest_digest"] = dest_digest
        
        if dest_path is not None:
            state["dest_path"] = dest_path
        
        if last_result is not None:
            state["last_result"] = last_result
            state["last_at"] = datetime.utcnow().isoformat() + "Z"
    
    def remove_file_state(self, cast_id: str) -> None:
        """Remove sync state for a file."""
        self.data["files"].pop(cast_id, None)
    
    def update_sync_time(self) -> None:
        """Update last sync timestamp."""
        self.data["last_sync"] = datetime.utcnow().isoformat() + "Z"
    
    def get_base_digest(self, cast_id: str) -> str | None:
        """Get baseline digest for a file."""
        state = self.get_file_state(cast_id)
        if state:
            return state.get("base_obj")
        return None
    
    def get_all_base_digests(self) -> set[str]:
        """Get all baseline digests referenced in this peer state."""
        digests = set()
        
        for file_state in self.data["files"].values():
            if "base_obj" in file_state:
                digests.add(file_state["base_obj"])
        
        return digests


def get_common_baseline(
    src_peer: PeerState,
    dst_peer: PeerState,
    cast_id: str,
) -> str | None:
    """Find common baseline between two peer states.
    
    Args:
        src_peer: Source vault's peer state for destination
        dst_peer: Destination vault's peer state for source
        cast_id: File identifier
        
    Returns:
        Common baseline digest or None
    """
    # Check source's record of last sync with dest
    src_state = src_peer.get_file_state(cast_id)
    
    # Check dest's record of last sync with source
    dst_state = dst_peer.get_file_state(cast_id)
    
    # If both have the same baseline, use it
    if src_state and dst_state:
        src_base = src_state.get("base_obj")
        dst_base = dst_state.get("base_obj")
        
        if src_base == dst_base:
            return src_base
    
    # Otherwise, no common baseline
    return None


def list_peers(vault_root: Path) -> list[str]:
    """List all peer IDs for a vault."""
    peers_dir = vault_root / ".cast" / "peers"
    
    if not peers_dir.exists():
        return []
    
    peers = []
    for path in peers_dir.glob("*.json"):
        if not path.name.endswith(".tmp"):
            peers.append(path.stem)
    
    return sorted(peers)


def cleanup_peer_state(vault_root: Path, active_ids: set[str]) -> list[str]:
    """Remove file states for non-existent files.
    
    Args:
        vault_root: Vault root directory
        active_ids: Set of cast-ids that still exist
        
    Returns:
        List of removed cast-ids
    """
    removed = []
    
    for peer_id in list_peers(vault_root):
        peer = PeerState(vault_root, peer_id)
        peer.load()
        
        # Find orphaned entries
        orphaned = set(peer.data["files"].keys()) - active_ids
        
        # Remove them
        for cast_id in orphaned:
            peer.remove_file_state(cast_id)
            removed.append(cast_id)
        
        if orphaned:
            peer.save()
    
    return removed