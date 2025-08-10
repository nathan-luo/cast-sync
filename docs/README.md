# Cast Sync Documentation

Welcome to the Cast Sync documentation! Cast is a decentralized, knowledge-aware synchronization system for Markdown vaults that provides intelligent conflict resolution and maintains complete data sovereignty.

## 📚 Documentation Overview

### For Users

- **[User Guide](USER_GUIDE.md)** - Complete guide for installing and using Cast
  - Quick start instructions
  - Basic and advanced usage
  - Troubleshooting guide
  - Best practices and FAQ

- **[Features](FEATURES.md)** - Comprehensive feature documentation
  - All Cast capabilities explained
  - Technical implementation details
  - Use cases and examples
  - Configuration options

### For Developers

- **[Development Guide](DEVELOPMENT.md)** - Contributing to Cast
  - Development setup
  - Code standards and testing
  - Adding new features
  - Release process

- **[API Reference](API_REFERENCE.md)** - Complete API documentation
  - CLI commands reference
  - Python API documentation
  - Data structures and formats
  - Error handling

### System Design

- **[Architecture](ARCHITECTURE.md)** - System architecture documentation
  - Core architecture and design philosophy
  - Component architecture
  - Data flow and synchronization
  - Security and performance

- **[Technical Overview](TECHNICAL_OVERVIEW.md)** - Technical deep dive
  - Core concepts and algorithms
  - Implementation details
  - Performance characteristics
  - Future enhancements

## 🚀 Quick Links

### Getting Started

1. **Installation**: `pip install cast-sync`
2. **Setup**: `cast install`
3. **Initialize Vault**: `cast init`
4. **Synchronize**: `cast sync`

### Common Tasks

