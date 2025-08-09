# Cast Sync Architecture

## System Architecture

Cast Sync follows a modular, layered architecture designed for extensibility and maintainability.

```
┌─────────────────────────────────────────┐
│           CLI Interface (cli.py)        │
├─────────────────────────────────────────┤
│         Sync Engine (sync.py)           │
├─────────┬───────────────┬───────────────┤
│  Plan   │    Actions    │   Conflicts   │
│(plan.py)│  (CREATE,     │ (resolve.py)  │
│         │   UPDATE,     │               │
│         │   DELETE,     │               │
│         │   MERGE)      │               │
├─────────┴───────────────┴───────────────┤
│         Core Components                 │
│  ┌──────────┬──────────┬──────────┐    │
│  │  Index   │  Peers   │ Objects  │    │
│  │(index.py)│(peers.py)│(objects.py)   │
│  └──────────┴──────────┴──────────┘    │
├─────────────────────────────────────────┤
│         Utilities                       │
│  ┌──────────┬──────────┬──────────┐    │
│  │   IDs    │ Normalize│  Merge   │    │
│  │ (ids.py) │(normalize│ (merge_* │    │
│  │          │   .py)   │   .py)   │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
```

## Core Components

### 1. CLI Interface (`cli.py`)

The command-line interface built with Typer, providing:
- Command routing and parameter parsing
- Rich terminal output with progress indicators
- Error handling and user feedback
- Commands: init, index, sync, conflicts, resolve, snapshot

### 2. Sync Engine (`sync.py`)

The heart of the synchronization system:

```python
class SyncEngine:
    def sync(source_vault, dest_vault, dry_run=False):
        # 1. Load vault configurations
        # 2. Create sync planner
        # 3. Generate sync plan
        # 4. Apply actions (if not dry_run)
        # 5. Update peer states
```

Key responsibilities:
- Orchestrates the entire sync process
- Manages vault locking for concurrent access safety
- Coordinates between planner and action executors
- Handles peer state updates

### 3. Sync Planner (`plan.py`)

Generates synchronization plans by comparing vault states:

```python
class SyncPlanner:
    def create_plan() -> list[SyncAction]:
        # 1. Compare source and destination indices
        # 2. Check peer states for baseline
        # 3. Determine sync mode (broadcast/bidirectional)
        # 4. Generate appropriate actions
        # 5. Detect conflicts vs simple appends
```

Action types:
- **CREATE**: File exists in source but not destination
- **UPDATE**: File changed in source, unchanged in destination
- **DELETE**: File removed from source
- **MERGE**: File changed in both, requires 3-way merge
- **SKIP**: Files already synchronized

### 4. Index Management (`index.py`)

Maintains file metadata and content tracking:

```python
class Index:
    def __init__(self, vault_path):
        self.index_path = vault_path / ".cast/index.json"
        self.entries = {}  # cast_id -> metadata
    
    def update(self, file_path):
        # Extract/generate cast-id
        # Compute content digest
        # Update metadata
        # Save to disk
```

Index entry structure:
```json
{
  "cast-id": "uuid-v4",
  "path": "relative/path/to/file.md",
  "digest": "sha256:...",
  "size": 1234,
  "updated": "2024-01-01T00:00:00Z",
  "title": "File Title",
  "tags": ["tag1", "tag2"],
  "cast_vaults": ["vault1 (sync)", "vault2 (cast)"]
}
```

### 5. Peer State Management (`peers.py`)

Tracks synchronization history between vault pairs:

```python
class PeerState:
    def __init__(self, vault_path, peer_id):
        self.state_path = vault_path / f".cast/peers/{peer_id}.json"
        self.files = {}  # cast_id -> file state
    
    def update_file_state(self, cast_id, result):
        # Update baseline digest
        # Record sync result
        # Save timestamp
```

Peer state structure:
```json
{
  "peer_id": "vault2",
  "last_sync": "2024-01-01T00:00:00Z",
  "files": {
    "cast-id": {
      "source_digest": "sha256:...",
      "dest_digest": "sha256:...",
      "base_obj": "sha256:...",
      "last_result": "UPDATE",
      "last_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### 6. Object Store (`objects.py`)

Content-addressable storage for file versions:

```python
class ObjectStore:
    def __init__(self, vault_path):
        self.objects_dir = vault_path / ".cast/objects"
    
    def write(self, content, digest):
        # Store content by digest
        # Enable deduplication
        # Support version history
    
    def read(self, digest):
        # Retrieve content by digest
        # Used for baseline in 3-way merge
