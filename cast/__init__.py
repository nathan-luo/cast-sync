"""Cast - Simple & reliable sync for Markdown vaults."""

__version__ = "1.0.0"

from cast.config import GlobalConfig, VaultConfig
from cast.index import Index, build_index
from cast.sync_simple import SimpleSyncEngine

__all__ = [
    "GlobalConfig",
    "VaultConfig", 
    "Index",
    "build_index",
    "SimpleSyncEngine",
]