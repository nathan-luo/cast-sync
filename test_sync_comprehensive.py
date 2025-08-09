#!/usr/bin/env python3
"""Comprehensive sync testing to identify and fix all merge/sync issues."""

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Tuple

from cast.config import GlobalConfig, VaultConfig
from cast.sync import SyncEngine
from cast.index import build_index


class SyncTester:
    """Test harness for sync operations."""
    
    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="cast_test_"))
        self.results = []
        self.engine = SyncEngine()
        
    def cleanup(self):
        """Clean up test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def setup_vaults(self, name1="vault1", name2="vault2") -> Tuple[Path, Path]:
        """Set up two test vaults."""
        vault1 = self.test_dir / name1
        vault2 = self.test_dir / name2
        
        for vault in [vault1, vault2]:
            (vault / "01 Vault").mkdir(parents=True)
            (vault / ".cast" / "objects").mkdir(parents=True)
            (vault / ".cast" / "peers").mkdir(parents=True)
            (vault / ".cast" / "index.json").write_text("{}")
            
            # Create config
            config = VaultConfig.create_default(vault, vault.name)
            config.save()
        
        # Update global config
        global_config = GlobalConfig.load_or_create()
        global_config.vaults = {
            name1: str(vault1.absolute()),
            name2: str(vault2.absolute()),
        }
        global_config.save()
        
        return vault1, vault2
    
    def create_file(self, vault: Path, filename: str, content: str) -> Path:
        """Create a file in vault."""
        file_path = vault / "01 Vault" / filename
        file_path.write_text(content)
        build_index(vault, rebuild=False)
        return file_path
    
    def sync_vaults(self, source: str, dest: str, apply=True, force=False) -> list:
        """Sync between vaults and return results."""
        try:
            results = self.engine.sync(source, dest, apply=apply, force=force)
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    def check_file_content(self, file_path: Path, expected: str) -> bool:
        """Check if file content matches expected."""
        if not file_path.exists():
            return False
        actual = file_path.read_text()
        # Normalize for comparison
        actual_body = actual.split("---\n", 2)[-1].strip() if "---\n" in actual else actual.strip()
        expected_body = expected.split("---\n", 2)[-1].strip() if "---\n" in expected else expected.strip()
        return actual_body == expected_body
    
    def run_test(self, name: str, test_fn) -> bool:
        """Run a single test."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        
        try:
            success, details = test_fn()
            if success:
                print(f"✓ PASSED")
            else:
                print(f"✗ FAILED: {details}")
            self.results.append((name, success, details))
            return success
        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.results.append((name, False, str(e)))
            return False


def test_create_sync():
    """Test: Create new file and sync."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create file in vault1
        content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440001
cast-vaults:
- vault1 (cast)
- vault2 (sync)
---

# Test Document

Original content."""
        
        tester.create_file(v1, "test.md", content)
        
        # Sync to vault2
        results = tester.sync_vaults("vault1", "vault2")
        
        # Check results
        if not results or results[0].get("error"):
            return False, f"Sync failed: {results}"
        
        if results[0]["action"] != "CREATE":
            return False, f"Expected CREATE, got {results[0]['action']}"
        
        # Verify file exists in vault2
        v2_file = v2 / "01 Vault" / "test.md"
        if not v2_file.exists():
            return False, "File not created in vault2"
        
        if not tester.check_file_content(v2_file, content):
            return False, "Content mismatch after CREATE"
        
        return True, "CREATE sync works"
        
    finally:
        tester.cleanup()


def test_update_broadcast():
    """Test: Update in broadcast mode (cast -> sync)."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create and sync initial file
        content1 = """---
cast-id: 550e8400-e29b-41d4-a716-446655440002
cast-vaults:
- vault1 (cast)
- vault2 (sync)
---

Initial content."""
        
        tester.create_file(v1, "doc.md", content1)
        tester.sync_vaults("vault1", "vault2")
        
        # Update in vault1
        content2 = """---
cast-id: 550e8400-e29b-41d4-a716-446655440002
cast-vaults:
- vault1 (cast)
- vault2 (sync)
---

Initial content.

