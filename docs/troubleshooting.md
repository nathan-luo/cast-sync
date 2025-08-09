# Cast Sync Troubleshooting Guide

## Common Issues and Solutions

### 1. "Not a Cast vault" Error

**Problem:**
```
Error: Not a Cast vault. Run 'cast init' first.
```

**Cause:** The vault hasn't been initialized with Cast metadata.

**Solution:**
```bash
cd /path/to/vault
cast init
```

**Prevention:** Always run `cast init` before attempting to sync a new vault.

---

### 2. "'dict' object has no attribute 'replace'" Error

**Problem:**
```
AttributeError: 'dict' object has no attribute 'replace'
```

**Cause:** Internal type mismatch, usually when processing frontmatter.

**Solutions:**

1. Update Cast Sync to latest version:
   ```bash
   pip install --upgrade cast-sync
   ```

2. Re-index the vault:
   ```bash
   cast index --force
   ```

3. Check for malformed YAML frontmatter:
   ```bash
   cast validate-frontmatter
   ```

**Debug:** Enable debug logging:
```bash
export CAST_LOG_LEVEL=DEBUG
cast sync vault1 vault2
```

---

### 3. Files Not Being Synced

**Problem:** Some files aren't included in sync operations.

**Causes:**
1. Files excluded by patterns
2. Files lack cast-id
3. Index out of date

**Solutions:**

1. Check exclusion patterns:
   ```bash
   cast debug-patterns "path/to/missing/file.md"
   ```

2. Force re-index:
   ```bash
   cast index --force
   ```

3. Review config:
   ```yaml
   # .cast/config.yaml
   index:
     include:
       - "**/*.md"  # Make sure pattern matches
     exclude:
       - "private/**"  # Check if file is excluded
   ```

4. Verify file has cast-id:
   ```bash
   head -n 10 "path/to/file.md"
   # Should show cast-id in frontmatter
   ```

---

### 4. Merge Conflicts on Every Sync

**Problem:** Files show conflicts even when changes don't overlap.

**Causes:**
1. Clock skew between systems
2. Line ending differences (CRLF vs LF)
3. Ephemeral fields being compared

**Solutions:**

1. Configure ephemeral fields:
   ```yaml
   # .cast/config.yaml
   merge:
     ephemeral_keys:
       - modified
       - updated
       - last_edited
   ```

2. Normalize line endings:
   ```bash
   # Convert to LF (Unix)
   dos2unix vault/**/*.md
   ```

3. Sync system clocks:
   ```bash
   # Linux/Mac
   sudo ntpdate -s time.nist.gov
   
   # Or use systemd
   sudo timedatectl set-ntp true
   ```

---

### 5. "Permission Denied" Errors

**Problem:**
```
PermissionError: [Errno 13] Permission denied: '.cast/index.json'
```

**Causes:**
1. Incorrect file permissions
2. Files owned by different user
3. Vault on read-only filesystem

**Solutions:**

1. Fix permissions:
   ```bash
   # Make files readable/writable by user
   chmod -R u+rw .cast/
   chmod -R u+rw *.md
   ```

2. Fix ownership:
   ```bash
   # Change to current user
   sudo chown -R $(whoami) .cast/
   ```

3. Check filesystem:
   ```bash
   # Check if mounted read-only
   mount | grep "vault\|path"
   ```

---

### 6. Sync Appears Stuck/Frozen

**Problem:** Sync command hangs without progress.

**Causes:**
1. Stale lock file
2. Large file processing
3. Network issues (future)

**Solutions:**

1. Remove stale lock:
   ```bash
   rm .cast/.lock
   ```

2. Check for large files:
   ```bash
   find . -type f -size +10M -name "*.md"
   ```

3. Run with timeout:
   ```bash
   timeout 60 cast sync vault1 vault2
   ```

4. Enable verbose mode:
   ```bash
   cast sync vault1 vault2 --verbose
   ```

---

### 7. "Index out of date" Warning

**Problem:**
```
Warning: Index may be out of date. Run 'cast index' to update.
```

**Cause:** Files changed since last index.

**Solution:**
```bash
cast index
```

**Automation:** Add to your workflow:
```bash
# Before sync
cast index && cast sync source dest --apply
```

---

### 8. Duplicate Cast IDs

