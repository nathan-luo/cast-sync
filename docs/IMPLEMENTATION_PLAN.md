# Cast 1.0 Implementation Plan

## Overview

Cast is a knowledge-aware sync service for Markdown vaults that tracks files by UUID, maintains last-sync baselines, and performs MKD-aware 3-way merges. This document outlines the implementation strategy and architecture.

## Core Design Principles

1. **UUID-based Identity**: Every file has a stable `cast-id` that survives renames/moves
2. **Baseline-driven Sync**: Store only last agreed content for 3-way merges
3. **MKD-aware Merging**: Understand YAML frontmatter, dependencies, and markdown structure
4. **Local-first**: No servers, cloud, or network dependencies in v1.0
5. **Git-agnostic**: Git handles history; Cast handles sync

## Architecture

### Module Structure

```
cast/
├── cli.py           # Typer-based CLI interface
├── config.py        # Vault and global configuration
├── ids.py           # UUID management
├── index.py         # File indexing and caching
├── normalize.py     # Content normalization and hashing
├── objects.py       # Content-addressed baseline store
├── peers.py         # Per-peer sync state tracking
├── select.py        # File selection and filtering
├── merge_mkd.py     # MKD-aware 3-way merge engine
├── plan.py          # Sync planning and action detection
├── sync.py          # Main sync engine
├── resolve.py       # Conflict resolution UI
├── vault.py         # Vault creation and management
├── snapshot.py      # State snapshots
├── obsidian.py      # Obsidian integration
└── util.py          # Shared utilities
```

### Data Flow

1. **Index Phase**
   - Scan vault per include/exclude patterns
   - Extract cast-id, metadata, compute normalized digest
   - Cache in `.cast/index.json`

2. **Plan Phase**
   - Load source and destination indices
   - Load peer states (last sync metadata)
   - Detect actions: CREATE, UPDATE, MERGE, CONFLICT, SKIP
   - Return structured plan

3. **Sync Phase**
   - Acquire destination lock
   - Apply each action atomically
   - Store new baselines in object store
   - Update peer states bidirectionally

4. **Merge Phase** (for bidirectional sync)
   - Split content into regions (YAML, body, dependencies)
   - Apply type-specific merge rules
   - Generate conflict markers if unresolvable
   - Write merged content or conflict file

## Key Algorithms

### Normalized Digest

```python
1. Normalize line endings to \n
2. Parse YAML frontmatter
3. Remove ephemeral keys (updated, last_synced)
4. Sort YAML keys deterministically
5. Trim trailing spaces
6. Ensure trailing newline
7. Compute SHA-256
```

### Action Detection

```python
if not dst_exists:
    CREATE
elif src_digest == dst_digest:
    SKIP
elif mode == "mirror":
    UPDATE (force)
elif mode == "broadcast":
    if dst_changed_since_baseline:
        CONFLICT
    else:
        UPDATE
elif mode == "bidirectional":
    if no_baseline:
        CONFLICT
    elif only_src_changed:
        UPDATE
    elif only_dst_changed:
        SKIP
    elif both_changed:
        MERGE
```

### MKD-aware Merge

```python
1. YAML merge:
   - tags: set union
   - type/category: must match or conflict
   - scalars: last-writer-wins (mtime)
   - maps: shallow merge

2. Dependencies merge:
   - Union of additions vs baseline
   - Max depth for same dep
   - Role conflicts → conflict

3. Body merge:
   - Split by top-level headings
   - Per-block diff3
   - Unresolved → conflict markers
```

## State Management

### Per-Vault State (`.cast/`)

```
.cast/
├── config.yaml      # Vault configuration
├── index.json       # File index cache
├── objects/         # Content-addressed baselines
│   └── <sha256>     # Normalized content
├── peers/           # Peer sync states
│   └── <peer>.json  # Last sync metadata
├── snapshots/       # Point-in-time snapshots
├── locks/           # Sync locks
└── logs/            # Action logs (optional)
```

### Global State (`~/.config/cast/`)

```yaml
vaults:
  nathansvault: /path/to/NC
  casting: /path/to/Casting
  dsc: /path/to/DSC
```

## Implementation Phases

### Phase 1: Foundation ✅
- [x] Project structure and tooling
- [x] Core modules (config, ids, normalize)
- [x] Index management
- [x] Object store

### Phase 2: Sync Engine ✅
- [x] Peer state tracking
- [x] Plan generation
- [x] Action detection
- [x] Basic sync (CREATE, UPDATE)

### Phase 3: Merging ✅
- [x] MKD-aware merge algorithm
- [x] YAML/Dependencies/Body splitting
- [x] Conflict generation
- [x] Resolver UI

### Phase 4: CLI & UX ✅
- [x] Typer CLI with all commands
- [x] Rich output formatting
- [x] Interactive conflict resolution
- [x] Progress indicators

### Phase 5: Testing & Hardening
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] Error handling
- [ ] Performance optimization

### Phase 6: Polish & Documentation
- [ ] User documentation
- [ ] API documentation
- [ ] Example workflows
- [ ] Release preparation

## Testing Strategy

### Unit Tests
- Normalization determinism
- UUID injection/extraction
- YAML merge rules
- Dependency parsing
- Index operations

### Integration Tests
- Full sync workflows
- Conflict scenarios
- Rename detection
- Lock contention
- Atomic writes

### Property Tests
- Digest determinism
- Merge commutativity (where applicable)
- Index consistency

## Performance Considerations

1. **Incremental indexing**: Use mtime/size to skip unchanged files
2. **Parallel hashing**: Thread pool for large vaults
3. **Lazy loading**: Don't load full content until needed
4. **Atomic writes**: Always write to temp then rename

## Security Considerations

1. **Path traversal**: Validate all paths stay within vault root
2. **Symlinks**: Don't follow symlinks outside vault
3. **Locks**: Prevent concurrent modifications
4. **Atomicity**: No partial writes on crash

## Future Extensions (Post-1.0)

1. **Transport adapters**: HTTP, S3, SSH remotes
2. **Tombstones**: Safe delete propagation
3. **Git integration**: Custom merge driver
4. **SQLite index**: For vaults >10k files
5. **File watcher**: Real-time index updates
6. **CCP protocol**: Cross-syntax exchange format

## Development Workflow

```bash
# Setup
uv sync --all-extras --dev

# Development
uv run poe fmt    # Format code
uv run poe lint   # Fix lints
uv run poe check  # Type check
uv run poe test   # Run tests
uv run poe all    # All checks

# Run CLI
uv run cast --help
python -m cast init

# Docker
docker build -t cast-sync .
docker run cast-sync --help
```

## Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Tag created
- [ ] GitHub release drafted
- [ ] PyPI package published

## Success Metrics

1. **Correctness**: No data loss, deterministic merges
2. **Performance**: <1s for 1000-file index rebuild
3. **Usability**: Single command sync, clear conflict resolution
4. **Reliability**: Atomic operations, graceful failure