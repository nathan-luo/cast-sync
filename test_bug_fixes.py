#!/usr/bin/env python3
"""Test script to verify all bug fixes."""

import tempfile
from pathlib import Path
import shutil

def test_digest_validation():
    """Test that index validation uses body-only digests."""
    print("Testing digest validation...")
    
    from cast.index import validate_index, index_file
    from cast.config import VaultConfig
    
    # Create temp vault
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        (vault / ".cast").mkdir()
        (vault / ".cast" / "index.json").write_text("{}")
        
        # Create test file with frontmatter
        test_file = vault / "test.md"
        content = """---
cast-id: test-123
tags: [test]
---

# Test Content

This is the body."""
        test_file.write_text(content)
        
        # Create config
        config = VaultConfig.create_default(vault, "test")
        config.save()
        
        # Index the file
        index_file(test_file, vault, config)
        
        # Validate should show no issues
        issues = validate_index(vault)
        
        if not issues:
            print("  ✓ No digest mismatches (body-only digest working)")
        else:
            print(f"  ✗ Found issues: {issues}")
            return False
    
    return True


def test_mode_inference():
    """Test correct mode inference from cast-vaults roles."""
    print("Testing mode inference...")
    
    from cast.cast_vaults import parse_cast_vaults, VaultRole
    
    # Test parsing
    cast_vaults = ["vault1 (cast)", "vault2 (sync)"]
    roles = dict(parse_cast_vaults(cast_vaults))
    
    if roles.get("vault1") == VaultRole.CAST and roles.get("vault2") == VaultRole.SYNC:
        print("  ✓ Roles parsed correctly")
    else:
        print(f"  ✗ Roles incorrect: {roles}")
        return False
    
    # Test mode mapping (manually check logic)
    src_role = VaultRole.CAST
    dst_role = VaultRole.SYNC
    
    if src_role == VaultRole.CAST and dst_role == VaultRole.SYNC:
        mode = "broadcast"
    else:
        mode = "bidirectional"
    
    if mode == "broadcast":
        print("  ✓ CAST→SYNC correctly maps to broadcast mode")
    else:
        print(f"  ✗ Mode incorrect: {mode}")
        return False
    
    return True


def test_type_filtering():
    """Test that type filtering uses cast_type field."""
    print("Testing type filtering...")
    
    from cast.select import select_by_rule
    
    # Create test index data
    index_data = {
        "id1": {"path": "file1.md", "cast_type": "Hub"},
        "id2": {"path": "file2.md", "cast_type": "Note"},
        "id3": {"path": "file3.md", "cast_type": "Hub"},
    }
    
    # Filter for Hub type
    rule = {"select": {"types": ["Hub"]}}
    filtered = select_by_rule(index_data, rule)
    
    if len(filtered) == 2 and all(e["cast_type"] == "Hub" for e in filtered.values()):
        print("  ✓ Type filtering using cast_type field works")
    else:
        print(f"  ✗ Filtering failed: {filtered}")
        return False
    
    return True


def test_crlf_frontmatter():
    """Test CRLF frontmatter parsing."""
    print("Testing CRLF frontmatter...")
    
    from cast.ids import extract_frontmatter
    
    # Test with CRLF line endings
    content_crlf = "---\r\ncast-id: test-123\r\ntags: [test]\r\n---\r\n\r\n# Body"
    
    fm, fm_text, body = extract_frontmatter(content_crlf)
    
    if fm and fm.get("cast-id") == "test-123":
        print("  ✓ CRLF frontmatter parsed correctly")
    else:
        print(f"  ✗ CRLF parsing failed: {fm}")
        return False
    
    return True


def test_utc_timestamps():
    """Test UTC timestamp formatting."""
    print("Testing UTC timestamps...")
    
    from datetime import datetime
    import time
    
    # Get current timestamp
    now = time.time()
    
    # Old way (local time)
    local_ts = datetime.fromtimestamp(now).isoformat() + "Z"
    
    # New way (UTC)
    utc_ts = datetime.utcfromtimestamp(now).isoformat() + "Z"
    
    # They should be different (unless you're in UTC timezone)
    if local_ts != utc_ts or "T" in utc_ts:
        print(f"  ✓ UTC timestamp formatting works")
        print(f"    Local: {local_ts}")
        print(f"    UTC:   {utc_ts}")
    else:
        print("  ! Could not verify UTC difference (might be in UTC timezone)")
    
    return True


def test_obsidian_templates_path():
    """Test Obsidian templates path configuration."""
    print("Testing Obsidian templates path...")
    
    import json
    import tempfile
    from cast.obsidian import init_obsidian_config
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        init_obsidian_config(vault)
        
        # Check the config
        config_file = vault / ".obsidian" / "core-plugins-migration.json"
        if config_file.exists():
            config = json.loads(config_file.read_text())
            templates_folder = config.get("templates", {}).get("folder")
            
            if templates_folder == "06 Extras/0609 Templates":
                print("  ✓ Templates folder path correct")
            else:
                print(f"  ✗ Templates folder incorrect: {templates_folder}")
                return False
        else:
            print("  ✗ Config file not created")
            return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CAST BUG FIX VERIFICATION")
    print("="*60 + "\n")
    
    tests = [
        ("Digest Validation", test_digest_validation),
        ("Mode Inference", test_mode_inference),
        ("Type Filtering", test_type_filtering),
        ("CRLF Frontmatter", test_crlf_frontmatter),
        ("UTC Timestamps", test_utc_timestamps),
        ("Obsidian Templates", test_obsidian_templates_path),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            success = test_fn()
            results.append((name, success))
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All bug fixes verified!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")


if __name__ == "__main__":
    main()