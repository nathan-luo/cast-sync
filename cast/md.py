"""Centralized markdown and frontmatter parsing utilities."""

import re
import yaml
from typing import Any, Tuple, Dict, Optional


_FM_OPEN = "---\n"
_FM_CLOSE_RE = re.compile(r"\n---\n")


def split_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """Split markdown content into frontmatter dict, raw frontmatter text, and body.
    
    Args:
        content: The full markdown content
        
    Returns:
        Tuple of (frontmatter_dict, frontmatter_text, body)
        - frontmatter_dict: Parsed YAML as dict, or None if invalid/missing
        - frontmatter_text: Raw YAML text (without delimiters)  
        - body: Content after frontmatter
    """
    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    # Check for frontmatter
    if not content.startswith(_FM_OPEN):
        return None, "", content
    
    # Find closing delimiter
    m = _FM_CLOSE_RE.search(content, len(_FM_OPEN))
    if not m:
        return None, "", content
    
    # Extract frontmatter text (without delimiters)
    fm_text = content[len(_FM_OPEN):m.start()]
    body = content[m.end():]
    
    # Parse YAML
    try:
        fm = yaml.safe_load(fm_text) or {}
        if not isinstance(fm, dict):
            fm = None
    except yaml.YAMLError:
        fm = None
    
    return fm, fm_text, body


def ensure_cast_id_first(fm: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure cast-id appears first in frontmatter dict.
    
    Args:
        fm: Frontmatter dictionary
        
    Returns:
        New dict with cast-id first if present, then other keys
    """
    if "cast-id" in fm:
        result = {"cast-id": fm["cast-id"]}
        for k, v in fm.items():
            if k != "cast-id":
                result[k] = v
        return result
    return fm.copy()


def serialize_frontmatter(fm: Dict[str, Any], body: str) -> str:
    """Serialize frontmatter dict and body back to markdown.
    
    Args:
        fm: Frontmatter dictionary (will put cast-id first if present)
        body: Markdown body content
        
    Returns:
        Complete markdown content with frontmatter
    """
    if not fm:
        return body
    
    # Ensure cast-id is first
    fm = ensure_cast_id_first(fm)
    
    # Serialize YAML
    yaml_str = yaml.dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    
    # Combine with body
    return f"---\n{yaml_str}---\n{body}"


def compute_body_digest(content: str) -> str:
    """Compute digest of markdown body only (ignoring frontmatter).
    
    Args:
        content: Full markdown content
        
    Returns:
        SHA256 hex digest of the body content
    """
    import hashlib
    _, _, body = split_frontmatter(content)
    return f"sha256:{hashlib.sha256(body.encode()).hexdigest()}"