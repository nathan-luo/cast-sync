# Cast Sync User Guide

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/cast-sync.git
cd cast-sync

# Install dependencies
pip install -r requirements.txt

# Install cast command
pip install -e .
```

### Using pip

```bash
pip install cast-sync
```

## Getting Started

### 1. Initialize Your First Vault

Navigate to your Obsidian vault or markdown directory:

```bash
cd /path/to/my-vault
cast init
```

This creates a `.cast/` directory with:
- `config.yaml` - Vault configuration
- `index.json` - File index (created on first index)
- `objects/` - Content store
- `peers/` - Sync state with other vaults

### 2. Index Your Files

Scan and index all markdown files:

```bash
cast index
```

Output:
```
Indexing vault: my-vault
Found 42 files to index
Indexed: my-notes/daily/2024-01-01.md
Indexed: my-notes/projects/cast-sync.md
...
✓ Indexed 42 files
```

### 3. Set Up a Second Vault

Initialize and index another vault:

```bash
cd /path/to/backup-vault
cast init
cast index
```

### 4. Sync Between Vaults

Preview what will be synced (dry run):

```bash
cast sync /path/to/my-vault /path/to/backup-vault
```

Apply the sync:

```bash
cast sync /path/to/my-vault /path/to/backup-vault --apply
```

## Common Use Cases

### Backing Up Your Vault

Create a one-way backup to another location:

```bash
# Set up backup vault
cd /backup/location
cast init

# Configure source vault as broadcast (cast) mode
# Edit my-vault file's frontmatter:
# cast-vaults:
# - my-vault (cast)
# - backup-vault (sync)

# Perform backup
cast sync /path/to/my-vault /backup/location --apply
```

### Bidirectional Sync Between Devices

Sync between desktop and laptop:

```bash
# On both vaults, set bidirectional mode in frontmatter:
# cast-vaults:
# - desktop (sync)
# - laptop (sync)

# Sync from desktop to laptop
cast sync ~/Desktop/vault ~/Laptop/vault --apply

# Later, sync from laptop to desktop
cast sync ~/Laptop/vault ~/Desktop/vault --apply
```

### Selective Sync

Configure which files to sync in `.cast/config.yaml`:

```yaml
index:
  include:
    - "Projects/**/*.md"
    - "Archive/**/*.md"
  exclude:
    - "Daily/**"
    - "Private/**"
    - ".obsidian/**"
```

Then reindex and sync:

```bash
cast index
cast sync source dest --apply
```

## Working with Conflicts

### Detecting Conflicts

When files are modified in both vaults:

```bash
cast sync vault1 vault2 --apply
```

Output:
```
Sync Results
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File             ┃ Action ┃ Status                  ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ notes/project.md │ MERGE  │ merged with 2 conflicts │
└──────────────────┴────────┴─────────────────────────┘
```

### Listing Conflict Files

```bash
cast conflicts
```

Output:
```
Found 2 conflict file(s)

  • notes/project.conflicted-20240101-120000.md
  • notes/meeting.conflicted-20240101-120100.md
