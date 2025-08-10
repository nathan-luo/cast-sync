#!/usr/bin/env python3
"""Comprehensive test suite for Cast sync system."""

import json
import tempfile
import shutil
from pathlib import Path
import uuid

# Test imports
from cast.config import VaultConfig, GlobalConfig
from cast.index import build_index
from cast.sync_simple import SimpleSyncEngine, SyncState
from cast.md import split_frontmatter, serialize_frontmatter
from cast.ids import add_cast_ids


def setup_test_vault(vault_path: Path, vault_id: str, files: dict = None):
    """Set up a test vault with config and files."""
    vault_path.mkdir(parents=True, exist_ok=True)
    
    # Create vault config
    config = VaultConfig.create_default(vault_path, vault_id)
    config.save()
    
    # Create .cast directory
    cast_dir = vault_path / ".cast"
    cast_dir.mkdir(exist_ok=True)
    
    # Create sync state
    (cast_dir / "sync_state.json").write_text("{}")
    
    # Create test files
    if files:
        for file_path, content in files.items():
            full_path = vault_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
    
    # Build index with auto-fix to add cast-ids to files with cast metadata
    build_index(vault_path, rebuild=True, auto_fix=True)
    
    return vault_path


def test_md_parser():
    """Test the centralized markdown parser."""
    print("\n=== Testing MD Parser ===")
    
    # Test 1: Parse with frontmatter
    content = """---
cast-id: test-123
title: Test
tags:
  - foo
  - bar
---

# Content

This is the body."""
    
    fm, fm_text, body = split_frontmatter(content)
    assert fm is not None
    assert fm["cast-id"] == "test-123"
    assert fm["title"] == "Test"
    assert "# Content" in body
    print("✓ Frontmatter parsing works")
    
    # Test 2: No frontmatter
    content2 = "Just body content"
    fm2, fm_text2, body2 = split_frontmatter(content2)
    assert fm2 is None
    assert body2 == "Just body content"
    print("✓ No frontmatter handled correctly")
    
    # Test 3: CRLF line endings
    content3 = "---\r\ncast-id: test\r\n---\r\nBody"
    fm3, _, body3 = split_frontmatter(content3)
    assert fm3["cast-id"] == "test"
    assert body3 == "Body"
    print("✓ CRLF line endings handled")
    
    # Test 4: Serialize with cast-id first
    fm4 = {"title": "Test", "cast-id": "123", "tags": ["a", "b"]}
    serialized = serialize_frontmatter(fm4, "Body content")
    lines = serialized.split("\n")
    assert lines[1].startswith("cast-id:")
    print("✓ cast-id serialized first")


