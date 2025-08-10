# Cast Sync - User Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Setting Up Your First Vault](#setting-up-your-first-vault)
- [Synchronizing Vaults](#synchronizing-vaults)
- [Managing Multiple Vaults](#managing-multiple-vaults)
- [Handling Conflicts](#handling-conflicts)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [FAQ](#faq)

## Quick Start

Get Cast up and running in 5 minutes:

```bash
# Install Cast
pip install cast-sync

# Initialize Cast system
cast install

# Navigate to your vault
cd ~/my-vault

# Initialize the vault
cast init
# Enter vault name when prompted

# Register another vault
cast register backup /path/to/backup-vault

# Synchronize vaults
cast sync
```

## Installation

### Requirements

- Python 3.8 or higher
- pip, pipx, or uv package manager
- Read/write access to vault directories

### Installation Methods

#### Using pip (Recommended)
```bash
pip install cast-sync
```

#### Using uv (Fast)
```bash
uv tool install cast-sync
```

#### Using pipx (Isolated)
```bash
pipx install cast-sync
```

#### From Source (Development)
```bash
git clone https://github.com/yourusername/cast-sync
cd cast-sync
pip install -e .
```

### Verify Installation

```bash
cast version
# Output: Cast version 1.0.0
```

## Basic Usage

### Command Structure

Cast commands follow this pattern:
```bash
cast <command> [arguments] [options]
```

### Getting Help

```bash
# General help
cast --help

# Command-specific help
cast sync --help
cast init --help
```

### Common Options

- `--verbose` or `-v`: Show detailed output
- `--quiet` or `-q`: Suppress non-error output
- `--help`: Show help message

## Setting Up Your First Vault

### Step 1: Install Cast System

First-time setup (only needed once per machine):

```bash
cast install
```

This creates the global configuration at:
- Linux/Mac: `~/.config/Cast/config.yaml`
- Windows: `%APPDATA%\Cast\config.yaml`

### Step 2: Initialize a Vault

Navigate to your Markdown vault directory:

```bash
cd ~/Documents/MyVault
cast init
```

You'll be prompted for a vault name:
```
Enter a name for this vault [MyVault]: my-main-vault
✓ Initialized Cast in /home/user/Documents/MyVault
  Vault ID: my-main-vault
  Registered in global config
```

### Step 3: Create Vault Structure (Optional)

If starting a new vault, use the recommended structure:

```bash
cast vault create ~/Documents/NewVault
cd ~/Documents/NewVault
cast init
```

This creates:
```
NewVault/
├── 01 Vault/       # Main content (synchronized)
├── 02 Journal/     # Daily notes
├── 03 Records/     # Audio/video
├── 04 Sources/     # References
├── 05 Media/       # Images
└── 06 Extras/      # Templates
```

### Step 4: Configure Vault (Optional)

Edit vault-specific settings:

```bash
cast config  # Opens global config
# OR edit .cast/config.yaml directly
```

## Synchronizing Vaults

### Basic Sync

Synchronize current vault with all connected vaults:

```bash
cast sync
```

Output:
```
Building index for my-main-vault...
✓ Index updated (1,234 files)

Syncing with backup-vault...
✓ 15 files synced
⚠ 2 conflicts need resolution

Summary:
✓ 15 files synced successfully
⚠ 2 conflicts remaining
```

### Sync Specific Vault

Sync from any directory by specifying vault name:

```bash
cast sync my-main-vault
```

### Force Sync (Overpower Mode)

Force current vault's version everywhere:

```bash
cast sync --overpower
```

**Warning**: This overwrites all conflicting files in other vaults!

### Batch Mode (Non-Interactive)

For automated scripts or cron jobs:

```bash
cast sync --batch
```

Conflicts are skipped in batch mode.

## Managing Multiple Vaults

### List All Vaults

View all registered vaults:

```bash
cast vaults
```

Output:
```
┌─────────────────────────────────────────┐
│         Configured Vaults               │
├──────────┬────────────────┬─────────────┤
│ ID       │ Path           │ Status      │
├──────────┼────────────────┼─────────────┤
│ main     │ ~/vaults/main  │ ✓ Initialized│
│ work     │ ~/vaults/work  │ ✓ Initialized│
│ backup   │ /mnt/backup    │ ⚠ Not init  │
└──────────┴────────────────┴─────────────┘
```

### Register Existing Vault

Add an existing vault to Cast:

```bash
cast register backup-vault /path/to/backup
cd /path/to/backup
cast init
```

### Remove Vault Registration

Edit the global config:

```bash
cast config
# Remove the vault entry from the YAML file
```

### Working with Multiple Vaults

```bash
# Sync specific vault
cast sync work

# Index specific vault
cast index ~/vaults/backup

# Reset specific vault
cast reset backup --force
```

## Handling Conflicts

### Understanding Conflicts

Conflicts occur when the same file is modified in multiple vaults between syncs.

### Interactive Resolution

When conflicts are detected, Cast shows:

```
════════════════════════════════════════════════
CONFLICT: 01 Vault/Notes/project.md
────────────────────────────────────────────────
Currently in main (1,234 bytes):
────────────────────────────────────────────────
# Project Notes
Last updated: 2024-01-15

New content from main vault...

────────────────────────────────────────────────
In backup (1,189 bytes):
────────────────────────────────────────────────
# Project Notes
Last updated: 2024-01-14

Different content from backup vault...

────────────────────────────────────────────────
Choose: [1] Use main / [2] Use backup / [3] Skip
> 
```

### Resolution Options

1. **Use Current Vault** (1): Keep your current version
2. **Use Other Vault** (2): Replace with other vault's version
3. **Skip** (3): Leave both versions as-is, resolve later

### Auto-Merge Scenarios

Cast automatically resolves when:
- Only one vault modified the file
- Both made identical changes
- Only metadata changed (timestamps, etc.)

### Conflict Prevention

Best practices to minimize conflicts:

1. **Sync frequently**: Run `cast sync` regularly
2. **Sync before editing**: Always sync before major work
3. **Sync after editing**: Sync immediately after changes
4. **Use vault roles**: Designate primary/secondary vaults

## Advanced Usage

### Controlling What Syncs

#### Using cast-vaults Field

Control which vaults receive a file:

```yaml
---
cast-id: "550e8400-e29b-41d4-a716-446655440000"
cast-vaults: ["main (primary)", "work (shared)"]
title: "Work Project"
---
```

This file only syncs between "main" and "work" vaults.

#### Include/Exclude Patterns

Edit `.cast/config.yaml`:

```yaml
index:
  include:
    - "01 Vault/**/*.md"
    - "Projects/**/*.md"
  exclude:
    - "**/_archive/**"
    - "**/*.tmp.md"
    - "private/**"
```

### Auto-ID Addition

Cast automatically adds IDs to files with cast metadata:

```yaml
# Before (missing cast-id)
---
cast-type: "note"
title: "My Note"
---

# After (auto-added cast-id)
---
cast-id: "generated-uuid-here"
cast-type: "note"
title: "My Note"
---
```

Disable auto-ID:
```bash
cast index --no-auto
```

### Rebuilding Index

Force complete index rebuild:

```bash
cast index --rebuild
```

Use when:
- Suspecting index corruption
- After major file reorganization
- Upgrading Cast version

### Resetting Vault State

Clear Cast metadata while keeping content:

```bash
# Interactive
cast reset

# Skip confirmation
cast reset --force

# Keep configuration
cast reset --keep-config
```

### Automation

#### Scheduled Sync (Linux/Mac)

Add to crontab:
```bash
# Sync every 4 hours
0 */4 * * * /usr/local/bin/cast sync --batch

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/cast sync backup --overpower --batch
```

#### Scheduled Sync (Windows)

Use Task Scheduler to run:
```batch
cast sync --batch
```

#### Git Integration

Combine with Git for version control:

```bash
#!/bin/bash
# sync-and-commit.sh

# Sync vaults
cast sync --batch

# Commit changes
cd ~/vaults/main
git add -A
git commit -m "Auto-sync $(date +%Y-%m-%d)"
git push
```

## Troubleshooting

### Common Issues

#### "No vaults configured"

**Problem**: No other vaults to sync with

**Solution**:
```bash
# Register another vault
cast register backup /path/to/backup
cd /path/to/backup
cast init
```

#### "Duplicate cast-id found"

**Problem**: Same ID in multiple files

**Solution**:
1. Find duplicates: Check the error message for file paths
2. Delete the cast-id from one file
3. Re-run `cast index` to generate new ID

#### "Permission denied"

**Problem**: Cannot read/write files

**Solution**:
```bash
# Check permissions
ls -la .cast/

# Fix permissions
chmod -R u+rw .cast/
```

#### "Index corrupted"

**Problem**: Invalid index file

**Solution**:
```bash
# Rebuild index
cast index --rebuild
```

#### Sync Not Finding Changes

**Problem**: Changes not detected

**Possible Causes**:
1. Files excluded by patterns
2. Only metadata changed
3. Index not updated

**Solution**:
```bash
# Force index rebuild
cast index --rebuild

# Check configuration
cat .cast/config.yaml
```

### Getting Help

1. **Check command help**: `cast <command> --help`
2. **Review configuration**: `cast config`
3. **Enable verbose mode**: `cast sync --verbose`
4. **Check logs**: Look for error messages
5. **Reset if needed**: `cast reset --force`

## Best Practices

### Organization

1. **Use Standard Structure**
   ```
   01 Vault/     # Synchronized content
   02 Journal/   # Daily notes (optional sync)
   03 Records/   # Large files (exclude)
   ```

2. **Consistent Naming**
   - Use descriptive file names
   - Avoid special characters
   - Keep paths reasonable length

3. **Metadata Standards**
   ```yaml
   ---
   cast-id: "uuid"
   cast-type: "note|project|reference"
   cast-vaults: ["main", "backup"]
   title: "Clear Title"
   tags: ["tag1", "tag2"]
   ---
   ```

### Workflow

1. **Morning Routine**
   ```bash
   cast sync                    # Get latest changes
   # Work on your content
   cast sync                    # Share your changes
   ```

2. **Before Major Work**
   ```bash
   cast sync                    # Ensure up-to-date
   cast index --rebuild         # Verify index
   ```

3. **After Major Changes**
   ```bash
   cast index                   # Update index
   cast sync                    # Propagate changes
   ```

### Safety

1. **Regular Backups**
   - Keep one vault as backup-only
   - Use `--overpower` carefully
   - Consider Git for version history

2. **Test First**
   - Try Cast on test vaults first
   - Understand conflict resolution
   - Practice recovery procedures

3. **Monitor Sync**
   - Check sync output regularly
   - Resolve conflicts promptly
   - Verify important changes propagated

### Performance

1. **Optimize Patterns**
   ```yaml
   index:
     include:
       - "01 Vault/**/*.md"  # Specific folders
     exclude:
       - "**/_archive/**"    # Old content
       - "**/node_modules/**" # Dependencies
       - "**/.git/**"        # Version control
   ```

2. **Manage Vault Size**
   - Archive old content
   - Exclude large media files
   - Split massive vaults

3. **Sync Strategy**
   - Sync frequently for small changes
   - Use batch mode for automation
   - Sync before and after work sessions

## FAQ

### General Questions

**Q: Is Cast free?**
A: Yes, Cast is open-source and free to use.

**Q: Does Cast need internet?**
A: No, Cast works entirely offline between local vaults.

**Q: Can I sync with cloud storage?**
A: Yes, if your cloud storage syncs to a local folder (Dropbox, OneDrive, etc.).

**Q: How many vaults can I sync?**
A: No limit, but sync time increases with more vaults.

### Setup Questions

**Q: Where is configuration stored?**
A: 
- Global: `~/.config/Cast/config.yaml` (Linux/Mac) or `%APPDATA%\Cast\config.yaml` (Windows)
- Vault: `.cast/config.yaml` in each vault

**Q: Can I change vault names?**
A: Yes, edit the global config file directly.

**Q: What if I move a vault?**
A: Update the path in global config using `cast config`.

### Sync Questions

**Q: What gets synchronized?**
A: Only files matching include patterns with valid cast-ids.

**Q: Can I exclude certain files?**
A: Yes, use exclude patterns in `.cast/config.yaml`.

**Q: How are conflicts detected?**
A: By comparing content digests with last sync state.

**Q: Can I undo a sync?**
A: No built-in undo, but you can use Git for version control.

### Technical Questions

**Q: What is a cast-id?**
A: A UUID v4 that uniquely identifies a file across all vaults.

**Q: Why use body-only digests?**
A: To ignore metadata changes that don't affect content.

**Q: Is Cast secure?**
A: Cast doesn't encrypt data but never sends it externally.

**Q: Can I customize Cast?**
A: Currently through configuration; plugin system planned.

### Troubleshooting Questions

**Q: Why aren't my files syncing?**
A: Check:
1. Files have cast-ids (`cast index`)
2. Files match include patterns
3. Other vault is initialized
4. No unresolved conflicts

**Q: How do I fix a corrupted index?**
A: Run `cast index --rebuild`

**Q: What if sync is interrupted?**
A: Just run `cast sync` again; it will resume.

**Q: How do I completely start over?**
A: Run `cast reset --force` then `cast init`

## Conclusion

Cast Sync provides powerful, reliable synchronization for your Markdown vaults while maintaining complete control over your data. By following this guide and best practices, you can maintain synchronized knowledge bases across multiple locations without depending on cloud services or sacrificing privacy.

For technical details, see the [Architecture Documentation](ARCHITECTURE.md) and [API Reference](API_REFERENCE.md).