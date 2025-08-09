# Cast Sync Configuration Guide

## Configuration File Location

Cast Sync stores configuration in `.cast/config.yaml` within each vault:

```
my-vault/
├── .cast/
│   ├── config.yaml      # Main configuration
│   ├── index.json       # File index
│   ├── objects/         # Content storage
│   └── peers/           # Sync state
└── ... (your files)
```

## Complete Configuration Reference

```yaml
# Cast protocol version
cast-version: '1'

# Vault identification and settings
vault:
  # Unique identifier for this vault
  id: my-vault
  
  # Absolute path to vault root
  root: /home/user/vaults/my-vault
  
  # Optional display name
  name: "My Personal Vault"
  
  # Optional description
  description: "Main knowledge base"

# File indexing configuration
index:
  # Glob patterns for files to include
  include:
    - "**/*.md"           # All markdown files
    - "**/*.markdown"     # Alternative extension
    - "journal/**/*.txt"  # Text files in journal
  
  # Glob patterns for files to exclude
  exclude:
    - ".git/**"           # Git repository
    - ".obsidian/**"      # Obsidian configuration
    - ".cast/**"          # Cast metadata
    - "**/.DS_Store"      # macOS metadata
    - "**/Thumbs.db"      # Windows metadata
    - "**/*.tmp"          # Temporary files
    - "private/**"        # Private folder
    - "archive/**"        # Archived content
  
  # Maximum file size to index (bytes)
  max_file_size: 104857600  # 100MB
  
  # Follow symbolic links
  follow_symlinks: false
  
  # Index hidden files (starting with .)
  index_hidden: false

# Synchronization settings
sync:
  # Sync mode (deprecated - uses frontmatter now)
  # mode: bidirectional  # or 'broadcast'
  
  # Conflict resolution strategy
  conflict_strategy: preserve  # or 'ours', 'theirs'
  
  # Create backup before sync
  backup: false
  
  # Backup directory (if backup enabled)
  backup_dir: .cast/backups
  
  # Maximum backup age (days)
  backup_retention: 30
  
  # Verify checksums after sync
  verify: true
  
  # Rules for sync behavior (deprecated)
  rules: []

# Merge configuration
merge:
  # Fields to exclude from comparison (ephemeral)
  ephemeral_keys:
    - updated         # File update timestamp
    - modified        # Modification time
    - accessed        # Last access time
    - created         # Creation time
    - last_synced     # Sync timestamp
    - word_count      # Dynamic statistics
    - char_count      # Dynamic statistics
    - cursor_position # Editor state
    - fold_state      # Editor folding
    - view_state      # View configuration
  
  # Merge strategy
  strategy: block  # 'block' or 'line'
  
  # Conflict marker style
  conflict_style: diff3  # 'merge' or 'diff3'
  
  # Auto-resolve simple conflicts
  auto_resolve: true
  
  # Preserve local formatting
  preserve_formatting: true

# Performance tuning
performance:
  # Number of parallel workers
  workers: 4
  
  # Chunk size for large files (bytes)
  chunk_size: 1048576  # 1MB
  
  # Cache digest results
  cache_digests: true
  
  # Cache expiry (seconds)
  cache_ttl: 3600
  
  # Memory limit (MB)
  memory_limit: 512

# Logging configuration
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR
  level: INFO
  
  # Log file location
  file: .cast/cast.log
  
  # Maximum log file size (bytes)
  max_size: 10485760  # 10MB
  
  # Number of backup log files
  backup_count: 5
  
  # Include timestamps
  timestamps: true

# Advanced settings
advanced:
  # Hash algorithm
  hash_algorithm: sha256
  
  # UUID version for cast-id
  uuid_version: 4
  
  # File encoding
  encoding: utf-8
  
  # Line ending style: 'lf', 'crlf', 'native'
  line_endings: lf
  
  # Timezone for timestamps
  timezone: UTC
  
  # Atomic write timeout (seconds)
  write_timeout: 30
  
  # Lock timeout (seconds)
  lock_timeout: 60

# Obsidian integration
obsidian:
  # Respect Obsidian settings
  respect_settings: true
  
  # Sync Obsidian plugins
  sync_plugins: false
  
  # Sync Obsidian themes
  sync_themes: false
  
  # Preserve workspace
  preserve_workspace: true

# Future: Network sync configuration
network:
  # Enable network sync
  enabled: false
  
  # Server URL
  server: https://sync.example.com
  
  # Authentication token
  token: ${CAST_SYNC_TOKEN}
  
  # Use TLS
  tls: true
  
  # Verify certificates
  verify_cert: true
  
  # Connection timeout (seconds)
  timeout: 30
  
  # Retry attempts
  retries: 3
```