def test_sync_state_with_vault_ids():
    """Test that sync state uses vault IDs, not folder names."""
    print("\n=== Testing SyncState with Vault IDs ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two vaults with same folder name but different IDs
        vault1 = Path(tmpdir) / "folder" / "vault1"
        vault2 = Path(tmpdir) / "folder" / "vault2"
        
        setup_test_vault(vault1, "unique_id_1")
        setup_test_vault(vault2, "unique_id_2")
        
        # Test sync states
        state1 = SyncState(vault1)
        state2 = SyncState(vault2)
        
        # Set digest using vault IDs
        cast_id = str(uuid.uuid4())
        digest = "sha256:abc123"
        
        state1.set_last_sync_digest("unique_id_2", cast_id, digest)
        state1.save()
        
        # Verify it uses vault ID, not folder name
        retrieved = state1.get_last_sync_digest("unique_id_2", cast_id)
        assert retrieved == digest
        
        # Verify folder name doesn't work
        assert state1.get_last_sync_digest("vault2", cast_id) is None
        
        print("✓ SyncState uses vault IDs, not folder names")


def test_cast_vaults_filtering():
    """Test that sync respects cast-vaults field."""
    print("\n=== Testing cast-vaults Filtering ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create 3 vaults
        vault1 = setup_test_vault(tmppath / "vault1", "vault1", {
            "01 Vault/file1.md": """---
cast-id: file1-id
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
File 1 content - should sync between vault1 and vault2 only""",
            "01 Vault/file2.md": """---
cast-id: file2-id
cast-vaults:
  - vault1 (sync)
  - vault3 (sync)
---
File 2 content - should sync between vault1 and vault3 only"""
        })
        
        vault2 = setup_test_vault(tmppath / "vault2", "vault2")
        vault3 = setup_test_vault(tmppath / "vault3", "vault3")
        
        # Set up global config - write it to the expected location
        import os
        os.environ["HOME"] = str(tmppath)  # Temporarily override HOME
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
            "vault3": str(vault3),
        }
        global_config.save()
        
        # Sync from vault1
        engine = SimpleSyncEngine()
        engine.global_config = global_config
        
        result = engine.sync_all(vault1, overpower=False, interactive=False)
        
        # Check that file1 synced to vault2 but not vault3
        assert (vault2 / "01 Vault" / "file1.md").exists()
        assert not (vault3 / "01 Vault" / "file1.md").exists()
        
        # Check that file2 synced to vault3 but not vault2
        assert not (vault2 / "01 Vault" / "file2.md").exists()
        assert (vault3 / "01 Vault" / "file2.md").exists()
        
        print("✓ Files only sync to vaults listed in cast-vaults")


def test_auto_merge():
    """Test auto-merge when only one side changed."""
    print("\n=== Testing Auto-merge ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Initial content
        initial_content = """---
cast-id: test-file
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Initial content"""
        
        # Set up two vaults with same file
        vault1 = setup_test_vault(tmppath / "vault1", "vault1", {
            "01 Vault/test.md": initial_content
        })
        vault2 = setup_test_vault(tmppath / "vault2", "vault2", {
            "01 Vault/test.md": initial_content
        })
        
        # Set up global config - write it to the expected location
        import os
        os.environ["HOME"] = str(tmppath)  # Temporarily override HOME
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
        }
        global_config.save()
        
        # Initial sync to establish baseline
        engine = SimpleSyncEngine()
        engine.global_config = global_config
        initial_result = engine.sync_all(vault1, interactive=False)
        print(f"Initial sync result: {initial_result}")
        
        # Change file in vault1 only
        # Need to preserve the cast-id that was auto-generated
        file1_content = (vault1 / "01 Vault" / "test.md").read_text()
        fm, _, _ = split_frontmatter(file1_content)
        cast_id = fm.get("cast-id")
        
        changed_content = f"""---
cast-id: {cast_id}
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Changed content from vault1"""
        (vault1 / "01 Vault" / "test.md").write_text(changed_content)
        
        # Rebuild index to get new digest
        build_index(vault1, auto_fix=True)
        
        # Sync again - should auto-merge
        result = engine.sync_all(vault1, interactive=False)
        
        # Check that vault2 got the change
        vault2_content = (vault2 / "01 Vault" / "test.md").read_text()
        
        # Debug: Print what actually happened
        print(f"Result: {result}")
        print(f"Vault2 content: {vault2_content[:200]}")
        
        assert "Changed content from vault1" in vault2_content
        
        # Check that it was an auto-merge
        assert any(
            action.get("type") in ["AUTO_MERGE_VAULT1", "COPY_TO_VAULT2"]
            for action in result["vaults"]["vault2"]["actions"]
        )
        
        print("✓ Auto-merge works when only one side changed")


def test_conflict_detection():
    """Test conflict detection when both sides changed."""
    print("\n=== Testing Conflict Detection ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Initial content
        initial_content = """---
cast-id: conflict-test
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Initial content"""
        
        # Set up two vaults
        vault1 = setup_test_vault(tmppath / "vault1", "vault1", {
            "01 Vault/test.md": initial_content
        })
        vault2 = setup_test_vault(tmppath / "vault2", "vault2", {
            "01 Vault/test.md": initial_content
        })
        
        # Set up global config - write it to the expected location
        import os
        os.environ["HOME"] = str(tmppath)  # Temporarily override HOME
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
        }
        global_config.save()
        
        # Initial sync
        engine = SimpleSyncEngine()
        engine.global_config = global_config
        engine.sync_all(vault1, interactive=False)
        
        # Get the actual cast-id that was generated
        file1_content = (vault1 / "01 Vault" / "test.md").read_text()
        fm, _, _ = split_frontmatter(file1_content)
        cast_id = fm.get("cast-id")
        
        # Change both files differently
        (vault1 / "01 Vault" / "test.md").write_text(f"""---
cast-id: {cast_id}
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Changed in vault1""")
        
        (vault2 / "01 Vault" / "test.md").write_text(f"""---
cast-id: {cast_id}
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Changed in vault2""")
        
        # Rebuild indices
        build_index(vault1)
        build_index(vault2)
        
        # Sync - should detect conflict
        result = engine.sync_all(vault1, interactive=False)
        
        assert result["conflicts"] > 0
        assert any(
            action.get("type") == "CONFLICT"
            for action in result["vaults"]["vault2"]["actions"]
        )
        
        print("✓ Conflicts detected when both sides changed")


def test_overpower_mode():
    """Test --overpower flag forces current vault's version."""
    print("\n=== Testing Overpower Mode ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Set up vaults with different content
        vault1 = setup_test_vault(tmppath / "vault1", "vault1", {
            "01 Vault/test.md": """---
cast-id: overpower-test
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Vault1 version - should win"""
        })
        
        vault2 = setup_test_vault(tmppath / "vault2", "vault2", {
            "01 Vault/test.md": """---
cast-id: overpower-test
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
Vault2 version - should lose"""
        })
        
        # Set up global config - write it to the expected location
        import os
        os.environ["HOME"] = str(tmppath)  # Temporarily override HOME
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
        }
        global_config.save()
        
        # Sync with overpower
        engine = SimpleSyncEngine()
        engine.global_config = global_config
        result = engine.sync_all(vault1, overpower=True, interactive=False)
        
        # Check vault2 has vault1's version
        vault2_content = (vault2 / "01 Vault" / "test.md").read_text()
        assert "Vault1 version - should win" in vault2_content
        assert "Vault2 version - should lose" not in vault2_content
        
        print("✓ Overpower mode forces current vault's version")


def test_index_auto_fix():
    """Test index --fix flag for adding cast-ids."""
    print("\n=== Testing Index Auto-fix ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir) / "vault"
        vault.mkdir(parents=True)
        
        # Create vault config manually (without auto-fix)
        config = VaultConfig.create_default(vault, "test")
        config.save()
        (vault / ".cast").mkdir(exist_ok=True)
        (vault / ".cast" / "sync_state.json").write_text("{}")
        
        # Create file with cast metadata but no ID
        (vault / "01 Vault").mkdir(parents=True, exist_ok=True)
        (vault / "01 Vault" / "test.md").write_text("""---
cast-vaults:
  - vault1 (sync)
---
Content""")
        
        # Don't use setup_test_vault which now has auto_fix=True
        # Instead build index manually
        
        # Index without auto-fix - should not modify
        build_index(vault, auto_fix=False)
        content = (vault / "01 Vault" / "test.md").read_text()
        assert "cast-id" not in content
        print("✓ Index without --fix doesn't modify files")
        
        # Index with auto-fix - should add cast-id
        build_index(vault, auto_fix=True)
        content = (vault / "01 Vault" / "test.md").read_text()
        assert "cast-id" in content
        
        # Verify cast-id is first
        lines = content.split("\n")
        yaml_lines = []
        in_yaml = False
        for line in lines:
            if line == "---":
                if in_yaml:
                    break
                in_yaml = True
            elif in_yaml:
                yaml_lines.append(line)
        
        assert yaml_lines[0].startswith("cast-id:")
        print("✓ Index --fix adds cast-id as first field")


def test_no_cast_vaults_no_sync():
    """Test that files without cast-vaults don't sync."""
    print("\n=== Testing No cast-vaults = No Sync ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create vault with file that has no cast-vaults
        vault1 = setup_test_vault(tmppath / "vault1", "vault1", {
            "01 Vault/no_sync.md": """---
cast-id: no-sync-id
title: Should not sync
---
This file has no cast-vaults field"""
        })
        
        vault2 = setup_test_vault(tmppath / "vault2", "vault2")
        
        # Set up global config - write it to the expected location
        import os
        os.environ["HOME"] = str(tmppath)  # Temporarily override HOME
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
        }
        global_config.save()
        
        # Sync
        engine = SimpleSyncEngine()
        engine.global_config = global_config
        engine.sync_all(vault1, interactive=False)
        
        # File should not appear in vault2
        assert not (vault2 / "01 Vault" / "no_sync.md").exists()
        
        print("✓ Files without cast-vaults don't sync")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*50)
    print("COMPREHENSIVE CAST SYNC TEST SUITE")
    print("="*50)
    
    tests = [
        test_md_parser,
        test_sync_state_with_vault_ids,
        test_cast_vaults_filtering,
        test_auto_merge,
        test_conflict_detection,
        test_overpower_mode,
        test_index_auto_fix,
        test_no_cast_vaults_no_sync,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*50)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)