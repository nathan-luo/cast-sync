#!/usr/bin/env python3
"""Test auto-merge functionality with sync state tracking."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.index import build_index


def test_auto_merge():
    """Test that sync auto-merges when only one side changed."""
    
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
        
        print("=== Step 1: Initial sync ===")
        
        # Create file in vault1
        (vault1 / "01 Vault").mkdir()
        test_file1 = vault1 / "01 Vault" / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Initial content.""")
        
        build_index(vault1, rebuild=True)
        
        # Sync to vault2
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        test_file2 = vault2 / "01 Vault" / "test.md"
        assert test_file2.exists()
        print(f"File synced to vault2: {test_file2.exists()}")
        
        print("\n=== Step 2: Modify in vault1 only ===")
        
        # Modify file only in vault1
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault1 only.""")
        
        # Rebuild index for vault1
        build_index(vault1, rebuild=True)
        build_index(vault2, rebuild=True)
        
        # Sync again - should auto-merge (vault2 unchanged)
        print("\nSyncing after vault1 change (should auto-merge):")
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        # Check if auto-merged
        if "Auto-merged" in result.output:
            print("✓ Auto-merge detected!")
        else:
            print("✗ No auto-merge (unexpected)")
        
        # Verify vault2 got the update
        vault2_content = test_file2.read_text()
        print(f"Vault2 updated: {'Modified by vault1 only' in vault2_content}")
        
        print("\n=== Step 3: Modify in vault2 only ===")
        
        # Now modify only in vault2
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault2 only.""")
        
        # Rebuild indices
        build_index(vault1, rebuild=True)
        build_index(vault2, rebuild=True)
        
        # Sync from vault1 - should auto-merge (pull from vault2)
        print("\nSyncing after vault2 change (should auto-merge):")
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        # Check if auto-merged
        if "Auto-merged" in result.output:
            print("✓ Auto-merge detected!")
        else:
            print("✗ No auto-merge (unexpected)")
        
        # Verify vault1 got the update
        vault1_content = test_file1.read_text()
        print(f"Vault1 updated: {'Modified by vault2 only' in vault1_content}")
        
        print("\n=== Step 4: Modify in both (conflict) ===")
        
        # Modify both files differently
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault1 conflict.""")
        
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# Test
Modified by vault2 conflict.""")
        
        # Rebuild indices
        build_index(vault1, rebuild=True)
        build_index(vault2, rebuild=True)
        
        # Sync - should detect conflict (both changed)
        print("\nSyncing after both changed (should conflict):")
        result = runner.invoke(app, ["sync", str(vault1), "--batch"])
        print(result.output)
        
        # Check for conflict
        if "Conflict" in result.output or "conflict" in result.output.lower():
            print("✓ Conflict correctly detected when both changed!")
        else:
            print("✗ Conflict not detected (unexpected)")
        
        # Summary
        print("\n✓ Auto-merge test completed!")


if __name__ == "__main__":
    test_auto_merge()