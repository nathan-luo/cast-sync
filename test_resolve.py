#!/usr/bin/env python3
"""Test the improved conflict resolution system."""

import shutil
from pathlib import Path

from cast.config import GlobalConfig, SyncRule, VaultConfig
from cast.sync import SyncEngine
from cast.resolve import ConflictResolver


def setup_test_vaults():
    """Set up test vaults with a conflict."""
    print("Setting up test vaults...")
    
    # Clean up
    base = Path("resolve_test")
    if base.exists():
        shutil.rmtree(base)
    
    # Create vaults
    vault1 = base / "vault1"
    vault2 = base / "vault2"
    
    for vault in [vault1, vault2]:
        (vault / "01 Vault").mkdir(parents=True)
        (vault / ".cast" / "objects").mkdir(parents=True)
        (vault / ".cast" / "peers").mkdir(parents=True)
        (vault / ".cast" / "logs").mkdir(parents=True)
        (vault / ".cast" / "locks").mkdir(parents=True)
        (vault / ".cast" / "index.json").write_text("{}")
    
    # Configure vaults
    vault1_config = VaultConfig.create_default(vault1, "vault1")
    vault1_config.sync_rules = [
        SyncRule(
            id="to-vault2",
            mode="broadcast",
            from_vault="vault1",
            to_vaults=[{"id": "vault2", "path": str(vault2.absolute())}],
            select={"paths_any": ["**/*.md"]},
        ),
    ]
    vault1_config.save()
    
    vault2_config = VaultConfig.create_default(vault2, "vault2")
    vault2_config.save()
    
    # Update global config
    global_config = GlobalConfig.load_or_create()
    global_config.vaults = {
        "vault1": str(vault1.absolute()),
        "vault2": str(vault2.absolute()),
    }
    global_config.save()
    
    return vault1, vault2


def create_conflict():
    """Create a conflict situation."""
    print("\nCreating conflict situation...")
    
    vault1, vault2 = setup_test_vaults()
    
    # Create initial file
    file1 = vault1 / "01 Vault" / "test_doc.md"
    initial_content = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [test]
---

# Test Document

This is the original content.

## Section 1

Some initial text here.

## Section 2

More content in section 2."""
    
    file1.write_text(initial_content)
    
    # Initial sync
    print("Performing initial sync...")
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    file2 = vault2 / "01 Vault" / "test_doc.md"
    
    # Wait a moment to ensure different timestamps
    import time
    time.sleep(0.1)
    
    # Now modify both files differently
    print("Creating conflicting changes...")
    
    # Vault1 changes - read current content to preserve cast-id
    vault1_current = file1.read_text()
    vault1_modified = vault1_current.replace(
        "This is the original content.",
        "This is the UPDATED content from vault1."
    ).replace(
        "Some initial text here.",
        "Modified text from vault1 in section 1."
    )
    file1.write_text(vault1_modified)
    
    # Vault2 changes - read current content to preserve cast-id
    vault2_current = file2.read_text()
    vault2_modified = vault2_current.replace(
        "This is the original content.",
        "This is the MODIFIED content from vault2."
    ).replace(
        "More content in section 2.",
        "Changed content in section 2 from vault2."
    )
    file2.write_text(vault2_modified)
    
    # Try to sync - will create conflict
    print("Syncing with conflicts...")
    try:
        results = engine.sync("vault1", "vault2", apply=True)
        print(f"Sync completed without error: {results}")
    except ValueError as e:
        print(f"Conflict detected: {e}")
        # Force sync to create conflict file
        print("Force syncing to create conflict file...")
        results = engine.sync("vault1", "vault2", apply=True, force=True)
        
        conflicts = [r for r in results if r["action"] == "CONFLICT"]
        if conflicts:
            print(f"✓ Created {len(conflicts)} conflict file(s)")
            for r in results:
                print(f"  - {r['action']}: {r.get('file', 'unknown')}")
        else:
            print("✗ No conflicts in results")
            print(f"Results: {results}")
    
    return vault2


def test_list_conflicts():
    """Test listing conflicts."""
    print("\n" + "="*60)
    print("TEST: List Conflicts")
    print("="*60)
    
    vault2 = create_conflict()
    
    # List conflicts
    print("\nListing conflicts...")
    resolver = ConflictResolver()
    conflict_files = resolver.list_conflicts(vault2)
    
    if conflict_files:
        print(f"✓ Found {len(conflict_files)} conflict file(s)")
    else:
        print("✗ No conflicts found")
    
    return vault2


def test_resolve_non_interactive():
    """Test non-interactive resolution."""
    print("\n" + "="*60)
    print("TEST: Non-Interactive Resolution")
    print("="*60)
    
    vault2 = create_conflict()
    
    # Resolve automatically (prefer source)
    print("\nResolving conflicts automatically (prefer source)...")
    resolver = ConflictResolver()
    results = resolver.resolve(vault2, interactive=False, auto_mode="source")
    
    if results and results[0]["resolved"]:
        print(f"✓ Conflict resolved: {results[0]['target']}")
        
        # Check resolved file
        resolved_file = vault2 / results[0]["target"]
        if resolved_file.exists():
            content = resolved_file.read_text()
            if "UPDATED content from vault1" in content:
                print("✓ Source version was used")
            else:
                print("✗ Source version not found")
            
            # Check conflict markers removed
            if "<<<<<<< SOURCE" not in content:
                print("✓ Conflict markers removed")
            else:
                print("✗ Conflict markers still present")
            
            # Check conflict file removed
            conflict_files = list((vault2 / "01 Vault").glob("*.conflicted-*.md"))
            if len(conflict_files) == 0:
                print("✓ Conflict file removed")
            else:
                print("✗ Conflict file still exists")
    else:
        print("✗ Resolution failed")


def main():
    """Run all tests."""
    print("\nCONFLICT RESOLUTION TEST SUITE")
    print("="*60)
    
    # Test 1: List conflicts
    test_list_conflicts()
    
    # Test 2: Non-interactive resolution
    test_resolve_non_interactive()
    
    print("\n" + "="*60)
    print("✓ All tests completed")
    print("\nNOTE: To test interactive resolution, run:")
    print("  1. python test_resolve.py  (to create conflicts)")
    print("  2. cast conflicts vault2    (to list conflicts)")
    print("  3. cast resolve vault2      (to resolve interactively)")


if __name__ == "__main__":
    # First create a conflict for manual testing
    vault2 = create_conflict()
    print(f"\n✓ Created test conflict in: {vault2}")
    print("\nYou can now test the commands:")
    print(f"  cast conflicts {vault2}")
    print(f"  cast resolve {vault2}")
    
    # Also run automated tests
    main()