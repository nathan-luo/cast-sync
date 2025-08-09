#!/usr/bin/env python3
"""Test automatic cast-id generation and ordering."""

import shutil
from pathlib import Path

from cast.config import VaultConfig
from cast.index import build_index
from cast.ids import get_cast_id


def test_auto_id_generation():
    """Test that files with cast-vaults automatically get cast-id."""
    print("=== Testing Auto ID Generation ===\n")
    
    # Clean up test vault
    test_vault = Path("test_vault")
    if test_vault.exists():
        shutil.rmtree(test_vault)
    
    # Create test vault structure
    test_vault.mkdir()
    (test_vault / ".cast").mkdir()
    (test_vault / "01 Vault").mkdir(parents=True)
    
    # Create vault config
    config = VaultConfig.create_default(test_vault, "test_vault")
    config.save()
    
    # Create a file with cast-vaults but no cast-id
    test_file = test_vault / "01 Vault" / "test_doc.md"
    content = """---
cast-vaults:
  - vault1 (cast)
  - vault2 (sync)
tags: [test, auto-id]
category: testing
---

# Test Document

This document should get an auto-generated cast-id."""
    
    test_file.write_text(content)
    print(f"Created test file: {test_file}")
    
    # Index the vault (should auto-add cast-id)
    print("\nIndexing vault...")
    index_data = build_index(test_vault)
    
    # Check if file got indexed and has cast-id
    if index_data:
        cast_id = list(index_data.keys())[0]
        print(f"✓ File indexed with cast-id: {cast_id}")
        
        # Read the file to verify cast-id was added
        updated_content = test_file.read_text()
        
        # Check cast-id is present
        if f"cast-id: {cast_id}" in updated_content:
            print("✓ cast-id was added to the file")
        else:
            print("✗ cast-id not found in file")
            return False
        
        # Check cast-id is first in YAML
        lines = updated_content.split('\n')
        yaml_started = False
        first_yaml_field = None
        
        for line in lines:
            if line == "---":
                if not yaml_started:
                    yaml_started = True
                else:
                    break  # End of YAML
            elif yaml_started and line.strip() and ':' in line:
                first_yaml_field = line.split(':')[0].strip()
                break
        
        if first_yaml_field == "cast-id":
            print("✓ cast-id is the first YAML field")
        else:
            print(f"✗ First YAML field is '{first_yaml_field}', not 'cast-id'")
            return False
        
        # Display the updated file content
        print("\nUpdated file content:")
        print("-" * 40)
        print(updated_content[:300] + "..." if len(updated_content) > 300 else updated_content)
        print("-" * 40)
        
    else:
        print("✗ File was not indexed")
        return False
    
    # Test 2: File with existing cast-id should not be modified
    print("\n=== Testing Existing ID Preservation ===\n")
    
    test_file2 = test_vault / "01 Vault" / "existing_id.md"
    existing_id = "12345678-1234-1234-1234-123456789abc"
    content2 = f"""---
category: existing
cast-id: {existing_id}
cast-vaults:
  - vault1 (cast)
tags: [existing]
---

# Existing ID Document

This document already has a cast-id."""
    
    test_file2.write_text(content2)
    print(f"Created file with existing cast-id: {existing_id}")
    
    # Re-index
    build_index(test_vault, rebuild=True)
    
    # Check that cast-id wasn't changed
    updated_content2 = test_file2.read_text()
    if f"cast-id: {existing_id}" in updated_content2:
        print("✓ Existing cast-id was preserved")
    else:
        print("✗ Existing cast-id was changed")
        return False
    
    # Check ordering was fixed
    lines = updated_content2.split('\n')
    yaml_started = False
    first_yaml_field = None
    
    for line in lines:
        if line == "---":
            if not yaml_started:
                yaml_started = True
            else:
                break
        elif yaml_started and line.strip() and ':' in line:
            first_yaml_field = line.split(':')[0].strip()
            break
    
    if first_yaml_field == "cast-id":
        print("✓ cast-id was moved to first position")
        print("\nReordered file content:")
        print("-" * 40)
        print(updated_content2[:300] + "..." if len(updated_content2) > 300 else updated_content2)
        print("-" * 40)
    else:
        print(f"✗ cast-id is not first (first field: '{first_yaml_field}')")
    
    print("\n=== All Tests Passed ✓ ===")
    return True


if __name__ == "__main__":
    test_auto_id_generation()