**Problem:**
```
Error: Duplicate cast-id found: 550e8400-e29b-41d4-a716-446655440000
```

**Cause:** Same cast-id in multiple files (usually from incorrect copying).

**Solutions:**

1. Find duplicates:
   ```bash
   grep -r "cast-id: 550e8400" --include="*.md"
   ```

2. Regenerate ID for duplicate:
   ```bash
   cast regenerate-id "path/to/duplicate.md"
   ```

3. Re-index:
   ```bash
   cast index --force
   ```

---

### 9. Conflict Files Accumulating

**Problem:** Many `.conflicted-*` files building up.

**Cause:** Unresolved conflicts from previous syncs.

**Solutions:**

1. List conflicts:
   ```bash
   cast conflicts
   ```

2. Resolve interactively:
   ```bash
   cast resolve
   ```

3. Bulk resolve (choose strategy):
   ```bash
   cast resolve --all --strategy=ours  # Keep local
   cast resolve --all --strategy=theirs  # Keep remote
   ```

4. Clean old conflicts:
   ```bash
   # Remove conflicts older than 30 days
   find . -name "*.conflicted-*" -mtime +30 -delete
   ```

---

### 10. Corrupted Index

**Problem:**
```
Error: Failed to parse index: JSONDecodeError
```

**Cause:** Index file corrupted or partially written.

**Solutions:**

1. Rebuild index:
   ```bash
   rm .cast/index.json
   cast index --force
   ```

2. Restore from backup:
   ```bash
   cp .cast/index.json.backup .cast/index.json
   ```

3. Validate and repair:
   ```bash
   cast repair-index
   ```

---

## Diagnostic Commands

### Check Vault Status

```bash
cast status
```

Output:
```
Vault: my-vault
Path: /home/user/my-vault
Files: 234 indexed
Last sync: 2024-01-01 12:00:00
Conflicts: 2 unresolved
```

### Debug Specific File

```bash
cast debug-file "notes/example.md"
```

Output:
```
File: notes/example.md
Cast ID: 550e8400-e29b-41d4-a716-446655440000
Digest: sha256:abc123...
Size: 1234 bytes
In index: Yes
Sync mode: bidirectional
Last synced: 2024-01-01 12:00:00
```

### Test Sync Without Applying

```bash
cast sync vault1 vault2 --dry-run --verbose
```

### Verify Installation

```bash
cast --version
cast doctor
```

Output:
```
Cast Sync v1.0.0
✓ Python 3.11.0
✓ Dependencies installed
✓ Config valid
✓ Permissions OK
```

---

## Error Messages Explained

### "No common cast-id between vaults"

**Meaning:** The vaults have no files in common.

**Action:** This is normal for first sync. Files will be copied.

### "Baseline object not found"

**Meaning:** The common ancestor for 3-way merge is missing.

**Action:** Treated as new merge. May create conflict if both changed.

### "Cast-id mismatch in frontmatter"

**Meaning:** File's cast-id doesn't match index.

**Action:** Re-index to update: `cast index --force`

### "Lock acquisition timeout"

**Meaning:** Couldn't get exclusive access to vault.

**Action:** Check for other Cast processes or stale locks.

---

## Performance Issues

### Slow Indexing

**Symptoms:** `cast index` takes long time.

**Solutions:**

1. Exclude large directories:
   ```yaml
   index:
     exclude:
       - "archive/**"
       - "attachments/**"
   ```

2. Enable caching:
   ```yaml
   performance:
     cache_digests: true
   ```

3. Increase workers:
   ```yaml
   performance:
     workers: 8
   ```

### High Memory Usage

**Symptoms:** Cast uses excessive RAM.

**Solutions:**

1. Limit memory:
   ```yaml
   performance:
     memory_limit: 256  # MB
   ```

2. Process files in chunks:
   ```yaml
   performance:
     chunk_size: 524288  # 512KB
   ```

### Slow Network Sync (Future)

**Solutions:**

1. Enable compression:
   ```yaml
   network:
     compression: true
   ```

2. Increase timeout:
   ```yaml
   network:
     timeout: 60
   ```

---

## Platform-Specific Issues

### Windows

#### Path Too Long

**Problem:** Windows path limit (260 characters) exceeded.

