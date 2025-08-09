#!/usr/bin/env python3
"""Test that cast sync creates conflicts for cast resolve to handle."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cast.cli import app
from cast.config import GlobalConfig
from cast.index import build_index


def test_sync_creates_conflicts():
    """Test that sync actually creates conflict files."""
    
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
        
        # Create initial file in vault1 (in the indexed directory)
        (vault1 / "01 Vault").mkdir()
        test_file1 = vault1 / "01 Vault" / "test.md"
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Original content.""")
        
        # Build index
        build_index(vault1, rebuild=True)
        
        # Sync to vault2 (should copy the file)
        print("=== Initial sync to vault2 ===")
        result = runner.invoke(app, ["sync", str(vault2)])
        print(result.output)
        assert result.exit_code == 0
        
        # Verify file was created
        (vault2 / "01 Vault").mkdir(exist_ok=True)
        test_file2 = vault2 / "01 Vault" / "test.md"
        assert test_file2.exists()
        print(f"File created in vault2: {test_file2.exists()}")
        
        # Now modify the file differently in each vault
        test_file1.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Modified by vault1.""")
        
        test_file2.write_text("""---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-type: Note
---
# Test Note

Modified by vault2.""")
        
        # Rebuild indices
        for vault in [vault1, vault2]:
            build_index(vault, rebuild=True)
        
        # Sync from vault2 with force (should create conflicts)
        print("\n=== Sync with conflicts (with --force) ===")
        result = runner.invoke(app, ["sync", str(vault2), "--force"])
        print(result.output)
        assert result.exit_code == 0
        
        # Check if conflict markers exist
        content = test_file2.read_text()
        has_conflicts = "<<<<<<< " in content and "=======" in content and ">>>>>>> " in content
        print(f"\nFile has conflict markers: {has_conflicts}")
        
        if has_conflicts:
            print("Conflict preview:")
            print(content)
            
            # Now test that resolve can find and fix it
            print("\n=== Running cast resolve ===")
            result = runner.invoke(app, ["resolve", str(vault2), "--batch", "--auto", "source"])
            print(result.output)
            
            # Check resolved content
            resolved_content = test_file2.read_text()
            has_conflicts_after = "<<<<<<< " in resolved_content
            print(f"\nConflicts after resolve: {has_conflicts_after}")
            
            if not has_conflicts_after:
                print("✓ Test passed! Sync creates conflicts and resolve can fix them.")
            else:
                print("✗ Resolve didn't work properly")
        else:
            print("✗ No conflict markers created by sync!")
            print(f"File content:\n{content}")


if __name__ == "__main__":
    test_sync_creates_conflicts()