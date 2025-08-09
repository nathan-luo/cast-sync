"""Integration tests for Cast sync functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from cast.cli import app
from cast.config import GlobalConfig, VaultConfig
from cast.ids import generate_cast_id
from cast.index import build_index
from cast.plan import create_plan
from cast.sync import SyncEngine


@pytest.fixture
def temp_vaults():
    """Create temporary test vaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create two test vaults
        vault1 = base / "vault1"
        vault2 = base / "vault2"
        
        # Create vault structures
        for vault in [vault1, vault2]:
            # Create directories
            (vault / ".cast").mkdir(parents=True)
            (vault / "01 Vault").mkdir(parents=True)
            (vault / "02 Journal").mkdir(parents=True)
            
            # Initialize vault config
            config = VaultConfig.create_default(vault, vault.name)
            config.save()
        
        # Setup global config
        global_config = GlobalConfig()
        global_config.vaults = {
            "vault1": str(vault1),
            "vault2": str(vault2),
        }
        
        # Temporarily override the global config path
        import cast.config
        original_config_path = cast.config.GlobalConfig.config_path
        
        # Create temp global config
        temp_config_path = base / "global_config.yaml"
        
        # Monkey patch the config path
        cast.config.GlobalConfig.config_path = property(lambda self: temp_config_path)
        global_config.save()
        
        yield vault1, vault2
        
        # Restore original config path
        cast.config.GlobalConfig.config_path = original_config_path


def create_test_file(vault_path: Path, filename: str, cast_vaults: list[str], content: str, local_tags: list[str] = None) -> str:
    """Create a test markdown file with cast-vaults."""
    cast_id = generate_cast_id()
    
    yaml_content = f"""---
cast-id: {cast_id}
cast-type: original
cast-version: 1
cast-vaults:
"""
    
    for vault_entry in cast_vaults:
        yaml_content += f"  - {vault_entry}\n"
    
    if local_tags:
        yaml_content += f"tags: {local_tags}\n"
    
    yaml_content += "---\n"
    
    full_content = yaml_content + content
    
    file_path = vault_path / "01 Vault" / filename
    file_path.write_text(full_content)
    
    return cast_id


def test_sync_single_file(temp_vaults):
    """Test syncing a single file between vaults."""
    vault1, vault2 = temp_vaults
    
    # Create a file in vault1 that should sync to vault2
    content = """# Test Document

This is test content that should sync.

## Section 1

Some content here."""
    
    cast_id = create_test_file(
        vault1,
        "test_doc.md",
        cast_vaults=["vault1 (cast)", "vault2 (sync)"],
        content=content,
        local_tags=["test", "vault1-only"]
    )
    
    # Build indices
    index1 = build_index(vault1)
    index2 = build_index(vault2)
    
    # File should be in vault1 index
    assert cast_id in index1
    # Not yet in vault2
    assert cast_id not in index2
    
    # Create and execute sync plan
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Check results
    assert len(results) == 1
    assert results[0]["action"] == "CREATE"
    assert results[0]["success"] is True
    
    # Verify file exists in vault2
    dest_file = vault2 / "01 Vault" / "test_doc.md"
    assert dest_file.exists()
    
    # Read and verify content
    dest_content = dest_file.read_text()
    
    # Should have cast fields
    assert "cast-id: " + cast_id in dest_content
    assert "vault1 (cast)" in dest_content
    assert "vault2 (sync)" in dest_content
    
    # Should have body content
    assert "This is test content that should sync" in dest_content
    
    # Should NOT have vault1's local tags
    assert "vault1-only" not in dest_content


