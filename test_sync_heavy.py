#!/usr/bin/env python3
"""Heavy testing suite for Cast sync operations."""

import json
import shutil
import time
from pathlib import Path

from cast.config import GlobalConfig, SyncRule, VaultConfig
from cast.ids import generate_cast_id
from cast.index import build_index
from cast.sync import SyncEngine


def reset_test_environment():
    """Clean up and create fresh test environment."""
    print("\n" + "="*60)
    print("RESETTING TEST ENVIRONMENT")
    print("="*60)
    
    # Clean up existing vaults
    base = Path("test_vaults")
    if base.exists():
        shutil.rmtree(base)
    
    # Create fresh vaults
    vault1 = base / "vault1"
    vault2 = base / "vault2"
    vault3 = base / "vault3"
    
    for vault in [vault1, vault2, vault3]:
        (vault / "01 Vault").mkdir(parents=True)
        (vault / "02 Journal").mkdir(parents=True)
        (vault / ".cast" / "objects").mkdir(parents=True)
        (vault / ".cast" / "peers").mkdir(parents=True)
        (vault / ".cast" / "logs").mkdir(parents=True)
        (vault / ".cast" / "locks").mkdir(parents=True)
        (vault / ".cast" / "index.json").write_text("{}")
    
    # Configure vault1 (hub vault)
    vault1_config = VaultConfig.create_default(vault1, "vault1")
    vault1_config.sync_rules = [
        SyncRule(
            id="to-vault2",
            mode="broadcast",
            from_vault="vault1",
            to_vaults=[{"id": "vault2", "path": str(vault2.absolute())}],
            select={"paths_any": ["**/*.md"]},
        ),
        SyncRule(
            id="to-vault3",
            mode="mirror",  # Mirror mode for vault3
            from_vault="vault1",
            to_vaults=[{"id": "vault3", "path": str(vault3.absolute())}],
            select={"paths_any": ["**/*.md"]},
        ),
    ]
    vault1_config.save()
    
    # Configure vault2 (sync vault)
    vault2_config = VaultConfig.create_default(vault2, "vault2")
    vault2_config.sync_rules = [
        SyncRule(
            id="from-vault1",
            mode="bidirectional",
            from_vault="vault2",
            to_vaults=[{"id": "vault1", "path": str(vault1.absolute())}],
            select={"paths_any": ["**/*.md"]},
        ),
    ]
    vault2_config.save()
    
    # Configure vault3 (mirror vault)
    vault3_config = VaultConfig.create_default(vault3, "vault3")
    vault3_config.sync_rules = []  # vault3 only receives from vault1
    vault3_config.save()
    
    # Update global config
    global_config = GlobalConfig.load_or_create()
    global_config.vaults = {
        "vault1": str(vault1.absolute()),
        "vault2": str(vault2.absolute()),
        "vault3": str(vault3.absolute()),
    }
    global_config.save()
    
    print(f"✓ Created vault1: {vault1}")
    print(f"✓ Created vault2: {vault2}")
    print(f"✓ Created vault3: {vault3}")
    
    return vault1, vault2, vault3


def test_basic_create():
    """Test CREATE operation from scratch."""
    print("\n" + "="*60)
    print("TEST: Basic CREATE Operation")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create a new file in vault1
    test_file = vault1 / "01 Vault" / "basic_create.md"
    content = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
  - vault3 (sync)
tags: [vault1-tag]
category: vault1-cat
---

# Basic Create Test

