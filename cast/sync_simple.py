"""Simple, reliable sync engine for Cast."""

import shutil
from pathlib import Path
from typing import Any
import json

from cast.config import GlobalConfig, VaultConfig
from cast.index import build_index


class SyncState:
    """Tracks last sync digests between vaults."""
    
    def __init__(self, vault_path: Path):
        """Initialize sync state for a vault."""
        self.vault_path = vault_path
        self.state_file = vault_path / ".cast" / "sync_state.json"
        self.state = {}
        self.load()
    
    def load(self):
        """Load sync state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self.state = json.load(f)
            except:
                self.state = {}
    
    def save(self):
        """Save sync state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_last_sync_digest(self, peer_vault: str, cast_id: str) -> str | None:
        """Get the last synced digest for a file with a peer vault."""
        peer_data = self.state.get(peer_vault, {})
        return peer_data.get(cast_id)
    
    def set_last_sync_digest(self, peer_vault: str, cast_id: str, digest: str):
        """Record the digest of a file after successful sync."""
        if peer_vault not in self.state:
            self.state[peer_vault] = {}
        self.state[peer_vault][cast_id] = digest


class SimpleSyncEngine:
    """Dead simple sync engine - no complex merging, just reliability."""
    
    def __init__(self):
        """Initialize sync engine."""
        self.global_config = GlobalConfig.load()
    
    def sync_all(
        self,
        current_vault: str | Path,
        overpower: bool = False,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Sync current vault with all other vaults.
        
        Simple logic:
        1. If overpower=True, push current vault to all others
        2. Otherwise, find differences and resolve conflicts interactively
        
        Args:
            current_vault: Current vault path
            overpower: Force current vault version everywhere
            interactive: Prompt for conflict resolution
            
        Returns:
            Sync results
        """
        # Get current vault path
        if isinstance(current_vault, str):
            current_path = self.global_config.get_vault_path(current_vault)
            if not current_path:
                current_path = Path(current_vault)
        else:
            current_path = current_vault
        
        if not current_path.exists():
            raise ValueError(f"Vault not found: {current_path}")
        
        # Load current vault config
        current_config = VaultConfig.load(current_path)
        current_id = current_config.vault_id
        
        # Find all other vaults
        other_vaults = []
        for vault_name, vault_path_str in self.global_config.vaults.items():
            vault_path = Path(vault_path_str)
            if vault_path != current_path and vault_path.exists():
                try:
                    config = VaultConfig.load(vault_path)
                    other_vaults.append({
                        "name": vault_name,
                        "path": vault_path,
                        "config": config,
                    })
                except FileNotFoundError:
                    continue
        
        if not other_vaults:
            return {
                "status": "no_other_vaults",
                "message": "No other vaults found to sync with",
            }
        
        # Build indices
        build_index(current_path, rebuild=False)
        index_file = current_path / ".cast" / "index.json"
        with open(index_file) as f:
            current_index = json.load(f)
        
        results = {
            "status": "completed",
            "synced": 0,
            "conflicts": 0,
            "vaults": {},
        }
        
        # Process each vault
        for other in other_vaults:
            other_path = other["path"]
            other_name = other["name"]
            
            build_index(other_path, rebuild=False)
            index_file = other_path / ".cast" / "index.json"
            with open(index_file) as f:
                other_index = json.load(f)
            
            vault_result = self._sync_vault_pair(
                current_path,
                current_index,
                other_path,
                other_index,
                overpower=overpower,
                interactive=interactive,
            )
            
            results["vaults"][other_name] = vault_result
            results["synced"] += vault_result["synced"]
            results["conflicts"] += vault_result["conflicts"]
        
        return results
    
    def _sync_vault_pair(
        self,
        vault1_path: Path,
        vault1_index: dict,
        vault2_path: Path,
        vault2_index: dict,
        overpower: bool = False,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Sync two vaults - simple and reliable.
        
        Args:
            vault1_path: First vault (current)
            vault1_index: First vault's index
            vault2_path: Second vault
            vault2_index: Second vault's index
            overpower: Force vault1's version
            interactive: Prompt for conflicts
            
        Returns:
            Sync results for this pair
        """
        result = {
            "synced": 0,
            "conflicts": 0,
            "actions": [],
        }
        
        # Load sync states for both vaults
        sync_state1 = SyncState(vault1_path)
        sync_state2 = SyncState(vault2_path)
        
        # Find all unique cast-ids
        all_ids = set(vault1_index.keys()) | set(vault2_index.keys())
        
        for cast_id in all_ids:
            file1_info = vault1_index.get(cast_id)
            file2_info = vault2_index.get(cast_id)
            
            # Case 1: File only in vault1
            if file1_info and not file2_info:
                self._copy_file(
                    vault1_path / file1_info["path"],
                    vault2_path / file1_info["path"],
                )
                result["synced"] += 1
                result["actions"].append({
                    "type": "COPY_TO_VAULT2",
                    "file": file1_info["path"],
                })
            
            # Case 2: File only in vault2
            elif file2_info and not file1_info:
                if not overpower:
                    self._copy_file(
                        vault2_path / file2_info["path"],
                        vault1_path / file2_info["path"],
                    )
                    result["synced"] += 1
                    result["actions"].append({
                        "type": "COPY_TO_VAULT1",
                        "file": file2_info["path"],
                    })
                # If overpower, we ignore files only in vault2
            
            # Case 3: File in both vaults
            elif file1_info and file2_info:
                file1_path = vault1_path / file1_info["path"]
                file2_path = vault2_path / file2_info["path"]
                
                # Get current digests
                digest1 = file1_info.get("digest")
                digest2 = file2_info.get("digest")
                
                # If digests missing, compare full content
                if not digest1 or not digest2:
                    content1 = file1_path.read_text()
                    content2 = file2_path.read_text()
                    files_different = content1 != content2
                else:
                    files_different = digest1 != digest2
                
                if files_different:
                    # Files differ - check if we can auto-merge
                    last_sync1 = sync_state1.get_last_sync_digest(vault2_path.name, cast_id)
                    last_sync2 = sync_state2.get_last_sync_digest(vault1_path.name, cast_id)
                    
                    # Auto-merge logic:
                    # - If vault1 changed but vault2 didn't (digest2 == last_sync): use vault1
                    # - If vault2 changed but vault1 didn't (digest1 == last_sync): use vault2
                    # - If both changed: conflict
                    can_auto_merge = False
                    auto_use_vault1 = False
                    
                    if last_sync1 and digest2 == last_sync1:
                        # Vault2 hasn't changed since last sync, use vault1
                        can_auto_merge = True
                        auto_use_vault1 = True
                    elif last_sync2 and digest1 == last_sync2:
                        # Vault1 hasn't changed since last sync, use vault2
                        can_auto_merge = True
                        auto_use_vault1 = False
                    
                    if can_auto_merge and not overpower:
                        # Auto-merge without prompting
                        if auto_use_vault1:
                            self._copy_file(file1_path, file2_path)
                            result["synced"] += 1
                            result["actions"].append({
                                "type": "AUTO_MERGE_VAULT1",
                                "file": file1_info["path"],
                            })
                        else:
                            self._copy_file(file2_path, file1_path)
                            result["synced"] += 1
                            result["actions"].append({
                                "type": "AUTO_MERGE_VAULT2",
                                "file": file2_info["path"],
                            })
                    else:
                        # Files are different and can't auto-merge - handle conflict
                        if overpower:
                            # Force vault1's version
                            self._copy_file(file1_path, file2_path)
                            result["synced"] += 1
                            result["actions"].append({
                                "type": "OVERPOWER",
                                "file": file1_info["path"],
                            })
                        elif interactive:
                            # Let user choose
                            choice = self._resolve_conflict_interactive(
                                cast_id,
                                file1_path,
                                file2_path,
                                vault1_path.name,
                                vault2_path.name,
                            )
                            
                            if choice == "1":
                                self._copy_file(file1_path, file2_path)
                                result["synced"] += 1
                                result["actions"].append({
                                    "type": "USE_VAULT1",
                                    "file": file1_info["path"],
                                })
                            elif choice == "2":
                                self._copy_file(file2_path, file1_path)
                                result["synced"] += 1
                                result["actions"].append({
                                    "type": "USE_VAULT2",
                                    "file": file2_info["path"],
                                })
                            else:
                                result["conflicts"] += 1
                                result["actions"].append({
                                    "type": "SKIP",
                                    "file": file1_info["path"],
                                })
                        else:
                            # Non-interactive mode - mark as conflict
                            result["conflicts"] += 1
                            result["actions"].append({
                                "type": "CONFLICT",
                                "file": file1_info["path"],
                                "vault1": vault1_path.name,
                                "vault2": vault2_path.name,
                            })
        
        # After all syncing is done, rebuild indices to get fresh digests
        build_index(vault1_path, rebuild=False)
        build_index(vault2_path, rebuild=False)
        
        # Reload indices with fresh digests
        with open(vault1_path / ".cast" / "index.json") as f:
            vault1_fresh = json.load(f)
        with open(vault2_path / ".cast" / "index.json") as f:
            vault2_fresh = json.load(f)
        
        # Now update sync states with fresh digests
        for cast_id in all_ids:
            # Skip files that had unresolved conflicts
            skip_action = any(
                a.get("type") == "SKIP" and 
                (vault1_fresh.get(cast_id, {}).get("path") == a.get("file") or
                 vault2_fresh.get(cast_id, {}).get("path") == a.get("file"))
                for a in result["actions"]
            )
            conflict_action = any(
                a.get("type") == "CONFLICT" and
                (vault1_fresh.get(cast_id, {}).get("path") == a.get("file") or
                 vault2_fresh.get(cast_id, {}).get("path") == a.get("file"))
                for a in result["actions"]
            )
            
            if not skip_action and not conflict_action:
                # Get the fresh digest (should be same in both vaults after sync)
                digest = None
                if cast_id in vault1_fresh:
                    digest = vault1_fresh[cast_id].get("digest")
                elif cast_id in vault2_fresh:
                    digest = vault2_fresh[cast_id].get("digest")
                
                if digest:
                    sync_state1.set_last_sync_digest(vault2_path.name, cast_id, digest)
                    sync_state2.set_last_sync_digest(vault1_path.name, cast_id, digest)
        
        # Save sync states
        sync_state1.save()
        sync_state2.save()
        
        return result
    
    def _copy_file(self, src: Path, dst: Path) -> None:
        """Copy file reliably."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy to temp file first for atomicity
        temp_file = dst.with_suffix(".tmp")
        shutil.copy2(src, temp_file)
        temp_file.replace(dst)
    
    def _resolve_conflict_interactive(
        self,
        cast_id: str,
        file1: Path,
        file2: Path,
        vault1_name: str,
        vault2_name: str,
    ) -> str:
        """Interactively resolve a conflict.
        
        Returns:
            "1" for vault1, "2" for vault2, "s" for skip
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.columns import Columns
        
        console = Console()
        
        # Read both versions
        content1 = file1.read_text()
        content2 = file2.read_text()
        
        # Extract just the body for display
        from cast.merge_cast import extract_yaml_and_body
        _, _, body1 = extract_yaml_and_body(content1)
        _, _, body2 = extract_yaml_and_body(content2)
        
        # Show both versions
        console.print(f"\n[yellow]Conflict in file:[/yellow] {file1.name}")
        console.print(f"[dim]Cast ID: {cast_id}[/dim]\n")
        
        # Display side by side
        panel1 = Panel(
            body1[:500] + ("..." if len(body1) > 500 else ""),
            title=f"[cyan]{vault1_name}[/cyan]",
            border_style="cyan",
        )
        panel2 = Panel(
            body2[:500] + ("..." if len(body2) > 500 else ""),
            title=f"[green]{vault2_name}[/green]",
            border_style="green",
        )
        
        console.print(Columns([panel1, panel2]))
        
        # Ask for choice
        while True:
            choice = console.input(
                f"\n[bold]Choose version:[/bold] "
                f"[cyan]1[/cyan]={vault1_name}, "
                f"[green]2[/green]={vault2_name}, "
                f"[yellow]s[/yellow]=skip, "
                f"[red]q[/red]=quit: "
            ).lower()
            
            if choice in ["1", "2", "s"]:
                return choice
            elif choice == "q":
                raise KeyboardInterrupt("User quit")
            else:
                console.print("[red]Invalid choice. Please enter 1, 2, s, or q.[/red]")


def sync_with_conflicts(
    vault_path: Path,
    overpower: bool = False,
    batch: bool = False,
) -> dict[str, Any]:
    """Simple wrapper for CLI usage.
    
    Args:
        vault_path: Vault to sync
        overpower: Force this vault's version everywhere
        batch: Non-interactive mode
        
    Returns:
        Sync results
    """
    engine = SimpleSyncEngine()
    return engine.sync_all(
        vault_path,
        overpower=overpower,
        interactive=not batch,
    )