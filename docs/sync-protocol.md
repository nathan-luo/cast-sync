# Cast Sync Protocol

## Overview

The Cast Sync Protocol defines how vaults exchange and synchronize content. It's designed to be:
- **Distributed**: No central server required
- **Conflict-aware**: Detects and handles conflicts intelligently
- **Content-preserving**: Never loses data, creates conflicts when needed
- **Incremental**: Only syncs changes since last sync

## Core Concepts

### 1. File Identity

Each file has a unique identity across all vaults:

```yaml
cast-id: 550e8400-e29b-41d4-a716-446655440000  # UUID v4
```

This ID:
- Persists across renames and moves
- Links the same logical file across vaults
- Enables tracking sync history

### 2. Content Digests

Files are tracked using SHA-256 digests:

```python
# Body digest (for change detection)
body_only_digest = sha256(markdown_body_without_frontmatter)

# Full digest (for integrity)
full_digest = sha256(entire_file_content)
```

### 3. Vault Roles

Vaults can have two roles that determine sync behavior:

#### Cast Role (Broadcast Source)
```yaml
cast-vaults:
- main-vault (cast)    # This vault broadcasts
- backup-vault (sync)  # Receives updates
```

#### Sync Role (Bidirectional)
```yaml
cast-vaults:
- desktop (sync)  # Can send and receive
- laptop (sync)   # Can send and receive
```

## Sync Modes

### Broadcast Mode (Unidirectional)

```
┌─────────────┐         ┌─────────────┐
│ Vault (cast)│ ──────> │ Vault (sync)│
└─────────────┘         └─────────────┘
     Source             Destination

Actions: CREATE, UPDATE, DELETE
Direction: One-way only
Conflicts: None (destination always accepts)
```

**Protocol Steps:**

1. **Source Analysis**
   - Load source index
   - Identify cast-role files

2. **Destination Analysis**
   - Load destination index
   - Check existing files

3. **Action Generation**
   - CREATE: File exists in source, not in destination
   - UPDATE: Source modified, destination unchanged
   - DELETE: File removed from source

4. **Execution**
   - Apply changes to destination
   - No reverse sync
   - No conflict checking

### Bidirectional Mode

```
┌─────────────┐         ┌─────────────┐
│ Vault (sync)│ <────> │ Vault (sync)│
└─────────────┘         └─────────────┘
    Vault A              Vault B

Actions: CREATE, UPDATE, DELETE, MERGE
Direction: Two-way
Conflicts: Detected and preserved
```

**Protocol Steps:**

1. **Baseline Retrieval**
   - Load peer state from last sync
   - Retrieve baseline digests

2. **Change Detection**
   ```
   Source changed = (current_source != baseline)
   Dest changed = (current_dest != baseline)
   ```

3. **Action Generation**
   - CREATE: New in source, not in destination
   - UPDATE: Changed in source only
   - MERGE: Changed in both (potential conflict)
   - DELETE: Removed from source
   - SKIP: Already synchronized

4. **Conflict Detection**
   - Simple append: One file extends the other
   - True conflict: Overlapping changes

## Peer State Protocol

### State Structure

Each vault maintains state about its peers:

```json
{
  "peer_id": "other-vault",
  "last_sync": "2024-01-01T00:00:00Z",
  "files": {
    "cast-id-1": {
      "source_digest": "sha256:abc...",
      "dest_digest": "sha256:def...",
      "base_obj": "sha256:ghi...",
      "last_result": "UPDATE",
      "last_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### State Updates

After each sync operation:

1. **Success Case**
   ```python
   peer_state.update_file_state(
       cast_id=file_id,
       source_digest=current_source,
       dest_digest=current_dest,
       base_obj=merged_digest,
       result="UPDATE"
   )
   ```

2. **Conflict Case**
   ```python
   peer_state.update_file_state(
       cast_id=file_id,
       source_digest=current_source,
       dest_digest=current_dest,
       base_obj=baseline_digest,  # Keep old baseline
       result="CONFLICT"
   )
   ```

## Merge Protocol

### 3-Way Merge Process

When both vaults modify a file:

```
     Baseline (B)
         / \
        /   \
   Source   Destination
     (S)      (D)
        \   /
         \ /
      Merged (M)
