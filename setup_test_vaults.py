#!/usr/bin/env python3
"""Setup test vaults for manual testing."""

from pathlib import Path

from cast.config import GlobalConfig, VaultConfig
from cast.ids import generate_cast_id


def setup_test_vaults():
    """Setup test vaults with sample files."""
    base = Path("vaults")
    
    # Ensure vaults exist
    vault1 = base / "vault1"
    vault2 = base / "vault2"
    
    for vault in [vault1, vault2]:
        if not vault.exists():
            print(f"Creating {vault}")
            vault.mkdir(parents=True)
    
    # Initialize Cast in both vaults with sync rules
    from cast.config import SyncRule
    
    # Vault1 config with sync rules
    vault1_config = VaultConfig.create_default(vault1, "vault1")
    vault1_config.sync_rules = [
        SyncRule(
            id="to-vault2",
            mode="broadcast",
            from_vault="vault1",
            to_vaults=[{"id": "vault2", "path": str(vault2.absolute())}],
            select={"paths_any": ["01 Vault/**/*.md"]},
        )
    ]
    vault1_config.save()
    
    # Vault2 config with sync rules
    vault2_config = VaultConfig.create_default(vault2, "vault2")
    vault2_config.sync_rules = [
        SyncRule(
            id="from-vault1",
            mode="bidirectional",
            from_vault="vault2",
            to_vaults=[{"id": "vault1", "path": str(vault1.absolute())}],
            select={"paths_any": ["01 Vault/**/*.md"]},
        )
    ]
    vault2_config.save()
    
    # Create .cast directories
    for vault in [vault1, vault2]:
        (vault / ".cast" / "objects").mkdir(parents=True, exist_ok=True)
        (vault / ".cast" / "peers").mkdir(parents=True, exist_ok=True)
        (vault / ".cast" / "logs").mkdir(parents=True, exist_ok=True)
        (vault / ".cast" / "locks").mkdir(parents=True, exist_ok=True)
    
    # Setup global config
    global_config = GlobalConfig.load_or_create()
    global_config.vaults = {
        "vault1": str(vault1.absolute()),
        "vault2": str(vault2.absolute()),
    }
    global_config.save()
    print(f"Registered vaults in global config: {global_config.config_path}")
    
    # Create test file in vault1
    test_file = vault1 / "01 Vault" / "test_sync_doc.md"
    if not test_file.exists():
        cast_id = generate_cast_id()
        content = f"""---
cast-id: {cast_id}
cast-type: original
cast-version: 1
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [vault1-local, test]
category: testing
---

# Test Sync Document

This document is set up to sync from vault1 to vault2.

## Content Section

This content should appear in both vaults after sync.

## Local Fields Test

The tags and category fields above are local to vault1 and should NOT sync to vault2.
Only the cast-* fields and this body content should sync.
"""
        test_file.write_text(content)
        print(f"Created test file: {test_file}")
    
    # Add existing file to vault2 if it exists
    existing_file = vault2 / "01 Vault" / "vault2file.md"
    if existing_file.exists():
        # Add cast fields to make it syncable
        content = existing_file.read_text()
        if "cast-id:" not in content:
            cast_id = generate_cast_id()
            new_content = f"""---
cast-id: {cast_id}
cast-type: sync
cast-version: 1
cast-vaults:
  - vault2 (cast)
  - vault1 (sync)
tags: [vault2-local]
---

# Vault2 File

This file originates from vault2."""
            existing_file.write_text(new_content)
            print(f"Updated {existing_file} with cast fields")
    
    print("\nSetup complete! You can now test with:")
    print("  cast vaults                    # List configured vaults")
    print("  cast index vaults/vault1       # Index vault1")
    print("  cast index vaults/vault2       # Index vault2")
    print("  cast plan vault1 vault2        # Plan sync")
    print("  cast sync vault1 vault2 --apply  # Execute sync")


if __name__ == "__main__":
    setup_test_vaults()