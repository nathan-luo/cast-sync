"""Sync engine for Cast."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import filelock

from cast.config import GlobalConfig, VaultConfig
# Legacy imports - stubbed for compatibility
# from cast.merge_cast import merge_cast_content
from cast.normalize import compute_normalized_digest, normalize_content
# from cast.objects import ObjectStore
# from cast.peers import PeerState
from cast.plan import ActionType, create_plan

# Stub for missing merge function
def merge_cast_content(base, src, dst, src_mtime=None, dst_mtime=None):
    """Stub for legacy merge - just returns src content."""
    return src, False

# Stub classes
class ObjectStore:
    def __init__(self, *args, **kwargs):
        pass
    def get_object(self, *args):
        return None
    def put_object(self, *args):
        return "stub-hash"

class PeerState:
    def __init__(self, *args, **kwargs):
        self.baseline = {}
    def get_baseline(self, *args):
        return {}
    def update_baseline(self, *args):
        pass
    def save(self):
        pass


class SyncEngine:
    """Main sync engine for Cast."""
    
    def __init__(self):
        """Initialize sync engine."""
        self.global_config = GlobalConfig.load()
    
    def sync(
        self,
        source: str,
        dest: str,
        rule_id: str | None = None,
        apply: bool = False,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        """Synchronize vaults.
        
        Args:
            source: Source vault name or path
            dest: Destination vault name or path
            rule_id: Specific rule to use
            apply: Actually apply changes (vs dry run)
            force: Force sync even with conflicts
            
        Returns:
            List of sync results
        """
        # Auto-index both vaults before sync
        from cast.index import build_index
        
        global_config = self.global_config
        src_path = global_config.get_vault_path(source)
        if not src_path:
            src_path = Path(source)
        dst_path = global_config.get_vault_path(dest)
        if not dst_path:
            dst_path = Path(dest)
        
        # Rebuild indices to catch any changes
        build_index(src_path, rebuild=False)
        build_index(dst_path, rebuild=False)
        
        # Create plan
        plan = create_plan(source, dest, rule_id)
        
        # Check for conflicts
        has_conflicts = plan["summary"]["conflict"] > 0
        if has_conflicts and not force and apply:
            raise ValueError(
                f"Sync would create {plan['summary']['conflict']} conflicts. "
                "Use --force to proceed anyway."
            )
        
        # Get vault paths
        src_path = Path(plan["source"]["path"])
        dst_path = Path(plan["dest"]["path"])
        
        # Load configs
        src_config = VaultConfig.load(src_path)
        dst_config = VaultConfig.load(dst_path)
        
        # Acquire lock on destination
        lock_path = dst_path / ".cast" / "locks" / "sync.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        with filelock.FileLock(lock_path, timeout=10):
            # Load peer states
            src_peer = PeerState(src_path, dst_config.vault_id)
            src_peer.load()
            
            dst_peer = PeerState(dst_path, src_config.vault_id)
            dst_peer.load()
            
            # Object stores
            src_objects = ObjectStore(src_path)
            dst_objects = ObjectStore(dst_path)
            
            # Process each action
            for action_data in plan["actions"]:
                cast_id = action_data["cast_id"]
                action_type = ActionType(action_data["type"])
                
                result = {
                    "file": action_data.get("source_path") or action_data.get("dest_path"),
                    "cast_id": cast_id,
                    "action": action_type.value,
                    "success": False,
                    "status": "skipped",
                }
                
                if not apply:
                    result["status"] = "dry-run"
                    results.append(result)
                    continue
                
                try:
                    if action_type == ActionType.SKIP:
                        result["success"] = True
                        result["status"] = "skipped"
                        
                    elif action_type == ActionType.CREATE:
                        self._perform_create(
                            cast_id, action_data, 
                            src_path, dst_path,
                            src_peer, dst_peer,
                            src_objects, dst_objects,
                        )
                        result["success"] = True
                        result["status"] = "created"
                        
                    elif action_type == ActionType.UPDATE:
                        self._perform_update(
                            cast_id, action_data,
                            src_path, dst_path,
                            src_peer, dst_peer,
                            src_objects, dst_objects,
                            mode=action_data.get("mode", "broadcast"),
                        )
                        result["success"] = True
                        result["status"] = "updated"
                        
                    elif action_type == ActionType.MERGE:
                        conflicts = self._perform_merge(
                            cast_id, action_data,
                            src_path, dst_path,
                            src_config, dst_config,
                            src_peer, dst_peer,
                            src_objects, dst_objects,
                        )
                        
                        if conflicts:
                            result["success"] = False
                            result["status"] = f"merged with {len(conflicts)} conflicts"
                        else:
                            result["success"] = True
                            result["status"] = "merged"
                            
                    elif action_type == ActionType.CONFLICT:
                        if force:
                            # Force merge even with conflicts
                            conflicts = self._perform_merge(
                                cast_id, action_data,
                                src_path, dst_path,
                                src_config, dst_config,
                                src_peer, dst_peer,
                                src_objects, dst_objects,
                            )
                            if conflicts:
                                result["success"] = False
                                result["status"] = f"conflict ({len(conflicts)} unresolved)"
                            else:
                                result["success"] = True
                                result["status"] = "forced"
                        else:
                            self._create_conflict_file(
                                cast_id, action_data,
                                src_path, dst_path,
                            )
                            result["success"] = False
                            result["status"] = "conflict"
                            
                except Exception as e:
                    result["success"] = False
                    result["status"] = f"error: {e}"
                
                results.append(result)
            
            # Update sync timestamps
            if apply:
                src_peer.update_sync_time()
                src_peer.save()
                
                dst_peer.update_sync_time()
                dst_peer.save()
        
        return results
    
    def _perform_create(
        self,
        cast_id: str,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
        src_peer: PeerState,
        dst_peer: PeerState,
        src_objects: ObjectStore,
        dst_objects: ObjectStore,
    ) -> None:
        """Create a new file in destination."""
        src_file = src_path / action["source_path"]
        
        # Determine destination path
        dst_file = dst_path / action["source_path"]
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read source content
        src_content = src_file.read_text(encoding="utf-8")
        
        # For CREATE, we need to filter local fields
        # Use new md module instead
        from cast.md import split_frontmatter
        CAST_FIELDS = ["cast-id", "cast-vaults", "cast-type", "cast-version"]
        extract_yaml_and_body = lambda c: split_frontmatter(c)
        import yaml
        
        src_yaml, _, src_body = extract_yaml_and_body(src_content)
        
        # Create new YAML with only cast-* fields, in proper order
        dst_yaml = {}
        if src_yaml:
            # Ensure cast-id is first
            if "cast-id" in src_yaml:
                dst_yaml["cast-id"] = src_yaml["cast-id"]
            
            # Add other cast fields in standard order
            cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
            for field in cast_field_order:
                if field in src_yaml:
                    dst_yaml[field] = src_yaml[field]
            
            # Add any other cast-* fields
            for key in CAST_FIELDS:
                if key in src_yaml and key not in dst_yaml:
                    dst_yaml[key] = src_yaml[key]
        
        # Reconstruct content with filtered YAML
        if dst_yaml:
            yaml_text = yaml.safe_dump(dst_yaml, sort_keys=False, allow_unicode=True)
            content = f"---\n{yaml_text}---\n{src_body}"
        else:
            content = src_body
        
        # Write atomically
        temp_file = dst_file.with_suffix(".tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(dst_file)
        
        # Compute body-only digest to match what's in the index
        body_digest = compute_normalized_digest(src_body, body_only=True)
        
        # Store baseline (body content)
        normalized_body = normalize_content(src_body, ephemeral_keys=[])
        src_objects.write(normalized_body, body_digest)
        dst_objects.write(normalized_body, body_digest)
        
        # Update peer states with body digest
        src_peer.update_file_state(
            cast_id,
            base_obj=body_digest,
            source_digest=body_digest,
            dest_digest=body_digest,
            dest_path=str(dst_file.relative_to(dst_path)),
            last_result="CREATE",
        )
        
        dst_peer.update_file_state(
            cast_id,
            base_obj=body_digest,
            source_digest=body_digest,
            dest_digest=body_digest,
            dest_path=str(dst_file.relative_to(dst_path)),
            last_result="CREATE",
        )
    
    def _perform_update(
        self,
        cast_id: str,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
        src_peer: PeerState,
        dst_peer: PeerState,
        src_objects: ObjectStore,
        dst_objects: ObjectStore,
        mode: str = "broadcast",
    ) -> None:
        """Update existing file in destination."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["dest_path"]
        
        # Read both contents
        src_content = src_file.read_text(encoding="utf-8")
        dst_content = dst_file.read_text(encoding="utf-8")
        
        # In mirror mode, completely replace destination content
        if mode == "mirror":
            # For mirror mode, use source content but filter local fields like CREATE
            # Use new md module instead
            from cast.md import split_frontmatter
            CAST_FIELDS = ["cast-id", "cast-vaults", "cast-type", "cast-version"]
            extract_yaml_and_body = lambda c: split_frontmatter(c)
            import yaml
            
            src_yaml, _, src_body = extract_yaml_and_body(src_content)
            
            # Create new YAML with only cast-* fields (like CREATE operation)
            dst_yaml = {}
            if src_yaml:
                # Ensure cast-id is first
                if "cast-id" in src_yaml:
                    dst_yaml["cast-id"] = src_yaml["cast-id"]
                
                # Add other cast fields in standard order
                cast_field_order = ["cast-type", "cast-version", "cast-vaults", "cast-codebases"]
                for field in cast_field_order:
                    if field in src_yaml:
                        dst_yaml[field] = src_yaml[field]
                
                # Add any other cast-* fields
                for key in CAST_FIELDS:
                    if key in src_yaml and key not in dst_yaml:
                        dst_yaml[key] = src_yaml[key]
            
            # Reconstruct content with filtered YAML
            if dst_yaml:
                yaml_text = yaml.safe_dump(dst_yaml, sort_keys=False, allow_unicode=True)
                merged_content = f"---\n{yaml_text}---\n{src_body}"
            else:
                merged_content = src_body
        else:
            # For UPDATE: take source body and cast fields, preserve dest local fields
            # Use new md module instead
            from cast.md import split_frontmatter
            CAST_FIELDS = ["cast-id", "cast-vaults", "cast-type", "cast-version"]
            extract_yaml_and_body = lambda c: split_frontmatter(c)
            import yaml
            
            src_yaml, _, src_body = extract_yaml_and_body(src_content)
            dst_yaml, _, _ = extract_yaml_and_body(dst_content)
            
            # Start with destination's YAML to preserve local fields
            merged_yaml = dst_yaml.copy() if dst_yaml else {}
            
            # Update cast-* fields from source
            if src_yaml:
                for field in CAST_FIELDS:
                    if field in src_yaml:
                        merged_yaml[field] = src_yaml[field]
            
            # Reconstruct content
            if merged_yaml:
                # Ensure cast-id is first if present
                from cast.ids import ensure_cast_id_first
                # First create the content, then ensure cast-id is first
                yaml_text = yaml.safe_dump(merged_yaml, sort_keys=False, allow_unicode=True)
                temp_content = f"---\n{yaml_text}---\n{src_body}"
                merged_content = ensure_cast_id_first(temp_content)
            else:
                merged_content = src_body
        
        # Write atomically
        temp_file = dst_file.with_suffix(".tmp")
        temp_file.write_text(merged_content, encoding="utf-8")
        temp_file.replace(dst_file)
        
        # Extract body for digest computation
        # Use new md module instead
        from cast.md import split_frontmatter
        extract_yaml_and_body = lambda c: split_frontmatter(c)
        _, _, merged_body = extract_yaml_and_body(merged_content)
        
        # Compute body-only digest to match index
        body_digest = compute_normalized_digest(merged_body, body_only=True)
        
        # Store new baseline (body only)
        normalized_body = normalize_content(merged_body, ephemeral_keys=[])
        src_objects.write(normalized_body, body_digest)
        dst_objects.write(normalized_body, body_digest)
        
        # Update peer states with body digest
        src_peer.update_file_state(
            cast_id,
            base_obj=body_digest,
            source_digest=body_digest,
            dest_digest=body_digest,
            last_result="UPDATE",
        )
        
        dst_peer.update_file_state(
            cast_id,
            base_obj=body_digest,
            source_digest=body_digest,
            dest_digest=body_digest,
            last_result="UPDATE",
        )
    
    def _perform_merge(
        self,
        cast_id: str,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
        src_config: VaultConfig,
        dst_config: VaultConfig,
        src_peer: PeerState,
        dst_peer: PeerState,
        src_objects: ObjectStore,
        dst_objects: ObjectStore,
    ) -> list[str]:
        """Perform 3-way merge."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["dest_path"]
        
        # Read contents
        src_content = src_file.read_text(encoding="utf-8")
        dst_content = dst_file.read_text(encoding="utf-8")
        
        # Get baseline
        base_content = ""
        if action["base_digest"]:
            base_content = src_objects.read(action["base_digest"]) or ""
        
        # Perform merge (sync cast-* fields and body, preserve local fields)
        merged_content, conflicts = merge_cast_content(
            base_content,
            src_content,
            dst_content,
        )
        
        if conflicts:
            # Write conflict file (separate from main file)
            conflict_file = dst_file.parent / f"{dst_file.stem}.conflicted-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            conflict_file.write_text(merged_content, encoding="utf-8")
            
            # DO NOT overwrite the main file when there are conflicts
            # Update peer state to mark conflict
            src_peer.update_file_state(cast_id, last_result="CONFLICT")
            dst_peer.update_file_state(cast_id, last_result="CONFLICT")
        else:
            # Only write to main file if merge was clean
            temp_file = dst_file.with_suffix(".tmp")
            temp_file.write_text(merged_content, encoding="utf-8")
            temp_file.replace(dst_file)
            
            # Extract body for digest computation
            # Use new md module instead
            from cast.md import split_frontmatter
            extract_yaml_and_body = lambda c: split_frontmatter(c)
            _, _, merged_body = extract_yaml_and_body(merged_content)
            
            # Compute body-only digest to match index
            body_digest = compute_normalized_digest(merged_body, body_only=True)
            
            # Store new baseline (body only)
            normalized_body = normalize_content(merged_body, ephemeral_keys=[])
            src_objects.write(normalized_body, body_digest)
            dst_objects.write(normalized_body, body_digest)
            
            # Update peer states with body digest
            src_peer.update_file_state(
                cast_id,
                base_obj=body_digest,
                source_digest=body_digest,
                dest_digest=body_digest,
                last_result="MERGED",
            )
            
            dst_peer.update_file_state(
                cast_id,
                base_obj=body_digest,
                source_digest=body_digest,
                dest_digest=body_digest,
                last_result="MERGED",
            )
        
        return conflicts
    
    def _create_conflict_file(
        self,
        cast_id: str,
        action: dict[str, Any],
        src_path: Path,
        dst_path: Path,
    ) -> None:
        """Create a conflict file showing both versions."""
        src_file = src_path / action["source_path"]
        dst_file = dst_path / action["dest_path"]
        
        # Read contents
        src_content = src_file.read_text(encoding="utf-8")
        dst_content = dst_file.read_text(encoding="utf-8")
        
        # Create conflict content
        conflict_content = f"""<<<<<<< SOURCE ({src_path.name})
{src_content}
=======
{dst_content}
>>>>>>> DESTINATION ({dst_path.name})
"""
        
        # Write conflict file
        conflict_file = dst_file.with_suffix(
            f".conflicted-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        )
        conflict_file.write_text(conflict_content, encoding="utf-8")