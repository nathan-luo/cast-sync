#!/usr/bin/env python3
"""Test bidirectional sync where only one vault has changes."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.index import build_index


def test_bidirectional_sync():
    """Test that sync pushes even when only current vault has changes."""
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create two test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        
        for vault in [vault1, vault2]:
            vault.mkdir()
            result = runner.invoke(app, ["init", str(vault), "--id", vault.name])
            assert result.exit_code == 0
        
        # Create initial file ONLY in vault1
        (vault1 / "01 Vault").mkdir()
        test_file1 = vault1 / "01 Vault" / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Created in vault1.""")
        
        build_index(vault1, rebuild=True)
        
        print("=== Initial state ===")
        print(f"File exists in vault1: {test_file1.exists()}")
        test_file2 = vault2 / "01 Vault" / "test.md"
        print(f"File exists in vault2: {test_file2.exists()}")
        
        # Sync from vault1 (should push to vault2 even though vault2 has no changes)
        print("\n=== Sync from vault1 (vault1 has changes, vault2 doesn't) ===")
        result = runner.invoke(app, ["sync", str(vault1)])
        print(result.output)
        assert result.exit_code == 0
        
        # Check that file was pushed to vault2
        print(f"\n=== After sync ===")
        print(f"File exists in vault2: {test_file2.exists()}")
        if test_file2.exists():
            print(f"Content matches: {'Created in vault1' in test_file2.read_text()}")
        
        # Now modify file in vault2 and sync
        if test_file2.exists():
            test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Modified by vault2.""")
            
            build_index(vault2, rebuild=True)
            
            print("\n=== Sync from vault2 after modification ===")
            result = runner.invoke(app, ["sync", str(vault2)])
            print(result.output)
            assert result.exit_code == 0
            
            # Check that vault1 got the update
            print(f"\n=== Final state ===")
            print(f"Vault1 content updated: {'Modified by vault2' in test_file1.read_text()}")
            print(f"Vault2 has content: {'Modified by vault2' in test_file2.read_text()}")
            
            if 'Modified by vault2' in test_file1.read_text():
                print("\n✓ Test passed! Bidirectional sync works correctly.")
            else:
                print("\n✗ Test failed: Changes not synced back to vault1")
        else:
            print("\n✗ Test failed: File not pushed to vault2")


if __name__ == "__main__":
    test_bidirectional_sync()