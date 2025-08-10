# Cast - Simple & Reliable Markdown Vault Sync

Cast is a lightweight, reliable synchronization tool for Markdown vaults (like Obsidian, Logseq, etc.). It tracks files by UUID rather than path, enabling robust sync across multiple vaults with automatic conflict resolution.

## Features

- **UUID-based tracking** - Files are tracked by `cast-id` in YAML frontmatter, not by path
- **Smart auto-merge** - Automatically applies changes when only one side has been modified
- **Interactive conflict resolution** - When both sides change, see a side-by-side diff and choose
- **Simple & reliable** - No complex merge algorithms, just straightforward file sync
- **Multi-vault support** - Sync across any number of registered vaults

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cast-sync.git
cd cast-sync

# Install dependencies
pip install -r requirements.txt

# Install Cast globally
cast install
```

## Quick Start

### 1. Initialize your vaults

```bash
# Initialize Cast in each vault
cast init /path/to/vault1 --id vault1
cast init /path/to/vault2 --id vault2
```

This creates a `.cast/` directory with:
- `config.yaml` - Vault configuration
- `index.json` - File index with content digests
- `sync_state.json` - Tracks last sync state for auto-merge

### 2. Add Cast IDs to your files

Cast tracks files using UUIDs in the YAML frontmatter:

```markdown
---
cast-id: 123e4567-e89b-12d3-a456-426614174000
---
# My Note

Content here...
```

Files with `cast-vaults` or other `cast-*` metadata will automatically get IDs when indexed:

```bash
# Build/update the index (auto-adds IDs to cast-* files)
cast index vault1
```

### 3. Sync your vaults

```bash
# Interactive sync (prompts for conflicts)
cast sync vault1

# Force current vault's version everywhere
cast sync vault1 --overpower

# Non-interactive mode (marks conflicts)
cast sync vault1 --batch
```

## How It Works

### Smart Auto-Merge

Cast tracks the content digest from the last successful sync. When syncing:

1. **Only vault1 changed** → Automatically uses vault1's version
2. **Only vault2 changed** → Automatically uses vault2's version  
3. **Both changed** → Shows conflict, lets you choose
4. **Neither changed** → Already in sync

This means you only see conflicts when both vaults have actual changes - no unnecessary prompts!

### Conflict Resolution

When both vaults have changes, Cast shows a side-by-side comparison:

```
╭────────── vault1 ──────────╮ ╭────────── vault2 ──────────╮
│ Content from vault1        │ │ Content from vault2        │
│ with vault1's changes      │ │ with vault2's changes      │
╰────────────────────────────╯ ╰────────────────────────────╯

Choose version: 1=vault1, 2=vault2, s=skip, q=quit:
```

### File Structure

Cast expects vaults to follow a standard structure:

```
vault/
├── 01 Vault/       # Indexed by default
│   ├── note1.md
│   └── note2.md
├── 02 Areas/       # Add to config to index
├── 03 Records/     # Excluded by default
└── .cast/
    ├── config.yaml
    ├── index.json
    └── sync_state.json
```

## Commands

### Core Commands

- `cast init <path>` - Initialize Cast in a vault
- `cast index [vault]` - Build/update the file index
- `cast sync [vault]` - Synchronize with other vaults
  - `--overpower` - Force current vault's version
  - `--batch` - Non-interactive mode
- `cast vaults` - List all registered vaults

### Management Commands

- `cast register <name> <path>` - Register a vault globally
- `cast reset [vault]` - Reset vault's Cast state
- `cast config` - Edit global configuration

### Utility Commands

- `cast ids add [vault]` - Add UUIDs to files
- `cast plan <source> <dest>` - Preview sync changes (dry run)
- `cast version` - Show Cast version

## Configuration

### Vault Configuration (`.cast/config.yaml`)

```yaml
cast-version: "1"
vault:
  id: vault1
  root: /path/to/vault
index:
  include:
    - "01 Vault/**/*.md"
    - "02 Areas/**/*.md"
  exclude:
    - ".git/**"
    - ".obsidian/**"
    - "03 Records/**"
```

### Global Configuration

Stored in `~/.config/Cast/config.yaml` (Linux/Mac) or `%APPDATA%\Cast\config.yaml` (Windows):

```yaml
vaults:
  vault1: /path/to/vault1
  vault2: /path/to/vault2
```

## Cast Metadata

Cast uses YAML frontmatter for tracking:

```yaml
---
cast-id: 123e4567-e89b-12d3-a456-426614174000  # Required - unique ID
cast-vaults:                                    # Optional - vault list
  - vault1
  - vault2
cast-type: Note                                 # Optional - document type
---
```

The `cast-id` is:
- Automatically added to files with other `cast-*` fields
- Always placed first in the YAML frontmatter
- Never changed once assigned

## Examples

### Sync all vaults with a file

```bash
# Add cast-vaults to specify sync targets
---
cast-id: 123e4567-e89b-12d3-a456-426614174000
cast-vaults:
  - personal
  - work
  - backup
---

# Now sync from any vault
cast sync personal  # Syncs to work and backup
cast sync work      # Syncs to personal and backup
```

### Handle a conflicted file

```bash
# When both vaults changed the same file
cast sync vault1

# Cast shows both versions side-by-side
# Choose: 1 (vault1), 2 (vault2), or s (skip)

# Or force one version everywhere
cast sync vault1 --overpower
```

### Set up automated sync

```bash
# Add to crontab for hourly sync
0 * * * * cd /path/to/vault1 && cast sync vault1 --batch

# Or use a sync script
#!/bin/bash
cast index vault1
cast index vault2
cast sync vault1 --batch || cast sync vault1  # Try batch, fall back to interactive
```

## Tips

1. **Always index before syncing** - Cast auto-indexes, but explicit indexing ensures freshness
2. **Use --overpower carefully** - It forces the current vault's version everywhere
3. **Commit after sync** - Use `cast commit` or git to snapshot your vault state
4. **Check sync state** - Look at `.cast/sync_state.json` to see last sync digests

## Troubleshooting

### Files not syncing
- Check they have a `cast-id` in frontmatter
- Ensure they're in an indexed directory (see `.cast/config.yaml`)
- Run `cast index` to rebuild the index

### Auto-merge not working
- Sync once to establish baseline digests
- Check `.cast/sync_state.json` has digest entries
- Ensure indices are up-to-date (`cast index`)

### Conflicts on every sync
- One vault may have outdated index
- Run `cast index` on both vaults
- Do one sync choosing versions to establish baseline

## Architecture

Cast is designed for simplicity and reliability:

- **No complex merging** - Just detects if files are different
- **No object store** - Files are the source of truth
- **No peer states** - Just tracks last sync digest
- **Body-only comparison** - Ignores YAML metadata changes

This makes Cast predictable and easy to debug - it's just comparing file contents and copying files.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Cast is designed to be simple and maintainable.

Key principles:
- Simplicity over features
- Reliability over performance  
- Explicit over implicit
- User control over automation