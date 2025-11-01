# IDOL Documentation Pipeline

Batch download and convert multiple IDOL documentation packages with an interactive TUI.

## Features

- 🔍 **Automatic Site Scanning** - Discovers all available documentation ZIPs from a documentation index page
- 🖥️ **Interactive TUI** - Vi-like interface for selecting documentation items
- 🔎 **Search/Filter** - Quickly find documentation by typing `/` + search term
- ⚡ **Batch Processing** - Convert multiple documentation packages in one run
- 📊 **Progress Tracking** - See conversion progress and final summary

## Quick Start

### Basic Usage

```bash
# Scan and process documentation from a specific version
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/

# Scan from the main IDOL documentation page (all versions)
python 04_pipeline.py https://www.microfocus.com/documentation/idol/
```

### TUI Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate up/down |
| `PgUp` / `PgDn` | Page up/down |
| `Home` / `End` | Jump to first/last item |
| `Space` | Toggle selection on current item |
| `/` | Enter search/filter mode |
| `a` | Select all filtered items |
| `n` | Deselect all filtered items |
| `A` (Shift+A) | Select all items (ignoring filter) |
| `N` (Shift+N) | Deselect all items (ignoring filter) |
| `Enter` | Confirm selection and start processing |
| `q` | Quit without processing |

### Search/Filter Mode

1. Press `/` to enter search mode
2. Type your search term (e.g., "Content" or "Connector")
3. Press `Enter` to apply filter
4. Press `Esc` to clear filter and return to normal mode

### Command-Line Options

```bash
python 04_pipeline.py [URL] [OPTIONS]

Required:
  URL                           Documentation index URL

Optional:
  --temp_download_dir DIR       Directory for downloaded ZIPs (default: ./tmp_downloads)
  --temp_extract_dir DIR        Directory for extracted files (default: ./tmp_extracts)
  --output_md_dir DIR           Directory for output MD files (default: ./md)
  --force                       Force re-download existing ZIPs
  --max_workers N               Number of conversion threads (default: 10)
  --copy_all_images_to_assets   Copy all images, even unreferenced ones
  --no-tui                      Skip TUI and auto-process all items
```

## Examples

### Example 1: Select Specific Documentation

```bash
# Launch TUI to select from Knowledge Discovery 25.4
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

Then in the TUI:
1. Press `/` and type "Connector" to filter only connectors
2. Press `a` to select all filtered connectors
3. Press `/` again and clear to see all items
4. Use arrow keys to select additional items with `Space`
5. Press `Enter` to start conversion

### Example 2: Browse All Versions

```bash
# Scan the main IDOL documentation page to see all versions
python 04_pipeline.py https://www.microfocus.com/documentation/idol/
```

### Example 3: Batch Process Everything

```bash
# Auto-select and process all items without TUI
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ --no-tui
```

### Example 4: Custom Output Directory

```bash
# Output to a specific directory
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --output_md_dir ~/Documents/idol-docs \
  --copy_all_images_to_assets
```

## Workflow

```
┌─────────────────────┐
│  Scan Documentation │
│       Website       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   TUI: Select Items │
│  (search, filter,   │
│   multi-select)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  For each selected: │
│  1. Download ZIP    │
│  2. Extract         │
│  3. Convert to MD   │
│  4. Copy to output  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Summary Report    │
│ (success/failures)  │
└─────────────────────┘
```

## Output Structure

After processing, your output directory will contain:

```
md/
├── Content_25.4_Documentation.md
├── Content_25.4_Documentation_assets/
│   ├── image1.png
│   ├── image2.jpg
│   └── ...
├── Community_25.4_Documentation.md
├── Community_25.4_Documentation_assets/
│   └── ...
└── ...
```

Each documentation package gets:
- One consolidated `.md` file
- One `_assets/` directory with all images

## Tips

### Efficient Selection

1. **Filter first, then select**: Use `/` to narrow down items, then `a` to select all filtered
2. **Category filtering**: Search by category name (e.g., "Text" for text-processing components)
3. **Multiple filters**: Clear and reapply filters to build your selection incrementally

### Large Documentation Sets

For processing many items:
- Use `--max_workers` to control parallel conversion threads
- Use `--force` only when needed (it re-downloads everything)
- Consider using `--no-tui` for automated/scripted workflows

### Disk Space

- Downloaded ZIPs are cached in `tmp_downloads/` by default
- Extracted files go to `tmp_extracts/` (can be large)
- Clean up temp directories periodically to save space

## Troubleshooting

### No items found

- Check the URL is correct and accessible
- Ensure the page contains ZIP download links
- Try the parent URL (e.g., remove version number)

### TUI not working

- Ensure you're on a Unix-like system (Linux, macOS)
- Check terminal supports curses (most do)
- Use `--no-tui` as fallback

### Conversion failures

- Check network connectivity for downloads
- Verify sufficient disk space
- Review individual item logs for details

## Integration

The pipeline uses `03_fetch_extract_convert.py` internally. You can also:

```bash
# Process a single item directly (bypass pipeline)
python 03_fetch_extract_convert.py https://example.com/docs/Content_25.4.zip

# Or use the pipeline for batch operations
python 04_pipeline.py https://example.com/docs/
```

## Dependencies

- Python 3.7+
- beautifulsoup4 (HTML parsing)
- requests (HTTP)
- curses (TUI, built-in on Unix)
- All dependencies from `03_fetch_extract_convert.py`

Install with:
```bash
pip install -r requirements.txt
```





