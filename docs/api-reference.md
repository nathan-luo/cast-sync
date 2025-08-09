# Cast Sync API Reference

## Core Modules

### cast.sync

Main synchronization engine.

#### Class: `SyncEngine`

```python
class SyncEngine:
    def __init__(self, lock_timeout: int = 30)
```

**Methods:**

##### `sync(source_path, dest_path, apply, force, verbose)`

Perform synchronization between two vaults.

**Parameters:**
- `source_path` (Path): Source vault path
- `dest_path` (Path): Destination vault path
- `apply` (bool): Apply changes (False for dry-run)
- `force` (bool): Ignore safety checks
- `verbose` (bool): Verbose output

**Returns:**
- `tuple[list[SyncResult], SyncStats]`: Results and statistics

**Example:**
```python
from cast.sync import SyncEngine

engine = SyncEngine()
results, stats = engine.sync(
    source_path=Path("/vault1"),
    dest_path=Path("/vault2"),
    apply=True,
    verbose=True
)
```

### cast.plan

Sync planning and action generation.

#### Class: `SyncPlanner`

```python
class SyncPlanner:
    def __init__(self, src_config, dst_config, src_index, dst_index, 
                 src_peer, dst_peer, src_objects, dst_objects)
```

**Methods:**

##### `create_plan() -> list[SyncAction]`

Generate sync plan based on vault states.

**Returns:**
- `list[SyncAction]`: List of sync actions to perform

#### Class: `SyncAction`

```python
@dataclass
class SyncAction:
    cast_id: str
    action_type: ActionType
    source_path: str
    dest_path: str
    source_digest: str | None
    dest_digest: str | None
    base_digest: str | None
    reason: str
```

#### Enum: `ActionType`

```python
class ActionType(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MERGE = "MERGE"
    SKIP = "SKIP"
```

### cast.index

File indexing and metadata management.

#### Class: `Index`

```python
class Index:
    def __init__(self, vault_path: Path)
```

**Methods:**

##### `load() -> dict[str, dict]`

Load index from disk.

**Returns:**
- `dict`: Index entries keyed by cast-id

##### `save(entries: dict[str, dict])`

Save index to disk.

**Parameters:**
- `entries` (dict): Index entries to save

##### `update(file_path: Path) -> dict | None`

Update index entry for a file.

**Parameters:**
- `file_path` (Path): File to index

**Returns:**
- `dict | None`: Updated entry or None if excluded

##### `get_by_cast_id(cast_id: str) -> dict | None`

Get entry by cast-id.

**Parameters:**
- `cast_id` (str): Cast ID to look up

**Returns:**
- `dict | None`: Entry or None if not found

**Example:**
```python
from cast.index import Index

index = Index(Path("/my-vault"))
entries = index.load()

# Update specific file
entry = index.update(Path("/my-vault/notes/test.md"))

# Save changes
index.save(entries)
```

### cast.peers

Peer state management for sync tracking.

#### Class: `PeerState`

```python
class PeerState:
    def __init__(self, vault_path: Path, peer_id: str)
```

**Methods:**

##### `load() -> dict`

Load peer state from disk.

**Returns:**
- `dict`: Peer state data

##### `save(state: dict)`

Save peer state to disk.

**Parameters:**
- `state` (dict): State data to save

##### `get_file_state(cast_id: str) -> dict | None`

Get sync state for a file.

**Parameters:**
- `cast_id` (str): File's cast ID

**Returns:**
- `dict | None`: File state or None

##### `update_file_state(cast_id, source_digest, dest_digest, base_obj, result)`

Update file sync state.

**Parameters:**
- `cast_id` (str): File's cast ID
- `source_digest` (str): Source file digest
- `dest_digest` (str): Destination file digest
- `base_obj` (str | None): Baseline object digest
- `result` (str): Sync result (UPDATE, MERGE, CONFLICT, etc.)

### cast.objects

Content-addressable object storage.

#### Class: `ObjectStore`

```python
class ObjectStore:
    def __init__(self, vault_path: Path)
```

**Methods:**

##### `write(content: str, digest: str) -> str`

Store content by digest.

**Parameters:**
- `content` (str): Content to store
- `digest` (str): Content digest

**Returns:**
- `str`: Stored object digest

##### `read(digest: str) -> str | None`

Read content by digest.

**Parameters:**
- `digest` (str): Object digest

**Returns:**
- `str | None`: Content or None if not found

##### `exists(digest: str) -> bool`

Check if object exists.

**Parameters:**
- `digest` (str): Object digest

**Returns:**
- `bool`: True if exists

### cast.ids

Cast ID management and frontmatter handling.

#### Functions:

##### `generate_cast_id() -> str`

Generate new UUID v4 cast-id.

**Returns:**
- `str`: New cast-id

##### `extract_frontmatter(content: str) -> tuple[dict | None, str, str]`

