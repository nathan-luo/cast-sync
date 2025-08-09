# Cast Sync Documentation

Cast Sync is a distributed file synchronization system designed specifically for Obsidian vaults and markdown-based knowledge management systems. It provides intelligent, content-aware synchronization with automatic conflict resolution and support for both unidirectional and bidirectional sync modes.

## Table of Contents

- [Overview](./overview.md) - High-level introduction to Cast Sync
- [Architecture](./architecture.md) - System design and components
- [User Guide](./user-guide.md) - How to use Cast Sync
- [Configuration](./configuration.md) - Detailed configuration options
- [Sync Protocol](./sync-protocol.md) - How synchronization works
- [API Reference](./api-reference.md) - Module and function documentation
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Development](./development.md) - Contributing and development setup

## Quick Links

- [CAST Fields Reference](./CAST_FIELDS.md) - YAML frontmatter fields
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Original design document

## Key Features

- **Content-aware synchronization**: Understands markdown structure and YAML frontmatter
- **Automatic conflict detection**: Smart detection of real conflicts vs simple appends
- **Bidirectional and broadcast modes**: Flexible sync patterns
- **Obsidian-friendly**: Preserves local metadata and respects .obsidian folders
- **Distributed architecture**: No central server required
- **Incremental sync**: Only syncs changed content
- **Peer state tracking**: Maintains sync history between vault pairs

## Getting Started

```bash
# Initialize a vault
cast init

# Index files in the vault
cast index

# Sync between vaults
cast sync source_vault dest_vault --apply

# List conflicts
cast conflicts

# Resolve conflicts interactively
cast resolve
```

## System Requirements

- Python 3.11 or higher
- Supported platforms: Linux, macOS, Windows
- Dependencies: PyYAML, pathspec, typer, rich, filelock

## License

This project is distributed under the MIT License. See the main README for details.