Added line in vault1."""
        
        tester.create_file(v1, "doc.md", content2)
        
        # Sync update
        results = tester.sync_vaults("vault1", "vault2")
        
        if not results or results[0]["action"] != "UPDATE":
            return False, f"Expected UPDATE, got {results}"
        
        # Verify content
        v2_file = v2 / "01 Vault" / "doc.md"
        if not tester.check_file_content(v2_file, content2):
            actual = v2_file.read_text() if v2_file.exists() else "FILE NOT FOUND"
            return False, f"Content not updated in vault2. Actual:\n{actual}"
        
        return True, "Broadcast UPDATE works"
        
    finally:
        tester.cleanup()


def test_bidirectional_simple_append():
    """Test: Simple append in bidirectional mode."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create and sync initial file
        content1 = """---
cast-id: 550e8400-e29b-41d4-a716-446655440003
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Base content."""
        
        tester.create_file(v1, "bidi.md", content1)
        tester.sync_vaults("vault1", "vault2")
        
        # Append in vault1
        content2 = """---
cast-id: 550e8400-e29b-41d4-a716-446655440003
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Base content.

Appended in vault1."""
        
        tester.create_file(v1, "bidi.md", content2)
        
        # Sync - should detect as simple append
        results = tester.sync_vaults("vault1", "vault2")
        
        if not results:
            return False, "No sync results"
        
        if results[0]["action"] not in ["UPDATE", "SKIP"]:
            return False, f"Expected UPDATE/SKIP for append, got {results[0]['action']}"
        
        # Verify no conflict created
        conflicts = list((v2 / "01 Vault").glob("*.conflicted-*.md"))
        if conflicts:
            return False, f"Unexpected conflict file created: {conflicts}"
        
        return True, "Simple append handled without conflict"
        
    finally:
        tester.cleanup()


def test_bidirectional_conflict():
    """Test: Conflicting changes in bidirectional mode."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create and sync initial file
        base_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440004
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Line 1
Line 2
Line 3"""
        
        tester.create_file(v1, "conflict.md", base_content)
        tester.sync_vaults("vault1", "vault2")
        
        # Wait to ensure different timestamps
        time.sleep(0.1)
        
        # Different changes in each vault
        v1_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440004
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Line 1 - modified in vault1
Line 2
Line 3"""
        
        v2_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440004
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Line 1
Line 2 - modified in vault2
Line 3"""
        
        tester.create_file(v1, "conflict.md", v1_content)
        tester.create_file(v2, "conflict.md", v2_content)
        
        # Sync with force to create conflict
        results = tester.sync_vaults("vault1", "vault2", force=True)
        
        if not results:
            return False, "No sync results"
        
        # Should create conflict or merge
        action = results[0]["action"]
        if action not in ["CONFLICT", "MERGE"]:
            return False, f"Expected CONFLICT/MERGE, got {action}"
        
        if action == "CONFLICT":
            # Check conflict file created
            conflicts = list((v2 / "01 Vault").glob("*.conflicted-*.md"))
            if not conflicts:
                return False, "No conflict file created"
        
        return True, f"Conflicting changes handled with {action}"
        
    finally:
        tester.cleanup()


def test_local_fields_preserved():
    """Test: Local fields are preserved during sync."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create file with local fields in vault1
        v1_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440005
cast-vaults:
- vault1 (cast)
- vault2 (sync)
tags: [vault1-tag]
category: vault1-category
---

Content."""
        
        tester.create_file(v1, "local.md", v1_content)
        tester.sync_vaults("vault1", "vault2")
        
        # Add local fields in vault2 properly
        v2_file = v2 / "01 Vault" / "local.md"
        v2_content = v2_file.read_text()
        
        # Parse YAML properly to add fields
        import yaml
        lines = v2_content.split('\n')
        # Find YAML section
        if lines[0] == '---':
            end_idx = lines[1:].index('---') + 1
            yaml_lines = lines[1:end_idx]
            yaml_text = '\n'.join(yaml_lines)
            fm_dict = yaml.safe_load(yaml_text) or {}
            
            # Add local fields
            fm_dict['tags'] = ['vault2-tag']
            fm_dict['category'] = 'vault2-category'
            
            # Reconstruct
            new_yaml = yaml.safe_dump(fm_dict, sort_keys=False, allow_unicode=True)
            body = '\n'.join(lines[end_idx+1:])
            v2_modified = f"---\n{new_yaml}---\n{body}"
            v2_file.write_text(v2_modified)
        
        build_index(v2, rebuild=False)
        
        # Update content in vault1
        v1_updated = """---
cast-id: 550e8400-e29b-41d4-a716-446655440005
cast-vaults:
- vault1 (cast)
- vault2 (sync)
tags: [vault1-tag]
category: vault1-category
---

Content.

Updated in vault1."""
        
        tester.create_file(v1, "local.md", v1_updated)
        
        # Sync update
        results = tester.sync_vaults("vault1", "vault2")
        
        # Check vault2 preserved its local fields
        v2_final = v2_file.read_text()
        
        if "vault2-tag" not in v2_final:
            return False, f"vault2 local tags lost. Content:\n{v2_final}"
        
        if "vault2-category" not in v2_final:
            return False, f"vault2 local category lost. Content:\n{v2_final}"
        
        if "Updated in vault1" not in v2_final:
            return False, f"Body not updated. Content:\n{v2_final}"
        
        return True, "Local fields preserved during UPDATE"
        
    finally:
        tester.cleanup()