```

**Steps:**

1. **Retrieve Baseline**
   ```python
   baseline = object_store.read(peer_state.base_obj)
   ```

2. **Separate YAML and Body**
   ```python
   base_yaml, base_body = extract(baseline)
   src_yaml, src_body = extract(source)
   dst_yaml, dst_body = extract(destination)
   ```

3. **Merge YAML**
   - Take cast-* fields from source
   - Preserve local fields from destination
   ```python
   merged_yaml = dst_yaml.copy()  # Keep local fields
   for field in CAST_FIELDS:
       merged_yaml[field] = src_yaml[field]  # Update cast fields
   ```

4. **Merge Body**
   - Attempt automatic merge
   - Detect conflicts
   - Create conflict markers if needed

5. **Store New Baseline**
   ```python
   new_baseline = merged_content
   object_store.write(new_baseline, digest)
   peer_state.base_obj = digest
   ```

### Conflict Detection Algorithm

```python
def detect_conflict(base, source, dest):
    # Strip whitespace for comparison
    base_stripped = base.strip()
    src_stripped = source.strip()
    dst_stripped = dest.strip()
    
    # Check for simple append
    if src_stripped.startswith(dst_stripped):
        return "SOURCE_EXTENDS"  # Use source
    elif dst_stripped.startswith(src_stripped):
        return "DEST_EXTENDS"    # Use destination
    
    # Check if only one changed
    if src_stripped == base_stripped:
        return "DEST_ONLY"       # Use destination
    elif dst_stripped == base_stripped:
        return "SOURCE_ONLY"     # Use source
    
    # Both changed differently
    return "CONFLICT"            # Need manual resolution
```

## Action Execution Protocol

### CREATE Action

```python
def execute_create(action, src_path, dst_path):
    src_file = src_path / action.source_path
    dst_file = dst_path / action.dest_path
    
    # Ensure directory exists
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy content
    content = src_file.read_text()
    
    # Atomic write
    temp_file = dst_file.with_suffix('.tmp')
    temp_file.write_text(content)
    temp_file.replace(dst_file)
    
    # Update indices and peer state
    update_index(dst_file)
    update_peer_state(action.cast_id, "CREATE")
```

### UPDATE Action

```python
def execute_update(action, src_path, dst_path):
    # Read source content
    src_content = read_file(src_path / action.source_path)
    
    # Preserve local fields if exists
    if dst_file.exists():
        dst_yaml = extract_yaml(dst_file)
        merged = preserve_local_fields(src_content, dst_yaml)
    else:
        merged = src_content
    
    # Write atomically
    atomic_write(dst_file, merged)
    
    # Store baseline
    store_baseline(merged)
```

### MERGE Action

```python
def execute_merge(action, src_path, dst_path):
    # Get baseline
    baseline = retrieve_baseline(action.base_digest)
    
    # Read current versions
    source = read_file(src_path / action.source_path)
    dest = read_file(dst_path / action.dest_path)
    
    # Perform 3-way merge
    merged, conflicts = merge_3way(baseline, source, dest)
    
    if conflicts:
        # Create conflict file
        write_conflict_file(merged, conflicts)
        update_peer_state(action.cast_id, "CONFLICT")
    else:
        # Write merged content
        atomic_write(dst_file, merged)
        store_baseline(merged)
        update_peer_state(action.cast_id, "MERGE")
```

## Conflict File Format

When conflicts occur, a special file is created:

```markdown
---
cast-id: 550e8400-e29b-41d4-a716-446655440000
cast-conflict: true
cast-conflict-time: 2024-01-01T00:00:00Z
---

# Content before conflict

<<<<<<< SOURCE (vault1)
Content from source vault
=======
Content from destination vault
>>>>>>> DESTINATION (vault2)