This is the original content."""
    
    test_file.write_text(content)
    print(f"\n✓ Created file in vault1: {test_file.name}")
    
    # Index and check for auto-ID
    print("\nIndexing vault1...")
    index1 = build_index(vault1)
    
    if not index1:
        print("✗ File was not indexed!")
        return False
    
    cast_id = list(index1.keys())[0]
    print(f"✓ File indexed with cast-id: {cast_id}")
    
    # Verify cast-id was added to file
    updated_content = test_file.read_text()
    if f"cast-id: {cast_id}" not in updated_content:
        print("✗ cast-id not added to file")
        return False
    print("✓ cast-id added to file")
    
    # Sync vault1 -> vault2
    print("\nSyncing vault1 -> vault2...")
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Check results
    created = [r for r in results if r["action"] == "CREATE"]
    if len(created) != 1:
        print(f"✗ Expected 1 CREATE, got {len(created)}")
        return False
    print(f"✓ File created in vault2")
    
    # Verify file exists in vault2
    vault2_file = vault2 / "01 Vault" / "basic_create.md"
    if not vault2_file.exists():
        print(f"✗ File not found in vault2: {vault2_file}")
        return False
    
    # Check content
    vault2_content = vault2_file.read_text()
    
    # Should have cast-id
    if f"cast-id: {cast_id}" not in vault2_content:
        print("✗ cast-id missing in vault2")
        return False
    print("✓ cast-id present in vault2")
    
    # Should have cast-vaults
    if "vault1 (cast)" not in vault2_content:
        print("✗ cast-vaults missing in vault2")
        return False
    print("✓ cast-vaults present in vault2")
    
    # Should NOT have vault1's local fields
    if "vault1-tag" in vault2_content:
        print("✗ vault1's tags incorrectly synced to vault2")
        return False
    if "vault1-cat" in vault2_content:
        print("✗ vault1's category incorrectly synced to vault2")
        return False
    print("✓ Local fields not synced")
    
    # Should have body content
    if "This is the original content" not in vault2_content:
        print("✗ Body content missing")
        return False
    print("✓ Body content synced")
    
    print("\n✓ Basic CREATE test PASSED")
    return True


def test_update_with_local_fields():
    """Test UPDATE when destination has local fields."""
    print("\n" + "="*60)
    print("TEST: UPDATE with Local Fields")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create initial file
    test_file = vault1 / "01 Vault" / "update_test.md"
    initial_content = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [original]
---

# Update Test

Original body content."""
    
    test_file.write_text(initial_content)
    
    # Initial sync
    print("\nInitial sync vault1 -> vault2...")
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    vault2_file = vault2 / "01 Vault" / "update_test.md"
    if not vault2_file.exists():
        print("✗ Initial sync failed")
        return False
    print("✓ Initial sync completed")
    
    # Add local fields to vault2
    print("\nAdding local fields to vault2...")
    vault2_content = vault2_file.read_text()
    
    # Parse and modify
    lines = vault2_content.split('\n')
    yaml_end = -1
    for i, line in enumerate(lines):
        if i > 0 and line == '---':
            yaml_end = i
            break
    
    # Insert local fields before closing ---
    lines.insert(yaml_end, "tags: [vault2-local, important]")
    lines.insert(yaml_end, "status: reviewed")
    lines.insert(yaml_end, "priority: high")
    
    vault2_file.write_text('\n'.join(lines))
    print("✓ Added local fields to vault2")
    
    # Modify vault1 body
    print("\nModifying vault1 body content...")
    vault1_content = test_file.read_text()
    updated_content = vault1_content.replace(
        "Original body content.",
        "Updated body content from vault1!"
    )
    test_file.write_text(updated_content)
    print("✓ Modified vault1 body")
    
    # Sync again
    print("\nSyncing vault1 -> vault2 again...")
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Should be UPDATE, not CONFLICT
    updates = [r for r in results if r["action"] == "UPDATE"]
    conflicts = [r for r in results if r["action"] == "CONFLICT"]
    
    if len(conflicts) > 0:
        print(f"✗ Incorrectly detected {len(conflicts)} conflicts")
        return False
    if len(updates) != 1:
        print(f"✗ Expected 1 UPDATE, got {len(updates)}")
        return False
    print("✓ Correctly detected UPDATE (not CONFLICT)")
    
    # Verify vault2 has updated body
    final_content = vault2_file.read_text()
    
    if "Updated body content from vault1!" not in final_content:
        print("✗ Body not updated in vault2")
        return False
    print("✓ Body updated in vault2")
    
    # Verify vault2 still has local fields
    if "vault2-local" not in final_content:
        print("✗ vault2 local tags lost")
        return False
    if "reviewed" not in final_content:
        print("✗ vault2 status lost")
        return False
    if "high" not in final_content:
        print("✗ vault2 priority lost")
        return False
    print("✓ vault2 local fields preserved")
    
    # Verify vault1 fields NOT in vault2
    if "original" in final_content:
        print("✗ vault1 tags incorrectly synced")
        return False
    print("✓ vault1 local fields not synced")
    
    print("\n✓ UPDATE with local fields test PASSED")
    return True


