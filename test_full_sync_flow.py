#!/usr/bin/env python3
"""Test full sync flow including push, peer states, and object store."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.config import GlobalConfig
from cast.index import build_index
from cast.objects import ObjectStore
from cast.peers import PeerState


def test_full_sync_flow():
    """Test that sync properly pushes, tracks peers, and stores objects."""
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create three test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        vault3 = tmpdir / "vault3"
        
        for vault in [vault1, vault2, vault3]:
            vault.mkdir()
            result = runner.invoke(app, ["init", str(vault), "--id", vault.name])
            assert result.exit_code == 0
        
        # Create initial file in vault1
        (vault1 / "01 Vault").mkdir()
        test_file1 = vault1 / "01 Vault" / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Content from vault1.""")
        
        # Build index and sync from vault1 (should push to vault2 and vault3)
        build_index(vault1, rebuild=True)
        
        print("=== Sync from vault1 (should push to vault2 and vault3) ===")
        result = runner.invoke(app, ["sync", str(vault1)])
        print(result.output)
        assert result.exit_code == 0
        
        # Check that files were created in vault2 and vault3
        test_file2 = vault2 / "01 Vault" / "test.md"
        test_file3 = vault3 / "01 Vault" / "test.md"
        
        print(f"\nFile exists in vault2: {test_file2.exists()}")
        print(f"File exists in vault3: {test_file3.exists()}")
        
        if test_file2.exists():
            print(f"vault2 content preview: {test_file2.read_text()[:100]}...")
        if test_file3.exists():
            print(f"vault3 content preview: {test_file3.read_text()[:100]}...")
        
        # Check peer states in vault1
        print("\n=== Peer states in vault1 ===")
        for peer_file in (vault1 / ".cast" / "peers").glob("*.json"):
            peer = PeerState(vault1, peer_file.stem)
            peer.load()
            print(f"{peer_file.stem}: {len(peer.data['files'])} files tracked, last_sync={peer.data['last_sync']}")
            if peer.data['files']:
                for cast_id, info in list(peer.data['files'].items())[:2]:
                    print(f"  - {cast_id}: {info}")
        
        # Check object store in vault1
        print("\n=== Object store in vault1 ===")
        objects = ObjectStore(vault1)
        obj_count = 0
        for obj_file in (vault1 / ".cast" / "objects").rglob("*"):
            if obj_file.is_file():
                obj_count += 1
                if obj_count <= 3:
                    print(f"  - {obj_file.name}: {obj_file.stat().st_size} bytes")
        print(f"Total objects: {obj_count}")
        
        # Now modify file in vault2 and sync (should pull to vault1 and push to vault3)
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Updated from vault2.""")
        
        build_index(vault2, rebuild=True)
        
        print("\n=== Sync from vault2 after modification ===")
        result = runner.invoke(app, ["sync", str(vault2)])
        print(result.output)
        assert result.exit_code == 0
        
        # Check that changes propagated
        print(f"\nvault1 content after sync: {test_file1.read_text()[:100]}...")
        print(f"vault3 content after sync: {test_file3.read_text()[:100]}...")
        
        # Check peer states again
        print("\n=== Final peer states in vault2 ===")
        for peer_file in (vault2 / ".cast" / "peers").glob("*.json"):
            peer = PeerState(vault2, peer_file.stem)
            peer.load()
            print(f"{peer_file.stem}: {len(peer.data['files'])} files tracked")
        
        # Check object store grew
        print("\n=== Final object store in vault2 ===")
        obj_count = 0
        for obj_file in (vault2 / ".cast" / "objects").rglob("*"):
            if obj_file.is_file():
                obj_count += 1
        print(f"Total objects: {obj_count}")
        
        # Summary
        all_synced = (
            test_file1.exists() and 
            test_file2.exists() and 
            test_file3.exists() and
            "Updated from vault2" in test_file1.read_text() and
            "Updated from vault2" in test_file3.read_text()
        )
        
        if all_synced:
            print("\n✓ Test passed! Full sync flow works correctly.")
        else:
            print("\n✗ Test failed: Not all vaults were properly synced.")


if __name__ == "__main__":
    test_full_sync_flow()