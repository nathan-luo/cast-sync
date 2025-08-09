"""Utility functions for Cast."""

import logging
import sys
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging for the application."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def safe_path_join(base: Path, relative: str) -> Path | None:
    """Safely join paths, preventing directory traversal.
    
    Args:
        base: Base directory
        relative: Relative path to join
        
    Returns:
        Joined path if safe, None if traversal detected
    """
    # Resolve the base path
    base = base.resolve()
    
    # Join and resolve
    joined = (base / relative).resolve()
    
    # Check if still under base
    try:
        joined.relative_to(base)
        return joined
    except ValueError:
        # Path escapes base directory
        return None


def format_size(bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"


def is_markdown_file(path: Path) -> bool:
    """Check if a file is a markdown file."""
    return path.suffix.lower() in [".md", ".markdown", ".mkd", ".mdown"]


def is_binary_file(path: Path) -> bool:
    """Check if a file appears to be binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
            
        # Check for null bytes
        if b"\x00" in chunk:
            return True
        
        # Try to decode as UTF-8
        try:
            chunk.decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True
            
    except Exception:
        # If we can't read it, assume binary
        return True


def atomic_write(path: Path, content: str | bytes, mode: str = "w") -> None:
    """Write file atomically using temp file and rename.
    
    Args:
        path: Target file path
        content: Content to write
        mode: File open mode ('w' for text, 'wb' for binary)
    """
    temp_path = path.with_suffix(".tmp")
    
    try:
        if mode == "wb":
            temp_path.write_bytes(content)
        else:
            temp_path.write_text(content, encoding="utf-8")
        
        # Atomic rename
        temp_path.replace(path)
        
    except Exception:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise