"""Multi-vault sync engine for Cast."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import filelock

from cast.config import GlobalConfig, VaultConfig
from cast.merge_cast import merge_cast_content
from cast.normalize import compute_normalized_digest, normalize_content
from cast.objects import ObjectStore
from cast.peers import PeerState
from cast.plan import ActionType, create_plan


class MultiVaultSyncEngine:
    """Multi-vault sync engine that syncs with all connected vaults at once."""
    
    def __init__(self):
        """Initialize sync engine."""
        self.global_config = GlobalConfig.load()
    
    def sync_all(
        self,
        current_vault: str | Path,
        apply: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Synchronize current vault with all connected vaults.
        
        This performs a multi-step process:
        1. Pull changes from all other vaults
        2. Detect and merge conflicts
        3. Apply changes to current vault
        4. After resolution, push changes to all other vaults
        
        Args:
            current_vault: Current vault name or path
            apply: Actually apply changes (vs dry run)
            force: Force sync even with conflicts
            
        Returns:
            Dict with sync results for each vault
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
        
        # Find all other registered vaults
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
                    # Skip vaults without Cast config
                    continue
        
        if not other_vaults:
            return {
                "current_vault": str(current_path),
                "status": "no_other_vaults",
                "message": "No other vaults found to sync with",
                "pull_results": {},
                "push_results": {},
            }
        
        # Auto-index current vault
        from cast.index import build_index
        build_index(current_path, rebuild=False)
        
        # Phase 1: Pull from all other vaults
        pull_results = {}
        all_conflicts = []
        changes_to_apply = []
        
        for other in other_vaults:
            other_path = other["path"]
            other_name = other["name"]
            
            # Auto-index other vault
            build_index(other_path, rebuild=False)
            
            # Create plan for pulling from this vault
            plan = create_plan(other_name, str(current_path))
            
            # Track conflicts
            conflicts = [a for a in plan["actions"] if a["type"] == "CONFLICT"]
            if conflicts:
                all_conflicts.extend({
                    **c,
                    "source_vault": other_name,
                } for c in conflicts)
            
            # Track changes
            changes = [a for a in plan["actions"] if a["type"] in ["CREATE", "UPDATE", "MERGE"]]
            if changes:
                changes_to_apply.extend({
                    **c,
                    "source_vault": other_name,
                    "source_path_full": other_path,
                } for c in changes)
            
            pull_results[other_name] = {
                "summary": plan["summary"],
                "conflicts": len(conflicts),
                "changes": len(changes),
            }
        
        # Check if we have conflicts
        total_conflicts = len(all_conflicts)
        if total_conflicts > 0 and not force and apply:
            return {
                "current_vault": str(current_path),
                "status": "conflicts_detected",
                "message": f"Found {total_conflicts} conflicts. Use --force to proceed or resolve conflicts first.",
                "conflicts": all_conflicts,
                "pull_results": pull_results,
                "push_results": {},
            }
        
        if not apply:
            return {
                "current_vault": str(current_path),
                "status": "dry_run",
                "message": "Dry run - no changes applied",
                "pull_results": pull_results,
                "changes_to_apply": len(changes_to_apply),
                "conflicts": all_conflicts,
                "push_results": {},
            }
        
        # Phase 2: Apply changes to current vault
        applied_changes = []
        
        # Acquire lock on current vault
        lock_path = current_path / ".cast" / "locks" / "sync.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        with filelock.FileLock(lock_path, timeout=10):
            # Process all changes (grouped by cast-id to avoid duplicates)
            changes_by_id = {}
            for change in changes_to_apply:
                cast_id = change["cast_id"]
                if cast_id not in changes_by_id:
                    changes_by_id[cast_id] = []
                changes_by_id[cast_id].append(change)
            
            # Apply each unique change
            for cast_id, changes in changes_by_id.items():
                # Use the most recent change if multiple vaults have same file
                # TODO: This could be smarter - merge from multiple sources
                change = changes[0]  # For now, just take first
                
                result = self._apply_change(
                    change,
                    Path(change["source_path_full"]),
                    current_path,
                    current_config,
                    force=force,
                )
                applied_changes.append(result)
            
            # Update peer states for all synced vaults
            for other in other_vaults:
                peer = PeerState(current_path, other["config"].vault_id)
                peer.load()
                peer.update_sync_time()
                peer.save()
        
        # Phase 3: Push changes to all other vaults
        push_results = {}
        
        if applied_changes:
            # Rebuild index after applying changes
            build_index(current_path, rebuild=False)
            
            for other in other_vaults:
                other_path = other["path"]
                other_name = other["name"]
                
                # Create plan for pushing to this vault
                plan = create_plan(str(current_path), other_name)
                
                # Apply the push
                if plan["summary"]["total"] > 0:
                    engine = SyncEngine()
                    results = engine.sync(
                        str(current_path),
                        str(other_path),
                        apply=True,
                        force=force,
                    )
                    
                    push_results[other_name] = {
                        "summary": plan["summary"],
                        "results": results,
                    }
                else:
                    push_results[other_name] = {
                        "summary": plan["summary"],
                        "results": [],
                    }
        
        return {
            "current_vault": str(current_path),
            "status": "completed",
            "message": f"Synced with {len(other_vaults)} vaults",
            "pull_results": pull_results,
            "push_results": push_results,
            "applied_changes": len(applied_changes),
            "conflicts": all_conflicts if force else [],
        }
    
    def _apply_change(
        self,
        change: dict[str, Any],
        source_path: Path,
        dest_path: Path,
        dest_config: VaultConfig,
        force: bool = False,
    ) -> dict[str, Any]:
        """Apply a single change to the destination vault.
        
        Args:
            change: Change action to apply
            source_path: Source vault path
            dest_path: Destination vault path
            dest_config: Destination vault config
            force: Force changes even with conflicts
            
        Returns:
            Result of applying the change
        """
        action_type = ActionType(change["type"])
        cast_id = change["cast_id"]
        
        result = {
            "file": change.get("source_path") or change.get("dest_path"),
            "cast_id": cast_id,
            "action": action_type.value,
            "source_vault": change.get("source_vault"),
            "success": False,
            "status": "pending",
        }
        
        try:
            if action_type == ActionType.CREATE:
                self._perform_create(change, source_path, dest_path)
                result["success"] = True
                result["status"] = "created"
                
            elif action_type == ActionType.UPDATE:
                self._perform_update(change, source_path, dest_path)
                result["success"] = True
                result["status"] = "updated"
                
            elif action_type == ActionType.MERGE:
                conflicts = self._perform_merge(
                    change, source_path, dest_path, dest_config
                )
                if conflicts:
                    result["success"] = False
                    result["status"] = f"merged with {len(conflicts)} conflicts"
                else:
                    result["success"] = True
                    result["status"] = "merged"
                    
            elif action_type == ActionType.CONFLICT:
                if force:
                    conflicts = self._perform_merge(
                        change, source_path, dest_path, dest_config
                    )
                    if conflicts:
                        result["success"] = False
                        result["status"] = f"conflict ({len(conflicts)} unresolved)"
                    else:
                        result["success"] = True
                        result["status"] = "forced"
                else:
                    result["success"] = False
                    result["status"] = "conflict"
                    
        except Exception as e:
            result["success"] = False
            result["status"] = f"error: {e}"
        
        return result
    
    def _perform_create(
        self,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
    ) -> None:
        """Create a new file in destination."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["source_path"]
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read source content
        src_content = src_file.read_text(encoding="utf-8")
        
        # Filter to only cast-* fields for CREATE
        from cast.merge_cast import extract_yaml_and_body, CAST_FIELDS
        import yaml
        
        src_yaml, _, src_body = extract_yaml_and_body(src_content)
        
        # Create new YAML with only cast-* fields
        dst_yaml = {}
        if src_yaml:
            if "cast-id" in src_yaml:
                dst_yaml["cast-id"] = src_yaml["cast-id"]
            
            cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
            for field in cast_field_order:
                if field in src_yaml:
                    dst_yaml[field] = src_yaml[field]
            
            for key in CAST_FIELDS:
                if key in src_yaml and key not in dst_yaml:
                    dst_yaml[key] = src_yaml[key]
        
        # Reconstruct content
        if dst_yaml:
            yaml_text = yaml.safe_dump(dst_yaml, sort_keys=False, allow_unicode=True)
            content = f"---\n{yaml_text}---\n{src_body}"
        else:
            content = src_body
        
        # Write atomically
        temp_file = dst_file.with_suffix(".tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(dst_file)
    
    def _perform_update(
        self,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
    ) -> None:
        """Update a file in destination."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["dest_path"]
        
        # Read source content
        src_content = src_file.read_text(encoding="utf-8")
        
        # For UPDATE in broadcast mode, preserve local fields
        from cast.merge_cast import extract_yaml_and_body, CAST_FIELDS
        import yaml
        
        src_yaml, _, src_body = extract_yaml_and_body(src_content)
        dst_content = dst_file.read_text(encoding="utf-8")
        dst_yaml, _, _ = extract_yaml_and_body(dst_content)
        
        # Merge YAML: cast-* from source, local from destination
        merged_yaml = {}
        
        # Keep destination's local fields
        if dst_yaml:
            for key, value in dst_yaml.items():
                if not key.startswith("cast-"):
                    merged_yaml[key] = value
        
        # Update cast-* fields from source
        if src_yaml:
            if "cast-id" in src_yaml:
                merged_yaml["cast-id"] = src_yaml["cast-id"]
            
            cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
            for field in cast_field_order:
                if field in src_yaml:
                    merged_yaml[field] = src_yaml[field]
            
            for key in CAST_FIELDS:
                if key in src_yaml and key not in merged_yaml:
                    merged_yaml[key] = src_yaml[key]
        
        # Reconstruct content
        if merged_yaml:
            yaml_text = yaml.safe_dump(merged_yaml, sort_keys=False, allow_unicode=True)
            content = f"---\n{yaml_text}---\n{src_body}"
        else:
            content = src_body
        
        # Write atomically
        temp_file = dst_file.with_suffix(".tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(dst_file)
    
    def _perform_merge(
        self,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
        dst_config: VaultConfig,
    ) -> list[str]:
        """Perform a 3-way merge."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["dest_path"]
        
        # Get baseline from object store
        dst_objects = ObjectStore(dst_path)
        src_peer = PeerState(src_path, dst_config.vault_id)
        src_peer.load()
        
        baseline_entry = src_peer.get_baseline(action["cast_id"])
        if baseline_entry and "digest" in baseline_entry:
            base_content = dst_objects.get(baseline_entry["digest"])
            if base_content is None:
                # Try source objects
                src_objects = ObjectStore(src_path)
                base_content = src_objects.get(baseline_entry["digest"])
        else:
            base_content = ""
        
        if base_content is None:
            base_content = ""
        
        # Read current contents
        src_content = src_file.read_text(encoding="utf-8")
        dst_content = dst_file.read_text(encoding="utf-8")
        
        # Perform merge
        merged_content, conflicts = merge_cast_content(
            base_content, src_content, dst_content
        )
        
        # Write merged content
        temp_file = dst_file.with_suffix(".tmp")
        temp_file.write_text(merged_content, encoding="utf-8")
        temp_file.replace(dst_file)
        
        # Store merged content
        merged_digest = compute_normalized_digest(merged_content)
        dst_objects.put(merged_digest, merged_content)
        
        return conflicts


# Keep the old SyncEngine for backward compatibility
from cast.sync import SyncEngine