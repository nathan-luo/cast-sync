# Cast Sync Development Guide

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)
- Make (optional, for automation)

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/cast-sync.git
cd cast-sync

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

### Development Dependencies

```txt
# requirements-dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
pre-commit>=3.0.0
tox>=4.0.0
sphinx>=6.0.0
```

## Project Structure

```
cast-sync/
├── cast/                    # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # CLI interface
│   ├── sync.py             # Sync engine
│   ├── plan.py             # Sync planning
│   ├── index.py            # File indexing
│   ├── peers.py            # Peer state management
│   ├── objects.py          # Object storage
│   ├── ids.py              # Cast ID management
│   ├── merge_cast.py       # Content merging
│   ├── merge_blocks.py     # Block-based merge
│   ├── normalize.py        # Content normalization
│   ├── resolve.py          # Conflict resolution
│   ├── config.py           # Configuration
│   ├── select.py           # File selection
│   ├── vault.py            # Vault operations
│   └── util.py             # Utilities
├── tests/                   # Test suite
│   ├── test_sync.py        # Sync tests
│   ├── test_merge.py       # Merge tests
│   ├── test_index.py       # Index tests
│   └── fixtures/           # Test fixtures
├── docs/                    # Documentation
├── scripts/                 # Development scripts
├── .github/                 # GitHub workflows
├── pyproject.toml          # Project configuration
├── setup.py                # Setup script
├── Makefile                # Build automation
└── README.md               # Project README
```

## Coding Standards

### Style Guide

Follow PEP 8 with these additions:

```python
# Imports: Standard library, third-party, local
import os
import sys
from pathlib import Path

import yaml
from typer import Typer

from cast.config import VaultConfig
from cast.index import Index


# Type hints for all functions
def process_file(path: Path, options: dict[str, Any]) -> FileResult:
    """Process a single file.
    
    Args:
        path: File path to process
        options: Processing options
        
    Returns:
        Processing result
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    pass


# Use dataclasses for data structures
@dataclass
class SyncAction:
    cast_id: str
    action_type: ActionType
    source_path: str
    dest_path: str
    

# Constants in UPPER_CASE
MAX_FILE_SIZE = 100 * 1024 * 1024
DEFAULT_TIMEOUT = 30


# Private functions/methods with underscore
def _internal_helper():
    pass


class MyClass:
    def _private_method(self):
        pass
```

### Code Formatting

Use Black for automatic formatting:

```bash
# Format all files
black cast/ tests/

# Check without modifying
black --check cast/ tests/

# Configure in pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
```

### Linting

Use Ruff for fast linting:

```bash
# Run linter
ruff cast/ tests/

# Fix auto-fixable issues
ruff --fix cast/ tests/

# Configure in pyproject.toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP"]
```

### Type Checking

Use MyPy for static type checking:

```bash
# Run type checker
mypy cast/

# Configure in pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

## Testing

### Test Structure

```python
# tests/test_sync.py
import pytest
from pathlib import Path
from cast.sync import SyncEngine


class TestSyncEngine:
    """Test sync engine functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create sync engine instance."""
        return SyncEngine()
    
    @pytest.fixture
    def test_vaults(self, tmp_path):
        """Create test vault structure."""
        vault1 = tmp_path / "vault1"
        vault2 = tmp_path / "vault2"
        vault1.mkdir()
        vault2.mkdir()
        return vault1, vault2
    
    def test_sync_create(self, engine, test_vaults):
        """Test CREATE action during sync."""
        vault1, vault2 = test_vaults
        
        # Create file in source
        (vault1 / "test.md").write_text("# Test")
        
        # Run sync
        results = engine.sync(vault1, vault2, apply=True)
        
        # Verify file created
        assert (vault2 / "test.md").exists()
        assert (vault2 / "test.md").read_text() == "# Test"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cast --cov-report=html

# Run specific test file
pytest tests/test_sync.py

# Run specific test
pytest tests/test_sync.py::TestSyncEngine::test_sync_create

# Run with verbose output
pytest -v

