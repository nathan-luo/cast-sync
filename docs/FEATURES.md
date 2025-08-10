# Cast Sync - Feature Documentation

## Table of Contents
- [Core Features](#core-features)
- [Installation & Setup Features](#installation--setup-features)
- [Vault Management Features](#vault-management-features)
- [Content Indexing Features](#content-indexing-features)
- [Synchronization Features](#synchronization-features)
- [Conflict Resolution Features](#conflict-resolution-features)
- [ID Management Features](#id-management-features)
- [Configuration Features](#configuration-features)
- [Reset & Recovery Features](#reset--recovery-features)
- [Integration Features](#integration-features)

## Core Features

### 1. Decentralized Vault Synchronization

**Description**: Peer-to-peer synchronization without central server dependency

**Technical Implementation**:
- Each vault maintains its own index and state
- Direct vault-to-vault synchronization
- No cloud infrastructure required
- Local-first architecture

**Benefits**:
- Complete data sovereignty
- No vendor lock-in
- Works offline
- No subscription fees
- Enhanced privacy

**Use Cases**:
- Personal knowledge management across devices
- Team knowledge bases without cloud dependency
- Backup and redundancy strategies
- Multi-location content distribution

### 2. UUID-Based File Tracking

**Description**: Universal unique identifiers for content-addressable storage

**Technical Implementation**:
```yaml
cast-id: "550e8400-e29b-41d4-a716-446655440000"  # UUID v4
```
- UUID v4 generation for each tracked file
- Frontmatter-based ID storage
- Persistent IDs across renames/moves
- Collision probability: 1 in 5.3 x 10^36

**Benefits**:
- Files trackable across vaults regardless of path
- Rename-safe synchronization
- Move-safe synchronization
- Globally unique identification

**Validation Rules**:
- Must be valid UUID v4 format
- Must appear first in frontmatter
- Cannot be duplicated within vault
- Automatically generated when missing

## Installation & Setup Features

### 1. Global Installation (`cast install`)

**Description**: One-time system setup for Cast

**Technical Details**:
- Creates global configuration directory
- Initializes vault registry
- Sets up platform-specific paths
- Creates default configuration

**Configuration Location**:
- Linux: `~/.config/Cast/config.yaml`
- macOS: `~/Library/Application Support/Cast/config.yaml`
- Windows: `%APPDATA%\Cast\config.yaml`

**Default Configuration**:
```yaml
cast-version: "1"
vaults: {}  # Empty vault registry
```

### 2. Vault Initialization (`cast init`)

**Description**: Initialize Cast tracking in a vault directory

**Technical Process**:
1. Prompts for vault name (with directory name as default)
2. Creates `.cast/` directory structure
3. Generates vault configuration
4. Creates empty index and sync state
5. Registers vault in global config

**Interactive Features**:
- Name prompting with smart defaults
- Automatic global registration
- Configuration validation
- Success confirmation

**Created Structure**:
```
vault/
└── .cast/
    ├── config.yaml      # Vault configuration
    ├── index.json       # Empty index {}
    └── sync_state.json  # Empty state {}
```

### 3. Vault Registration (`cast register`)

**Description**: Add existing vaults to global registry

**Technical Implementation**:
- Path resolution to absolute paths
- Duplicate name detection
- Registry update atomicity
- Configuration persistence

**Command Syntax**:
```bash
cast register <name> <path>
```

**Registry Management**:
- Name must be unique
- Path must exist
- Supports relative path input
- Converts to absolute paths

## Vault Management Features

### 1. Vault Creation (`cast vault create`)

**Description**: Create new vault with recommended structure

**Technical Implementation**:
- Template-based directory creation
- Standard folder hierarchy
- README file generation
- Automatic initialization option

**Standard Structure Created**:
```
new-vault/
├── 01 Vault/       # Main synchronized content
│   └── README.md
├── 02 Journal/     # Daily journals
│   └── README.md
├── 03 Records/     # Audio/video recordings
│   └── README.md
├── 04 Sources/     # External references
│   └── README.md
├── 05 Media/       # Images and attachments
│   └── README.md
└── 06 Extras/      # Templates and tools
    └── README.md
```

**Template Support**:
- Default template included
- Custom template support planned
- Configurable folder names
- Extensible structure

### 2. Vault Listing (`cast vaults`)

**Description**: Display all registered vaults with status

**Technical Display**:
```
┌─────────────────────────────────────┐
│       Configured Vaults             │
├──────┬──────────────┬──────────────┤
│ ID   │ Path         │ Status       │
├──────┼──────────────┼──────────────┤
│ main │ ~/vaults/main│ ✓ Initialized│
│ work │ ~/vaults/work│ ⚠ Not init   │
│ old  │ ~/vaults/old │ ✗ Missing    │
└──────┴──────────────┴──────────────┘
```

**Status Indicators**:
- ✓ Initialized: Cast configured and ready
- ⚠ Not initialized: Registered but not initialized
- ✗ Missing: Path no longer exists

### 3. Obsidian Integration (`cast vault obsidian`)

**Description**: Configure Obsidian settings for vault

**Technical Configuration**:
- `.obsidian/` directory creation
- Core plugin configuration
- Workspace settings
- Appearance preferences

**Generated Settings**:
```json
{
  "app.json": {
    "showInlineTitle": true,
    "showViewHeader": true,
    "showBacklinks": true
  },
  "core-plugins.json": [
    "file-explorer",
    "search",
    "quick-switcher",
    "graph-view",
    "backlink",
    "outline",
    "tags-view",
    "daily-note"
  ]
}
```

## Content Indexing Features

### 1. Intelligent File Indexing (`cast index`)

**Description**: Build and maintain content index with smart processing

**Technical Process**:
1. **File Discovery**: Traverse vault directories
2. **Pattern Matching**: Apply include/exclude rules
3. **Metadata Extraction**: Parse frontmatter
4. **Digest Computation**: SHA256 hashing
5. **Change Detection**: Compare with previous index
6. **Auto-Fix**: Add missing cast-ids

**Indexing Rules**:
```yaml
index:
  include:
    - "01 Vault/**/*.md"  # All markdown in Vault
  exclude:
    - ".git/**"           # Version control
    - ".cast/**"          # Cast metadata
    - ".obsidian/**"      # Obsidian config
    - "**/.DS_Store"      # System files
```

**Performance Optimizations**:
- Incremental indexing (only changed files)
- Parallel file processing
- Memory-efficient streaming
- Cached digest computation

### 2. Auto Cast-ID Addition

**Description**: Automatically add UUIDs to files with cast metadata

**Technical Trigger Conditions**:
- File has frontmatter
- Contains cast-type or cast-vaults
- Missing cast-id field
- Index operation with auto-fix enabled

**Implementation Details**:
```python
# Before auto-fix
---
cast-type: "note"
title: "My Note"
---

# After auto-fix
---
cast-id: "generated-uuid-here"
cast-type: "note"
title: "My Note"
---
```

**Safety Features**:
- Atomic file updates
- Backup during modification
- Validation after addition
- Rollback on failure

### 3. Body-Only Digest Computation

**Description**: Content hashing that ignores metadata changes

**Technical Rationale**:
- Frontmatter contains ephemeral data
- Sync decisions based on content only
- Metadata changes don't trigger sync
- Reduces unnecessary synchronization

**Implementation**:
```python
def compute_body_digest(file_path):
    frontmatter, body = split_markdown(content)
    return sha256(body.encode()).hexdigest()
```

**Ephemeral Keys Ignored**:
- updated (timestamp)
- last_synced (timestamp)
- base-version (version tracking)
- Other configured keys

## Synchronization Features

### 1. Multi-Vault Synchronization (`cast sync`)

**Description**: Synchronize current vault with all connected vaults

**Technical Workflow**:
1. **Index Building**: Auto-index all vaults
2. **Vault Discovery**: Find all registered vaults
3. **Pair-wise Sync**: Sync with each vault
4. **Conflict Resolution**: Handle differences
5. **File Transfer**: Copy/update files
6. **State Update**: Record sync state

**Sync Algorithm**:
```
For each registered vault:
  Build/update indexes
  Compare file sets
  For each file with cast-id:
    If exists in both:
      If digests differ:
        Resolve conflict
    Else:
      Copy to missing vault
  Update sync state
```

### 2. Overpower Mode (`--overpower`)

**Description**: Force current vault's version to all other vaults

**Technical Behavior**:
- Skips conflict resolution
- Current vault always wins
- Overwrites all differences
- No user interaction required

**Use Cases**:
- Authoritative source updates
- Bulk content distribution
- Recovery from corruption
- Testing and development

**Warning Indicators**:
```
⚡ Overpower mode active
⚡ Forced update: file.md → vault2
⚡ 15 files overpowered
```

### 3. Batch Mode (`--batch`)

**Description**: Non-interactive synchronization for automation

**Technical Features**:
- No user prompts
- Automatic conflict resolution
- Log-based reporting
- Exit codes for scripts

**Conflict Resolution in Batch**:
- Auto-merge when possible
- Skip true conflicts
- Report unresolved items
- Return appropriate exit code

**Automation Support**:
```bash
# Cron job example
0 */4 * * * cast sync --batch
```

### 4. Selective Vault Sync

**Description**: Control which vaults receive specific files

**Technical Implementation**:
```yaml
cast-vaults: ["main (primary)", "backup (secondary)"]
```

**Vault Role System**:
- Primary: Main authoritative copy
- Secondary: Backup/read-only
- Shared: Collaborative editing
- Archive: Historical preservation

**Sync Rules**:
- Only syncs to listed vaults
- Respects role permissions
- Validates vault existence
- Handles missing vaults gracefully

## Conflict Resolution Features

### 1. Three-Way Merge Detection

**Description**: Intelligent conflict detection using sync history

**Technical Implementation**:
```
Current A ←→ Last Sync State ←→ Current B
     ↓            ↓                ↓
  Changed?     Base Version    Changed?
     ↓            ↓                ↓
         Merge Decision Matrix
```

**Decision Logic**:
- A changed, B unchanged → Use A
- A unchanged, B changed → Use B
- Both changed → Interactive resolution
- Both unchanged → Skip

### 2. Interactive Conflict Resolution

**Description**: Side-by-side comparison with user choice

**Technical Display**:
```
════════════════════════════════════════
CONFLICT: example.md
────────────────────────────────────────
Currently in main (504 bytes):
────────────────────────────────────────
# Main Version
This is the content from main vault...

────────────────────────────────────────
In backup (492 bytes):
────────────────────────────────────────
# Backup Version
This is the content from backup vault...

────────────────────────────────────────
Choose: [1] Use main / [2] Use backup / [3] Skip
```

**User Options**:
1. Use current vault version
2. Use other vault version
3. Skip this file
4. View full content
5. Abort sync operation

### 3. Auto-Merge Capabilities

**Description**: Automatic resolution for non-conflicting changes

**Technical Scenarios**:
- New file in one vault only
- Deletion in one vault only
- Metadata-only changes
- Identical content changes

**Auto-Merge Rules**:
```python
if only_one_changed():
    use_changed_version()
elif both_changed_identically():
    keep_current()
elif only_metadata_changed():
    use_content_version()
else:
    require_user_decision()
```

## ID Management Features

### 1. UUID Generation System

**Description**: Cryptographically secure unique identifier generation

**Technical Specification**:
- Algorithm: UUID version 4
- Entropy: 122 bits of randomness
- Format: 8-4-4-4-12 hexadecimal
- Collision resistance: 2^61 IDs for 50% probability

**Generation Process**:
```python
import uuid
cast_id = str(uuid.uuid4())
# Result: "550e8400-e29b-41d4-a716-446655440000"
```

### 2. Duplicate ID Detection

**Description**: Find and report files with duplicate cast-ids

**Technical Implementation**:
- Index-time validation
- Cross-vault checking
- Detailed error reporting
- Resolution suggestions

**Detection Output**:
```
⚠ Duplicate cast-id found:
  ID: 550e8400-e29b-41d4-a716-446655440000
  Files:
    - vault1/notes/file1.md
    - vault2/archive/file1-old.md
  
Suggested resolution:
  1. Regenerate ID for one file
  2. Merge if files are identical
  3. Archive older version
```

### 3. Cast-ID Validation

**Description**: Strict validation of ID format and placement

**Technical Rules**:
1. **Format**: Must match UUID v4 regex
2. **Position**: Must be first frontmatter field
3. **Uniqueness**: No duplicates in vault
4. **Persistence**: Never auto-changed

**Validation Regex**:
```python
pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
```

## Configuration Features

### 1. Hierarchical Configuration System

**Description**: Multi-level configuration with inheritance

**Technical Hierarchy**:
```
Global Config (machine-wide)
    ↓
Vault Config (per-vault)
    ↓
File Metadata (per-file)
```

**Configuration Precedence**:
1. Command-line arguments (highest)
2. Environment variables
3. Vault configuration
4. Global configuration
5. Default values (lowest)

### 2. Pattern-Based File Selection

**Description**: Flexible include/exclude patterns for indexing

**Technical Pattern Support**:
- Glob patterns (`*.md`, `**/*.txt`)
- Directory patterns (`folder/**`)
- Negation patterns (`!exclude.md`)
- Complex combinations

**Example Configuration**:
```yaml
index:
  include:
    - "01 Vault/**/*.md"
    - "02 Journal/**/*.md"
  exclude:
    - "**/_archive/**"
    - "**/*.tmp.md"
    - "**/node_modules/**"
```

### 3. Ephemeral Key Management

**Description**: Define metadata keys ignored during sync

**Technical Purpose**:
- Prevent sync loops
- Ignore local-only data
- Reduce unnecessary conflicts
- Maintain local state

**Default Ephemeral Keys**:
```yaml
merge:
  ephemeral_keys:
    - updated        # Last modified time
    - last_synced    # Sync timestamp
    - base-version   # Version tracking
    - local_cache    # Local-only data
```

## Reset & Recovery Features

### 1. Vault State Reset (`cast reset`)

**Description**: Clear Cast state while preserving content

**Technical Capabilities**:
- Clear index completely
- Remove sync state
- Delete peer information
- Preserve configuration (optional)
- Keep content intact

**Reset Options**:
```bash
cast reset              # Reset current vault
cast reset vault-name   # Reset specific vault
cast reset --force      # Skip confirmation
cast reset --keep-config # Preserve settings
```

**What Gets Reset**:
```
.cast/
├── index.json         → {} (empty)
├── sync_state.json    → {} (empty)
├── config.yaml        → preserved if --keep-config
└── [other files]      → removed
```

### 2. Recovery Mechanisms

**Description**: Built-in recovery from various failure scenarios

**Technical Safeguards**:
- Atomic file operations
- Temporary file usage
- Validation before commit
- Automatic rollback

**Recovery Scenarios**:
1. **Interrupted Sync**: Resume from last state
2. **Corrupted Index**: Rebuild with `--rebuild`
3. **Invalid Config**: Use defaults
4. **Missing Files**: Skip and report

### 3. Force Rebuild (`--rebuild`)

**Description**: Complete index reconstruction from scratch

**Technical Process**:
1. Delete existing index
2. Full directory traversal
3. Complete metadata extraction
4. Fresh digest computation
5. New index creation

**When to Use**:
- Index corruption suspected
- Major vault reorganization
- Cast version upgrade
- Debugging sync issues

## Integration Features

### 1. Obsidian Compatibility

**Description**: Full compatibility with Obsidian knowledge management

**Technical Integration**:
- Preserves Obsidian metadata
- Respects `.obsidian/` directory
- Compatible frontmatter format
- Link preservation

**Supported Features**:
- WikiLinks (`[[Note]]`)
- Tags (`#tag`)
- Frontmatter metadata
- Embedded files
- Canvas files (excluded from sync)

### 2. CLI Integration

**Description**: Rich command-line interface with modern UX

**Technical Features**:
- Colored output with Rich
- Progress indicators
- Interactive prompts
- Table formatting
- Error highlighting

**Output Formatting**:
```
✓ Success messages in green
⚠ Warnings in yellow
✗ Errors in red
→ Actions in cyan
[dim] Supplementary info
```

### 3. Cross-Platform Support

**Description**: Consistent behavior across operating systems

**Technical Compatibility**:
- Windows (path handling)
- macOS (file system)
- Linux (permissions)
- WSL (hybrid environment)

**Platform-Specific Handling**:
```python
# Configuration paths
Windows: %APPDATA%\Cast\
macOS: ~/Library/Application Support/Cast/
Linux: ~/.config/Cast/

# Editor selection
Windows: notepad
macOS: open
Linux: $EDITOR or nano
```

### 4. Scripting Support

**Description**: Automation-friendly design for scripts and workflows

**Technical Features**:
- Exit codes for success/failure
- Machine-readable output options
- Batch mode operation
- Quiet mode support
- Verbose logging

**Exit Codes**:
- 0: Success
- 1: General error
- 2: Configuration error
- 3: Sync conflict
- 4: File system error

**Automation Examples**:
```bash
# Scheduled sync
0 */4 * * * cast sync --batch --quiet

# Backup script
cast sync backup --overpower && echo "Backup complete"

# CI/CD integration
cast index --rebuild && cast sync --batch || exit 1
```

## Advanced Features

### 1. Intelligent Change Detection

**Description**: Smart detection of meaningful changes

**Technical Implementation**:
- Body-only comparison
- Metadata filtering
- Binary file detection
- Size-based optimization

**Change Types**:
- Content changes (trigger sync)
- Metadata changes (often ignored)
- Structural changes (always sync)
- Binary changes (size-based)

### 2. Atomic Operations

**Description**: All-or-nothing file operations for data safety

**Technical Process**:
```python
# Atomic write pattern
write_to_temp_file(content)
validate_temp_file()
atomic_rename(temp_file, target_file)
cleanup_temp_files()
```

**Guarantees**:
- No partial writes
- No corruption on interrupt
- Consistent state always
- Automatic cleanup

### 3. Performance Optimization

**Description**: Built-in optimizations for large vaults

**Technical Strategies**:
- Incremental indexing
- Parallel processing
- Memory streaming
- Lazy loading
- Cache utilization

**Performance Metrics**:
- 10,000 files: ~5 seconds indexing
- 100 MB file: Streamed, not loaded
- Sync check: <1 second typically
- Memory usage: O(index size)

### 4. Extensibility Framework

**Description**: Designed for future enhancements

**Technical Extension Points**:
- Sync strategies
- Storage backends
- Merge algorithms
- File processors
- UI frontends

**Plugin Architecture** (Planned):
```python
class SyncStrategy:
    def should_sync(self, file_a, file_b): pass
    def resolve_conflict(self, file_a, file_b): pass
    def post_sync(self, result): pass
```