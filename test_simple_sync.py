#!/usr/bin/env python3
"""Test the new simple sync engine."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.index import build_index


def test_simple_sync():
    """Test simple sync with conflicts and overpower."""
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create three test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        vault3 = tmpdir / "vault3"
        
        for vault in [vault1, vault2, vault3]:
            vault.mkdir()
            result = runner.invoke(app, ["init", str(vault), "--id", vault.name])
            assert result.exit_code == 0
        
        print("=== Test 1: Basic sync (file only in vault1) ===")
        
        # Create file in vault1 (in the indexed directory)
        (vault1 / "01 Vault").mkdir()
        test_file1 = vault1 / "01 Vault" / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Content from vault1.""")
        
        build_index(vault1, rebuild=True)
        
        # Sync from vault1 (should copy to vault2 and vault3)
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        if result.exit_code != 0:
            if result.exception:
                import traceback
                traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
        assert result.exit_code == 0
        
        # Check files were created
        test_file2 = vault2 / "01 Vault" / "test.md"
        test_file3 = vault3 / "01 Vault" / "test.md"
        
        print(f"File in vault2: {test_file2.exists()}")
        print(f"File in vault3: {test_file3.exists()}")
        
        print("\n=== Test 2: Conflict resolution with --overpower ===")
        
        # Modify differently in each vault
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault1.""")
        
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault2.""")
        
        test_file3.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault3.""")
        
        # Rebuild indices
        for vault in [vault1, vault2, vault3]:
            build_index(vault, rebuild=True)
        
        # Sync with overpower from vault1
        print("\nForcing vault1's version everywhere with --overpower:")
        result = runner.invoke(app, ["sync", str(vault1), "--overpower"])
        print(result.output)
        assert result.exit_code == 0
        
        # Check all vaults have vault1's version
        print(f"\nvault2 content: {'Modified by vault1' in test_file2.read_text()}")
        print(f"vault3 content: {'Modified by vault1' in test_file3.read_text()}")
        
        print("\n=== Test 3: File only in other vault (pull) ===")
        
        # Create new file only in vault2 (in indexed directory)
        new_file2 = vault2 / "01 Vault" / "new.md"
        new_file2.write_text("""---
cast-id: 456e7890-e89b-12d3-a456-426614174000
---
# New File
Created in vault2.""")
        
        build_index(vault2, rebuild=True)
        
        # Sync from vault1 (should pull new file)
        print("\nSyncing from vault1 (should pull new file from vault2):")
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        new_file1 = vault1 / "01 Vault" / "new.md"
        print(f"\nNew file pulled to vault1: {new_file1.exists()}")
        if new_file1.exists():
            print(f"Content correct: {'Created in vault2' in new_file1.read_text()}")
        
        print("\n=== Test 4: Everything in sync ===")
        
        # First sync from vault1 to push new file to vault3
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        
        # Rebuild indices
        for vault in [vault1, vault2, vault3]:
            build_index(vault, rebuild=True)
        
        # Sync again - should show everything in sync
        print("\nSyncing when everything is already in sync:")
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        if "All vaults are in sync" in result.output:
            print("\n✓ Simple sync test passed!")
        else:
            print("\n✗ Test failed")


if __name__ == "__main__":
    test_simple_sync()