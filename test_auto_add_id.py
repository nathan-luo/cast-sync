#!/usr/bin/env python3
"""Test that cast index automatically adds cast-id to files with cast metadata."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.index import build_index
import json


def test_auto_add_id():
    """Test automatic cast-id addition during indexing."""
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test vault
        vault = tmpdir / "vault"
        vault.mkdir()
        result = runner.invoke(app, ["init", str(vault), "--id", "test-vault"])
        assert result.exit_code == 0
        
        # Create file with cast-vaults but no cast-id
        (vault / "01 Vault").mkdir()
        test_file = vault / "01 Vault" / "test.md"
        test_file.write_text("""---
cast-vaults:
  - vault1
  - vault2
title: Test Note
---
# Test Note

This file has cast-vaults but no cast-id.""")
        
        print("=== Before indexing ===")
        print(f"File content:\n{test_file.read_text()}\n")
        
        # Build index - should auto-add cast-id
        build_index(vault, rebuild=True)
        
        print("=== After indexing ===")
        content_after = test_file.read_text()
        print(f"File content:\n{content_after}\n")
        
        # Check that cast-id was added
        has_cast_id = "cast-id:" in content_after
        print(f"Has cast-id: {has_cast_id}")
        
        # Check that cast-id is first
        lines = content_after.split('\n')
        first_field = None
        for line in lines[1:]:  # Skip the first ---
            if line.strip() and line != '---':
                first_field = line.split(':')[0].strip()
                break
        
        print(f"First field: {first_field}")
        is_first = first_field == "cast-id"
        print(f"Cast-id is first: {is_first}")
        
        # Check index
        index_file = vault / ".cast" / "index.json"
        with open(index_file) as f:
            index = json.load(f)
        
        print(f"\nIndex entries: {len(index)}")
        if index:
            for cast_id, entry in index.items():
                print(f"  - {cast_id}: {entry.get('path')}")
        
        # Test 2: File without any cast metadata (should not get cast-id)
        print("\n=== Test 2: File without cast metadata ===")
        
        plain_file = vault / "01 Vault" / "plain.md"
        plain_file.write_text("""---
title: Plain Note
tags: [test]
---
# Plain Note

This file has no cast metadata.""")
        
        print(f"Before: {plain_file.read_text()[:50]}...")
        
        # Rebuild index
        build_index(vault, rebuild=True)
        
        plain_after = plain_file.read_text()
        print(f"After: {plain_after[:50]}...")
        plain_has_id = "cast-id:" in plain_after
        print(f"Plain file got cast-id: {plain_has_id}")
        
        # Summary
        if has_cast_id and is_first and not plain_has_id:
            print("\n✓ Test passed! Cast-id is automatically added to files with cast metadata.")
        else:
            print("\n✗ Test failed!")
            if not has_cast_id:
                print("  - Cast-id was not added")
            if not is_first:
                print("  - Cast-id is not first field")
            if plain_has_id:
                print("  - Plain file incorrectly got cast-id")


if __name__ == "__main__":
    test_auto_add_id()