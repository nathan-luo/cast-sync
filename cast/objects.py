"""Object store for baseline content."""

from pathlib import Path


class ObjectStore:
    """Content-addressed store for baseline objects."""
    
    def __init__(self, vault_root: Path):
        """Initialize object store for a vault."""
        self.vault_root = vault_root
        self.store_path = vault_root / ".cast" / "objects"
        self.store_path.mkdir(parents=True, exist_ok=True)
    
    def get_object_path(self, digest: str) -> Path:
        """Get path for an object by digest."""
        # Remove algorithm prefix if present
        if ":" in digest:
            _, hex_digest = digest.split(":", 1)
        else:
            hex_digest = digest
        
        return self.store_path / hex_digest
    
    def exists(self, digest: str) -> bool:
        """Check if an object exists."""
        return self.get_object_path(digest).exists()
    
    def read(self, digest: str) -> str | None:
        """Read an object by digest."""
        path = self.get_object_path(digest)
        
        if not path.exists():
            return None
        
        return path.read_text(encoding="utf-8")
    
    def write(self, content: str, digest: str) -> None:
        """Write an object with given digest.
        
        Note: Caller is responsible for ensuring digest matches content.
        """
        path = self.get_object_path(digest)
        
        # Write atomically
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
    
    def delete(self, digest: str) -> bool:
        """Delete an object.
        
        Returns:
            True if object was deleted, False if it didn't exist
        """
        path = self.get_object_path(digest)
        
        if path.exists():
            path.unlink()
            return True
        
        return False
    
    def list_objects(self) -> list[str]:
        """List all object digests in store."""
        objects = []
        
        for path in self.store_path.glob("*"):
            if path.is_file() and not path.name.endswith(".tmp"):
                # Reconstruct digest with sha256 prefix
                objects.append(f"sha256:{path.name}")
        
        return sorted(objects)
    
    def cleanup_orphans(self, referenced_digests: set[str]) -> list[str]:
        """Remove objects not referenced by any peer state.
        
        Args:
            referenced_digests: Set of digests still in use
            
        Returns:
            List of removed object digests
        """
        removed = []
        
        for digest in self.list_objects():
            if digest not in referenced_digests:
                self.delete(digest)
                removed.append(digest)
        
        return removed
    
    def size_bytes(self) -> int:
        """Calculate total size of object store in bytes."""
        total = 0
        
        for path in self.store_path.glob("*"):
            if path.is_file() and not path.name.endswith(".tmp"):
                total += path.stat().st_size
        
        return total