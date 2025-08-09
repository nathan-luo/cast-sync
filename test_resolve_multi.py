#!/usr/bin/env python3
"""Test conflict resolution with multi-vault sync."""

import tempfile
from pathlib import Path

from cast.config import GlobalConfig
from cast.index import build_index
from cast.sync_multi import MultiVaultSyncEngine
from cast.resolve import ConflictResolver


def test_resolve_with_multi_sync():
    """Test resolving conflicts created by multi-vault sync."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create three test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        vault3 = tmpdir / "vault3"
        
        for vault in [vault1, vault2, vault3]:
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
        global_config.register_vault("vault3", str(vault3))
        global_config.save()
        
        # Create initial file in vault1
        test_file1 = vault1 / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content from vault1.""")
        
        # Build index
        build_index(vault1, rebuild=True)
        
        # Sync to vault2 and vault3
        engine = MultiVaultSyncEngine()
        
        print("=== Initial sync to vault2 ===")
        result = engine.sync_all(vault2, apply=True)
        print(f"Status: {result['status']}")
        
        print("\n=== Initial sync to vault3 ===")
        result = engine.sync_all(vault3, apply=True)
        print(f"Status: {result['status']}")
        
        # Now modify the file differently in each vault
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content from vault1.

Added in vault1.""")
        
        test_file2 = vault2 / "test.md"
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content from vault1.

Added in vault2.""")
        
        test_file3 = vault3 / "test.md"
        test_file3.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content from vault1.

Added in vault3.""")
        
        # Rebuild indices
        for vault in [vault1, vault2, vault3]:
            build_index(vault, rebuild=True)
        
        # Now sync from vault3 - should create conflicts
        print("\n=== Sync from vault3 (should create conflicts) ===")
        
        # First check what plans would be created
        from cast.plan import create_plan
        plan1 = create_plan("vault1", "vault3")
        plan2 = create_plan("vault2", "vault3")
        print(f"Plan from vault1 to vault3: {plan1['summary']}")
        print(f"Plan from vault2 to vault3: {plan2['summary']}")
        
        result = engine.sync_all(vault3, apply=True, force=True)
        print(f"Status: {result['status']}")
        print(f"Conflicts reported: {len(result.get('conflicts', []))}")
        if result.get('applied_changes'):
            print(f"Applied changes: {result['applied_changes']}")
        
        # Check if conflict markers exist in vault3
        content = test_file3.read_text()
        has_conflicts = "<<<<<<< " in content and "=======" in content and ">>>>>>> " in content
        print(f"File has conflict markers: {has_conflicts}")
        
        print(f"\nFile content:\n{content}\n")
        
        # Test resolve
        print("\n=== Testing resolve ===")
        resolver = ConflictResolver()
        
        # List conflicts
        conflict_files = resolver.list_conflicts(vault3)
        print(f"Found {len(conflict_files)} files with conflicts")
        
        # Auto-resolve using source
        if conflict_files:
            results = resolver.resolve(
                vault3,
                files=[conflict_files[0]],
                interactive=False,
                auto_mode="source"
            )
            
            print(f"Resolution results: {results}")
            
            # Check resolved content
            resolved_content = test_file3.read_text()
            has_conflicts_after = "<<<<<<< " in resolved_content
            print(f"File has conflicts after resolve: {has_conflicts_after}")
            
            if not has_conflicts_after:
                print(f"\nResolved content preview:\n{resolved_content[:300]}...")
                print("\n✓ Conflict resolution successful!")
            else:
                print("\n✗ Conflicts still present after resolution")
        else:
            print("No conflicts found to resolve")


if __name__ == "__main__":
    test_resolve_with_multi_sync()