## Configuration Sections

### Vault Configuration

The `vault` section identifies and configures the vault:

```yaml
vault:
  id: my-vault  # Must be unique across all synced vaults
  root: /absolute/path/to/vault
```

**Important:**
- `id` must be unique across all vaults you sync
- `root` should be an absolute path
- These are set during `cast init`

### Index Configuration

Controls which files are tracked:

```yaml
index:
  include:
    - "**/*.md"        # Include all markdown
    - "notes/**/*"     # Include everything in notes/
  exclude:
    - "temp/**"        # Exclude temp folder
    - "**/.DS_Store"   # Exclude OS files
```

**Pattern Syntax:**
- `*` matches any characters except `/`
- `**` matches any characters including `/`
- `?` matches single character
- `[abc]` matches any of a, b, c
- `{a,b}` matches a or b

### Merge Configuration

Controls how conflicts are handled:

```yaml
merge:
  ephemeral_keys:
    - updated      # Don't sync these fields
    - modified
  strategy: block  # Use block-based merging
  auto_resolve: true
```

**Ephemeral Keys:**
Fields listed here are preserved locally and not synchronized. Useful for:
- Timestamps that vary by system
- Editor state and preferences
- Local-only metadata

### Performance Configuration

Tune for your system:

```yaml
performance:
  workers: 4          # Parallel operations
  cache_digests: true # Speed up re-indexing
  memory_limit: 512   # MB
```

**Recommendations:**
- Increase workers for large vaults
- Enable cache for frequently synced vaults
- Adjust memory limit for system capacity

## Environment Variables

Cast Sync respects these environment variables:

```bash
# Override config file location
export CAST_CONFIG_PATH=/custom/path/config.yaml

# Set vault root
export CAST_VAULT_ROOT=/path/to/vault

# Set log level
export CAST_LOG_LEVEL=DEBUG

# Network token (for future network sync)
export CAST_SYNC_TOKEN=secret-token

# Disable colored output
export NO_COLOR=1

# Force colored output
export FORCE_COLOR=1
```

## Per-File Configuration

Files can override sync behavior using frontmatter:

```yaml
---
cast-id: 550e8400-e29b-41d4-a716-446655440000
cast-vaults:
  - vault1 (cast)   # This file broadcasts from vault1
  - vault2 (sync)   # Receives updates in vault2
cast-sync: false    # Exclude this file from sync
cast-merge: manual  # Always require manual merge
---
```

## Vault Profiles

Create profiles for different sync scenarios:

### Work Vault Profile

```yaml
# .cast/profiles/work.yaml
index:
  include:
    - "work/**/*.md"
    - "projects/**/*.md"
  exclude:
    - "personal/**"
    - "archive/**"

merge:
  ephemeral_keys:
    - company_metadata
    - internal_id
```

### Personal Vault Profile

```yaml
# .cast/profiles/personal.yaml
index:
  include:
    - "**/*.md"
  exclude:
    - "work/**"
    - "client/**"

merge:
  auto_resolve: false  # Manual review for personal notes
```

Load profile:
```bash
cast --profile personal sync vault1 vault2
```

## Sync Rules (Deprecated)