# Run in parallel
pytest -n auto
```

### Test Fixtures

Create reusable test fixtures:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from cast.vault import Vault


@pytest.fixture
def sample_vault(tmp_path):
    """Create a sample vault with test data."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    
    # Initialize vault
    vault = Vault(vault_path)
    vault.init()
    
    # Add sample files
    (vault_path / "note1.md").write_text("""---
cast-id: test-id-1
---
# Note 1
Content here""")
    
    return vault


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "vault": {"id": "test", "root": "/tmp/test"},
        "index": {
            "include": ["**/*.md"],
            "exclude": [".git/**"]
        }
    }
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_sync_workflow(tmp_path):
    """Test complete sync workflow."""
    # Setup
    vault1 = create_vault(tmp_path / "vault1")
    vault2 = create_vault(tmp_path / "vault2")
    
    # Create content
    create_test_files(vault1)
    
    # Index
    vault1.index_files()
    vault2.index_files()
    
    # Sync
    engine = SyncEngine()
    results = engine.sync(vault1.path, vault2.path, apply=True)
    
    # Verify
    assert_files_synced(vault1, vault2)
    assert_no_conflicts(vault2)
```

## Debugging

### Debug Mode

Enable debug logging:

```python
# In code
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
os.environ["CAST_LOG_LEVEL"] = "DEBUG"
```

### Using PDB

```python
# Insert breakpoint
import pdb; pdb.set_trace()

# Or in Python 3.7+
breakpoint()

# Run with pdb
python -m pdb -m cast.cli sync vault1 vault2
```

### VS Code Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Cast Sync",
            "type": "python",
            "request": "launch",
            "module": "cast.cli",
            "args": ["sync", "vault1", "vault2", "--apply"],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

## Contributing

### Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/cast-sync.git
   cd cast-sync
   git remote add upstream https://github.com/original/cast-sync.git
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run Tests**
   ```bash
   make test  # Or: pytest
   ```

5. **Format and Lint**
   ```bash
   make format  # Or: black . && ruff --fix .
   make lint    # Or: ruff . && mypy cast/
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature
   
   - Detailed description
   - Breaking changes (if any)"
   ```

7. **Push and Create PR**
   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

### Commit Message Convention

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
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Test changes
- `chore`: Maintenance

Examples:
```bash
git commit -m "feat(sync): add parallel file processing"
git commit -m "fix(merge): handle unicode in conflict markers"
git commit -m "docs: update sync protocol documentation"
```

### Pull Request Guidelines

1. **Title**: Clear and descriptive
2. **Description**: Include:
   - What changes were made
   - Why changes were needed
   - How to test changes
3. **Tests**: All new features need tests
4. **Documentation**: Update relevant docs
5. **Backwards Compatibility**: Note any breaking changes

## Building and Publishing

### Build Package

```bash
# Build wheel and source distribution
python -m build

# Files created in dist/
ls dist/
# cast_sync-1.0.0-py3-none-any.whl
# cast_sync-1.0.0.tar.gz
```

### Test Package

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install from wheel
pip install dist/cast_sync-1.0.0-py3-none-any.whl

# Test installation
cast --version
```

### Publish to PyPI

```bash
# Install publishing tools
pip install twine

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ cast-sync