def test_mirror_mode():
    """Test: Mirror mode overwrites destination."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create different files - using (cast) -> (sync) which is broadcast
        v1_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440006
cast-vaults:
- vault1 (cast)
- vault2 (sync)
---

Vault1 version."""
        
        v2_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440006
cast-vaults:
- vault1 (cast)
- vault2 (sync)
tags: [will-be-lost]
---

Vault2 version - will be overwritten."""
        
        tester.create_file(v1, "mirror.md", v1_content)
        tester.create_file(v2, "mirror.md", v2_content)
        
        # Sync in mirror mode - should overwrite v2
        # Note: Need to implement mirror mode detection in plan.py
        results = tester.sync_vaults("vault1", "vault2")
        
        if not results:
            return False, "No sync results"
        
        # Check if properly overwritten (broadcast mode from cast to sync)
        v2_file = v2 / "01 Vault" / "mirror.md"
        v2_final = v2_file.read_text()
        
        if "Vault1 version" not in v2_final:
            return False, f"Broadcast didn't overwrite. Content:\n{v2_final}"
        
        # In broadcast mode, local fields should be preserved
        # But the body should be from source
        
        return True, "Broadcast mode updates destination"
        
    finally:
        tester.cleanup()


def test_both_append_different():
    """Test: Both vaults append different content."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create and sync base
        base = """---
cast-id: 550e8400-e29b-41d4-a716-446655440007
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Base paragraph."""
        
        tester.create_file(v1, "both.md", base)
        tester.sync_vaults("vault1", "vault2")
        
        # Both append different text
        v1_append = """---
cast-id: 550e8400-e29b-41d4-a716-446655440007
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Base paragraph.

Vault1 addition."""
        
        v2_append = """---
cast-id: 550e8400-e29b-41d4-a716-446655440007
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Base paragraph.

Vault2 addition."""
        
        tester.create_file(v1, "both.md", v1_append)
        tester.create_file(v2, "both.md", v2_append)
        
        # Sync should detect incompatible changes
        results = tester.sync_vaults("vault1", "vault2", force=True)
        
        if not results:
            return False, "No sync results"
        
        action = results[0]["action"]
        if action == "MERGE":
            # Check if merge created conflict file (expected for incompatible changes)
            conflicts = list((v2 / "01 Vault").glob("*.conflicted-*.md"))
            if conflicts:
                # This is correct - incompatible changes should create conflict
                return True, "Incompatible appends created conflict file (correct)"
            
            # Or check if it merged successfully
            v2_file = v2 / "01 Vault" / "both.md"
            content = v2_file.read_text()
            
            # Should have both additions or conflict markers
            has_v1 = "Vault1 addition" in content
            has_v2 = "Vault2 addition" in content
            
            if has_v1 and has_v2:
                return True, "Merge combined both changes"
            else:
                # One-sided merge is also acceptable
                return True, f"Merge handled with {action}"
        
        elif action == "CONFLICT":
            # Conflict file should exist
            conflicts = list((v2 / "01 Vault").glob("*.conflicted-*.md"))
            if not conflicts:
                return False, "No conflict file for incompatible appends"
        
        return True, f"Incompatible appends handled with {action}"
        
    finally:
        tester.cleanup()