# Content after conflict
```

## Index Protocol

### Index Structure

```json
{
  "cast-id-1": {
    "path": "notes/example.md",
    "digest": "sha256:abc123...",
    "size": 1234,
    "updated": "2024-01-01T00:00:00Z",
    "title": "Example Note",
    "tags": ["tag1", "tag2"],
    "cast_vaults": ["vault1 (sync)", "vault2 (sync)"],
    "cast_version": "1"
  }
}
```

### Index Update Protocol

1. **File Discovery**
   ```python
   files = select_files(include_patterns, exclude_patterns)
   ```

2. **Digest Computation**
   ```python
   for file in files:
       content = read_file(file)
       body = extract_body(content)
       digest = sha256(body)
   ```

3. **Cast-ID Management**
   ```python
   cast_id = extract_cast_id(content)
   if not cast_id:
       cast_id = generate_uuid4()
       content = inject_cast_id(content, cast_id)
       write_file(file, content)
   ```

4. **Index Entry Update**
   ```python
   index[cast_id] = {
       "path": relative_path,
       "digest": digest,
       "size": file_size,
       "updated": mtime,
       # ... metadata
   }
   ```

## Object Store Protocol

### Storage Format

Objects are stored by their content digest:

```
.cast/objects/
├── abc123def456...  # SHA-256 digest as filename
├── 789012345678...
└── ...
```

### Storage Operations

```python
def store_object(content: str) -> str:
    digest = sha256(content)
    path = objects_dir / digest
    
    if not path.exists():
        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_text(content)
        temp.replace(path)
    
    return digest

def retrieve_object(digest: str) -> str | None:
    path = objects_dir / digest
    return path.read_text() if path.exists() else None
```

## Lock Protocol

### Vault Locking

Prevents concurrent modifications:

```python
lock_file = vault_path / ".cast/.lock"

with FileLock(lock_file, timeout=30):
    # Exclusive access to vault
    perform_sync_operations()
```

### Lock Recovery

If a process crashes:

1. Check lock age
2. If older than timeout, remove
3. Retry operation

## Network Protocol (Future)

### Planned Remote Sync

```
┌──────────┐  HTTPS  ┌──────────┐
│  Client  │ <────> │  Server  │
└──────────┘         └──────────┘

1. Client: GET /api/index
2. Server: Returns index.json
3. Client: Calculates diff
4. Client: POST /api/sync
   Body: {actions: [...]}
5. Server: Applies actions
6. Server: Returns results
```

### Authentication

- Token-based authentication
- Per-vault access control
- Optional encryption

## Safety Guarantees

### 1. No Data Loss

- Never overwrites without consent
- Creates conflict files for ambiguous cases
- Maintains object store history

### 2. Atomic Operations

- All file writes use temp + rename
- Index updates are atomic
- Peer state updates are atomic

### 3. Consistency

- Cast-IDs maintain file identity
- Digests ensure content integrity
- Peer states track sync history

### 4. Idempotency

- Running sync twice has no additional effect
- SKIP actions for already-synced files
- Baseline tracking prevents re-conflicts

## Protocol Versioning

### Current Version: 1

```yaml
cast-version: "1"
```

### Version Compatibility

- Forward compatible: Newer versions read older formats
- Backward compatible: Older versions reject newer formats
- Migration path: Upgrade command for version transitions

## Error Handling

### Protocol Errors

1. **Missing Cast-ID**: Generate and inject
2. **Digest Mismatch**: Re-index and retry
3. **Lock Timeout**: Retry with backoff
4. **Conflict During Merge**: Create conflict file
5. **Missing Baseline**: Treat as new merge

### Recovery Procedures

1. **Corrupted Index**
   ```bash
   cast index --force  # Rebuild from files
   ```

2. **Stuck Lock**
   ```bash
   rm .cast/.lock  # Remove stale lock
   ```

3. **Missing Objects**
   ```bash
   cast repair  # Rebuild object store
   ```

## Performance Considerations

### Optimization Strategies

1. **Incremental Indexing**
   - Only reindex modified files
   - Use mtime for quick checks

2. **Parallel Processing**
   - Index files in parallel
   - Apply non-conflicting actions concurrently

3. **Digest Caching**
   - Cache digests for unchanged files
   - Validate cache on mtime change

4. **Compression** (Future)
   - Compress objects in store
   - Compress network transfers

## Security Considerations

### Threat Model

1. **Local Attacks**: Filesystem permissions
2. **Network Attacks**: TLS for remote sync
3. **Data Integrity**: SHA-256 verification

### Mitigations

1. **Access Control**
   - Respect OS file permissions
   - Vault-level access tokens

2. **Integrity Verification**
   - Verify digests after transfer
   - Check index signatures (future)

3. **Audit Trail**
   - Log all sync operations
   - Track modification history