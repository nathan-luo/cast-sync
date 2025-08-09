# Cast Fields Documentation

## Overview

Cast uses specific YAML frontmatter fields to manage document synchronization across vaults. These fields are divided into two categories:

1. **Cast fields** (prefixed with `cast-`) - Synchronized across all vaults
2. **Local fields** - Remain unique to each vault

## Cast Fields (Synchronized)

### `cast-id`
- **Type**: UUID string
- **Required**: Yes
- **Example**: `f47ac10b-58cc-4372-a567-0e02b2c3d479`
- **Purpose**: Unique identifier that persists across renames and moves

### `cast-vaults`
- **Type**: List of vault entries
- **Required**: Yes (for files to be synced)
- **Format**: `"vault-name (role)"`
- **Roles**:
  - `(cast)` - Original/authoritative vault
  - `(sync)` - Synchronized copy
- **Example**:
  ```yaml
  cast-vaults:
    - nathansvault (cast)
    - backup (sync)
    - shared (sync)
  ```

### `cast-type`
- **Type**: String enum
- **Required**: No (defaults based on cast-vaults)
- **Values**:
  - `original` - Original document (typically when only cast destinations exist)
  - `sync` - Document intended for synchronization
  - `casted` - Processed/transformed version of a document
- **Example**: `cast-type: original`

### `cast-version`
- **Type**: String
- **Required**: No (defaults to "1")
- **Purpose**: Indicates Cast protocol version compatibility
- **Example**: `cast-version: 1`

### `cast-codebases` (Future)
- **Type**: List of codebase references
- **Required**: No
- **Purpose**: Link documents to related codebases
- **Example**:
  ```yaml
  cast-codebases:
    - repo: myproject
      path: /docs
  ```

## Local Fields (Not Synchronized)

Any field not prefixed with `cast-` remains local to each vault:

- `tags` - Local categorization
- `category` - Local organization
- `status` - Local workflow state
- `priority` - Local importance
- Custom fields specific to each vault

## Example Document

```yaml
---
# Cast fields (synced across vaults)
cast-id: f47ac10b-58cc-4372-a567-0e02b2c3d479
cast-type: original
cast-version: 1
cast-vaults:
  - nathansvault (cast)
  - backup (sync)
  - teamvault (sync)

# Local fields (stay in this vault only)
tags: [personal, draft, important]
category: research
status: in-progress
custom_field: local-value
---

# Document Content

This body content is synchronized across all vaults listed in cast-vaults.
```

## Sync Behavior

When Cast synchronizes a document:

1. **All `cast-*` fields** are copied from source to destination
2. **Body content** (everything after the YAML) is synchronized
3. **Local fields** in the destination vault are preserved unchanged

This allows each vault to maintain its own organizational system while keeping content synchronized.

## Title Handling

Document titles are derived from the **filename**, not from YAML. This ensures consistency across vaults and prevents title mismatches. The filename (without extension) becomes the document's title.

## File Selection

Cast only processes files that have a non-empty `cast-vaults` field. Files without this field are completely ignored by the sync system.

## Vault Roles in Detail

### `(cast)` Role
- Indicates the original/authoritative location
- Typically the vault where content is primarily edited
- In broadcast mode, changes flow FROM cast TO sync vaults

### `(sync)` Role  
- Indicates a synchronized copy
- Receives updates from cast vaults
- Can propagate changes in bidirectional mode

## Future Extensions

The Cast protocol is designed to be extensible. Future versions may add:

- `cast-dependencies` - Document dependency tracking
- `cast-status` - Sync-aware document status
- `cast-permissions` - Access control hints
- `cast-transforms` - Processing instructions

All future Cast fields will follow the `cast-*` naming convention to ensure they're synchronized.