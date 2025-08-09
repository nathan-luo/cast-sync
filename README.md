# Cast Sync Service

Knowledge-aware sync for Markdown vaults. Cast synchronizes content blocks between vaults while preserving each vault's local YAML frontmatter.

## Features

- **Selective sync**: Only syncs files with `cast-vaults` field in YAML
- **Content-only sync**: Syncs body content while preserving local YAML
- **Vault roles**: Files specify `vault (cast)` for originals, `vault (sync)` for copies
- **UUID-based tracking**: Files maintain identity across renames and moves
- **Block-aware merging**: Understands markdown heading structure
- **Conflict resolution**: Interactive resolver for content conflicts
- **Local-first**: No servers or cloud dependencies

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv tool install cast-sync

# Or with pip
pip install cast-sync

# Or from source
git clone https://github.com/yourusername/cast-sync
cd cast-sync
uv sync
```

### Basic Usage

```bash
# Initialize Cast in a vault
cast init

# Create a new vault with recommended structure
cast vault create ~/Vaults/MyVault

# Add UUIDs to existing files
cast ids add

# Build/update the index
cast index

# Configure sync between vaults
cast install  # Creates global config
# Edit ~/.config/cast/config.yaml to add vault paths

# Plan a sync (dry run)
cast plan source-vault dest-vault

# Execute sync
cast sync source-vault dest-vault --apply

# Resolve conflicts interactively
cast resolve
```

## Vault Structure

Cast works with the following recommended vault layout:

```
/VaultRoot
├── .cast/                  # Cast state files
├── 01 Vault/              # All Markdown documents
├── 02 Journal/            # Time-based index pages
├── 03 Records/            # Raw recordings (audio/video)
├── 04 Sources/            # External materials (PDFs/books)
├── 05 Media/              # Images and diagrams
├── 06 Extras/             # Templates and snippets
└── 09 Exports/            # Generated outputs
```

## Configuration

### Vault Configuration (`.cast/config.yaml`)

```yaml
cast-version: 1
vault:
  id: "MyVault"
  root: "."
index:
  include:
    - "01 Vault/**/*.md"
  exclude:
    - ".git/**"
    - ".cast/**"
sync:
  rules:
    - id: "to-backup"
      mode: "broadcast"  # broadcast | bidirectional | mirror
      from: "MyVault"
      to:
        - id: "BackupVault"
          path: "/path/to/backup"
      select:
        paths_any: ["01 Vault/**/*.md"]
```

### Global Configuration (`~/.config/cast/config.yaml`)

```yaml
vaults:
  MyVault: "/Users/me/Vaults/MyVault"
  BackupVault: "/Users/me/Vaults/Backup"
  SharedVault: "/Users/me/Vaults/Shared"
```

## Sync Modes

### Broadcast (One-way)
Source is authoritative. Conflicts if destination was modified.

```bash
cast sync source dest --rule broadcast-rule --apply
```

### Bidirectional (Merge)
Performs 3-way merge using stored baselines.

```bash
cast sync vault1 vault2 --rule bidir-rule --apply
```

### Mirror (Force)
Overwrites destination regardless of changes.

```bash
cast sync source dest --rule mirror-rule --apply --force
```

## How Cast Works

### File Selection

Cast only syncs files that have a `cast-vaults` field in their YAML frontmatter:

```yaml
---
cast-id: f47ac10b-58cc-4372-a567-0e02b2c3d479
cast-type: original         # original | sync | casted
cast-version: 1             # Cast protocol version
cast-vaults:
  - nathansvault (cast)     # Original vault
  - backup (sync)           # Synchronized copy
  - shared (sync)           # Another copy
tags: [personal, draft]     # Local field - stays in this vault
category: notes             # Local field - stays in this vault
---
```

Files without `cast-vaults` are ignored by Cast.

### Content Syncing

Cast syncs **cast-* fields and body content** while preserving local fields:

**What syncs across vaults:**
- All `cast-*` fields (cast-id, cast-type, cast-vaults, cast-version, cast-codebases)
- Body content (markdown after the YAML)

**What stays local to each vault:**
- Non-cast fields (tags, category, status, custom fields)
- These let each vault maintain its own organization

**Title comes from filename**, not YAML - ensuring consistency across vaults.

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/cast-sync
cd cast-sync

# Install with dev dependencies
uv sync --all-extras --dev

# Run tests
uv run poe test

# Format and lint
uv run poe fmt
uv run poe lint

# Type checking
uv run poe check

# Run all checks
uv run poe all
```

### Project Structure

```
cast-sync/
├── cast/              # Main package
│   ├── cli.py        # CLI interface
│   ├── config.py     # Configuration management
│   ├── ids.py        # UUID management
│   ├── index.py      # File indexing
│   ├── merge_mkd.py  # MKD-aware merging
│   ├── sync.py       # Sync engine
│   └── ...
├── tests/            # Test suite
├── docs/             # Documentation
└── pyproject.toml    # Project configuration
```

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=cast

# Specific test file
uv run pytest tests/test_merge.py
```

## Docker

Build and run Cast in a container:

```bash
# Build image
docker build -t cast-sync .

# Run command
docker run -v ~/Vaults:/vaults cast-sync sync /vaults/Source /vaults/Dest

# Interactive shell
docker run -it -v ~/Vaults:/vaults cast-sync bash
```

## Troubleshooting

### Common Issues

1. **Lock contention**: Another Cast process is running
   - Solution: Wait or remove stale lock file

2. **Missing cast-id**: Files lack UUID
   - Solution: Run `cast ids add`

3. **Conflicts detected**: Both sides changed
   - Solution: Run `cast resolve` or use `--force`

4. **Index out of date**: File changes not detected
   - Solution: Run `cast index --rebuild`

### Debug Mode

```bash
# Enable verbose output
cast --verbose sync source dest

# Check configuration
cast config show

# Validate index
cast index --validate
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run `uv run poe all` to verify
6. Submit a pull request

## License

Apache 2.0 - See LICENSE file for details

## Roadmap

- [x] Core sync engine
- [x] MKD-aware merging
- [x] CLI interface
- [ ] Transport adapters (HTTP/S3/SSH)
- [ ] Delete propagation (tombstones)
- [ ] Git merge driver
- [ ] Real-time file watching
- [ ] CCP protocol for cross-syntax exchange

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/cast-sync/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/cast-sync/discussions)
- Documentation: [docs/](docs/)