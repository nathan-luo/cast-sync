#!/usr/bin/env python3
"""Test multi-vault sync functionality."""

import shutil
import tempfile
from pathlib import Path

from cast.cli import app
from cast.config import GlobalConfig, VaultConfig
from cast.index import build_index
from typer.testing import CliRunner


def test_multi_vault_sync():
    """Test syncing between multiple vaults."""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create three test vaults
        vault1 = tmpdir / "vault1"
        vault2 = tmpdir / "vault2"
        vault3 = tmpdir / "vault3"
        
        for vault in [vault1, vault2, vault3]:
            vault.mkdir()
            
            # Initialize vault (this also registers it)
            result = runner.invoke(app, ["init", str(vault), "--id", vault.name])
            if result.exit_code != 0:
                print(f"Failed to init {vault.name}: {result.output}")
            assert result.exit_code == 0
        
        # Create the default vault directory structure
        for vault in [vault1, vault2, vault3]:
            vault_dir = vault / "01 Vault"
            vault_dir.mkdir()
        
        # Create a test file in vault1
        test_file1 = vault1 / "01 Vault" / "test1.md"
        test_file1.write_text("""---
cast-id: test-001
cast-type: Note
---
# Test Note 1

Content from vault1.""")
        
        # Create a different file in vault2
        test_file2 = vault2 / "01 Vault" / "test2.md"
        test_file2.write_text("""---
cast-id: test-002
cast-type: Note
---
# Test Note 2

Content from vault2.""")
        
        # Index all vaults
        for vault in [vault1, vault2, vault3]:
            build_index(vault, rebuild=True)
        
        # First, let's check what's in the indices
        print("\n=== Checking indices ===")
        result = runner.invoke(app, ["status", str(vault1)])
        print(f"Vault1 status: {result.output}")
        
        result = runner.invoke(app, ["status", str(vault2)])
        print(f"Vault2 status: {result.output}")
        
        # Test 1: Dry run sync from vault3 (should pull from vault1 and vault2)
        print("\n=== Test 1: Dry run multi-vault sync from vault3 ===")
        result = runner.invoke(app, ["sync", str(vault3)])
        print(result.output)
        assert result.exit_code == 0
        assert "Pull Results" in result.output
        assert "vault1" in result.output
        assert "vault2" in result.output
        
        # Test 2: Apply sync from vault3
        print("\n=== Test 2: Apply multi-vault sync from vault3 ===")
        result = runner.invoke(app, ["sync", str(vault3), "--apply"])
        print(result.output)
        assert result.exit_code == 0
        
        # Verify files were created in vault3
        assert (vault3 / "01 Vault" / "test1.md").exists()
        assert (vault3 / "01 Vault" / "test2.md").exists()
        
        # Test 3: Modify file in vault3 and sync back
        test_file3 = vault3 / "01 Vault" / "test1.md"
        content = test_file3.read_text()
        test_file3.write_text(content.replace("Content from vault1.", "Content from vault1.\n\nModified in vault3."))
        
        # Rebuild index
        build_index(vault3, rebuild=True)
        
        print("\n=== Test 3: Sync modified file from vault3 ===")
        result = runner.invoke(app, ["sync", str(vault3), "--apply"])
        print(result.output)
        assert result.exit_code == 0
        
        # Test 4: Create conflict scenario
        print("\n=== Test 4: Create conflict scenario ===")
        
        # Modify same file in vault1 and vault2 differently
        test1_v1 = vault1 / "01 Vault" / "test1.md"
        test1_v2 = vault2 / "01 Vault" / "test1.md"
        
        # First ensure vault2 has the file
        result = runner.invoke(app, ["sync", str(vault2), "--apply"])
        
        # Now modify differently
        content1 = test1_v1.read_text()
        test1_v1.write_text(content1.replace("Modified in vault3.", "Modified in vault3.\n\nVault1 change."))
        
        content2 = test1_v2.read_text()
        test1_v2.write_text(content2.replace("Modified in vault3.", "Modified in vault3.\n\nVault2 change."))
        
        # Rebuild indices
        build_index(vault1, rebuild=True)
        build_index(vault2, rebuild=True)
        
        # Try to sync from vault3 - should detect conflicts
        print("\n=== Syncing with conflicts ===")
        result = runner.invoke(app, ["sync", str(vault3)])
        print(result.output)
        
        # Test 5: Test legacy mode
        print("\n=== Test 5: Legacy two-vault sync ===")
        result = runner.invoke(app, ["sync", "--legacy", "--source", "vault1", "--dest", "vault2"])
        print(result.output)
        assert result.exit_code == 0
        assert "Legacy" in result.output
        
        print("\n=== All tests passed! ===")


if __name__ == "__main__":
    test_multi_vault_sync()