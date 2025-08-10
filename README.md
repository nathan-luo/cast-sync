# Cast - Simple Multi-Vault Markdown Sync

Cast is a production-ready synchronization tool for Markdown vaults (Obsidian, Logseq, etc.) that uses UUIDs to track files across multiple vaults with smart conflict resolution.

## Features

- **UUID-based tracking** - Files tracked by `cast-id`, not path
- **Smart auto-merge** - Automatically syncs when only one side changed
- **Interactive conflicts** - Side-by-side comparison when both changed
- **Selective sync** - `cast-vaults` field controls which vaults sync
- **Simple & reliable** - No complex merging, just straightforward sync

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/cast-sync.git
cd cast-sync

# Install dependencies
pip install typer rich pyyaml filelock

# Install Cast globally
python -m cast install
```

## Quick Start

### 1. Initialize Vaults

```bash
# Initialize Cast in each vault
cast init ~/vault1 --id vault1
cast init ~/vault2 --id vault2
cast init ~/vault3 --id vault3

# Or from within a vault
cd ~/my-vault
cast init
```

### 2. Add Files to Sync

Files need a `cast-vaults` field to sync:

```markdown
---
cast-vaults:
  - vault1 (sync)
  - vault2 (sync)
---
# My Note

Content that syncs between vault1 and vault2
```

Run `cast index --fix` to auto-add `cast-id` to files with cast metadata.

### 3. Sync Vaults

```bash
# Interactive sync (default)
cast sync vault1

# Force current vault everywhere
cast sync vault1 --overpower

# Non-interactive batch mode
cast sync vault1 --batch
```

## How It Works

1. **Files are tracked by UUID** (`cast-id`) not path - rename/move freely
2. **Body-only comparison** - Ignores metadata changes in YAML frontmatter
3. **Smart auto-merge** - If only one vault changed since last sync, auto-applies
4. **Selective sync** - Only syncs files where both vaults are listed in `cast-vaults`

## Commands

### Core Commands

- `cast init [path]` - Initialize Cast in a vault
- `cast index` - Build/update file index
  - `--fix` - Auto-add cast-ids to files with cast metadata
- `cast sync [vault]` - Sync with other vaults
  - `--overpower` - Force current version everywhere
  - `--batch` - Non-interactive mode
- `cast vaults` - List registered vaults

### Vault Management

- `cast vault create <path>` - Create new vault structure
- `cast vault obsidian` - Initialize Obsidian config
- `cast register <name> <path>` - Register existing vault
- `cast reset [vault]` - Reset Cast state

## Configuration

### Vault Config (`.cast/config.yaml`)

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
```

### Cast Metadata

```yaml
---
cast-id: 123e4567-e89b-12d3-a456-426614174000  # Auto-generated UUID
cast-vaults:                                    # Which vaults to sync with
  - vault1 (sync)
  - vault2 (sync)
---
```

## Examples

### Sync Specific Vaults

```yaml
---
cast-vaults:
  - personal (sync)
  - work (sync)
  # Not synced to backup vault
---
```

### Handle Conflicts

When both vaults changed:

```
╭────── vault1 ──────╮ ╭────── vault2 ──────╮
│ Content from       │ │ Different content  │
│ vault1             │ │ from vault2        │
╰────────────────────╯ ╰────────────────────╯

Choose: 1=vault1, 2=vault2, s=skip, q=quit:
```

## Best Practices

1. **Run `cast index` before syncing** to ensure fresh state
2. **Use `--batch` for automation** with cron/scheduled tasks
3. **Use `--overpower` sparingly** - it forces changes everywhere
4. **Set `cast-vaults` deliberately** - controls sync scope

## Troubleshooting

**Files not syncing?**
- Check `cast-vaults` field lists both vaults
- Run `cast index --fix` to add missing cast-ids
- Verify include patterns in `.cast/config.yaml`

**Too many conflicts?**
- Sync more frequently for auto-merge to work
- Use `--overpower` from authoritative vault
- Check `.cast/sync_state.json` for last sync info

## License

MIT