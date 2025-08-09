"""Vault creation and management for Cast."""

from pathlib import Path


def create_vault_structure(root: Path, template: str = "default") -> None:
    """Create recommended vault folder structure.
    
    Args:
        root: Root directory for the vault
        template: Template to use (default, minimal, etc.)
    """
    # Create base directories with actual structure
    directories = [
        ".cast",
        ".cast/objects",
        ".cast/peers",
        ".cast/logs",
        ".cast/locks",
        "00 Software",
        "01 Vault",
        "02 Journal",
        "03 Records",
        "03 Records/0301 Audio",
        "03 Records/0302 Chats",
        "03 Records/0303 Videos",
        "04 Sources",
        "04 Sources/0401 Papers",
        "04 Sources/0402 Clippings",
        "04 Sources/0403 Books",
        "05 Media",
        "05 Media/0501 Landing",
        "05 Media/0502 Public",
        "05 Media/0503 Images",
        "05 Media/0504 Excalidraw",
        "05 Media/0509 Everything",
        "06 Extras",
        "06 Extras/0609 Templates",
        "09 Exports",
    ]
    
    for dir_path in directories:
        (root / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create folder label files (empty hub pages without content)
    # These are just placeholders - no YAML needed since they don't sync
    folder_labels = [
        "01 Vault/01 Vault.md",
        "02 Journal/02 Journal.md",
        "03 Records/03 Records.md",
        "04 Sources/04 Sources.md",
        "05 Media/05 Media.md",
    ]
    
    for file_path in folder_labels:
        full_path = root / file_path
        # Just create empty files - they're folder labels only
        if not full_path.exists():
            full_path.touch()
    
    # Create .gitignore
    gitignore_content = """# Cast
.cast/locks/
.cast/logs/
*.tmp
*.conflicted-*
*.backup

# Obsidian
.obsidian/workspace*
.obsidian/cache
.obsidian/hotkeys.json

# System
.DS_Store
Thumbs.db
"""
    
    (root / ".gitignore").write_text(gitignore_content)