**Note:** Sync rules in config are deprecated. Use frontmatter `cast-vaults` instead.

Legacy format (for reference):
```yaml
sync:
  rules:
    - pattern: "daily/**"
      mode: local  # Don't sync
    - pattern: "shared/**"
      mode: bidirectional
    - pattern: "published/**"
      mode: broadcast
```

## Advanced Patterns

### Selective Sync by Tags

```yaml
index:
  include:
    - "**/*.md"
  
  # Custom processor (future feature)
  processors:
    - type: tag_filter
      tags: ["sync", "shared"]
      exclude_tags: ["private", "draft"]
```

### Conditional Sync

```yaml
sync:
  conditions:
    - if: "file.size > 10MB"
      action: skip
    - if: "file.age > 365 days"
      action: archive
```

### Custom Merge Handlers

```yaml
merge:
  handlers:
    - pattern: "**/*.json"
      handler: json_merge
    - pattern: "**/*.csv"
      handler: csv_merge
    - pattern: "daily/*.md"
      handler: append_only
```

## Validation

Validate configuration:

```bash
cast validate-config
```

Output:
```
✓ Vault ID is unique
✓ Root path exists
✓ Include patterns are valid
✓ No conflicting exclude patterns
✓ Configuration is valid
```

## Migration

### From Version 0.x to 1.x

```bash
cast migrate-config
```

This will:
1. Backup old configuration
2. Convert to new format
3. Validate migrated config
4. Update vault metadata

## Best Practices

### 1. Minimal Excludes

Start with minimal excludes and add as needed:

```yaml
index:
  exclude:
    - ".git/**"
    - ".obsidian/**"
    - ".cast/**"
```

### 2. Consistent IDs

Use descriptive, consistent vault IDs:

```yaml
vault:
  id: john-laptop  # Good: identifies owner and device
  # id: vault1     # Bad: not descriptive
```

### 3. Document Ephemeral Keys

Comment why fields are ephemeral:

```yaml
merge:
  ephemeral_keys:
    - updated        # System-generated timestamp
    - word_count     # Calculated dynamically
    - last_opened    # Editor-specific
```

### 4. Test Patterns

Test include/exclude patterns:

```bash
cast ls --pattern "**/*.md" --exclude "private/**"
```

### 5. Version Control Config

Include `.cast/config.yaml` in version control:

```bash
git add .cast/config.yaml
git commit -m "Cast Sync configuration"
```

## Troubleshooting Configuration

### Files Not Being Indexed

Check include/exclude patterns:

```bash
cast debug-patterns "path/to/file.md"
```

Output:
```
File: path/to/file.md
✗ Excluded by pattern: private/**
```

### Unexpected Merge Behavior

Review ephemeral keys:

```bash
cast debug-merge file.md
```

Shows which fields are treated as ephemeral.

### Performance Issues

Profile configuration impact:

```bash
cast profile-config
```

Output:
```
Index patterns: 0.3s
Exclude checks: 0.1s
Cache lookups: 0.05s
Total: 0.45s
```

## Default Configuration

If no config exists, Cast uses these defaults:

```python
DEFAULT_CONFIG = {
    "cast-version": "1",
    "vault": {
        "id": os.path.basename(vault_path),
        "root": str(vault_path)
    },
    "index": {
        "include": ["**/*.md"],
        "exclude": [".git/**", ".obsidian/**", ".cast/**"]
    },
    "merge": {
        "ephemeral_keys": ["updated", "modified"],
        "strategy": "block"
    }
}
```

## Configuration Schema

JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["cast-version", "vault"],
  "properties": {
    "cast-version": {
      "type": "string",
      "enum": ["1"]
    },
    "vault": {
      "type": "object",
      "required": ["id", "root"],
      "properties": {
        "id": {"type": "string"},
        "root": {"type": "string"}
      }
    },
    "index": {
      "type": "object",
      "properties": {
        "include": {
          "type": "array",
          "items": {"type": "string"}
        },
        "exclude": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```