def test_bidirectional_sync():
    """Test bidirectional sync between vaults."""
    print("\n" + "="*60)
    print("TEST: Bidirectional Sync")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create file in vault1
    file1 = vault1 / "01 Vault" / "bidirectional.md"
    content1 = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [vault1]
---

# Bidirectional Test

Content from vault1."""
    
    file1.write_text(content1)
    
    # Initial sync vault1 -> vault2
    print("\nInitial sync vault1 -> vault2...")
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    file2 = vault2 / "01 Vault" / "bidirectional.md"
    if not file2.exists():
        print("✗ Initial sync failed")
        return False
    print("✓ File synced to vault2")
    
    # Create another file in vault2
    file2b = vault2 / "01 Vault" / "from_vault2.md"
    content2b = """---
cast-vaults:
  - vault1 (sync)
  - vault2 (cast)
tags: [vault2-origin]
---

# From Vault2

This file originated in vault2."""
    
    file2b.write_text(content2b)
    print("✓ Created new file in vault2")
    
    # Sync vault2 -> vault1 (bidirectional)
    print("\nSyncing vault2 -> vault1 (bidirectional)...")
    results = engine.sync("vault2", "vault1", apply=True)
    
    # Check the new file was created in vault1
    file1b = vault1 / "01 Vault" / "from_vault2.md"
    if not file1b.exists():
        print("✗ File from vault2 not created in vault1")
        print(f"  Results: {results}")
        return False
    print("✓ File from vault2 created in vault1")
    
    # Verify content
    vault1_new_content = file1b.read_text()
    if "This file originated in vault2" not in vault1_new_content:
        print("✗ Body content not synced")
        return False
    print("✓ Body content synced")
    
    # Verify vault2's tags NOT in vault1
    if "vault2-origin" in vault1_new_content:
        print("✗ vault2 local fields incorrectly synced")
        return False
    print("✓ Local fields not synced")
    
    print("\n✓ Bidirectional sync test PASSED")
    return True


def test_conflict_detection():
    """Test proper conflict detection."""
    print("\n" + "="*60)
    print("TEST: Conflict Detection")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create and sync initial file
    file1 = vault1 / "01 Vault" / "conflict_test.md"
    initial = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
---

# Conflict Test

Initial content."""
    
    file1.write_text(initial)
    
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    file2 = vault2 / "01 Vault" / "conflict_test.md"
    if not file2.exists():
        print("✗ Initial sync failed")
        return False
    print("✓ Initial sync completed")
    
    # Modify BOTH files' body content
    print("\nModifying both files...")
    
    # Vault1 modification
    content1 = file1.read_text()
    content1_mod = content1.replace("Initial content.", "Modified by vault1.")
    file1.write_text(content1_mod)
    
    # Vault2 modification (body, not just local fields)
    content2 = file2.read_text()
    content2_mod = content2.replace("Initial content.", "Modified by vault2.")
    file2.write_text(content2_mod)
    
    print("✓ Modified both files")
    
    # Try to sync - should detect conflict
    print("\nSyncing vault1 -> vault2 (should conflict)...")
    try:
        results = engine.sync("vault1", "vault2", apply=True)
        # Should have raised error about conflicts
        print("✗ Did not raise error for conflicts")
        return False
    except ValueError as e:
        if "conflict" in str(e).lower():
            print("✓ Correctly detected conflict")
        else:
            print(f"✗ Wrong error: {e}")
            return False
    
    # Force sync to create conflict file
    print("\nForce syncing to create conflict file...")
    results = engine.sync("vault1", "vault2", apply=True, force=True)
    
    conflicts = [r for r in results if r["action"] == "CONFLICT"]
    if len(conflicts) != 1:
        print(f"✗ Expected 1 conflict, got {len(conflicts)}")
        return False
    print("✓ Conflict recorded")
    
    # Check for conflict file
    conflict_files = list((vault2 / "01 Vault").glob("conflict_test.conflicted-*.md"))
    if len(conflict_files) == 0:
        print("✗ No conflict file created")
        return False
    print(f"✓ Conflict file created: {conflict_files[0].name}")
    
    # Verify conflict markers
    conflict_content = conflict_files[0].read_text()
    if "<<<<<<< SOURCE" not in conflict_content:
        print("✗ Missing conflict markers")
        return False
    if "Modified by vault1" not in conflict_content:
        print("✗ vault1 changes not in conflict")
        return False
    if "Modified by vault2" not in conflict_content:
        print("✗ vault2 changes not in conflict")
        return False
    print("✓ Conflict file has both changes")
    
    print("\n✓ Conflict detection test PASSED")
    return True


