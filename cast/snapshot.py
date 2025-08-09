"""Snapshot management for Cast."""

import json
from datetime import datetime
from pathlib import Path

from cast.index import Index
from cast.peers import list_peers, PeerState


def create_snapshot(
    vault_root: Path,
    message: str | None = None,
) -> Path:
    """Create a snapshot of current vault state.
    
    Args:
        vault_root: Vault root directory
        message: Optional snapshot message
        
    Returns:
        Path to created snapshot file
    """
    # Create snapshots directory
    snapshots_dir = vault_root / ".cast" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    # Load current index
    index = Index(vault_root)
    index.load()
    
    # Collect peer summaries
    peer_summaries = {}
    
    for peer_id in list_peers(vault_root):
        peer = PeerState(vault_root, peer_id)
        peer.load()
        
        peer_summaries[peer_id] = {
            "last_sync": peer.data.get("last_sync"),
            "file_count": len(peer.data.get("files", {})),
            "conflict_count": sum(
                1 for f in peer.data.get("files", {}).values()
                if f.get("last_result") == "CONFLICT"
            ),
        }
    
    # Build snapshot data
    snapshot = {
        "timestamp": timestamp,
        "message": message or f"Snapshot at {timestamp}",
        "index": {
            "file_count": len(index.data),
            "total_size": sum(
                e.get("size", 0) for e in index.data.values()
            ),
        },
        "peers": peer_summaries,
        "full_index": index.data,
    }
    
    # Write snapshot
    snapshot_path = snapshots_dir / f"{timestamp}.json"
    
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
    
    return snapshot_path


def list_snapshots(vault_root: Path) -> list[dict]:
    """List all snapshots for a vault.
    
    Returns:
        List of snapshot summaries
    """
    snapshots_dir = vault_root / ".cast" / "snapshots"
    
    if not snapshots_dir.exists():
        return []
    
    snapshots = []
    
    for path in sorted(snapshots_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        
        snapshots.append({
            "path": str(path),
            "timestamp": data.get("timestamp"),
            "message": data.get("message"),
            "file_count": data.get("index", {}).get("file_count", 0),
        })
    
    return snapshots


def restore_snapshot(vault_root: Path, snapshot_path: Path) -> None:
    """Restore vault state from a snapshot.
    
    Note: This only restores Cast metadata, not file contents.
    
    Args:
        vault_root: Vault root directory
        snapshot_path: Path to snapshot file
    """
    with open(snapshot_path) as f:
        snapshot = json.load(f)
    
    # Restore index
    index = Index(vault_root)
    index.data = snapshot.get("full_index", {})
    index.save()
    
    # Note: Peer states are not restored as they represent
    # relationships with external vaults that may have changed