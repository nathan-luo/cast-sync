#!/usr/bin/env python3
"""Comprehensive test of Cast sync operations."""

import shutil
import time
from pathlib import Path

from cast.config import GlobalConfig, SyncRule, VaultConfig
from cast.ids import generate_cast_id
from cast.index import build_index
from cast.sync import SyncEngine


def setup_clean_vaults():
    """Set up clean test vaults."""
    print("=== Setting up clean vaults ===")
    
    # Clean up existing
    base = Path("vaults")
    if base.exists():
        shutil.rmtree(base)
    
    # Create fresh vaults
    vault1 = base / "vault1"
    vault2 = base / "vault2"
    
    for vault in [vault1, vault2]:
        (vault / "01 Vault").mkdir(parents=True)
        (vault / ".cast" / "objects").mkdir(parents=True)
        (vault / ".cast" / "peers").mkdir(parents=True)
        (vault / ".cast" / "logs").mkdir(parents=True)
        (vault / ".cast" / "locks").mkdir(parents=True)
    
    # Configure vault1
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
    
    # Configure vault2
    vault2_config = VaultConfig.create_default(vault2, "vault2")
    vault2_config.sync_rules = [
        SyncRule(
            id="to-vault1",
            mode="bidirectional",
            from_vault="vault2",
            to_vaults=[{"id": "vault1", "path": str(vault1.absolute())}],
            select={"paths_any": ["01 Vault/**/*.md"]},
        )
    ]
    vault2_config.save()
    
    # Update global config
    global_config = GlobalConfig.load_or_create()
    global_config.vaults = {
        "vault1": str(vault1.absolute()),
        "vault2": str(vault2.absolute()),
    }
    global_config.save()
    
    print(f"  ✓ Created vault1: {vault1}")
    print(f"  ✓ Created vault2: {vault2}")
    
    return vault1, vault2


def test_create_operation(vault1, vault2):
    """Test CREATE: new file syncs to empty destination."""
    print("\n=== Test 1: CREATE operation ===")
    
    # Create a new file in vault1
    file1 = vault1 / "01 Vault" / "test_create.md"
    cast_id = generate_cast_id()
    
    content = f"""---
cast-id: {cast_id}
cast-type: original
cast-version: 1
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [vault1-only, test]
category: vault1-category
---

# Test Create Document

This is a new document created in vault1.

## Content Section

This content should sync to vault2.

## Important

The local fields (tags, category) should NOT sync."""
    
    file1.write_text(content)
    print(f"  Created: {file1}")
    
    # Sync
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Verify
    file2 = vault2 / "01 Vault" / "test_create.md"
    assert file2.exists(), "File should exist in vault2"
    
    content2 = file2.read_text()
    
    # Check cast fields synced
    assert f"cast-id: {cast_id}" in content2
    assert "vault1 (cast)" in content2
    assert "vault2 (sync)" in content2
    
    # Check body synced
    assert "This is a new document created in vault1" in content2
    
    # Check local fields NOT synced
    assert "vault1-only" not in content2
    assert "vault1-category" not in content2
    
    print(f"  ✓ File synced to vault2")
    print(f"  ✓ Cast fields present")
    print(f"  ✓ Local fields excluded")
    
    return cast_id


def test_update_operation(vault1, vault2, cast_id):
    """Test UPDATE: modified file updates destination."""
    print("\n=== Test 2: UPDATE operation ===")
    
    # Add local fields to vault2 version
    file2 = vault2 / "01 Vault" / "test_create.md"
    content2 = file2.read_text()
    
    # Add vault2 local fields
    from cast.merge_cast import extract_yaml_and_body
    import yaml
    
    yaml_dict, _, body = extract_yaml_and_body(content2)
    yaml_dict["tags"] = ["vault2-local", "important"]
    yaml_dict["status"] = "reviewed"
    
    new_yaml = yaml.safe_dump(yaml_dict, sort_keys=False)
    new_content2 = f"---\n{new_yaml}---\n{body}"
    file2.write_text(new_content2)
    print(f"  Added local fields to vault2 version")
    
    # Modify vault1 version
    file1 = vault1 / "01 Vault" / "test_create.md"
    content1 = file1.read_text()
    
    # Update the body
    updated_content1 = content1.replace(
        "This content should sync to vault2.",
        "This content should sync to vault2. UPDATED FROM VAULT1!"
    )
    file1.write_text(updated_content1)
    print(f"  Modified vault1 version")
    
    # Sync again
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Verify
    final_content = file2.read_text()
    
    # Check body updated
    assert "UPDATED FROM VAULT1!" in final_content
    
    # Check vault2 local fields preserved
    assert "vault2-local" in final_content
    assert "important" in final_content
    assert "reviewed" in final_content
    
    # Check vault1 local fields still not there
    assert "vault1-only" not in final_content
    assert "vault1-category" not in final_content
    
    print(f"  ✓ Body content updated")
    print(f"  ✓ Vault2 local fields preserved")
    print(f"  ✓ Vault1 local fields still excluded")