def test_multiple_files():
    """Test syncing multiple files at once."""
    print("\n" + "="*60)
    print("TEST: Multiple Files Sync")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create multiple files in vault1
    files_to_create = [
        ("doc1.md", "Document 1", ["tag1"]),
        ("doc2.md", "Document 2", ["tag2"]),
        ("doc3.md", "Document 3", ["tag3"]),
        ("subfolder/doc4.md", "Document 4", ["tag4"]),
    ]
    
    print("\nCreating multiple files in vault1...")
    for filename, title, tags in files_to_create:
        filepath = vault1 / "01 Vault" / filename
        filepath.parent.mkdir(exist_ok=True)
        
        content = f"""---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: {tags}
---

# {title}

Content of {title}."""
        
        filepath.write_text(content)
    
    print(f"✓ Created {len(files_to_create)} files")
    
    # Sync all at once
    print("\nSyncing vault1 -> vault2...")
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Check all were created
    created = [r for r in results if r["action"] == "CREATE"]
    if len(created) != len(files_to_create):
        print(f"✗ Expected {len(files_to_create)} CREATEs, got {len(created)}")
        return False
    print(f"✓ All {len(files_to_create)} files synced")
    
    # Verify each file exists in vault2
    for filename, title, tags in files_to_create:
        filepath = vault2 / "01 Vault" / filename
        if not filepath.exists():
            print(f"✗ File not found: {filepath}")
            return False
        
        content = filepath.read_text()
        if f"Content of {title}" not in content:
            print(f"✗ Body missing for {filename}")
            return False
        
        # Check local fields not synced
        for tag in tags:
            if tag in content:
                print(f"✗ Local tag {tag} incorrectly synced")
                return False
    
    print("✓ All files correctly synced")
    
    print("\n✓ Multiple files sync test PASSED")
    return True


def test_file_without_cast_vaults():
    """Test that files without cast-vaults are ignored."""
    print("\n" + "="*60)
    print("TEST: Files Without cast-vaults")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create file WITHOUT cast-vaults
    file_no_cast = vault1 / "01 Vault" / "no_cast.md"
    content_no_cast = """---
tags: [local-only]
---

# Local Only File

This file should NOT sync."""
    
    file_no_cast.write_text(content_no_cast)
    
    # Create file WITH cast-vaults
    file_with_cast = vault1 / "01 Vault" / "with_cast.md"
    content_with_cast = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
