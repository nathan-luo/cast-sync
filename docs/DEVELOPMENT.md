# Cast Sync - Development Guide

## Table of Contents
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contributing](#contributing)
- [Architecture Decisions](#architecture-decisions)
- [Adding Features](#adding-features)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- pip or uv package manager
- Virtual environment tool (venv, virtualenv, or uv)
- Text editor or IDE (VS Code, PyCharm recommended)

### Clone Repository

```bash
git clone https://github.com/yourusername/cast-sync
cd cast-sync
```

### Setup Development Environment

#### Using venv (Standard)
```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt
```

#### Using uv (Fast)
```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# Install dependencies
uv pip install -e .
uv pip install -r requirements-dev.txt
```

### IDE Configuration

#### VS Code

`.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [88]
}
```

#### PyCharm

1. Set Project Interpreter to virtual environment
2. Enable pytest as test runner
3. Configure Black as formatter
4. Set line length to 88 characters

## Project Structure

```
cast-sync/
├── cast/                   # Main package
│   ├── __init__.py        # Package initialization
│   ├── __main__.py        # Entry point
│   ├── cli.py             # CLI commands
│   ├── config.py          # Configuration management
│   ├── ids.py             # UUID management
│   ├── index.py           # Indexing system
│   ├── md.py              # Markdown processing
│   ├── obsidian.py        # Obsidian integration
│   ├── sync_simple.py     # Sync engine
│   ├── util.py            # Utilities
│   └── vault.py           # Vault management
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_ids.py        # ID management tests
│   ├── test_index.py      # Indexing tests
│   ├── test_sync.py       # Sync engine tests
│   ├── test_config.py     # Configuration tests
│   ├── test_md.py         # Markdown tests
│   └── fixtures/          # Test data
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md    # System architecture
│   ├── FEATURES.md        # Feature documentation
│   ├── API_REFERENCE.md   # API documentation
│   ├── USER_GUIDE.md      # User guide
│   └── DEVELOPMENT.md     # This file
├── pyproject.toml         # Project configuration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── README.md             # Project README
├── LICENSE               # License file
├── .gitignore           # Git ignore rules
└── .github/             # GitHub configuration
    └── workflows/       # CI/CD workflows
```

### Module Responsibilities

#### `cli.py` - Command Line Interface
- Command definitions
- Argument parsing
- User interaction
- Output formatting

#### `config.py` - Configuration Management
- Global configuration
- Vault configuration
- Settings validation
- Path resolution

#### `ids.py` - ID Management
- UUID generation
- ID validation
- Frontmatter manipulation
- Duplicate detection

#### `index.py` - Content Indexing
- File discovery
- Metadata extraction
- Digest computation
- Change detection

#### `sync_simple.py` - Synchronization Engine
- Vault synchronization
- Conflict detection
- File transfer
- State management

#### `md.py` - Markdown Processing
- Frontmatter parsing
- Content splitting
- Digest computation
- File serialization

#### `util.py` - Utilities
- Logging setup
- Path operations
- File operations
- Helper functions

## Development Workflow

### Branch Strategy

```
main (stable)
├── develop (integration)
│   ├── feature/add-encryption
│   ├── feature/remote-storage
│   └── bugfix/sync-conflict
└── release/v1.1.0
```

### Feature Development

1. **Create Feature Branch**
```bash
git checkout develop
git checkout -b feature/your-feature
```

2. **Implement Feature**
```python
# cast/new_feature.py
def new_functionality():
    """Implement new feature."""
    pass
```

3. **Add Tests**
```python
# tests/test_new_feature.py
def test_new_functionality():
    """Test new feature."""
    result = new_functionality()
    assert result == expected
```

4. **Update Documentation**
```markdown
# docs/FEATURES.md
## New Feature
Description of the new feature...
```

5. **Submit Pull Request**
```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature
# Create PR on GitHub
```

### Commit Convention

Follow Conventional Commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style
- `refactor`: Refactoring
- `test`: Testing
- `chore`: Maintenance

Examples:
```bash
git commit -m "feat(sync): add differential sync support"
git commit -m "fix(index): handle missing files gracefully"
git commit -m "docs: update installation instructions"
```

## Code Standards

### Python Style Guide

Follow PEP 8 with these modifications:
- Line length: 88 characters (Black default)
- Use Black for formatting
- Use type hints for public APIs

### Code Formatting

```bash
# Format with Black
black cast/

# Check without modifying
black --check cast/
```

### Type Hints

```python
from typing import Dict, List, Optional, Path, Union

def sync_vaults(
    vault1: Path,
    vault2: Path,
    overpower: bool = False
) -> Dict[str, Any]:
    """Synchronize two vaults."""
    pass
```

### Docstrings

Use Google style docstrings:

```python
def process_file(file_path: Path, auto_fix: bool = True) -> Dict[str, Any]:
    """Process a markdown file for indexing.
    
    Args:
        file_path: Path to the markdown file
        auto_fix: Whether to auto-add cast-ids
        
    Returns:
        Dictionary containing file metadata
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    pass
```

### Import Organization

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Optional

# Third-party
import yaml
from rich.console import Console
from typer import Typer

# Local
from cast.config import VaultConfig
from cast.index import Index
from cast.util import setup_logging
```

### Error Handling

```python
class CastError(Exception):
    """Base exception for Cast errors."""
    pass

class ConfigError(CastError):
    """Configuration-related errors."""
    pass

def load_config(path: Path) -> VaultConfig:
    """Load configuration with proper error handling."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config not found: {path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")
    
    return VaultConfig.from_dict(data)
```

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_ids.py
│   └── test_config.py
├── integration/       # Integration tests
│   ├── test_sync.py
│   └── test_index.py
├── fixtures/         # Test data
│   ├── vault1/
│   └── vault2/
└── conftest.py      # Pytest configuration
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_ids.py
import pytest
from cast.ids import generate_cast_id, validate_cast_id

def test_generate_cast_id():
    """Test UUID generation."""
    cast_id = generate_cast_id()
    assert validate_cast_id(cast_id)
    assert len(cast_id) == 36

def test_validate_cast_id():
    """Test UUID validation."""
    assert validate_cast_id("550e8400-e29b-41d4-a716-446655440000")
    assert not validate_cast_id("invalid-id")
    assert not validate_cast_id("")

@pytest.mark.parametrize("input_id,expected", [
    ("550e8400-e29b-41d4-a716-446655440000", True),
    ("not-a-uuid", False),
    ("", False),
    (None, False),
])
def test_validate_cast_id_parametrized(input_id, expected):
    """Test UUID validation with parameters."""
    assert validate_cast_id(input_id) == expected
```

#### Integration Test Example

```python
# tests/integration/test_sync.py
import tempfile
from pathlib import Path
import pytest

from cast.sync_simple import SimpleSyncEngine
from cast.config import VaultConfig

@pytest.fixture
def temp_vaults():
    """Create temporary test vaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault1 = Path(tmpdir) / "vault1"
        vault2 = Path(tmpdir) / "vault2"
        
        # Setup vaults
        vault1.mkdir()
        vault2.mkdir()
        
        # Initialize Cast
        for vault in [vault1, vault2]:
            (vault / ".cast").mkdir()
            config = VaultConfig.create_default(vault, vault.name)
            config.save()
        
        yield vault1, vault2

def test_sync_empty_vaults(temp_vaults):
    """Test syncing empty vaults."""
    vault1, vault2 = temp_vaults
    engine = SimpleSyncEngine()
    
    result = engine.sync_vaults(vault1, vault2)
    
    assert result["status"] == "success"
    assert result["synced"] == 0
    assert result["conflicts"] == 0
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cast --cov-report=html

# Run specific test file
pytest tests/test_ids.py

# Run specific test
pytest tests/test_ids.py::test_generate_cast_id

# Run with verbose output
pytest -v

# Run with print statements
pytest -s

# Run only marked tests
pytest -m "not slow"
```

### Test Coverage

Maintain minimum 80% test coverage:

```bash
# Generate coverage report
pytest --cov=cast --cov-report=term-missing

# Generate HTML report
pytest --cov=cast --cov-report=html
# Open htmlcov/index.html
```

## Debugging

### Debug Mode

Enable debug logging:

```python
# cast/util.py
import logging

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

Run with verbose output:
```bash
cast sync --verbose
```

### Using pdb

```python
import pdb

def problematic_function():
    data = process_data()
    pdb.set_trace()  # Debugger stops here
    result = transform(data)
    return result
```

### VS Code Debugging

`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Cast Sync",
            "type": "python",
            "request": "launch",
            "module": "cast",
            "args": ["sync", "--verbose"],
            "console": "integratedTerminal"
        }
    ]
}
```

### Common Debug Scenarios

#### Sync Issues

```python
# Add debug output in sync_simple.py
logger.debug(f"Comparing files: {file1} vs {file2}")
logger.debug(f"Digests: {digest1} vs {digest2}")
logger.debug(f"Sync decision: {decision}")
```

#### Index Problems

```python
# Add validation in index.py
def build_index(self):
    logger.debug(f"Found {len(files)} files to index")
    for file in files:
        logger.debug(f"Processing: {file}")
        try:
            entry = self.process_file(file)
        except Exception as e:
            logger.error(f"Failed to process {file}: {e}")
```

## Contributing

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Type hints added
- [ ] No hardcoded values
- [ ] Error handling appropriate
- [ ] Performance considered
- [ ] Security reviewed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added
```

## Architecture Decisions

### ADR-001: Use UUIDs for File Identification

**Status**: Accepted

**Context**: Need to track files across renames and moves

**Decision**: Use UUID v4 as cast-id

**Consequences**:
- Files trackable regardless of path
- Requires frontmatter modification
- Permanent file identity

### ADR-002: Body-Only Digests

**Status**: Accepted

**Context**: Metadata changes shouldn't trigger sync

**Decision**: Compute separate digest for body content

**Consequences**:
- Fewer unnecessary syncs
- Metadata can vary between vaults
- More complex digest computation

### ADR-003: Three-Way Merge

**Status**: Accepted

**Context**: Need intelligent conflict resolution

**Decision**: Compare current states with last sync state

**Consequences**:
- Better auto-merge capability
- Requires state persistence
- More complex sync logic

## Adding Features

### Example: Adding Encryption Support

#### 1. Design Phase

```python
# cast/crypto.py
from cryptography.fernet import Fernet

class VaultEncryption:
    """Handles vault encryption/decryption."""
    
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_file(self, path: Path) -> None:
        """Encrypt file in place."""
        pass
    
    def decrypt_file(self, path: Path) -> None:
        """Decrypt file in place."""
        pass
```

#### 2. Implementation

```python
# cast/sync_simple.py
def sync_with_encryption(self, vault1, vault2, key):
    """Sync with encryption support."""
    crypto = VaultEncryption(key)
    
    # Decrypt before sync
    crypto.decrypt_file(file_path)
    
    # Perform sync
    self.sync_file(file_path)
    
    # Re-encrypt after sync
    crypto.encrypt_file(file_path)
```

#### 3. Testing

```python
# tests/test_crypto.py
def test_encryption_roundtrip():
    """Test encrypt/decrypt cycle."""
    crypto = VaultEncryption(key)
    
    # Create test file
    test_file.write_text("test content")
    
    # Encrypt
    crypto.encrypt_file(test_file)
    assert test_file.read_bytes() != b"test content"
    
    # Decrypt
    crypto.decrypt_file(test_file)
    assert test_file.read_text() == "test content"
```

#### 4. Documentation

```markdown
# docs/FEATURES.md
## Encryption Support

Cast now supports optional encryption for vaults:

```bash
cast sync --encrypt --key-file ~/.cast/key
```
```

## Release Process

### Version Numbering

Follow Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH (e.g., 1.2.3)
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

### Release Checklist

1. **Update Version**
```python
# cast/__init__.py
__version__ = "1.2.0"

# pyproject.toml
version = "1.2.0"
```

2. **Update Changelog**
```markdown
# CHANGELOG.md
## [1.2.0] - 2024-01-15
### Added
- New feature X
### Fixed
- Bug Y
### Changed
- Behavior Z
```

3. **Run Tests**
```bash
pytest
black --check cast/
mypy cast/
```

4. **Create Release Branch**
```bash
git checkout -b release/v1.2.0
git commit -m "chore: prepare release v1.2.0"
```

5. **Tag Release**
```bash
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

6. **Build Distribution**
```bash
python -m build
```

7. **Upload to PyPI**
```bash
python -m twine upload dist/*
```

8. **Create GitHub Release**
- Go to GitHub releases
- Create release from tag
- Add changelog notes
- Upload artifacts

### Post-Release

1. Merge release branch to main
2. Merge main to develop
3. Bump version for next development
4. Announce release

## Performance Profiling

### Using cProfile

```python
import cProfile
import pstats

def profile_sync():
    """Profile sync operation."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run sync
    engine = SimpleSyncEngine()
    engine.sync_all(vault_path)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_operation():
    """Monitor memory usage."""
    large_data = load_index()
    process_data(large_data)
```

Run with:
```bash
python -m memory_profiler cast/index.py
```

## Security Considerations

### Input Validation

Always validate user input:

```python
def safe_path_join(base: Path, user_input: str) -> Path:
    """Safely join paths preventing traversal."""
    resolved = (base / user_input).resolve()
    
    # Ensure resolved path is within base
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path traversal detected: {user_input}")
    
    return resolved
```

### Dependency Security

Regular security updates:

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

## Conclusion

This development guide provides the foundation for contributing to Cast Sync. Follow these guidelines to maintain code quality, ensure reliability, and create a better synchronization tool for the community.

For questions or discussions, open an issue on GitHub or join our community chat.