"""Obsidian integration for Cast."""

import json
from pathlib import Path


def init_obsidian_config(vault_root: Path, profile: str = "default") -> None:
    """Initialize Obsidian configuration for a vault.
    
    Args:
        vault_root: Vault root directory
        profile: Configuration profile to use
    """
    obsidian_dir = vault_root / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    
    # App configuration
    app_config = {
        "attachmentFolderPath": "05 Media",
        "alwaysUpdateLinks": True,
        "newFileLocation": "folder",
        "newFileFolderPath": "01 Vault",
        "useMarkdownLinks": False,
        "strictLineBreaks": False,
        "showFrontmatter": True,
        "foldHeading": True,
        "foldIndent": True,
        "defaultViewMode": "preview",
        "showLineNumber": True,
        "spellcheck": True,
    }
    
    with open(obsidian_dir / "app.json", "w") as f:
        json.dump(app_config, f, indent=2)
    
    # Appearance configuration
    appearance_config = {
        "theme": "obsidian",
        "cssTheme": "",
        "translucency": False,
        "nativeMenus": False,
        "baseFontSize": 16,
        "enabledCssSnippets": [],
    }
    
    with open(obsidian_dir / "appearance.json", "w") as f:
        json.dump(appearance_config, f, indent=2)
    
    # Core plugins
    core_plugins = {
        "file-explorer": True,
        "global-search": True,
        "switcher": True,
        "graph": True,
        "backlink": True,
        "outgoing-link": True,
        "tag-pane": True,
        "properties": True,
        "page-preview": True,
        "templates": True,
        "note-composer": True,
        "command-palette": True,
        "slash-command": False,
        "editor-status": True,
        "bookmarks": True,
        "markdown-importer": False,
        "zk-prefixer": False,
        "random-note": False,
        "outline": True,
        "word-count": True,
        "slides": False,
        "audio-recorder": False,
        "workspaces": False,
        "file-recovery": True,
        "publish": False,
        "sync": False,
    }
    
    with open(obsidian_dir / "core-plugins.json", "w") as f:
        json.dump(core_plugins, f, indent=2)
    
    # Core plugin settings for core plugins
    core_plugin_config = {
        "file-explorer": {
            "showHiddenFiles": False,
        },
        "templates": {
            "folder": "06 Extras/0609 Templates",
        },
    }
    
    with open(obsidian_dir / "core-plugins-migration.json", "w") as f:
        json.dump(core_plugin_config, f, indent=2)
    
    # Community plugins (initially empty)
    community_plugins = []
    
    with open(obsidian_dir / "community-plugins.json", "w") as f:
        json.dump(community_plugins, f, indent=2)
    
    # Hotkeys (some useful defaults)
    if profile == "default":
        hotkeys = {
            "file-explorer:new-file": [
                {
                    "modifiers": ["Mod"],
                    "key": "n",
                }
            ],
            "switcher:open": [
                {
                    "modifiers": ["Mod"],
                    "key": "p",
                }
            ],
            "graph:open": [
                {
                    "modifiers": ["Mod", "Shift"],
                    "key": "g",
                }
            ],
            "command-palette:open": [
                {
                    "modifiers": ["Mod", "Shift"],
                    "key": "p",
                }
            ],
        }
        
        with open(obsidian_dir / "hotkeys.json", "w") as f:
            json.dump(hotkeys, f, indent=2)