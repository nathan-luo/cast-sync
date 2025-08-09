"""Cast vaults field parsing and management."""

import re
from enum import Enum
from typing import Any


class VaultRole(Enum):
    """Role of a vault in cast-vaults list."""
    CAST = "cast"      # Original/authoritative
    SYNC = "sync"      # Synchronized copy
    

def parse_cast_vaults(cast_vaults: list[str] | None) -> list[tuple[str, VaultRole]]:
    """Parse cast-vaults field from YAML frontmatter.
    
    Args:
        cast_vaults: List of vault entries like ["vault1 (cast)", "vault2 (sync)"]
        
    Returns:
        List of (vault_name, role) tuples
    """
    if not cast_vaults:
        return []
    
    parsed = []
    pattern = re.compile(r"^(.+?)\s*\((cast|sync)\)\s*$")
    
    for entry in cast_vaults:
        if not isinstance(entry, str):
            continue
            
        match = pattern.match(entry.strip())
        if match:
            vault_name = match.group(1).strip()
            role = VaultRole(match.group(2))
            parsed.append((vault_name, role))
    
    return parsed


def has_cast_vaults(frontmatter: dict[str, Any] | None) -> bool:
    """Check if a file has non-empty cast-vaults field.
    
    Args:
        frontmatter: Parsed YAML frontmatter
        
    Returns:
        True if file has cast-vaults with at least one entry
    """
    if not frontmatter:
        return False
    
    cast_vaults = frontmatter.get("cast-vaults")
    if not cast_vaults:
        return False
    
    if isinstance(cast_vaults, list) and len(cast_vaults) > 0:
        return True
    
    return False


def get_vault_role(cast_vaults: list[str] | None, vault_name: str) -> VaultRole | None:
    """Get the role of a specific vault from cast-vaults.
    
    Args:
        cast_vaults: List of vault entries
        vault_name: Name of vault to look up
        
    Returns:
        Role of the vault or None if not found
    """
    parsed = parse_cast_vaults(cast_vaults)
    
    for name, role in parsed:
        if name == vault_name:
            return role
    
    return None


def should_sync_to_vault(
    cast_vaults: list[str] | None,
    source_vault: str,
    dest_vault: str,
) -> bool:
    """Check if a file should sync from source to destination vault.
    
    Rules:
    - File must have the destination vault in its cast-vaults list
    - If source is (cast) and dest is (sync), allow sync
    - If both are (sync), allow bidirectional sync
    - If dest is (cast) and source is (sync), only in bidirectional mode
    
    Args:
        cast_vaults: List of vault entries from file
        source_vault: Source vault name
        dest_vault: Destination vault name
        
    Returns:
        True if sync should proceed
    """
    parsed = parse_cast_vaults(cast_vaults)
    vault_dict = dict(parsed)
    
    # Destination must be in the list
    if dest_vault not in vault_dict:
        return False
    
    # Source should also be in the list for proper sync
    if source_vault not in vault_dict:
        return False
    
    source_role = vault_dict[source_vault]
    dest_role = vault_dict[dest_vault]
    
    # Cast -> Sync: always allow (broadcast)
    if source_role == VaultRole.CAST and dest_role == VaultRole.SYNC:
        return True
    
    # Sync -> Sync: allow (for chains)
    if source_role == VaultRole.SYNC and dest_role == VaultRole.SYNC:
        return True
    
    # Sync -> Cast: only in special cases (bidirectional)
    # This would need to check sync mode
    if source_role == VaultRole.SYNC and dest_role == VaultRole.CAST:
        return True  # Let sync mode determine behavior
    
    return True


def format_cast_vaults(vaults: list[tuple[str, VaultRole]]) -> list[str]:
    """Format vault list for YAML frontmatter.
    
    Args:
        vaults: List of (vault_name, role) tuples
        
    Returns:
        Formatted list for YAML
    """
    return [f"{name} ({role.value})" for name, role in vaults]