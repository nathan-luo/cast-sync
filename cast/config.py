"""Configuration management for Cast."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import platformdirs
import yaml


@dataclass
class SyncRule:
    """Sync rule configuration."""
    
    id: str
    mode: str  # broadcast | bidirectional | mirror
    from_vault: str
    to_vaults: list[dict[str, str]]
    select: dict[str, Any]
    include_assets: bool = False


@dataclass
class VaultConfig:
    """Per-vault configuration (.cast/config.yaml)."""
    
    cast_version: str = "1"
    vault_id: str = ""
    vault_root: Path = field(default_factory=Path.cwd)
    
    # Index configuration
    include_patterns: list[str] = field(default_factory=lambda: ["01 Vault/**/*.md"])
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git/**", ".cast/**", ".obsidian/**",
        "00 Software/**", "03 Records/**", "04 Sources/**",
        "05 Media/**", "06 Extras/**", "09 Exports/**",
    ])
    
    # Sync rules
    sync_rules: list[SyncRule] = field(default_factory=list)
    
    # Merge settings
    ephemeral_keys: list[str] = field(default_factory=lambda: [
        "updated", "last_synced", "base-version"
    ])
    
    @property
    def config_path(self) -> Path:
        """Path to the vault config file."""
        return self.vault_root / ".cast" / "config.yaml"
    
    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "cast-version": self.cast_version,
            "vault": {
                "id": self.vault_id,
                "root": str(self.vault_root),
            },
            "index": {
                "include": self.include_patterns,
                "exclude": self.exclude_patterns,
            },
            "sync": {
                "rules": [
                    {
                        "id": rule.id,
                        "mode": rule.mode,
                        "from": rule.from_vault,
                        "to": rule.to_vaults,
                        "select": rule.select,
                        "include_assets": rule.include_assets,
                    }
                    for rule in self.sync_rules
                ],
            },
            "merge": {
                "ephemeral_keys": self.ephemeral_keys,
            },
        }
        
        with open(self.config_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    
    @classmethod
    def load(cls, vault_root: Path) -> "VaultConfig":
        """Load configuration from vault."""
        config_path = vault_root / ".cast" / "config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"No Cast configuration found at {config_path}")
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        config = cls(
            cast_version=data.get("cast-version", "1"),
            vault_id=data["vault"]["id"],
            vault_root=Path(data["vault"].get("root", vault_root)),
        )
        
        if "index" in data:
            config.include_patterns = data["index"].get("include", config.include_patterns)
            config.exclude_patterns = data["index"].get("exclude", config.exclude_patterns)
        
        if "merge" in data:
            config.ephemeral_keys = data["merge"].get("ephemeral_keys", config.ephemeral_keys)
        
        if "sync" in data and "rules" in data["sync"]:
            config.sync_rules = [
                SyncRule(
                    id=r["id"],
                    mode=r["mode"],
                    from_vault=r["from"],
                    to_vaults=r["to"],
                    select=r.get("select", {}),
                    include_assets=r.get("include_assets", False),
                )
                for r in data["sync"]["rules"]
            ]
        
        return config
    
    @classmethod
    def create_default(cls, vault_root: Path, vault_id: Optional[str] = None) -> "VaultConfig":
        """Create default configuration for a vault."""
        if vault_id is None:
            vault_id = vault_root.name
        
        return cls(
            vault_id=vault_id,
            vault_root=vault_root,
        )


@dataclass
class GlobalConfig:
    """Global Cast configuration (per machine)."""
    
    vaults: dict[str, str] = field(default_factory=dict)
    
    @property
    def config_path(self) -> Path:
        """Path to global config file."""
        config_dir = Path(platformdirs.user_config_dir("Cast", "Cast"))
        return config_dir / "config.yaml"
    
    def save(self) -> None:
        """Save global configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "vaults": self.vaults,
        }
        
        with open(self.config_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    
    @classmethod
    def load(cls) -> "GlobalConfig":
        """Load global configuration."""
        config = cls()
        
        if config.config_path.exists():
            with open(config.config_path) as f:
                data = yaml.safe_load(f) or {}
                config.vaults = data.get("vaults", {})
        
        return config
    
    @classmethod
    def load_or_create(cls) -> "GlobalConfig":
        """Load or create default global configuration."""
        config = cls.load()
        
        if not config.config_path.exists():
            config.save()
        
        return config
    
    @classmethod
    def create_default(cls) -> "GlobalConfig":
        """Create default global configuration."""
        return cls()
    
    def register_vault(self, name: str, path: str) -> None:
        """Register a vault in global config."""
        self.vaults[name] = path
    
    def get_vault_path(self, name: str) -> Optional[Path]:
        """Get vault path by name."""
        if name in self.vaults:
            return Path(self.vaults[name])
        
        # Check if it's already a path
        path = Path(name)
        if path.exists():
            return path
        
        return None


class CastConfig:
    """Combined configuration manager."""
    
    def __init__(self, vault_root: Path):
        """Initialize configuration manager."""
        self.vault_root = vault_root
        self.vault_config = VaultConfig.load(vault_root)
        self.global_config = GlobalConfig.load()
    
    def get_peer_vault_path(self, peer_id: str) -> Optional[Path]:
        """Get path to a peer vault."""
        return self.global_config.get_vault_path(peer_id)