# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-10-30

#### New Batch Pipeline with TUI
- **`04_pipeline.py`**: Complete batch processing pipeline with interactive TUI
  - Web scraping capability to discover all documentation ZIPs from index pages
  - Full-featured Terminal User Interface (TUI) using curses
  - Vi-like search/filter functionality with `/` command
  - Multi-selection with bulk operations (select all, deselect all)
  - Batch processing of multiple documentation packages
  - Progress tracking and comprehensive summary reports
  - Integration with existing conversion scripts via subprocess
  - Support for both interactive and automated (`--no-tui`) modes

#### Comprehensive Documentation Suite
- **PIPELINE_README.md**: Complete user guide for the batch pipeline
  - Feature descriptions and usage instructions
  - TUI controls reference
  - Command-line options documentation
  - Workflow examples and tips
  
- **TUI_GUIDE.md**: Detailed interface guide
  - Visual TUI layout diagrams
  - Mode descriptions (normal vs search)
  - Keyboard reference with all shortcuts
  - Workflow walkthroughs with examples
  - Error messages and troubleshooting
  
- **EXAMPLES.md**: Real-world use cases and examples
  - Basic workflows for common tasks
  - Advanced selection techniques
  - Automation scenarios (cron, CI/CD)
  - Integration examples
  
- **QUICK_REFERENCE.md**: One-page cheat sheet
  - Command syntax quick reference
  - Keyboard shortcuts table
  - Common patterns and commands
  - Troubleshooting quick fixes
  
- **WORKFLOW_DIAGRAM.md**: Visual workflow documentation
  - ASCII workflow diagrams
  - Comparison tables between workflows
  - Decision trees for choosing workflows
  - Data flow and architecture diagrams
  
- **GETTING_STARTED_PIPELINE.md**: Beginner-friendly tutorial
  - Step-by-step first conversion guide
  - Quick examples for common tasks
  - Troubleshooting for beginners
  - Learning path progression
  
- **PIPELINE_SUMMARY.md**: Technical implementation summary
  - Architecture overview
  - Design patterns used
  - Performance characteristics
  - Known limitations and workarounds

#### Testing and Utilities
- **test_pipeline.py**: Non-interactive test script for site scanning

### Changed - 2025-10-30
- **README.md**: Updated to include new Workflow A (Batch Pipeline)
  - Reorganized workflows: A (Pipeline), B (Single), C (Step-by-Step)
  - Enhanced feature list with icons
  - Updated output structure examples
  - Added links to new documentation

### Technical Details

**New Features:**
- Web scraping with BeautifulSoup4
- Interactive TUI with curses
- Real-time search and filtering
- Bulk selection operations
- Subprocess-based batch processing
- Comprehensive error handling and reporting
- Support for multiple documentation categories

**Dependencies:**
- No new runtime dependencies (beautifulsoup4 and requests already in requirements.txt)
- curses is built-in on Unix systems

**Compatibility:**
- Requires Unix-like system for TUI (Linux, macOS, WSL)
- `--no-tui` flag for Windows or CI/CD environments
- Python 3.7+ (same as before)

**File Statistics:**
- New files: 9 (1 script + 8 documentation files)
- Lines of code: ~500 (04_pipeline.py)
- Lines of documentation: ~2500+ (across all new docs)
- Modified files: 1 (README.md)

## [1.0.0] - Previous Version

### Features

#### Workflow B: Single Document Conversion
- **`03_fetch_extract_convert.py`**: All-in-one conversion for single ZIPs
  - Download from URL
  - Extract and process
  - Convert to Markdown
  - Clean terminal output with progress bars

#### Workflow C: Step-by-Step Conversion
- **`01_extract_zips.py`**: ZIP extraction with interactive selection
- **`02_convert_to_md.py`**: HTML to Markdown conversion
  - Multi-threaded processing
  - TOC structure preservation
  - Image handling and asset management
  - Online header link generation
- **`03_generate_documents.py`**: Multi-format document generation (EPUB, HTML, PDF)
- **`04_copy_md_files.py`**: Batch file copying utility

#### Documentation
- **README.md**: Project overview and usage guide
- **requirements.txt**: Python dependencies

#### Environment Setup
- **scripts/activate_env.sh**: Virtual environment helper script

---

## Version History Summary

| Version | Date | Major Changes |
|---------|------|---------------|
| Unreleased | 2025-10-30 | Added batch pipeline with TUI |
| 1.0.0 | Previous | Initial release with 3 workflows |

---

## Migration Guide

### For Existing Users

**No breaking changes** - All existing workflows (B and C) continue to work exactly as before.

**What's New:**
- New Workflow A (Pipeline) for batch processing
- Existing workflows renamed in documentation but functionality unchanged:
  - Old "Workflow A" → New "Workflow B" (03_fetch_extract_convert.py)
  - Old "Workflow B" → New "Workflow C" (step-by-step scripts)

**Getting Started with New Pipeline:**
```bash
# Quick start - try the new batch pipeline
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/

# Your existing commands still work
python 03_fetch_extract_convert.py [ZIP_URL]
python 01_extract_zips.py [ZIP_FILE]
# ... etc
```

### Recommended Workflow Selection

**Use New Workflow A (Pipeline) for:**
- Multiple documents from online sites
- Don't know exact ZIP URLs
- Want interactive selection
- Batch operations

**Use Workflow B (Single) for:**
- Single documents
- Have exact ZIP URL
- Scripting/automation
- Quick one-off conversions

**Use Workflow C (Step-by-Step) for:**
- Local ZIP files
- Need EPUB/PDF output
- Maximum control
- Custom processing

---

## Future Roadmap

### Planned Features

- [ ] Parallel item processing in pipeline
- [ ] Resume capability for interrupted batches
- [ ] Configuration file support
- [ ] Enhanced search with regex
- [ ] Web-based GUI alternative to TUI
- [ ] Progress estimation and time remaining
- [ ] Export/import selection capability

### Under Consideration

- [ ] Windows native TUI support
- [ ] Database backend for caching
- [ ] Version comparison tools
- [ ] Documentation diff viewer
- [ ] Plugin system for custom processors

---

## Contributing

Contributions are welcome! Areas where help is needed:

1. **Testing**: Test on different systems and terminals
2. **Documentation**: Improve guides and examples
3. **Features**: Implement items from roadmap
4. **Bug Reports**: Report issues with detailed reproduction steps

---

## Credits

### Authors
- Initial implementation: Original author
- Pipeline feature (v2.0): AI Assistant (2025-10-30)

### Dependencies
- BeautifulSoup4 - HTML/XML parsing
- requests - HTTP library
- markdownify - HTML to Markdown conversion
- tqdm - Progress bars
- bleach - HTML sanitization
- curses - Terminal UI (built-in)
- pandoc - Document conversion (external)

---

## License

See [LICENSE](LICENSE) file for details.

---

## Notes

### Breaking Changes
- None in this release

### Deprecations
- None in this release

### Security
- No security vulnerabilities addressed in this release
- Web scraping respects robots.txt (best practice)
- No sensitive data stored or transmitted

### Performance
- Pipeline processes items sequentially (not parallel)
- Individual item conversion remains multi-threaded
- Caching reduces redundant downloads

---

**Last Updated**: 2025-10-30