- [Setting up your first vault](USER_GUIDE.md#setting-up-your-first-vault)
- [Synchronizing multiple vaults](USER_GUIDE.md#synchronizing-vaults)
- [Handling sync conflicts](USER_GUIDE.md#handling-conflicts)
- [Configuring what syncs](USER_GUIDE.md#advanced-usage)

### Key Concepts

- **Cast-ID**: UUID-based file identification system
- **Three-Way Merge**: Intelligent conflict detection using sync history
- **Body-Only Digests**: Content comparison ignoring metadata
- **Atomic Operations**: Safe file operations preventing corruption

## 📖 Documentation Map

```
For New Users:
USER_GUIDE.md → FEATURES.md → TECHNICAL_OVERVIEW.md

For Developers:
DEVELOPMENT.md → API_REFERENCE.md → ARCHITECTURE.md

For System Understanding:
TECHNICAL_OVERVIEW.md → ARCHITECTURE.md → FEATURES.md
```

## 🎯 Documentation by Role

### Knowledge Worker / Note Taker

Start with:
1. [User Guide - Quick Start](USER_GUIDE.md#quick-start)
2. [User Guide - Basic Usage](USER_GUIDE.md#basic-usage)
3. [Features - Core Features](FEATURES.md#core-features)

### System Administrator

Focus on:
1. [User Guide - Installation](USER_GUIDE.md#installation)
2. [Features - Configuration](FEATURES.md#configuration-features)
3. [Architecture - Security](ARCHITECTURE.md#security-architecture)

### Developer / Contributor

Essential reading:
1. [Development Guide](DEVELOPMENT.md)
2. [API Reference](API_REFERENCE.md)
3. [Architecture - Component Architecture](ARCHITECTURE.md#component-architecture)

### Technical Evaluator

Review:
1. [Technical Overview](TECHNICAL_OVERVIEW.md)
2. [Architecture - System Design](ARCHITECTURE.md#system-design-philosophy)
3. [Features - Technical Details](FEATURES.md)

## 💡 Key Features

### Core Capabilities

- **Decentralized Sync**: No server required, peer-to-peer synchronization
- **Smart Conflict Resolution**: Three-way merge with intelligent auto-resolution
- **UUID Tracking**: Files tracked by ID, not path (rename-safe)
- **Selective Sync**: Control which files sync to which vaults
- **Atomic Operations**: All file operations are atomic and safe
- **Incremental Indexing**: Only changed files are processed

### User Experience

- **Interactive Conflicts**: Side-by-side comparison for manual resolution
- **Batch Mode**: Automated operation for scripts and cron jobs
- **Rich CLI**: Modern command-line interface with colors and tables
- **Auto-Fix**: Automatically adds IDs to trackable files
- **Force Sync**: Overpower mode for authoritative updates

### Technical Excellence

- **Body-Only Digests**: Ignore metadata changes in sync decisions
- **Platform Support**: Windows, macOS, and Linux compatibility
- **Extensible Design**: Plugin architecture for future features
- **Performance**: Handles vaults with 50,000+ files efficiently
- **Data Integrity**: SHA-256 verification on all operations

## 🛠️ Technology Stack

- **Language**: Python 3.8+
- **CLI Framework**: Typer
- **UI Library**: Rich
- **Configuration**: YAML
- **Data Storage**: JSON
- **Hashing**: SHA-256

## 📝 Documentation Standards

Our documentation follows these principles:

1. **Comprehensive**: Every feature and API is documented
2. **Practical**: Real-world examples and use cases
3. **Accessible**: Clear language for all skill levels
4. **Maintained**: Updated with each release
5. **Structured**: Logical organization and cross-references

## 🤝 Contributing to Documentation

Found an error or want to improve the docs?

1. Fork the repository
2. Make your changes in the `docs/` directory
3. Submit a pull request

Documentation improvements are always welcome!

## 📞 Getting Help

- **Documentation**: You're here!
- **Command Help**: `cast --help` or `cast <command> --help`
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Community support and questions

## 🎓 Learning Path

### Beginner Path

1. Install Cast ([User Guide](USER_GUIDE.md#installation))
2. Create first vault ([User Guide](USER_GUIDE.md#setting-up-your-first-vault))
3. Understand basic sync ([User Guide](USER_GUIDE.md#synchronizing-vaults))
4. Learn conflict resolution ([User Guide](USER_GUIDE.md#handling-conflicts))

### Advanced Path

1. Master configuration ([Features](FEATURES.md#configuration-features))
2. Understand sync algorithm ([Technical Overview](TECHNICAL_OVERVIEW.md#key-algorithms))
3. Explore architecture ([Architecture](ARCHITECTURE.md))
4. Contribute code ([Development](DEVELOPMENT.md))

### System Design Path

1. Core concepts ([Technical Overview](TECHNICAL_OVERVIEW.md#core-concepts))
2. Architecture principles ([Architecture](ARCHITECTURE.md#system-design-philosophy))
3. Component design ([Architecture](ARCHITECTURE.md#component-architecture))
4. Extension points ([Architecture](ARCHITECTURE.md#future-architecture-considerations))

## 📊 Documentation Statistics

- **Total Pages**: 7 comprehensive documents
- **Topics Covered**: 50+ features and concepts
- **Code Examples**: 100+ practical examples
- **API Methods**: 40+ documented functions
- **Use Cases**: 20+ real-world scenarios

## 🚦 Documentation Status

| Document | Status | Last Updated | Completeness |
|----------|--------|--------------|--------------|
| User Guide | ✅ Complete | 2024-01 | 100% |
| Features | ✅ Complete | 2024-01 | 100% |
| API Reference | ✅ Complete | 2024-01 | 100% |
| Architecture | ✅ Complete | 2024-01 | 100% |
| Technical Overview | ✅ Complete | 2024-01 | 100% |
| Development | ✅ Complete | 2024-01 | 100% |

## 📜 License

Cast Sync and its documentation are open source. See the [LICENSE](../LICENSE) file for details.

---

**Cast Sync** - Knowledge-aware synchronization for Markdown vaults

*Empowering knowledge workers with decentralized, intelligent content synchronization*