# Upload to PyPI
twine upload dist/*
```

## Performance Optimization

### Profiling

```python
# Profile code
import cProfile
import pstats

def profile_sync():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Code to profile
    engine.sync(vault1, vault2)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Function to analyze
    pass
```

### Optimization Tips

1. **Use generators for large datasets**
   ```python
   def process_files(paths):
       for path in paths:
           yield process_file(path)
   ```

2. **Cache expensive computations**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def compute_digest(content: str) -> str:
       return hashlib.sha256(content.encode()).hexdigest()
   ```

3. **Parallel processing**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       results = executor.map(process_file, files)
   ```

## Architecture Decisions

### Why SHA-256 for Digests?

- Cryptographically secure
- Low collision probability
- Wide tool support
- Good performance

### Why UUID v4 for Cast IDs?

- No central authority needed
- Statistically unique
- Standard format
- Library support

### Why YAML Frontmatter?

- Human readable
- Obsidian compatible
- Structured metadata
- Wide language support

## Adding New Features

### Feature Checklist

- [ ] Design document
- [ ] Tests written
- [ ] Documentation updated
- [ ] Backwards compatible
- [ ] Performance impact assessed
- [ ] Security implications considered
- [ ] Error handling complete
- [ ] Logging added
- [ ] Configuration options added

### Example: Adding New Merge Strategy

1. **Define Strategy Interface**
   ```python
   # cast/merge/base.py
   class MergeStrategy(ABC):
       @abstractmethod
       def merge(self, base: str, source: str, dest: str) -> tuple[str, list[str]]:
           pass
   ```

2. **Implement Strategy**
   ```python
   # cast/merge/semantic.py
   class SemanticMergeStrategy(MergeStrategy):
       def merge(self, base: str, source: str, dest: str) -> tuple[str, list[str]]:
           # Implementation
           pass
   ```

3. **Register Strategy**
   ```python
   # cast/merge/__init__.py
   STRATEGIES = {
       "line": LineMergeStrategy(),
       "block": BlockMergeStrategy(),
       "semantic": SemanticMergeStrategy(),  # New
   }
   ```

4. **Add Tests**
   ```python
   # tests/test_semantic_merge.py
   def test_semantic_merge():
       strategy = SemanticMergeStrategy()
       merged, conflicts = strategy.merge(base, source, dest)
       assert merged == expected
   ```

5. **Update Documentation**
   ```markdown
   # docs/configuration.md
   merge:
     strategy: semantic  # New option
   ```

## Release Process

### Version Numbering

Follow Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH
- 1.0.0 → 1.0.1 (bug fix)
- 1.0.0 → 1.1.0 (new feature)
- 1.0.0 → 2.0.0 (breaking change)

### Release Checklist

1. **Update Version**
   ```python
   # cast/__init__.py
   __version__ = "1.1.0"
   ```

2. **Update Changelog**
   ```markdown
   # CHANGELOG.md
   ## [1.1.0] - 2024-01-15
   ### Added
   - New feature X
   ### Fixed
   - Bug Y
   ```

3. **Run Full Test Suite**
   ```bash
   tox  # Test all Python versions
   ```

4. **Create Git Tag**
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

5. **Build and Upload**
   ```bash
   python -m build
   twine upload dist/*
   ```

6. **Create GitHub Release**
   - Go to GitHub releases
   - Create release from tag
   - Add changelog notes
   - Attach built artifacts

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install -r requirements-dev.txt
    
    - name: Lint
      run: |
        black --check .
        ruff .
        mypy cast/
    
    - name: Test
      run: |
        pytest --cov=cast --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Security Considerations

### Input Validation

```python
def validate_cast_id(cast_id: str) -> bool:
    """Validate cast-id format."""
    try:
        uuid.UUID(cast_id, version=4)
        return True
    except ValueError:
        return False
```

### Path Traversal Prevention

```python
def safe_path_join(base: Path, relative: str) -> Path:
    """Safely join paths preventing traversal."""
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"Path traversal attempt: {relative}")
    return target
```

### Secure File Operations

```python
def atomic_write(path: Path, content: str):
    """Write file atomically with proper permissions."""
    temp = path.with_suffix('.tmp')
    try:
        # Write with restricted permissions
        temp.touch(mode=0o600)
        temp.write_text(content)
        temp.replace(path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
```

## Troubleshooting Development

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure package is installed in dev mode
   pip install -e .
   ```

2. **Test Failures**
   ```bash
   # Run single test for debugging
   pytest -xvs tests/test_file.py::test_name
   ```

3. **Type Check Errors**
   ```bash
   # Ignore specific error
   # type: ignore[error-code]
   ```

## Resources

### Documentation
- [Python Packaging Guide](https://packaging.python.org/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [PyYAML Documentation](https://pyyaml.org/)

### Tools
- [Black Formatter](https://black.readthedocs.io/)
- [Ruff Linter](https://beta.ruff.rs/)
- [MyPy Type Checker](https://mypy-lang.org/)
- [Pytest Framework](https://pytest.org/)

### Community
- GitHub Issues: Bug reports and features
- Discussions: Design decisions
- Wiki: Additional documentation