```

### Resolving Conflicts

Interactive resolution:

```bash
cast resolve
```

This will:
1. Show each conflict with context
2. Let you choose: keep source, keep destination, or edit manually
3. Clean up conflict files after resolution

Manual resolution:

1. Open the `.conflicted-*` file
2. Look for conflict markers:
   ```
   <<<<<<< SOURCE
   Content from source vault
   =======
   Content from destination vault
   >>>>>>> DESTINATION
   ```
3. Edit to your desired state
4. Save and remove conflict markers
5. Delete the `.conflicted-*` file

## Understanding Sync Modes

### Broadcast Mode (One-Way)

Used for publishing or one-way backup:

```yaml
# In source files' frontmatter:
cast-vaults:
- main (cast)      # This vault broadcasts
- published (sync) # This vault receives
```

Characteristics:
- Changes only flow from (cast) to (sync)
- No changes accepted from (sync) vault
- Ideal for: backups, publishing, distribution

### Bidirectional Mode (Two-Way)

Used for active work across devices:

```yaml
# In all files' frontmatter:
cast-vaults:
- desktop (sync)
- mobile (sync)
```

Characteristics:
- Changes flow both directions
- Automatic conflict detection
- 3-way merge with baseline tracking
- Ideal for: multi-device work, collaboration

## YAML Frontmatter

### Cast Fields

Cast Sync uses special fields in YAML frontmatter:

```yaml
---
cast-id: 550e8400-e29b-41d4-a716-446655440000
cast-vaults:
- vault1 (sync)
- vault2 (sync)
cast-version: 1
cast-type: note
---
```

- **cast-id**: Unique identifier (auto-generated)
- **cast-vaults**: List of vaults and their roles
- **cast-version**: Format version
- **cast-type**: Optional content type

### Local Fields

Non-cast fields are preserved locally and not synced:

```yaml
---
cast-id: 550e8400-e29b-41d4-a716-446655440000
# These fields stay local to each vault:
modified: 2024-01-01
favorite: true
workspace: personal
---
```

## Command Reference

### cast init

Initialize a vault for synchronization.

```bash
cast init [OPTIONS]
```

Options:
- `--vault-id TEXT`: Custom vault identifier (default: directory name)

### cast index

Index or reindex files in the vault.

```bash
cast index [OPTIONS] [VAULT_PATH]
```

Options:
- `--force`: Force reindex all files
- `--verbose`: Show detailed progress

Arguments:
- `VAULT_PATH`: Path to vault (default: current directory)

### cast sync

Synchronize between two vaults.

```bash
cast sync SOURCE DEST [OPTIONS]
```

Options:
- `--apply`: Apply changes (without this, runs in dry-run mode)
- `--verbose`: Show detailed operations
- `--force`: Ignore safety checks

Arguments:
- `SOURCE`: Source vault path
- `DEST`: Destination vault path

### cast conflicts

List conflict files in a vault.

```bash
cast conflicts [VAULT_PATH]
```

Arguments:
- `VAULT_PATH`: Path to vault (default: current directory)

### cast resolve

Interactively resolve conflicts.

```bash
cast resolve [OPTIONS] [VAULT_PATH]
```

Options:
- `--all`: Resolve all conflicts with same choice
- `--strategy [ours|theirs|manual]`: Resolution strategy

Arguments:
- `VAULT_PATH`: Path to vault (default: current directory)

### cast snapshot

Create a snapshot of the vault state.

```bash
cast snapshot [OPTIONS] [VAULT_PATH]
```

Options:
- `--output PATH`: Snapshot output path
- `--include-objects`: Include object store in snapshot

## Best Practices

### 1. Regular Indexing

Run `cast index` after:
- Adding new files
- Renaming files
- Major content changes

### 2. Dry Run First

Always preview sync operations:

```bash
# Preview
cast sync source dest

# If looks good, apply
cast sync source dest --apply
```

### 3. Conflict Prevention

- Sync frequently to minimize conflicts
- Avoid editing same sections simultaneously
- Use broadcast mode for one-way flows
- Communicate with collaborators

### 4. Backup Strategy

- Keep multiple vault copies
- Use broadcast mode for backups
- Store snapshots periodically
- Test restore procedures

### 5. Performance Tips

For large vaults:
- Use selective sync with include/exclude patterns
- Index incrementally with regular `cast index`
- Clean up old conflict files
- Periodically clean `.cast/objects/`

## Troubleshooting Quick Fixes

### "Not a Cast vault"

Run `cast init` in the vault directory.

### "Index out of date"

Run `cast index` to update.

### "Merge conflicts detected"

Use `cast resolve` or manually edit conflict files.

### "Permission denied"

Check file permissions and vault lock files.

### "Sync seems stuck"

1. Check for `.lock` files in `.cast/`
2. Remove stale locks if process crashed
3. Retry operation

## Advanced Usage

### Scripting and Automation

Automate syncs with cron or task scheduler:

```bash
#!/bin/bash
# Daily backup script
cast index /home/user/vault
cast sync /home/user/vault /backup/vault --apply

# Check for conflicts
if cast conflicts /backup/vault | grep -q "conflict"; then
    echo "Conflicts detected!" | mail -s "Vault Sync Alert" user@example.com
fi
```

### Custom Merge Strategies

Configure merge behavior in `.cast/config.yaml`:

```yaml
merge:
  ephemeral_keys:
    - modified
    - accessed
    - session_data
  strategy: block  # or 'line'
  conflict_style: diff3  # or 'merge'
```

### Integration with Git

Combine with Git for version control:

```bash
# After sync
cd vault
git add .
git commit -m "Sync from $(cast info --vault-id)"
git push
```

## Tips and Tricks

### 1. Quick Vault Switch

```bash
# Create aliases
alias vault1='cd ~/vaults/personal && cast index'
alias vault2='cd ~/vaults/work && cast index'
```

### 2. Conflict Prevention Workflow

```bash
# Before starting work
cast sync other-vault this-vault --apply

# After finishing work
cast index
cast sync this-vault other-vault --apply
```

### 3. Monitoring Changes

```bash
# See what changed since last sync
cast diff vault1 vault2
```

### 4. Vault Statistics

```bash
# Count synced files
cast info --stats
```

## Safety Notes

1. **Always backup** before major sync operations
2. **Test with dry-run** before applying changes
3. **Resolve conflicts promptly** to avoid confusion
4. **Keep vaults indexed** for accurate sync
5. **Avoid simultaneous edits** when possible

## Getting Help

- Run `cast --help` for command help
- Check [Troubleshooting Guide](./troubleshooting.md) for common issues
- See [Configuration Guide](./configuration.md) for detailed options
- Review [Architecture](./architecture.md) for understanding internals