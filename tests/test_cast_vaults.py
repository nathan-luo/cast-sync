"""Tests for cast-vaults field parsing and sync logic."""

import pytest

from cast.cast_vaults import (
    VaultRole,
    format_cast_vaults,
    get_vault_role,
    has_cast_vaults,
    parse_cast_vaults,
    should_sync_to_vault,
)


def test_parse_cast_vaults():
    """Test parsing of cast-vaults field."""
    # Standard format
    vaults = ["vault1 (cast)", "vault2 (sync)", "vault3 (sync)"]
    parsed = parse_cast_vaults(vaults)
    
    assert len(parsed) == 3
    assert parsed[0] == ("vault1", VaultRole.CAST)
    assert parsed[1] == ("vault2", VaultRole.SYNC)
    assert parsed[2] == ("vault3", VaultRole.SYNC)
    
    # With extra spaces
    vaults2 = ["  vault1  (cast)  ", "vault2(sync)"]
    parsed2 = parse_cast_vaults(vaults2)
    
    assert parsed2[0] == ("vault1", VaultRole.CAST)
    assert parsed2[1] == ("vault2", VaultRole.SYNC)
    
    # Empty list
    assert parse_cast_vaults([]) == []
    assert parse_cast_vaults(None) == []
    
    # Invalid entries (ignored)
    vaults3 = ["vault1", "vault2 (invalid)", "vault3 (sync)"]
    parsed3 = parse_cast_vaults(vaults3)
    
    assert len(parsed3) == 1
    assert parsed3[0] == ("vault3", VaultRole.SYNC)


def test_has_cast_vaults():
    """Test checking for cast-vaults field."""
    # Has cast-vaults
    fm1 = {"cast-vaults": ["vault1 (cast)"]}
    assert has_cast_vaults(fm1) is True
    
    # Empty cast-vaults
    fm2 = {"cast-vaults": []}
    assert has_cast_vaults(fm2) is False
    
    # No cast-vaults field
    fm3 = {"title": "Test"}
    assert has_cast_vaults(fm3) is False
    
    # None frontmatter
    assert has_cast_vaults(None) is False


def test_get_vault_role():
    """Test getting vault role."""
    vaults = ["vault1 (cast)", "vault2 (sync)"]
    
    assert get_vault_role(vaults, "vault1") == VaultRole.CAST
    assert get_vault_role(vaults, "vault2") == VaultRole.SYNC
    assert get_vault_role(vaults, "vault3") is None


def test_should_sync_to_vault():
    """Test sync decision logic."""
    # Cast to sync - should sync
    vaults1 = ["source (cast)", "dest (sync)"]
    assert should_sync_to_vault(vaults1, "source", "dest") is True
    
    # Sync to sync - should sync
    vaults2 = ["source (sync)", "dest (sync)"]
    assert should_sync_to_vault(vaults2, "source", "dest") is True
    
    # Destination not in list - should not sync
    vaults3 = ["source (cast)", "other (sync)"]
    assert should_sync_to_vault(vaults3, "source", "dest") is False
    
    # Source not in list - should not sync
    vaults4 = ["other (cast)", "dest (sync)"]
    assert should_sync_to_vault(vaults4, "source", "dest") is False


def test_format_cast_vaults():
    """Test formatting vault list for YAML."""
    vaults = [
        ("vault1", VaultRole.CAST),
        ("vault2", VaultRole.SYNC),
    ]
    
    formatted = format_cast_vaults(vaults)
    
    assert formatted == ["vault1 (cast)", "vault2 (sync)"]