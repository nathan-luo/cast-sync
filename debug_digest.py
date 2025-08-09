#!/usr/bin/env python3
"""Debug digest computation."""

from pathlib import Path
from cast.ids import extract_frontmatter
from cast.normalize import compute_normalized_digest

# Read both files
vault1_file = Path("vaults/vault1/01 Vault/test_create.md")
vault2_file = Path("vaults/vault2/01 Vault/test_create.md")

if vault1_file.exists():
    vault1_content = vault1_file.read_text()
    _, _, vault1_body = extract_frontmatter(vault1_content)
    vault1_digest = compute_normalized_digest(vault1_body, body_only=True)
    print(f"Vault1 body digest: {vault1_digest}")
    print(f"Vault1 body preview: {vault1_body[:100]}...")
    print()

if vault2_file.exists():
    vault2_content = vault2_file.read_text()
    _, _, vault2_body = extract_frontmatter(vault2_content)
    vault2_digest = compute_normalized_digest(vault2_body, body_only=True)
    print(f"Vault2 body digest: {vault2_digest}")
    print(f"Vault2 body preview: {vault2_body[:100]}...")
    print()
    
    # Are bodies identical?
    if vault1_file.exists():
        if vault1_body == vault2_body:
            print("Bodies are IDENTICAL (string comparison)")
        else:
            print("Bodies are DIFFERENT")
            # Find first difference
            for i, (c1, c2) in enumerate(zip(vault1_body, vault2_body)):
                if c1 != c2:
                    print(f"First difference at position {i}:")
                    print(f"  Vault1: {repr(vault1_body[max(0,i-10):i+20])}")
                    print(f"  Vault2: {repr(vault2_body[max(0,i-10):i+20])}")
                    break