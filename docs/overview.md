# Cast Sync Overview

## What is Cast Sync?

Cast Sync is a distributed synchronization system designed for markdown-based knowledge management systems, particularly Obsidian vaults. Unlike traditional file sync tools, Cast Sync understands the structure and semantics of markdown files with YAML frontmatter, enabling intelligent conflict resolution and content-aware synchronization.

## Core Concepts

### Vaults

A **vault** is a directory containing markdown files and associated metadata. Each vault maintains:
- A collection of markdown files with optional YAML frontmatter
- A `.cast/` directory containing sync metadata and configuration
- An index of all tracked files with their content digests
- Peer state information tracking sync history with other vaults

### Cast IDs

Every synchronized file is assigned a unique **cast-id** (UUID v4) that persists across vaults. This ID:
- Enables tracking the same logical file across different vaults
- Survives file renames and moves
- Is stored in the YAML frontmatter of each file
- Serves as the primary key for synchronization

### Sync Modes

Cast Sync supports two primary synchronization modes:

#### 1. Broadcast Mode (Unidirectional)
- Source vault marked as `(cast)` pushes changes to `(sync)` vaults
- Changes flow in one direction only
- Ideal for publishing or distribution scenarios
- Example: Main vault → Published vault

#### 2. Bidirectional Mode
- Both vaults marked as `(sync)` exchange changes
- Full two-way synchronization with conflict detection
- Ideal for collaborative editing
- Example: Desktop vault ↔ Mobile vault

### Content Digests

Cast Sync uses SHA-256 digests to track content changes:
- **Body digest**: Hash of markdown body only (excluding frontmatter)
- **Full digest**: Hash of entire file content
- Enables efficient change detection
- Supports incremental synchronization

## How It Works

### 1. Initialization
```bash
cast init
```
- Creates `.cast/` directory structure
- Generates vault configuration
- Sets up object store for content versioning

### 2. Indexing
```bash
cast index
```
- Scans vault for markdown files
- Extracts/generates cast-ids
- Computes content digests
- Updates `.cast/index.json`

### 3. Synchronization
```bash
cast sync vault1 vault2 --apply
```
- Compares indices between vaults
- Generates sync plan with actions (CREATE, UPDATE, DELETE, MERGE)
- Applies changes preserving local metadata
- Updates peer state for future syncs

### 4. Conflict Resolution
```bash
cast conflicts  # List conflicts
cast resolve    # Interactive resolution
```
- Detects true conflicts vs simple appends
- Creates `.conflicted-*` files when needed
- Provides interactive resolution tools
- Preserves both versions until resolved

## Architecture Highlights

### Distributed Design
- No central server required
- Each vault is self-contained
- Peer-to-peer synchronization
- Works offline with eventual consistency

### Content-Aware Sync
- Understands YAML frontmatter structure
- Preserves local-only fields
- Syncs cast-* fields globally
- Smart conflict detection

### Incremental Updates
- Tracks baseline content between syncs
- Only transfers changed files
- Maintains sync history per peer
- Efficient for large vaults

### Safety Features
- Never overwrites without user consent
- Creates conflict files instead of data loss
- Atomic file operations
- Comprehensive state tracking

## Use Cases

### Personal Knowledge Management
- Sync Obsidian vaults across devices
- Maintain separate work/personal vaults with selective sync
- Version control for markdown notes

### Team Collaboration
- Share knowledge bases between team members
- Distributed documentation management
- Collaborative note-taking with conflict resolution

### Content Publishing
- Broadcast from private to public vaults
- Selective publishing with inclusion/exclusion rules
- Maintain draft and published versions

### Backup and Archival
- Incremental vault backups
- Multi-location redundancy
- Historical version tracking

## Comparison with Other Tools

### vs Git
- **Advantages**: Automatic conflict resolution, no commit history needed, understands markdown structure
- **Disadvantages**: Less granular version control, no branching

### vs Dropbox/Cloud Sync
- **Advantages**: Content-aware sync, intelligent conflict handling, works offline
- **Disadvantages**: Requires manual sync commands, no real-time sync

### vs Obsidian Sync
- **Advantages**: Free, self-hosted, more control over sync behavior
- **Disadvantages**: Command-line only, requires technical knowledge

## Next Steps

- [User Guide](./user-guide.md) - Learn how to use Cast Sync
- [Configuration](./configuration.md) - Customize sync behavior
- [Architecture](./architecture.md) - Deep dive into system design