Extract YAML frontmatter from markdown.

**Parameters:**
- `content` (str): Markdown content

**Returns:**
- `tuple[dict | None, str, str]`: (frontmatter_dict, frontmatter_text, body)

##### `inject_cast_id(content: str, cast_id: str) -> str`

Inject cast-id into markdown content.

**Parameters:**
- `content` (str): Markdown content
- `cast_id` (str): Cast ID to inject

**Returns:**
- `str`: Content with cast-id

##### `ensure_cast_id_first(content: str) -> str`

Ensure cast-id is first field in frontmatter.

**Parameters:**
- `content` (str): Markdown content

**Returns:**
- `str`: Content with reordered frontmatter

**Example:**
```python
from cast.ids import generate_cast_id, inject_cast_id

# Generate new ID
cast_id = generate_cast_id()

# Inject into content
content = "# My Note\n\nContent here"
updated = inject_cast_id(content, cast_id)
```

### cast.merge_cast

Content-aware merging for Cast files.

#### Functions:

##### `merge_cast_content(base_content, src_content, dst_content) -> tuple[str, list[str]]`

Perform 3-way merge of Cast content.

**Parameters:**
- `base_content` (str): Baseline content
- `src_content` (str): Source content
- `dst_content` (str): Destination content

**Returns:**
- `tuple[str, list[str]]`: (merged_content, conflicts)

##### `extract_yaml_and_body(content: str) -> tuple[dict, str, str]`

Extract YAML and body separately.

**Parameters:**
- `content` (str): Markdown content

**Returns:**
- `tuple[dict, str, str]`: (yaml_dict, yaml_text, body)

### cast.merge_blocks

Block-based merge for markdown content.

#### Functions:

##### `merge_body_blocks(base_body, src_body, dst_body) -> tuple[str, list[str]]`

Merge markdown bodies using block detection.

**Parameters:**
- `base_body` (str): Baseline body
- `src_body` (str): Source body
- `dst_body` (str): Destination body

**Returns:**
- `tuple[str, list[str]]`: (merged_body, conflicts)

### cast.normalize

Content normalization utilities.

#### Functions:

##### `normalize_content(content: str, ephemeral_keys: list[str]) -> str`

Normalize content for comparison.

**Parameters:**
- `content` (str): Content to normalize
- `ephemeral_keys` (list[str]): Keys to exclude from comparison

**Returns:**
- `str`: Normalized content

##### `compute_normalized_digest(content: str, body_only: bool = False) -> str`

Compute SHA-256 digest of normalized content.

**Parameters:**
- `content` (str): Content to hash
- `body_only` (bool): Hash body only (exclude frontmatter)

**Returns:**
- `str`: SHA-256 digest

### cast.resolve

Conflict resolution utilities.

#### Class: `ConflictResolver`

```python
class ConflictResolver:
    def __init__(self)
```

**Methods:**

##### `list_conflicts(vault_path: Path) -> list[Path]`

Find all conflict files in vault.

**Parameters:**
- `vault_path` (Path): Vault path

**Returns:**
- `list[Path]`: List of conflict file paths

##### `parse_conflict_file(file_path: Path) -> list[dict]`

Parse conflict markers from file.

**Parameters:**
- `file_path` (Path): Conflict file path

**Returns:**
- `list[dict]`: List of conflicts with source/dest/base content

##### `resolve_conflicts(vault_path: Path, strategy: str = "interactive")`

Resolve conflicts in vault.

**Parameters:**
- `vault_path` (Path): Vault path
- `strategy` (str): Resolution strategy (interactive, ours, theirs)

### cast.config

Configuration management.

#### Class: `VaultConfig`

```python
class VaultConfig:
    def __init__(self, vault_path: Path)
```

**Properties:**
- `vault_id` (str): Vault identifier
- `vault_root` (Path): Vault root path
- `include_patterns` (list[str]): Include globs
- `exclude_patterns` (list[str]): Exclude globs
- `ephemeral_keys` (list[str]): Keys to ignore in merge

**Methods:**

##### `load() -> dict`

Load configuration from disk.

##### `save(config: dict)`

Save configuration to disk.

##### `should_include(file_path: Path) -> bool`

Check if file should be included.

**Parameters:**
- `file_path` (Path): File to check

**Returns:**
- `bool`: True if should be included

### cast.select

File selection and filtering.

#### Functions:

##### `select_files(root: Path, include: list[str], exclude: list[str]) -> list[Path]`

Select files matching patterns.

**Parameters:**
- `root` (Path): Root directory
- `include` (list[str]): Include patterns
- `exclude` (list[str]): Exclude patterns

**Returns:**
- `list[Path]`: Matching file paths

### cast.vault

High-level vault operations.

#### Class: `Vault`

```python
class Vault:
    def __init__(self, path: Path)
```