**Solution:**

1. Enable long paths:
   ```powershell
   # Run as Administrator
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```

2. Use shorter vault paths:
   ```bash
   cast init --vault-id vault1
   ```

#### Line Ending Issues

**Problem:** CRLF vs LF conflicts.

**Solution:**

Configure Git:
```bash
git config core.autocrlf false
```

Configure Cast:
```yaml
advanced:
  line_endings: lf  # Force LF
```

### macOS

#### .DS_Store Files

**Problem:** macOS metadata files causing noise.

**Solution:**

Add to excludes:
```yaml
index:
  exclude:
    - "**/.DS_Store"
    - "**/.localized"
```

#### Permissions on External Drives

**Problem:** Can't write to external drives.

**Solution:**

1. Check mount options:
   ```bash
   mount | grep "diskname"
   ```

2. Remount with write permissions:
   ```bash
   sudo diskutil mount readWrite /dev/diskname
   ```

### Linux

#### Filesystem Watching Limits

**Problem:** Too many files for inotify.

**Solution:**

Increase limits:
```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Recovery Procedures

### Recover from Corrupted Vault

```bash
# 1. Backup current state
cp -r vault vault.backup

# 2. Reset Cast metadata
rm -rf vault/.cast

# 3. Reinitialize
cast init

# 4. Restore from object store
cast restore-from-objects

# 5. Re-index
cast index --force
```

### Undo Last Sync

```bash
# If backup enabled
cast restore --timestamp="2024-01-01T12:00:00"

# From snapshot
cast restore --snapshot=".cast/snapshots/20240101.zip"

# From Git
git revert HEAD
```

### Reset Sync State

```bash
# Clear peer states
rm -rf .cast/peers/*

# Reset specific peer
rm .cast/peers/other-vault.json

# Re-sync from scratch
cast sync --reset vault1 vault2
```

---

## Debug Logging

### Enable Debug Output

```bash
# Environment variable
export CAST_LOG_LEVEL=DEBUG

# Or in config
logging:
  level: DEBUG
  file: .cast/debug.log
```

### Analyze Logs

```bash
# View recent errors
grep ERROR .cast/cast.log | tail -20

# Find sync operations
grep "SYNC:" .cast/cast.log

# Track specific file
grep "cast-id-here" .cast/cast.log
```

---

## Getting Help

### Built-in Help

```bash
cast --help
cast sync --help
cast debug --help
```

### Version Information

```bash
cast --version
pip show cast-sync
```

### Submit Bug Report

Include:
1. Cast version: `cast --version`
2. Python version: `python --version`
3. Platform: `uname -a` or Windows version
4. Config file: `.cast/config.yaml`
5. Error messages and stack traces
6. Steps to reproduce

### Community Support

- GitHub Issues: Report bugs and request features
- Documentation: Check docs/ directory
- Examples: See test files for usage patterns

---

## Preventive Measures

### Regular Maintenance

```bash
# Weekly tasks
cast index
cast clean-conflicts --older-than 30

# Monthly tasks
cast verify-integrity
cast optimize-objects
```

### Monitoring Script

```bash
#!/bin/bash
# monitor-cast.sh

# Check for conflicts
if cast conflicts | grep -q "conflict"; then
    echo "Warning: Unresolved conflicts found"
fi

# Check index age
if find .cast/index.json -mtime +7 | grep -q index; then
    echo "Warning: Index older than 7 days"
fi

# Check lock files
if find .cast -name "*.lock" -mmin +60 | grep -q lock; then
    echo "Warning: Stale lock files found"
fi
```

### Pre-sync Checklist

1. ✓ System clocks synchronized
2. ✓ Sufficient disk space
3. ✓ Recent backup available
4. ✓ No pending conflicts
5. ✓ Index up to date
6. ✓ Test with dry-run first

---

## Advanced Debugging

### Trace Execution

```bash
# Python trace
python -m trace -t $(which cast) sync vault1 vault2

# System calls
strace cast sync vault1 vault2 2> trace.log
```

### Profile Performance

```bash
# Python profiling
python -m cProfile -o profile.stats $(which cast) index

# Analyze profile
python -m pstats profile.stats
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory_profiler

# Run with profiling
mprof run cast sync vault1 vault2
mprof plot
```