def test_conflict_operation(vault1, vault2):
    """Test CONFLICT: both sides modified."""
    print("\n=== Test 3: CONFLICT operation ===")
    
    # Import needed for this test
    from cast.merge_cast import extract_yaml_and_body
    import yaml
    
    # Create a new file in vault1
    file1 = vault1 / "01 Vault" / "test_conflict.md"
    cast_id = generate_cast_id()
    
    base_content = f"""---
cast-id: {cast_id}
cast-type: original
cast-version: 1
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [vault1-tag]
---

# Conflict Test

Original content.

## Section 1

Base content here."""
    
    file1.write_text(base_content)
    
    # Initial sync to establish baseline
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    file2 = vault2 / "01 Vault" / "test_conflict.md"
    assert file2.exists()
    print(f"  ✓ Initial sync completed")
    
    # Now modify BOTH files differently
    time.sleep(0.1)  # Ensure different timestamps
    
    # Vault1 modification
    vault1_modified = base_content.replace(
        "Original content.",
        "Original content modified by VAULT1."
    )
    file1.write_text(vault1_modified)
    
    # Vault2 modification (with local fields)
    vault2_content = file2.read_text()
    yaml_dict, _, body = extract_yaml_and_body(vault2_content)
    yaml_dict["tags"] = ["vault2-tag", "conflict-test"]
    
    vault2_modified_body = body.replace(
        "Base content here.",
        "Base content modified by VAULT2."
    )
    
    new_yaml = yaml.safe_dump(yaml_dict, sort_keys=False)
    vault2_modified = f"---\n{new_yaml}---\n{vault2_modified_body}"
    file2.write_text(vault2_modified)
    
    print(f"  Modified both files differently")
    
    # Sync with force to create conflict file
    results = engine.sync("vault1", "vault2", apply=True, force=True)
    
    # Check for conflict file
    conflict_files = list((vault2 / "01 Vault").glob("test_conflict.conflicted-*.md"))
    assert len(conflict_files) == 1, f"Should have 1 conflict file, found {len(conflict_files)}"
    
    conflict_file = conflict_files[0]
    print(f"  ✓ Conflict file created: {conflict_file.name}")
    
    # Check conflict file content
    conflict_content = conflict_file.read_text()
    
    # Should have conflict markers
    assert "<<<<<<< SOURCE" in conflict_content
    assert ">>>>>>> DESTINATION" in conflict_content
    
    # Should have vault2 local fields preserved
    assert "vault2-tag" in conflict_content
    assert "conflict-test" in conflict_content
    
    # Should have both modifications in conflict
    assert "VAULT1" in conflict_content
    assert "VAULT2" in conflict_content
    
    print(f"  ✓ Conflict markers present")
    print(f"  ✓ Local fields preserved in conflict")
    print(f"  ✓ Both modifications captured")
    
    # Original file should remain unchanged
    original_content = file2.read_text()
    assert "<<<<<<< SOURCE" not in original_content, "Original file should not have conflict markers"
    
    print(f"  ✓ Original file unchanged")


def main():
    """Run comprehensive tests."""
    print("CAST COMPREHENSIVE TEST SUITE")
    print("=" * 40)
    
    # Setup
    vault1, vault2 = setup_clean_vaults()
    
    # Test 1: CREATE
    cast_id = test_create_operation(vault1, vault2)
    
    # Test 2: UPDATE
    test_update_operation(vault1, vault2, cast_id)
    
    # Test 3: CONFLICT
    test_conflict_operation(vault1, vault2)
    
    print("\n" + "=" * 40)
    print("ALL TESTS PASSED ✓")


if __name__ == "__main__":
    main()