def test_sync_with_local_fields_preserved(temp_vaults):
    """Test that local fields are preserved during sync."""
    vault1, vault2 = temp_vaults
    
    # Create file in vault1
    cast_id = create_test_file(
        vault1,
        "doc_with_local.md",
        cast_vaults=["vault1 (cast)", "vault2 (sync)"],
        content="# Original\n\nOriginal content.",
        local_tags=["vault1-tag"]
    )
    
    # First sync to create file in vault2
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    # Now add local fields to vault2 version
    dest_file = vault2 / "01 Vault" / "doc_with_local.md"
    content = dest_file.read_text()
    
    # Add vault2-specific tags
    import yaml
    from cast.ids import extract_frontmatter
    
    fm_dict, _, body = extract_frontmatter(content)
    fm_dict["tags"] = ["vault2-local", "important"]
    fm_dict["category"] = "vault2-category"
    
    # Rewrite with local fields
    new_yaml = yaml.safe_dump(fm_dict, sort_keys=False)
    new_content = f"---\n{new_yaml}---\n{body}"
    dest_file.write_text(new_content)
    
    # Update content in vault1
    src_file = vault1 / "01 Vault" / "doc_with_local.md"
    src_content = src_file.read_text()
    updated_content = src_content.replace("Original content.", "Updated content from vault1.")
    src_file.write_text(updated_content)
    
    # Sync again
    engine.sync("vault1", "vault2", apply=True)
    
    # Read vault2 version
    final_content = dest_file.read_text()
    
    # Body should be updated
    assert "Updated content from vault1" in final_content
    
    # Local fields should be preserved
    assert "vault2-local" in final_content
    assert "important" in final_content
    assert "vault2-category" in final_content
    
    # vault1 tags should NOT be there
    assert "vault1-tag" not in final_content


def test_bidirectional_sync(temp_vaults):
    """Test bidirectional sync with changes in both vaults."""
    vault1, vault2 = temp_vaults
    
    # Create initial file
    cast_id = create_test_file(
        vault1,
        "bidir_doc.md",
        cast_vaults=["vault1 (sync)", "vault2 (sync)"],  # Both are sync
        content="""# Document

## Section 1
Initial content.

## Section 2
More content."""
    )
    
    # Initial sync
    engine = SyncEngine()
    engine.sync("vault1", "vault2", apply=True)
    
    # Now modify different sections in each vault
    file1 = vault1 / "01 Vault" / "bidir_doc.md"
    content1 = file1.read_text()
    content1 = content1.replace("Initial content.", "Vault1 modified this.")
    file1.write_text(content1)
    
    file2 = vault2 / "01 Vault" / "bidir_doc.md"
    content2 = file2.read_text()
    content2 = content2.replace("More content.", "Vault2 modified this.")
    file2.write_text(content2)
    
    # Configure bidirectional sync rule
    config1 = VaultConfig.load(vault1)
    from cast.config import SyncRule
    config1.sync_rules = [
        SyncRule(
            id="bidir",
            mode="bidirectional",
            from_vault="vault1",
            to_vaults=[{"id": "vault2", "path": str(vault2)}],
            select={"paths_any": ["01 Vault/**/*.md"]},
        )
    ]
    config1.save()
    
    # Sync with bidirectional mode
    results = engine.sync("vault1", "vault2", rule_id="bidir", apply=True)
    
    # Both files should have both changes
    final1 = file1.read_text()
    final2 = file2.read_text()
    
    # The body content should be merged (both changes present)
    # Due to the merge, vault2's change should be in vault1
    assert "Vault2 modified this" in final1
    
    # And vault1's change should already be in vault2 from the sync
    assert "Vault1 modified this" in final2


def test_file_not_synced_without_cast_vaults(temp_vaults):
    """Test that files without cast-vaults field are ignored."""
    vault1, vault2 = temp_vaults
    
    # Create file WITHOUT cast-vaults
    file_path = vault1 / "01 Vault" / "no_sync.md"
    file_path.write_text("""---
cast-id: test-id-123
tags: [test]
---
# Document

This should NOT sync because it lacks cast-vaults field.""")
    
    # Try to sync
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Should have no results (file ignored)
    assert len(results) == 0
    
    # File should not exist in vault2
    assert not (vault2 / "01 Vault" / "no_sync.md").exists()


def test_sync_only_to_listed_vaults(temp_vaults):
    """Test that files only sync to vaults listed in cast-vaults."""
    vault1, vault2 = temp_vaults
    
    # Create file that lists only vault1 (not vault2)
    cast_id = create_test_file(
        vault1,
        "vault1_only.md",
        cast_vaults=["vault1 (cast)"],  # Only vault1, not vault2
        content="# Vault1 Only\n\nThis should not sync to vault2."
    )
    
    # Try to sync to vault2
    engine = SyncEngine()
    results = engine.sync("vault1", "vault2", apply=True)
    
    # Should have no results (vault2 not in cast-vaults)
    assert len(results) == 0
    
    # File should not exist in vault2
    assert not (vault2 / "01 Vault" / "vault1_only.md").exists()