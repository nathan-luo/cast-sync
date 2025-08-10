# Cast Sync - API Reference

## Table of Contents
- [CLI Commands](#cli-commands)
- [Python API](#python-api)
- [Configuration API](#configuration-api)
- [Index API](#index-api)
- [Sync API](#sync-api)
- [ID Management API](#id-management-api)
- [Markdown Processing API](#markdown-processing-api)
- [Utility Functions](#utility-functions)
- [Data Structures](#data-structures)
- [File Formats](#file-formats)

## CLI Commands

### Global Commands

#### `cast version`
Display Cast version information.

```bash
cast version
```

**Output**: `Cast version 1.0.0`

**Exit Codes**:
- 0: Success

---

#### `cast install`
Create global configuration and initialize Cast system.

```bash
cast install
```

**Effects**:
- Creates `~/.config/Cast/config.yaml`
- Initializes empty vault registry

**Exit Codes**:
- 0: Success
- 1: Configuration already exists

---

#### `cast config`
Open global configuration in default text editor.

```bash
cast config
```

**Environment Variables**:
- `EDITOR`: Preferred text editor
- `VISUAL`: Alternative editor

**Platform Defaults**:
- Windows: `notepad`
- macOS: `open`
- Linux: `nano`

**Exit Codes**:
- 0: Success
- 1: Editor launch failed

---

#### `cast vaults`
List all registered vaults with status.

```bash
cast vaults
```

**Output Format**:
```
┌────────────────────────────┐
│   Configured Vaults        │
├─────┬──────────┬───────────┤
│ ID  │ Path     │ Status    │
└─────┴──────────┴───────────┘
```

**Status Values**:
- `✓ Initialized`: Ready for sync
- `⚠ Not initialized`: Needs init
- `✗ Missing`: Path not found

**Exit Codes**:
- 0: Success

---

### Vault Commands

#### `cast init`
Initialize Cast in a vault directory.

```bash
cast init [PATH] [OPTIONS]
```

**Arguments**:
- `PATH`: Vault root directory (default: current directory)

**Options**:
- `--id <name>`: Vault ID for global config (prompts if not provided)

**Interactive Prompts**:
```
Enter a name for this vault [directory-name]: 
```

**Effects**:
- Creates `.cast/` directory
- Generates `config.yaml`
- Creates empty `index.json`
- Creates empty `sync_state.json`
- Registers in global config

**Exit Codes**:
- 0: Success
- 1: Already initialized
- 2: Invalid path

---

#### `cast register`
Register a vault in global configuration.

```bash
cast register <NAME> <PATH>
```

**Arguments**:
- `NAME`: Unique vault identifier
- `PATH`: Path to vault directory

**Validation**:
- Name must be unique
- Path must exist
- Path resolved to absolute

**Exit Codes**:
- 0: Success
- 1: Name already exists
- 2: Path not found

---

#### `cast vault create`
Create new vault with standard structure.

```bash
cast vault create <PATH> [OPTIONS]
```

**Arguments**:
- `PATH`: Directory for new vault

**Options**:
- `--template <name>`: Structure template (default: "default")

**Created Structure**:
```
path/
├── 01 Vault/
├── 02 Journal/
├── 03 Records/
├── 04 Sources/
├── 05 Media/
└── 06 Extras/
```

**Exit Codes**:
- 0: Success
- 1: Path already exists
- 2: Template not found

---

#### `cast vault obsidian`
Initialize Obsidian configuration.

```bash
cast vault obsidian [PATH] [OPTIONS]
```

**Arguments**:
- `PATH`: Vault directory (default: current)

**Options**:
- `--profile <name>`: Configuration profile (default: "default")

**Created Files**:
- `.obsidian/app.json`
- `.obsidian/core-plugins.json`
- `.obsidian/appearance.json`

**Exit Codes**:
- 0: Success
- 1: Not a vault
- 2: Obsidian already configured

---

### Indexing Commands

#### `cast index`
Build or update vault index.

```bash
cast index [PATH] [OPTIONS]
```

**Arguments**:
- `PATH`: Vault directory (default: current)

**Options**:
- `--rebuild`: Force complete rebuild
- `--no-auto`: Don't auto-add cast-ids

**Index Process**:
1. Scan files matching patterns
2. Extract metadata
3. Compute digests
4. Auto-fix if enabled
5. Save to `.cast/index.json`

**Exit Codes**:
- 0: Success
- 1: Not a vault
- 2: Index error

---

### Synchronization Commands

#### `cast sync`
Synchronize vaults.

```bash
cast sync [VAULT] [OPTIONS]
```

**Arguments**:
- `VAULT`: Vault ID or path (default: current)

**Options**:
- `--overpower`: Force current vault version
- `--batch`: Non-interactive mode

**Sync Process**:
1. Auto-index all vaults
2. Compare file sets
3. Resolve conflicts
4. Transfer files
5. Update sync state

**Interactive Prompts**:
```
Choose: [1] Use vault1 / [2] Use vault2 / [3] Skip
```

**Exit Codes**:
- 0: Success
- 1: Not a vault
- 2: No other vaults
- 3: Unresolved conflicts

---

### Maintenance Commands

#### `cast reset`
Reset vault Cast state.

```bash
cast reset [VAULT] [OPTIONS]
```

**Arguments**:
- `VAULT`: Vault ID from global config

**Options**:
- `--path <path>`: Vault path
- `--force`: Skip confirmation
- `--keep-config`: Preserve configuration

**Reset Actions**:
- Clear index
- Remove sync state
- Delete peer data
- Keep content files

**Confirmation Prompt**:
```
Are you sure you want to reset this vault's Cast state? [y/N]
```

**Exit Codes**:
- 0: Success
- 1: Not a vault
- 2: User cancelled

---

## Python API

### Module: `cast.config`

#### Class: `GlobalConfig`

Global configuration manager.

```python
from cast.config import GlobalConfig

# Load configuration
config = GlobalConfig.load()

# Create default
config = GlobalConfig.create_default()

# Load or create
config = GlobalConfig.load_or_create()
```

**Methods**:

##### `load() -> GlobalConfig`
Load existing global configuration.

**Returns**: GlobalConfig instance
**Raises**: FileNotFoundError if not exists

##### `create_default() -> GlobalConfig`
Create new default configuration.

**Returns**: GlobalConfig with empty vault registry

##### `load_or_create() -> GlobalConfig`
Load existing or create new configuration.

**Returns**: GlobalConfig instance

##### `save() -> None`
Save configuration to disk.

**Effects**: Writes to config file
**Raises**: IOError on write failure

##### `register_vault(name: str, path: str) -> None`
Register vault in global registry.

**Parameters**:
- `name`: Unique vault identifier
- `path`: Absolute path to vault

**Raises**: ValueError if name exists

##### `get_vault_path(name: str) -> Optional[Path]`
Get vault path by name.

**Parameters**:
- `name`: Vault identifier

**Returns**: Path or None if not found

**Properties**:
- `config_path`: Path to config file
- `vaults`: Dict[str, str] of name → path

---

#### Class: `VaultConfig`

Per-vault configuration manager.

```python
from cast.config import VaultConfig

# Load vault config
config = VaultConfig.load(vault_path)

# Create default
config = VaultConfig.create_default(vault_path, vault_id)
```

**Methods**:

##### `load(vault_path: Path) -> VaultConfig`
Load vault configuration.

**Parameters**:
- `vault_path`: Path to vault root

**Returns**: VaultConfig instance
**Raises**: FileNotFoundError

##### `create_default(vault_path: Path, vault_id: str) -> VaultConfig`
Create default vault configuration.

**Parameters**:
- `vault_path`: Vault root directory
- `vault_id`: Unique identifier

**Returns**: VaultConfig with defaults

##### `save() -> None`
Save configuration to vault.

**Effects**: Writes `.cast/config.yaml`

**Properties**:
- `vault_id`: Unique identifier
- `vault_root`: Root directory path
- `include_patterns`: List of include globs
- `exclude_patterns`: List of exclude globs
- `ephemeral_keys`: Keys to ignore in sync

---

### Module: `cast.index`

#### Class: `Index`

Vault content index manager.

```python
from cast.index import Index

# Create index
index = Index(vault_path)

# Load existing
data = index.load()

# Build/update
index.build(auto_fix=True)
```

**Methods**:

##### `__init__(vault_path: Path)`
Initialize index for vault.

**Parameters**:
- `vault_path`: Vault root directory

##### `load() -> Dict[str, Any]`
Load existing index from disk.

**Returns**: Index data dictionary
**Raises**: FileNotFoundError

##### `save(data: Dict[str, Any]) -> None`
Save index to disk.

**Parameters**:
- `data`: Index dictionary

**Effects**: Writes `.cast/index.json`

##### `build(rebuild: bool = False, auto_fix: bool = True) -> Dict[str, Any]`
Build or update index.

**Parameters**:
- `rebuild`: Force complete rebuild
- `auto_fix`: Auto-add cast-ids

**Returns**: Updated index data

##### `find_files() -> List[Path]`
Find all indexable files.

**Returns**: List of file paths matching patterns

**Index Entry Structure**:
```python
{
    "path/to/file.md": {
        "cast_id": "uuid-string",
        "digest": "sha256-hash",
        "body_digest": "content-hash",
        "size": 1234,
        "modified": "2024-01-01T00:00:00",
        "cast_type": "note",
        "cast_vaults": ["vault1", "vault2"]
    }
}
```

---

#### Function: `build_index`

High-level index building function.

```python
from cast.index import build_index

index_data = build_index(
    vault_path,
    rebuild=False,
    auto_fix=True
)
```

**Parameters**:
- `vault_path`: Path to vault
- `rebuild`: Force rebuild
- `auto_fix`: Auto-add cast-ids

**Returns**: Index dictionary

---

### Module: `cast.sync_simple`

#### Class: `SimpleSyncEngine`

Main synchronization engine.

```python
from cast.sync_simple import SimpleSyncEngine

engine = SimpleSyncEngine()
result = engine.sync_all(
    vault_path,
    overpower=False,
    interactive=True
)
```

**Methods**:

##### `sync_all(vault_path: Path, overpower: bool = False, interactive: bool = True) -> Dict`
Sync vault with all others.

**Parameters**:
- `vault_path`: Current vault path
- `overpower`: Force current version
- `interactive`: Enable user prompts

**Returns**:
```python
{
    "status": "success|no_other_vaults|error",
    "synced": 10,  # Total files synced
    "conflicts": 2,  # Remaining conflicts
    "vaults": {
        "vault2": {
            "synced": 5,
            "conflicts": 1,
            "actions": [...]
        }
    }
}
```

##### `sync_vaults(vault1: Path, vault2: Path, overpower: bool, interactive: bool) -> Dict`
Sync two specific vaults.

**Parameters**:
- `vault1`: First vault path
- `vault2`: Second vault path
- `overpower`: Force vault1 version
- `interactive`: Enable prompts

**Returns**: Sync result dictionary

---

#### Class: `SyncState`

Synchronization state manager.

```python
from cast.sync_simple import SyncState

state = SyncState(vault_path)
last_digest = state.get_last_digest(vault1_id, vault2_id, cast_id)
state.update_digest(vault1_id, vault2_id, cast_id, new_digest)
```

**Methods**:

##### `load() -> Dict`
Load sync state from disk.

**Returns**: State dictionary

##### `save() -> None`
Save sync state to disk.

**Effects**: Writes `.cast/sync_state.json`

##### `get_last_digest(vault1_id: str, vault2_id: str, cast_id: str) -> Optional[str]`
Get last synced digest for file.

**Parameters**:
- `vault1_id`: First vault ID
- `vault2_id`: Second vault ID  
- `cast_id`: File UUID

**Returns**: Digest string or None

##### `update_digest(vault1_id: str, vault2_id: str, cast_id: str, digest: str) -> None`
Update sync digest for file.

**Parameters**:
- `vault1_id`: First vault ID
- `vault2_id`: Second vault ID
- `cast_id`: File UUID
- `digest`: New digest value

---

### Module: `cast.ids`

#### Function: `generate_cast_id`

Generate new UUID v4.

```python
from cast.ids import generate_cast_id

new_id = generate_cast_id()
# Returns: "550e8400-e29b-41d4-a716-446655440000"
```

**Returns**: UUID string

---

#### Function: `validate_cast_id`

Validate UUID format.

```python
from cast.ids import validate_cast_id

is_valid = validate_cast_id("550e8400-e29b-41d4-a716-446655440000")
# Returns: True
```

**Parameters**:
- `cast_id`: String to validate

**Returns**: Boolean validity

---

#### Function: `parse_frontmatter`

Extract YAML frontmatter from content.

```python
from cast.ids import parse_frontmatter

frontmatter = parse_frontmatter(content)
# Returns: {"cast-id": "...", "title": "..."}
```

**Parameters**:
- `content`: File content string

**Returns**: Dict or None

---

#### Function: `ensure_cast_id_first`

Reorder frontmatter with cast-id first.

```python
from cast.ids import ensure_cast_id_first

ordered = ensure_cast_id_first(frontmatter_dict)
```

**Parameters**:
- `frontmatter`: Dictionary

**Returns**: Ordered dictionary

---

#### Function: `add_cast_id_to_file`

Add UUID to file with cast metadata.

```python
from cast.ids import add_cast_id_to_file

success = add_cast_id_to_file(file_path)
```

**Parameters**:
- `file_path`: Path to markdown file

**Returns**: Boolean success

**Effects**: Modifies file with new cast-id

---

#### Function: `find_duplicate_ids`

Find files with duplicate cast-ids.

```python
from cast.ids import find_duplicate_ids

duplicates = find_duplicate_ids(index_data)
# Returns: {"uuid": ["file1.md", "file2.md"]}
```

**Parameters**:
- `index_data`: Index dictionary

**Returns**: Dict[str, List[str]] of duplicates

---

### Module: `cast.md`

#### Function: `split_markdown`

Split markdown into frontmatter and body.

```python
from cast.md import split_markdown

frontmatter, body = split_markdown(content)
```

**Parameters**:
- `content`: Full file content

**Returns**: Tuple[Optional[str], str]

---

#### Function: `parse_frontmatter`

Parse YAML frontmatter string.

```python
from cast.md import parse_frontmatter

data = parse_frontmatter(yaml_string)
```

**Parameters**:
- `frontmatter`: YAML string

**Returns**: Dict or None

---

#### Function: `compute_body_digest`

Compute SHA256 of body only.

```python
from cast.md import compute_body_digest

digest = compute_body_digest(file_path)
```

**Parameters**:
- `file_path`: Path to markdown file

**Returns**: Hex digest string

---

#### Function: `serialize_frontmatter`

Convert dict to YAML frontmatter.

```python
from cast.md import serialize_frontmatter

yaml_str = serialize_frontmatter(data_dict)
```

**Parameters**:
- `data`: Dictionary

**Returns**: YAML string with --- markers

---

### Module: `cast.vault`

#### Function: `create_vault_structure`

Create standard vault directory structure.

```python
from cast.vault import create_vault_structure

create_vault_structure(path, template="default")
```

**Parameters**:
- `path`: Directory path
- `template`: Structure template

**Effects**: Creates directories with READMEs

---

### Module: `cast.obsidian`

#### Function: `init_obsidian_config`

Initialize Obsidian configuration.

```python
from cast.obsidian import init_obsidian_config

init_obsidian_config(vault_path, profile="default")
```

**Parameters**:
- `vault_path`: Vault directory
- `profile`: Config profile

**Effects**: Creates `.obsidian/` configs

---

### Module: `cast.util`

#### Function: `setup_logging`

Configure application logging.

```python
from cast.util import setup_logging

setup_logging(verbose=True, quiet=False)
```

**Parameters**:
- `verbose`: Enable debug output
- `quiet`: Suppress non-errors

---

#### Function: `safe_join`

Safely join paths preventing traversal.

```python
from cast.util import safe_join

safe_path = safe_join(base_path, "subdir", "file.md")
```

**Parameters**:
- `base`: Base directory
- `*parts`: Path components

**Returns**: Safe resolved path
**Raises**: ValueError on traversal

---

#### Function: `atomic_write`

Write file atomically.

```python
from cast.util import atomic_write

atomic_write(file_path, content)
```

**Parameters**:
- `path`: Target file path
- `content`: File content

**Effects**: Atomic file write

---

#### Function: `is_binary`

Check if file is binary.

```python
from cast.util import is_binary

if not is_binary(file_path):
    # Process as text
```

**Parameters**:
- `path`: File path

**Returns**: Boolean

---

#### Function: `format_size`

Format bytes as human-readable.

```python
from cast.util import format_size

size_str = format_size(1234567)
# Returns: "1.2 MB"
```

**Parameters**:
- `size`: Bytes

**Returns**: Formatted string

---

## Data Structures

### Cast-ID Format
```yaml
cast-id: "550e8400-e29b-41d4-a716-446655440000"
```

**Specification**:
- Type: UUID version 4
- Format: 8-4-4-4-12 hexadecimal
- Example: `550e8400-e29b-41d4-a716-446655440000`

### Frontmatter Structure
```yaml
---
cast-id: "uuid"
cast-type: "document-type"
cast-vaults: ["vault1 (role)", "vault2 (role)"]
title: "Document Title"
tags: ["tag1", "tag2"]
updated: "2024-01-01T00:00:00"
---
```

### Index Entry
```json
{
  "path/to/file.md": {
    "cast_id": "uuid",
    "digest": "full-content-sha256",
    "body_digest": "body-only-sha256",
    "size": 1234,
    "modified": "2024-01-01T00:00:00",
    "cast_type": "note",
    "cast_vaults": ["vault1", "vault2"]
  }
}
```

### Sync State Entry
```json
{
  "vault1::vault2": {
    "last_sync": "2024-01-01T00:00:00",
    "files": {
      "cast-id-uuid": {
        "digest": "sha256-hash",
        "last_action": "COPY_TO_VAULT2"
      }
    }
  }
}
```

### Sync Result
```json
{
  "status": "success",
  "synced": 15,
  "conflicts": 2,
  "vaults": {
    "vault2": {
      "synced": 10,
      "conflicts": 1,
      "actions": [
        {
          "type": "COPY_TO_VAULT2",
          "file": "notes/example.md",
          "cast_id": "uuid"
        }
      ]
    }
  }
}
```

## File Formats

### Global Configuration (`~/.config/Cast/config.yaml`)
```yaml
cast-version: "1"
vaults:
  main: "/home/user/vaults/main"
  work: "/home/user/vaults/work"
  backup: "/mnt/backup/vault"
```

### Vault Configuration (`.cast/config.yaml`)
```yaml
cast-version: "1"
vault:
  id: "main"
  root: "/home/user/vaults/main"
index:
  include:
    - "01 Vault/**/*.md"
    - "02 Journal/**/*.md"
  exclude:
    - ".git/**"
    - ".cast/**"
    - ".obsidian/**"
    - "**/.DS_Store"
    - "**/node_modules/**"
sync:
  rules: []
merge:
  ephemeral_keys:
    - "updated"
    - "last_synced"
    - "base-version"
```

### Index File (`.cast/index.json`)
```json
{
  "01 Vault/Notes/example.md": {
    "cast_id": "550e8400-e29b-41d4-a716-446655440000",
    "digest": "sha256:abcdef1234567890",
    "body_digest": "sha256:1234567890abcdef",
    "size": 1234,
    "modified": "2024-01-01T12:00:00",
    "cast_type": "note",
    "cast_vaults": ["main", "backup"]
  },
  "01 Vault/Projects/project.md": {
    "cast_id": "660e8400-e29b-41d4-a716-446655440001",
    "digest": "sha256:fedcba0987654321",
    "body_digest": "sha256:0987654321fedcba",
    "size": 5678,
    "modified": "2024-01-02T10:30:00",
    "cast_type": "project",
    "cast_vaults": ["main", "work"]
  }
}
```

### Sync State File (`.cast/sync_state.json`)
```json
{
  "main::backup": {
    "last_sync": "2024-01-01T15:30:00",
    "files": {
      "550e8400-e29b-41d4-a716-446655440000": {
        "digest": "sha256:abcdef1234567890",
        "last_action": "COPY_TO_VAULT2"
      }
    }
  },
  "main::work": {
    "last_sync": "2024-01-02T09:00:00",
    "files": {
      "660e8400-e29b-41d4-a716-446655440001": {
        "digest": "sha256:fedcba0987654321",
        "last_action": "AUTO_MERGE_VAULT1"
      }
    }
  }
}
```

## Error Handling

### Exception Types

#### `CastConfigError`
Configuration-related errors.

```python
class CastConfigError(Exception):
    """Raised for configuration issues"""
```

#### `CastSyncError`
Synchronization errors.

```python
class CastSyncError(Exception):
    """Raised for sync failures"""
```

#### `CastIndexError`
Index operation errors.

```python
class CastIndexError(Exception):
    """Raised for index problems"""
```

### Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| 0 | Success | N/A |
| 1 | General error | Check logs |
| 2 | Configuration error | Fix config |
| 3 | Sync conflict | Resolve manually |
| 4 | File system error | Check permissions |
| 5 | Index error | Rebuild index |

### Error Messages

**Configuration Errors**:
```
Error: Vault 'main' already registered
Error: Configuration file not found
Error: Invalid vault ID format
```

**Sync Errors**:
```
Error: No other vaults configured for sync
Error: Unresolved conflicts remain
Error: Cannot sync - vault not initialized
```

**Index Errors**:
```
Error: Failed to build index - permission denied
Error: Duplicate cast-id found
Error: Invalid frontmatter format
```

## Best Practices

### Development

1. **Import Order**:
```python
# Standard library
import os
from pathlib import Path

# Third-party
import yaml
from rich.console import Console

# Local
from cast.config import VaultConfig
from cast.index import Index
```

2. **Error Handling**:
```python
try:
    result = engine.sync_all(vault_path)
except CastSyncError as e:
    console.print(f"[red]Sync failed: {e}[/red]")
    return 1
```

3. **Path Handling**:
```python
# Always use Path objects
vault_path = Path(vault_str).resolve()

# Safe joining
file_path = safe_join(vault_path, "01 Vault", "note.md")
```

### Testing

1. **Unit Tests**:
```python
def test_generate_cast_id():
    cast_id = generate_cast_id()
    assert validate_cast_id(cast_id)
```

2. **Integration Tests**:
```python
def test_sync_vaults():
    engine = SimpleSyncEngine()
    result = engine.sync_vaults(vault1, vault2)
    assert result["status"] == "success"
```

3. **Mock File System**:
```python
from unittest.mock import patch, mock_open

with patch("builtins.open", mock_open(read_data=content)):
    result = parse_frontmatter(path)
```

### Performance

1. **Lazy Loading**:
```python
@property
def config(self):
    if not self._config:
        self._config = VaultConfig.load(self.path)
    return self._config
```

2. **Batch Operations**:
```python
# Good: Single write
index.save(all_data)

# Bad: Multiple writes
for entry in entries:
    index.add_entry(entry)
    index.save()
```

3. **Memory Management**:
```python
# Stream large files
with open(large_file, 'r') as f:
    for line in f:
        process_line(line)
```