# Cast Sync - System Architecture

## Table of Contents
- [Overview](#overview)
- [System Design Philosophy](#system-design-philosophy)
- [Core Architecture](#core-architecture)
- [Component Architecture](#component-architecture)
- [Data Flow Architecture](#data-flow-architecture)
- [Synchronization Architecture](#synchronization-architecture)
- [Storage Architecture](#storage-architecture)
- [Security Architecture](#security-architecture)
- [Performance Architecture](#performance-architecture)

## Overview

Cast Sync is a distributed, knowledge-aware synchronization system designed for Markdown vault ecosystems. It implements a decentralized, peer-to-peer synchronization protocol that maintains content integrity across multiple vault instances while preserving local autonomy and user control.

### Key Architectural Principles

1. **Decentralized Design**: No central server; all vaults are equal peers
2. **Content-Addressable Storage**: Files tracked via UUID-based cast-ids
3. **Deterministic Conflict Resolution**: Three-way merge with user control
4. **Atomic Operations**: All file operations are atomic to prevent corruption
5. **Incremental Synchronization**: Only changed content is processed
6. **Pluggable Architecture**: Extensible design for future enhancements

## System Design Philosophy

### Design Goals

1. **Reliability First**: Data integrity over speed
2. **User Sovereignty**: Users control their data and sync decisions
3. **Transparency**: Clear visibility into sync operations
4. **Simplicity**: Minimal configuration and maintenance
5. **Extensibility**: Support for future features without breaking changes

### Non-Goals

1. **Real-time Collaboration**: Not designed for simultaneous editing
2. **Version Control**: Not a replacement for Git
3. **Binary File Optimization**: Focused on text/markdown content
4. **Centralized Authority**: No server-side control

## Core Architecture

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface Layer                   │
│                    (typer + rich UI)                     │
├─────────────────────────────────────────────────────────┤
│                  Command Processing Layer                │
│              (Commands, Options, Validation)             │
├─────────────────────────────────────────────────────────┤
│                   Business Logic Layer                   │
│        (Sync Engine, Index Manager, ID Manager)          │
├─────────────────────────────────────────────────────────┤
│                    Data Access Layer                     │
│         (Config, Index, State, File Operations)          │
├─────────────────────────────────────────────────────────┤
│                   Storage Layer                          │
│            (File System, JSON, YAML Storage)             │
└─────────────────────────────────────────────────────────┘
```

### Module Dependency Graph

```
                    ┌─────────┐
                    │   CLI   │
                    └────┬────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │  Config  │ │   Sync   │ │  Index   │
      └────┬─────┘ └─────┬────┘ └────┬─────┘
           │             │            │
           └─────────────┼────────────┘
                         ▼
                   ┌──────────┐
                   │    IDs   │
                   └────┬─────┘
                        │
                        ▼
                   ┌──────────┐
                   │    MD    │
                   └────┬─────┘
                        │
                        ▼
                   ┌──────────┐
                   │   Util   │
                   └──────────┘
```

## Component Architecture

### 1. CLI Component (`cli.py`)

**Purpose**: Command-line interface and user interaction layer

**Responsibilities**:
- Command parsing and validation
- User prompting and feedback
- Output formatting and presentation
- Error handling and reporting

**Design Pattern**: Command pattern with Typer framework

**Key Classes**:
- `app`: Main Typer application
- `vault_app`: Sub-application for vault commands
- `console`: Rich console for formatted output

### 2. Configuration Component (`config.py`)

**Purpose**: Hierarchical configuration management

**Responsibilities**:
- Global configuration (machine-wide vault registry)
- Vault configuration (per-vault settings)
- Configuration validation and defaults
- Platform-specific path resolution

**Design Pattern**: Singleton with lazy loading

**Key Classes**:
- `GlobalConfig`: Machine-wide vault registry
- `VaultConfig`: Per-vault configuration
- `CastConfig`: Unified configuration interface

**Configuration Hierarchy**:
```
Global Config (~/.config/Cast/config.yaml)
    └── Vault Registry (name → path mappings)
    
Vault Config (vault/.cast/config.yaml)
    ├── Vault Identity (id, root)
    ├── Index Rules (include/exclude patterns)
    ├── Sync Rules (future extensibility)
    └── Merge Settings (ephemeral keys)
```

### 3. ID Management Component (`ids.py`)

**Purpose**: UUID-based file identification system

**Responsibilities**:
- UUID generation (v4)
- Cast-ID validation
- Frontmatter manipulation
- Duplicate detection
- ID consistency enforcement

**Design Pattern**: Functional with validation decorators

**Key Functions**:
- `generate_cast_id()`: Create new UUID
- `validate_cast_id()`: Verify UUID format
- `ensure_cast_id_first()`: Enforce ordering
- `add_cast_id_to_file()`: Inject ID into file
- `find_duplicate_ids()`: Detect ID conflicts

**ID Format Specification**:
```yaml
cast-id: "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"  # UUID v4
```

### 4. Index Component (`index.py`)

**Purpose**: Content indexing and change detection

**Responsibilities**:
- File discovery and filtering
- Metadata extraction
- Digest computation
- Change detection
- Auto-fix operations

**Design Pattern**: Repository pattern with caching

**Key Classes**:
- `Index`: Main index manager
- `IndexEntry`: File metadata container

**Index Structure**:
```json
{
  "file_path": {
    "cast_id": "uuid",
    "digest": "sha256_hash",
    "body_digest": "content_only_hash",
    "size": 1234,
    "modified": "2024-01-01T00:00:00",
    "cast_type": "type",
    "cast_vaults": ["vault1", "vault2"]
  }
}
```

### 5. Sync Engine Component (`sync_simple.py`)

**Purpose**: Multi-vault synchronization orchestration

**Responsibilities**:
- Vault discovery
- Difference detection
- Conflict resolution
- File synchronization
- State management

**Design Pattern**: Strategy pattern for conflict resolution

**Key Classes**:
- `SimpleSyncEngine`: Main sync orchestrator
- `SyncState`: Sync history tracker
- `ConflictResolver`: Interactive/automatic resolution

**Sync Algorithm**:
```python
for each file in union(vault1_files, vault2_files):
    if file in both vaults:
        if digests match:
            continue  # Already synced
        else:
            resolve_conflict()
    elif file in vault1 only:
        copy_to_vault2()
    elif file in vault2 only:
        copy_to_vault1()
```

### 6. Markdown Component (`md.py`)

**Purpose**: Markdown file processing and manipulation

**Responsibilities**:
- Frontmatter parsing
- Content extraction
- Digest computation
- File reconstruction
- Format validation

**Design Pattern**: Parser/Serializer pattern

**Key Functions**:
- `split_markdown()`: Separate frontmatter/body
- `parse_frontmatter()`: Extract YAML metadata
- `compute_body_digest()`: Hash content only
- `serialize_markdown()`: Reconstruct file

### 7. Vault Component (`vault.py`)

**Purpose**: Vault structure and lifecycle management

**Responsibilities**:
- Vault creation
- Structure initialization
- Template application
- Directory organization

**Design Pattern**: Factory pattern for vault creation

**Standard Vault Structure**:
```
vault/
├── .cast/                 # Cast metadata
│   ├── config.yaml       # Vault configuration
│   ├── index.json        # Content index
│   └── sync_state.json   # Sync history
├── 01 Vault/             # Main content (synced)
├── 02 Journal/           # Daily journals
├── 03 Records/           # Audio/video
├── 04 Sources/           # References
├── 05 Media/             # Attachments
└── 06 Extras/            # Templates
```

## Data Flow Architecture

### 1. Indexing Data Flow

```
File System → File Discovery → Pattern Filtering → Metadata Extraction
     ↓              ↓                ↓                    ↓
  [*.md files]  [Include/Exclude]  [Apply Rules]    [Parse YAML]
                                                          ↓
                                                    Digest Computation
                                                          ↓
                                                    Index Storage
                                                    (.cast/index.json)
```

### 2. Synchronization Data Flow

```
Vault A Index ←→ Difference Detection ←→ Vault B Index
                         ↓
                  Change Analysis
                         ↓
              ┌──────────┴──────────┐
              ▼                     ▼
        Three-Way Merge      Direct Copy
              │                     │
              ▼                     ▼
        Conflict Resolution    File Transfer
              │                     │
              ▼                     ▼
         User Decision         Atomic Write
              │                     │
              └──────────┬──────────┘
                         ▼
                   State Update
                 (sync_state.json)
```

### 3. Configuration Data Flow

```
User Input → CLI Parser → Config Loader → Validation
                               ↓              ↓
                         [File System]   [Schema Check]
                               ↓              ↓
                          Config Cache    Error Report
                               ↓
                         Business Logic
```

## Synchronization Architecture

### Sync State Management

**State Tracking**: Each vault pair maintains sync state
```json
{
  "vault1::vault2": {
    "last_sync": "2024-01-01T00:00:00",
    "files": {
      "cast-id-1": {
        "digest": "sha256_hash",
        "last_action": "COPY_TO_VAULT2"
      }
    }
  }
}
```

### Conflict Resolution Strategy

**Three-Way Merge Logic**:
1. **Current State**: File content in each vault
2. **Base State**: Last synchronized version
3. **Resolution**: Automatic or interactive

**Decision Matrix**:
| Vault A | Vault B | Base | Action |
|---------|---------|------|--------|
| Changed | Same | Exists | Use A |
| Same | Changed | Exists | Use B |
| Changed | Changed | Exists | Conflict |
| New | Missing | None | Copy to B |
| Missing | New | None | Copy to A |

### Auto-Merge Capabilities

**Automatic Resolution Cases**:
1. Only one vault modified the file
2. Additions don't conflict
3. Deletions are unambiguous
4. Ephemeral key changes only

**Interactive Resolution**:
- Side-by-side diff display
- Full content preview
- Skip option available
- Batch mode override

## Storage Architecture

### File System Layout

```
~/.config/Cast/           # Global configuration
    └── config.yaml       # Vault registry

/path/to/vault/           # Vault instance
    ├── .cast/            # Cast metadata
    │   ├── config.yaml   # Vault config
    │   ├── index.json    # Content index
    │   └── sync_state.json # Sync state
    └── content/          # User files
```

### Data Persistence

**Configuration Storage**: YAML for human readability
**Index Storage**: JSON for performance
**State Storage**: JSON for atomicity

### Atomic Operations

**Write Strategy**:
1. Write to temporary file
2. Validate content
3. Atomic rename to target
4. Clean up temp files

**Rollback Capability**:
- No partial writes
- State consistency guaranteed
- Recovery from interruption

## Security Architecture

### Path Traversal Protection

```python
def safe_join(base: Path, *parts: str) -> Path:
    """Prevent directory traversal attacks"""
    result = base.joinpath(*parts).resolve()
    if not result.is_relative_to(base):
        raise ValueError("Path traversal detected")
    return result
```

### Input Validation

**UUID Validation**: Strict regex pattern matching
**YAML Parsing**: Safe loader with type restrictions
**Path Validation**: Canonicalization and boundary checks

### Data Integrity

**Digest Verification**: SHA256 for content verification
**Atomic Updates**: Prevent corruption during writes
**State Consistency**: Transaction-like state updates

## Performance Architecture

### Optimization Strategies

1. **Incremental Indexing**: Only process changed files
2. **Body-Only Digests**: Ignore metadata for sync decisions
3. **Lazy Loading**: Load configurations on demand
4. **Batch Operations**: Group file operations
5. **Memory Efficiency**: Stream large files

### Caching Strategy

**Index Cache**: In-memory during operations
**Config Cache**: Singleton pattern
**Digest Cache**: Computed once per session

### Scalability Considerations

**File Count**: O(n) indexing, O(n log n) sync
**Vault Count**: O(n²) for all-pairs sync
**File Size**: Streaming for large files
**Memory Usage**: Bounded by index size

### Performance Metrics

| Operation | Complexity | Typical Time |
|-----------|------------|--------------|
| Index Build | O(n) | 1-5 seconds |
| Sync Check | O(n) | <1 second |
| File Copy | O(size) | Variable |
| Conflict Resolution | O(1) | User-dependent |

## Future Architecture Considerations

### Planned Enhancements

1. **Plugin System**: Extensible sync strategies
2. **Remote Storage**: Cloud backend support
3. **Compression**: Differential sync compression
4. **Encryption**: End-to-end encryption option
5. **Webhooks**: Integration notifications

### Extension Points

- Custom merge strategies
- Alternative storage backends
- Protocol adapters
- UI frontends
- Monitoring integrations

### API Stability

**Stable APIs**:
- CLI commands
- Configuration format
- Cast-ID format
- Index structure

**Internal APIs**: Subject to change
**Migration Path**: Config version management