---

# Should Sync

This file SHOULD sync."""
    
    file_with_cast.write_text(content_with_cast)
    
    print("✓ Created 2 files (1 with, 1 without cast-vaults)")
    
    # Index and sync
    print("\nIndexing and syncing...")
    build_index(vault1)
    
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Only 1 file should sync
    created = [r for r in results if r["action"] == "CREATE"]
    if len(created) != 1:
        print(f"✗ Expected 1 CREATE, got {len(created)}")
        return False
    print("✓ Only 1 file synced (correct)")
    
    # Verify correct file synced
    should_sync = vault2 / "01 Vault" / "with_cast.md"
    should_not_sync = vault2 / "01 Vault" / "no_cast.md"
    
    if not should_sync.exists():
        print("✗ File with cast-vaults didn't sync")
        return False
    if should_not_sync.exists():
        print("✗ File without cast-vaults incorrectly synced")
        return False
    
    print("✓ Correct file synced")
    print("✓ File without cast-vaults ignored")
    
    print("\n✓ Files without cast-vaults test PASSED")
    return True


def test_mirror_mode():
    """Test mirror mode sync."""
    print("\n" + "="*60)
    print("TEST: Mirror Mode")
    print("="*60)
    
    vault1, vault2, vault3 = reset_test_environment()
    
    # Create file in vault1
    file1 = vault1 / "01 Vault" / "mirror_test.md"
    content = """---
cast-vaults:
  - vault1 (cast)
  - vault3 (sync)
---

# Mirror Test

Original content."""
    
    file1.write_text(content)
    
    # Sync to vault3 (mirror mode)
    print("\nSyncing vault1 -> vault3 (mirror)...")
    engine = SyncEngine()
    engine.sync("vault1", "vault3", apply=True)
    
    file3 = vault3 / "01 Vault" / "mirror_test.md"
    if not file3.exists():
        print("✗ Initial sync failed")
        return False
    print("✓ File mirrored to vault3")
    
    # Modify vault3 file
    print("\nModifying vault3 file...")
    content3 = file3.read_text()
    content3_mod = content3.replace("Original content.", "Modified in vault3.")
    file3.write_text(content3_mod)
    
    # Modify vault1 file
    print("Modifying vault1 file...")
    content1 = file1.read_text()
    content1_mod = content1.replace("Original content.", "Modified in vault1.")
    file1.write_text(content1_mod)
    
    # Sync again - mirror mode should overwrite vault3
    print("\nSyncing vault1 -> vault3 again (should overwrite)...")
    results = engine.sync("vault1", "vault3", apply=True)
    
    # Should be UPDATE, not CONFLICT
    updates = [r for r in results if r["action"] == "UPDATE"]
    if len(updates) != 1:
        print(f"✗ Expected 1 UPDATE, got {len(updates)}")
        return False
    print("✓ Mirror mode forced update")
    
    # Verify vault3 has vault1's content
    final_content = file3.read_text()
    if "Modified in vault1." not in final_content:
        print("✗ vault3 not overwritten")
        return False
    if "Modified in vault3." in final_content:
        print("✗ vault3 changes not overwritten")
        return False
    print("✓ vault3 overwritten with vault1 content")
    
    print("\n✓ Mirror mode test PASSED")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("CAST SYNC HEAVY TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic CREATE", test_basic_create),
        ("UPDATE with Local Fields", test_update_with_local_fields),
        ("Bidirectional Sync", test_bidirectional_sync),
        ("Conflict Detection", test_conflict_detection),
        ("Multiple Files", test_multiple_files),
        ("Files Without cast-vaults", test_file_without_cast_vaults),
        ("Mirror Mode", test_mirror_mode),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:30} {status}")
    
    print("-"*60)
    print(f"Total: {passed_count}/{total} passed")
    
    if passed_count == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️  {total - passed_count} TESTS FAILED")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)