**Properties:**
- `path` (Path): Vault path
- `config` (VaultConfig): Vault configuration
- `index` (Index): Vault index
- `objects` (ObjectStore): Object store

**Methods:**

##### `init(vault_id: str | None = None)`

Initialize vault.

**Parameters:**
- `vault_id` (str | None): Custom vault ID

##### `index_files(force: bool = False) -> int`

Index vault files.

**Parameters:**
- `force` (bool): Force reindex

**Returns:**
- `int`: Number of files indexed

##### `get_peer_state(peer_id: str) -> PeerState`

Get peer state for another vault.

**Parameters:**
- `peer_id` (str): Peer vault ID

**Returns:**
- `PeerState`: Peer state manager

## Utility Functions

### cast.util

General utilities.

#### Functions:

##### `atomic_write(path: Path, content: str | bytes)`

Write file atomically.

**Parameters:**
- `path` (Path): Target path
- `content` (str | bytes): Content to write

##### `safe_yaml_load(text: str) -> dict | None`

Safely load YAML with error handling.

**Parameters:**
- `text` (str): YAML text

**Returns:**
- `dict | None`: Parsed YAML or None

##### `format_size(bytes: int) -> str`

Format byte size for display.

**Parameters:**
- `bytes` (int): Size in bytes

**Returns:**
- `str`: Formatted size (e.g., "1.5 MB")

## CLI Module

### cast.cli

Command-line interface.

#### Main App

```python
app = typer.Typer(
    name="cast",
    help="Cast Sync - Distributed vault synchronization"
)
```

#### Commands:

##### `init(vault_id: str | None = None)`

Initialize vault.

##### `index(vault_path: Path = ".", force: bool = False)`

Index vault files.

##### `sync(source: Path, dest: Path, apply: bool = False)`

Sync between vaults.

##### `conflicts(vault_path: Path = ".")`

List conflict files.

##### `resolve(vault_path: Path = ".", strategy: str = "interactive")`

Resolve conflicts.

##### `snapshot(vault_path: Path = ".", output: Path | None = None)`

Create vault snapshot.

## Error Classes

### Common Exceptions

```python
class CastError(Exception):
    """Base exception for Cast errors"""

class VaultNotInitialized(CastError):
    """Vault not initialized"""

class IndexOutOfDate(CastError):
    """Index needs updating"""

class SyncConflict(CastError):
    """Sync conflict detected"""

class InvalidCastId(CastError):
    """Invalid cast-id format"""
```

## Type Definitions

### Common Types

```python
from typing import TypeAlias

CastId: TypeAlias = str  # UUID v4 string
Digest: TypeAlias = str  # SHA-256 hex string
VaultId: TypeAlias = str  # Vault identifier

# Sync result tuple
SyncResult: TypeAlias = tuple[Path, ActionType, str]

# File metadata
FileMetadata: TypeAlias = dict[str, Any]
```

## Constants

### cast.constants

```python
# Version
CAST_VERSION = "1"

# File patterns
DEFAULT_INCLUDE = ["**/*.md"]
DEFAULT_EXCLUDE = [".git/**", ".obsidian/**", ".cast/**"]

# Cast fields
CAST_FIELDS = [
    "cast-id",
    "cast-vaults", 
    "cast-version",
    "cast-type",
    "cast-codebases"
]

# Ephemeral fields (not synced)
DEFAULT_EPHEMERAL = [
    "modified",
    "updated", 
    "accessed",
    "created"
]

# Digest algorithm
HASH_ALGORITHM = "sha256"

# File size limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

## Usage Examples

### Basic Sync Operation

```python
from pathlib import Path
from cast.sync import SyncEngine
from cast.vault import Vault

# Initialize vaults
vault1 = Vault(Path("/path/to/vault1"))
vault2 = Vault(Path("/path/to/vault2"))

# Index both vaults
vault1.index_files()
vault2.index_files()

# Perform sync
engine = SyncEngine()
results, stats = engine.sync(
    vault1.path,
    vault2.path,
    apply=True
)

print(f"Synced {stats.updated} files")
```

### Custom Merge Strategy

```python
from cast.merge_cast import merge_cast_content

def custom_merge(base, source, dest):
    # Custom merge logic
    merged, conflicts = merge_cast_content(base, source, dest)
    
    # Additional processing
    if conflicts:
        # Handle conflicts specially
        pass
    
    return merged, conflicts
```

### Programmatic Conflict Resolution

```python
from cast.resolve import ConflictResolver
from pathlib import Path

resolver = ConflictResolver()
vault_path = Path("/my-vault")

# Find conflicts
conflicts = resolver.list_conflicts(vault_path)

for conflict_file in conflicts:
    # Parse conflict
    parsed = resolver.parse_conflict_file(conflict_file)
    
    # Resolve programmatically
    for conflict in parsed:
        # Choose source version
        resolved = conflict["source"]
        # Apply resolution...
```