#!/usr/bin/env python3
"""Test that push is blocked when conflicts exist."""

import tempfile
from pathlib import Path

from cast.config import GlobalConfig
from cast.index import build_index
from cast.sync_multi import MultiVaultSyncEngine


def test_push_blocked():
    """Test that push is blocked when there are unresolved conflicts."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create two test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        
        for vault in [vault1, vault2]:
            vault.mkdir()
            cast_dir = vault / ".cast"
            cast_dir.mkdir()
            
            # Create config
            config_file = cast_dir / "config.yaml"
            config_file.write_text(f"""cast-version: "1"
vault:
  id: {vault.name}
  root: {vault}
index:
  include:
    - "**/*.md"
  exclude:
    - ".git/**"
    - ".cast/**"
""")
            
            # Create objects and peers dirs
            (cast_dir / "objects").mkdir()
            (cast_dir / "peers").mkdir()
        
        # Register vaults
        global_config = GlobalConfig.load_or_create()
        global_config.register_vault("vault1", str(vault1))
        global_config.register_vault("vault2", str(vault2))
        global_config.save()
        
        # Create initial file in vault1
        test_file1 = vault1 / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content.""")
        
        # Build index
        build_index(vault1, rebuild=True)
        
        # Sync to vault2
        engine = MultiVaultSyncEngine()
        result = engine.sync_all(vault2, apply=True)
        print(f"Initial sync to vault2: {result['status']}")
        
        # Now modify the file differently in each vault
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Modified by vault1.""")
        
        test_file2 = vault2 / "test.md"
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Modified by vault2.""")
        
        # Rebuild indices
        for vault in [vault1, vault2]:
            build_index(vault, rebuild=True)
        
        # Sync from vault2 with force to create conflicts
        print("\n=== Syncing with conflicts ===")
        result = engine.sync_all(vault2, apply=True, force=True)
        print(f"Status: {result['status']}")
        
        # Check push results
        push_results = result.get("push_results", {})
        print(f"Push results: {push_results}")
        
        if isinstance(push_results, dict) and push_results.get("status") == "blocked":
            print(f"✓ Push correctly blocked: {push_results['message']}")
            
            # Check file has conflicts
            content = test_file2.read_text()
            has_conflicts = "<<<<<<< " in content and "=======" in content and ">>>>>>> " in content
            print(f"File has conflict markers: {has_conflicts}")
            
            if has_conflicts:
                print("\n✓ Test passed! Push is blocked when conflicts exist.")
            else:
                print("\n✗ Test failed: No conflict markers found")
        else:
            print(f"\n✗ Test failed: Push was not blocked! Results: {push_results}")


if __name__ == "__main__":
    test_push_blocked()