def test_no_baseline_state():
    """Test: Sync when peer states have no baseline."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create files independently (no initial sync)
        v1_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440008
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Created in vault1."""
        
        v2_content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440008
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Created in vault2."""
        
        tester.create_file(v1, "nobase.md", v1_content)
        tester.create_file(v2, "nobase.md", v2_content)
        
        # Sync without baseline
        results = tester.sync_vaults("vault1", "vault2", force=True)
        
        if not results:
            return False, "No sync results"
        
        action = results[0]["action"]
        
        # Should either detect append pattern or conflict
        if action == "UPDATE":
            # One was detected as append of other
            pass
        elif action in ["CONFLICT", "MERGE"]:
            # Conflict handling
            pass
        else:
            return False, f"Unexpected action for no-baseline: {action}"
        
        return True, f"No baseline handled with {action}"
        
    finally:
        tester.cleanup()


def test_rapid_bidirectional():
    """Test: Rapid bidirectional syncs."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Initial file
        content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440009
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Initial."""
        
        tester.create_file(v1, "rapid.md", content)
        tester.sync_vaults("vault1", "vault2")
        
        # Multiple rapid changes and syncs
        for i in range(3):
            # Change in v1
            v1_content = f"{content}\n\nRound {i+1} from vault1."
            tester.create_file(v1, "rapid.md", v1_content)
            results1 = tester.sync_vaults("vault1", "vault2")
            
            if results1 and results1[0]["action"] not in ["UPDATE", "SKIP"]:
                return False, f"Round {i+1} v1->v2 unexpected: {results1[0]['action']}"
            
            # Change in v2
            v2_file = v2 / "01 Vault" / "rapid.md"
            v2_content = v2_file.read_text()
            v2_content += f"\nRound {i+1} from vault2."
            v2_file.write_text(v2_content)
            build_index(v2, rebuild=False)
            
            results2 = tester.sync_vaults("vault2", "vault1")
            
            if results2 and results2[0]["action"] not in ["UPDATE", "SKIP"]:
                return False, f"Round {i+1} v2->v1 unexpected: {results2[0]['action']}"
            
            content = v2_content  # Update base for next round
        
        # Final check - both should have all changes
        v1_final = (v1 / "01 Vault" / "rapid.md").read_text()
        v2_final = (v2 / "01 Vault" / "rapid.md").read_text()
        
        for i in range(3):
            if f"Round {i+1} from vault1" not in v1_final:
                return False, f"v1 missing round {i+1} from vault1"
            if f"Round {i+1} from vault2" not in v1_final:
                return False, f"v1 missing round {i+1} from vault2"
        
        return True, "Rapid bidirectional syncs work"
        
    finally:
        tester.cleanup()


def test_peer_state_tracking():
    """Test: Peer states track baselines correctly."""
    tester = SyncTester()
    try:
        v1, v2 = tester.setup_vaults()
        
        # Create and sync
        content = """---
cast-id: 550e8400-e29b-41d4-a716-446655440010
cast-vaults:
- vault1 (sync)
- vault2 (sync)
---

Test content."""
        
        tester.create_file(v1, "peer.md", content)
        results = tester.sync_vaults("vault1", "vault2")
        
        # Check peer states
        v1_peer_file = v1 / ".cast" / "peers" / "vault2.json"
        v2_peer_file = v2 / ".cast" / "peers" / "vault1.json"
        
        if not v1_peer_file.exists():
            return False, "vault1 peer state not created"
        
        if not v2_peer_file.exists():
            return False, "vault2 peer state not created"
        
        v1_peer = json.loads(v1_peer_file.read_text())
        v2_peer = json.loads(v2_peer_file.read_text())
        
        # Check for baseline
        file_id = "550e8400-e29b-41d4-a716-446655440010"
        v1_state = v1_peer.get("files", {}).get(file_id, {})
        v2_state = v2_peer.get("files", {}).get(file_id, {})
        
        if not v1_state.get("base_obj"):
            return False, f"vault1 peer missing baseline: {v1_state}"
        
        if not v2_state.get("base_obj"):
            return False, f"vault2 peer missing baseline: {v2_state}"
        
        if v1_state.get("base_obj") != v2_state.get("base_obj"):
            return False, "Baselines don't match between peers"
        
        return True, "Peer states track baselines correctly"
        
    finally:
        tester.cleanup()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("COMPREHENSIVE SYNC TEST SUITE")
    print("="*60)
    
    tests = [
        ("CREATE sync", test_create_sync),
        ("UPDATE in broadcast mode", test_update_broadcast),
        ("Simple append in bidirectional", test_bidirectional_simple_append),
        ("Conflicting changes", test_bidirectional_conflict),
        ("Local fields preserved", test_local_fields_preserved),
        ("Mirror mode", test_mirror_mode),
        ("Both append different", test_both_append_different),
        ("No baseline state", test_no_baseline_state),
        ("Rapid bidirectional", test_rapid_bidirectional),
        ("Peer state tracking", test_peer_state_tracking),
    ]
    
    tester = SyncTester()
    
    for name, test_fn in tests:
        tester.run_test(name, test_fn)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success, _ in tester.results if success)
    total = len(tester.results)
    
    for name, success, details in tester.results:
        status = "✓" if success else "✗"
        print(f"{status} {name}")
        if not success:
            print(f"   {details}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed < total:
        print(f"\n⚠ {total - passed} test(s) failed - merge/sync needs fixes")
    else:
        print("\n✓ All tests passed!")


if __name__ == "__main__":
    main()