```

## Merge System

### Content-Aware Merging (`merge_cast.py`)

Handles YAML frontmatter and markdown body separately:

```python
def merge_cast_content(base, source, dest):
    # 1. Extract YAML and body from each version
    # 2. Merge YAML: cast-* from source, local from dest
    # 3. Merge body: block-based or line-based
    # 4. Detect conflicts
    # 5. Reconstruct merged content
```

### Block-Based Merging (`merge_blocks.py`)

Understands markdown structure:
- Treats headers as block boundaries
- Merges at block level for better semantics
- Reduces false conflicts from line-based merging

### Conflict Detection

Smart conflict detection distinguishes between:
- **Simple appends**: One version extends the other
- **True conflicts**: Overlapping changes requiring resolution
- **Mergeable changes**: Non-overlapping modifications

## File Processing Pipeline

### 1. Content Normalization (`normalize.py`)

Ensures consistent content comparison:
- Normalizes line endings (CRLF → LF)
- Strips trailing whitespace
- Removes ephemeral fields from comparison
- Handles Unicode normalization

### 2. ID Management (`ids.py`)

Manages cast-id lifecycle:
- Generates new UUIDs for untracked files
- Extracts existing IDs from frontmatter
- Ensures cast-id is first field in YAML
- Validates ID format and uniqueness

### 3. Digest Computation

Two-level digest system:
- **Body digest**: For change detection (excludes frontmatter)
- **Full digest**: For content integrity
- Uses SHA-256 for cryptographic security
- Enables efficient incremental sync

## Sync Protocol

### Broadcast Mode (Unidirectional)

```
Source (cast) → Destination (sync)
─────────────────────────────────→
    CREATE/UPDATE/DELETE only
    No reverse sync
    Source is authoritative
```

### Bidirectional Mode

```
Vault A (sync) ↔ Vault B (sync)
←─────────────────────────────────→
    Full bidirectional sync
    3-way merge with baseline
    Conflict detection
    Both vaults equal
```

### Sync Process Flow

```
1. PLANNING PHASE
   ├─ Load indices
   ├─ Load peer states
   ├─ Compare files
   └─ Generate actions

2. EXECUTION PHASE
   ├─ Apply CREATE actions
   ├─ Apply UPDATE actions
   ├─ Apply DELETE actions
   └─ Apply MERGE actions

3. FINALIZATION PHASE
   ├─ Update indices
   ├─ Update peer states
   ├─ Store baselines
   └─ Write metadata
```

## Safety and Reliability

### Atomic Operations

All file operations are atomic:
```python
# Write to temporary file first
temp_file = target.with_suffix('.tmp')
temp_file.write_text(content)
# Atomic rename
temp_file.replace(target)
```

### Locking Mechanism

Prevents concurrent modifications:
```python
with filelock.FileLock(lock_path, timeout=10):
    # Exclusive access to vault
    perform_sync_operations()
```

### Data Integrity

- Never overwrites without user consent
- Creates conflict files for manual resolution
- Maintains object store for recovery
- Validates digests after operations

## Configuration System (`config.py`)

### Vault Configuration

```yaml
cast-version: '1'
vault:
  id: vault_name
  root: /path/to/vault
index:
  include:
    - "**/*.md"
  exclude:
    - ".obsidian/**"
    - ".git/**"
sync:
  rules: []  # Deprecated, uses YAML frontmatter
merge:
  ephemeral_keys:
    - updated
    - last_synced
```

### Selection Rules (`select.py`)

File selection using glob patterns:
- Include patterns for files to sync
- Exclude patterns for files to ignore
- Respects .gitignore-style matching
- Supports recursive wildcards

## Performance Optimizations

### Incremental Indexing
- Only re-indexes changed files
- Uses file modification time for quick checks
- Caches digests when unchanged

### Efficient Diff Computation
- Body-only comparison for change detection
- Baseline tracking reduces comparison scope
- Parallel processing for large vaults

### Memory Management
- Streaming for large files
- Lazy loading of content
- Efficient digest computation

## Extension Points

### Custom Merge Strategies
- Pluggable merge algorithms
- Format-specific handlers
- User-defined conflict resolution

### Vault Providers
- Local filesystem (current)
- Remote storage (future)
- Cloud providers (future)

### Metadata Extractors
- Obsidian tags and links
- Custom frontmatter fields
- Content analysis plugins

## Security Considerations

### Data Privacy
- All operations local
- No network communication
- No telemetry or tracking

### Content Integrity
- SHA-256 digest verification
- Atomic file operations
- Backup via object store

### Access Control
- Respects filesystem permissions
- Vault-level locking
- No privilege escalation