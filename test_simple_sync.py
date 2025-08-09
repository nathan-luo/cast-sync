#!/usr/bin/env python3
"""Simple test for multi-vault sync."""

import json
import tempfile
from pathlib import Path

from cast.config import GlobalConfig
from cast.index import build_index
from cast.plan import create_plan


def test_simple_sync():
    """Test basic sync detection."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create two test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        
        # Initialize vaults manually
        for vault in [vault1, vault2]:
            vault.mkdir()
            cast_dir = vault / ".cast"
            cast_dir.mkdir()
            
            # Create config with proper patterns
            config_file = cast_dir / "config.yaml"
            config_file.write_text(f"""cast-version: "1"
vault:
  id: {vault.name}
  root: {vault}
index:
  include:
    - "01 Vault/**/*.md"
  exclude:
    - ".git/**"
    - ".cast/**"
    - ".obsidian/**"
""")
            
            # Create objects dir
            (cast_dir / "objects").mkdir()
            
            # Create vault dir
            (vault / "01 Vault").mkdir()
        
        # Register vaults
        global_config = GlobalConfig.load_or_create()
        global_config.register_vault("vault1", str(vault1))
        global_config.register_vault("vault2", str(vault2))
        global_config.save()
        
        # Create a test file in vault1
        test_file = vault1 / "01 Vault" / "test.md"
        test_file.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

This is a test.""")
        
        print(f"Test file created: {test_file.exists()}")
        print(f"Test file path: {test_file}")
        print(f"Test file size: {test_file.stat().st_size}")
        
        # Build indices
        print("\nBuilding index for vault1...")
        
        # Debug: check what select_files finds
        from cast.select import select_files
        from cast.config import VaultConfig
        
        config = VaultConfig.load(vault1)
        files = select_files(
            vault1,
            include_patterns=config.include_patterns,
            exclude_patterns=config.exclude_patterns,
        )
        print(f"Files found by select_files: {list(files)}")
        
        # Try indexing manually
        from cast.index import index_file
        from cast.ids import get_cast_id
        
        cast_id = get_cast_id(test_file)
        print(f"Cast ID from file: {cast_id}")
        
        result = index_file(test_file, vault1, config)
        print(f"Manual index result: {result}")
        
        build_index(vault1, rebuild=True)
        
        print("Building index for vault2...")
        build_index(vault2, rebuild=True)
        
        # Check indices
        index1 = vault1 / ".cast" / "index.json"
        index2 = vault2 / ".cast" / "index.json"
        
        print(f"\nVault1 index exists: {index1.exists()}")
        if index1.exists():
            data = json.loads(index1.read_text())
            print(f"Index keys: {list(data.keys())}")
            if 'files' in data:
                print(f"Vault1 files: {len(data['files'])} files")
                for cast_id, entry in data['files'].items():
                    print(f"  - {cast_id}: {entry['path']}")
            else:
                print(f"Vault1 entries: {len(data)} entries")
                for cast_id, entry in list(data.items())[:5]:
                    print(f"  - {cast_id}: {entry}")
        
        print(f"\nVault2 index exists: {index2.exists()}")
        if index2.exists():
            data = json.loads(index2.read_text())
            if 'files' in data:
                print(f"Vault2 files: {len(data['files'])} files")
            else:
                print(f"Vault2 entries: {len(data)} entries")
        
        # Create plan from vault1 to vault2
        print("\n=== Creating plan from vault1 to vault2 ===")
        plan = create_plan("vault1", "vault2")
        
        print(f"Plan summary: {plan['summary']}")
        print(f"Actions: {len(plan['actions'])} actions")
        for action in plan['actions']:
            print(f"  - {action['type']}: {action.get('source_path', action.get('dest_path'))}")
        
        # Now test multi-vault sync
        from cast.sync_multi import MultiVaultSyncEngine
        
        print("\n=== Testing multi-vault sync from vault2 ===")
        engine = MultiVaultSyncEngine()
        
        result = engine.sync_all(vault2, apply=False)
        print(f"Status: {result['status']}")
        print(f"Pull results: {result['pull_results']}")
        
        # Apply the sync
        print("\n=== Applying sync ===")
        result = engine.sync_all(vault2, apply=True)
        print(f"Status: {result['status']}")
        print(f"Applied changes: {result.get('applied_changes', 0)}")
        
        # Check if file was created
        synced_file = vault2 / "01 Vault" / "test.md"
        print(f"\nFile synced to vault2: {synced_file.exists()}")
        if synced_file.exists():
            print(f"Content preview: {synced_file.read_text()[:100]}...")
        
        print("\n✓ Test completed!")


if __name__ == "__main__":
    test_simple_sync()