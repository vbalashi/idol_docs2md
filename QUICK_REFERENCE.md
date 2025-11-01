# Pipeline Quick Reference Card

One-page reference for IDOL documentation pipeline.

## Command Syntax

```bash
python 04_pipeline.py <URL> [OPTIONS]
```

## URLs

| URL | Description |
|-----|-------------|
| `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/` | Specific version |
| `https://www.microfocus.com/documentation/idol/` | All versions |

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output_md_dir DIR` | Output directory | `./md` |
| `--force` | Re-download existing ZIPs | False |
| `--no-tui` | Skip TUI, auto-process all | False |
| `--max_workers N` | Parallel threads | 10 |
| `--copy_all_images_to_assets` | Copy all images | False |

## Keyboard Shortcuts (TUI)

### Navigation
- `↑` `↓` - Move cursor
- `PgUp` `PgDn` - Page up/down
- `Home` `End` - First/last item

### Selection
- `Space` - Toggle current item
- `a` - Select all filtered
- `n` - Deselect all filtered
- `A` - Select ALL items
- `N` - Deselect ALL items

### Search/Filter
- `/` - Enter search mode
- `Esc` - Clear filter
- `Enter` - Apply filter / Confirm selection

### Control
- `Enter` - Start processing
- `q` - Quit

## Quick Workflows

### 1. Select All Connectors
```
/ → connector → Enter → a → / → Esc → Enter
```

### 2. Select Everything Except X
```
A → / → X → Enter → n → / → Esc → Enter
```

### 3. Select Multiple Categories
```
/ → category1 → Enter → a
/ → category2 → Enter → a
/ → Esc → Enter
```

## Example Commands

### Basic Usage
```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

### Custom Output Directory
```bash
python 04_pipeline.py [URL] --output_md_dir ~/Documents/idol-docs
```

### Auto-Process All Items
```bash
python 04_pipeline.py [URL] --no-tui
```

### Force Re-download
```bash
python 04_pipeline.py [URL] --force
```

### Include All Images
```bash
python 04_pipeline.py [URL] --copy_all_images_to_assets
```

## Output Structure

```
md/
├── Content_25.4_Documentation.md
├── Content_25.4_Documentation_assets/
│   └── (images)
├── Community_25.4_Documentation.md
├── Community_25.4_Documentation_assets/
│   └── (images)
└── ...
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No items found | Check URL is accessible |
| TUI not working | Use `--no-tui` flag |
| Download fails | Check network connection |
| Conversion fails | Run single item with `03_fetch_extract_convert.py` |

## Tips

1. **Start with search**: Use `/` to quickly find items
2. **Cache downloads**: Don't use `--force` unnecessarily
3. **Organize output**: Use descriptive output directories
4. **Test first**: Try a few items before batch processing
5. **Check disk space**: Large conversions need space

## File Locations

| Type | Default Location | Purpose |
|------|-----------------|----------|
| Downloaded ZIPs | `./tmp_downloads/` | Cache |
| Extracted files | `./tmp_extracts/` | Temp processing |
| Output MD files | `./md/` | Final output |
| Assets | `./md/*_assets/` | Images |

## Common Patterns

### Pattern 1: Version Comparison
```bash
python 04_pipeline.py [URL_v1] --output_md_dir ./docs_v1 --no-tui
python 04_pipeline.py [URL_v2] --output_md_dir ./docs_v2 --no-tui
diff -r docs_v1/ docs_v2/
```

### Pattern 2: Selective Update
```bash
# First time: download all
python 04_pipeline.py [URL] --no-tui

# Later: update specific items in TUI
python 04_pipeline.py [URL]
# Use search to find and select updated items
```

### Pattern 3: Offline Archive
```bash
python 04_pipeline.py [URL] --no-tui --copy_all_images_to_assets
tar -czf idol_docs.tar.gz md/
```

## Environment

- **Python**: 3.7+
- **OS**: Linux, macOS (curses required for TUI)
- **Dependencies**: See `requirements.txt`

## Links

- Full documentation: [PIPELINE_README.md](PIPELINE_README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- TUI guide: [TUI_GUIDE.md](TUI_GUIDE.md)
- Project: [README.md](README.md)

---

**Print this page for quick reference!**





