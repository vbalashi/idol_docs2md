# Getting Started with the Pipeline

A beginner-friendly guide to using the IDOL documentation pipeline.

## Prerequisites

Before you begin, ensure you have:

- ✅ Python 3.7 or higher
- ✅ Unix-like system (Linux, macOS, WSL on Windows)
- ✅ Internet connection
- ✅ Dependencies installed (see below)

## Installation

### 1. Install Dependencies

```bash
# Using the provided helper script (recommended)
source scripts/activate_env.sh

# Or manually
pip install -r requirements.txt
```

**Dependencies:**
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `markdownify` - HTML to Markdown conversion
- `tqdm` - Progress bars
- `bleach` - HTML sanitization
- `curses` - TUI (built-in on Unix systems)

### 2. Verify Installation

```bash
python 04_pipeline.py --help
```

You should see the help text with all available options.

## Your First Conversion

### Step 1: Launch the Pipeline

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

This will:
1. Scan the documentation site (takes a few seconds)
2. Display found items
3. Launch the TUI

### Step 2: Navigate in TUI

You'll see something like this:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃          IDOL Documentation Selector          ┃
┃                                               ┃
┃  Selected: 0/45 | Showing: 45                 ┃
┃  No filter (press '/' to search)              ┃
┃                                               ┃
┃  > [ ] Getting Started: Getting Started Guide ┃
┃    [ ] Text: Category                         ┃
┃    [ ] Text: Community                        ┃
┃    [ ] Text: Content                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Step 3: Select Items

**Option A: Select Individual Items**
1. Use ↑/↓ arrow keys to move
2. Press `Space` to select/deselect
3. Repeat for all desired items

**Option B: Select All Items**
1. Press `A` (Shift+A)
2. All items are now selected

**Option C: Select by Category** (Recommended for beginners)
1. Press `/` to enter search mode
2. Type `content` (or any category name)
3. Press `Enter` to apply filter
4. Press `a` to select all filtered items
5. Press `/` then `Esc` to clear filter
6. Press `Enter` to confirm

### Step 4: Confirm and Process

1. Review your selections (items marked with [X])
2. Press `Enter` to start processing
3. Wait for conversions to complete

### Step 5: Find Your Output

Your converted documentation will be in the `md/` directory:

```bash
ls -lh md/
```

Output:
```
Content_25.4_Documentation.md
Content_25.4_Documentation_assets/
```

Each item gets:
- One `.md` file (the documentation)
- One `_assets/` directory (images)

## Quick Examples

### Example 1: Convert All Connectors

**Goal**: Get documentation for all IDOL connectors

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

**In TUI**:
1. Press `/`
2. Type `connector`
3. Press `Enter`
4. Press `a` (select all connectors)
5. Press `Enter` (start processing)

**Result**: All connector documentation converted to Markdown

---

### Example 2: Convert Specific Items

**Goal**: Get only Content, Community, and Category documentation

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

**In TUI**:
1. Press `/`, type `content`, press `Enter`
2. Press `Space` to select Content
3. Press `/`, type `community`, press `Enter`
4. Press `Space` to select Community
5. Press `/`, type `category`, press `Enter`
6. Press `Space` to select Category
7. Press `/`, press `Esc` (clear filter)
8. Verify three items selected
9. Press `Enter`

---

### Example 3: Convert Everything

**Goal**: Get all available documentation

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ --no-tui
```

The `--no-tui` flag skips the interface and processes everything automatically.

## Common Tasks

### Task: Search for Specific Documentation

```
Press '/' → Type search term → Press Enter
```

Examples:
- `/server` - Find all server-related docs
- `/admin` - Find administration guides
- `/connector` - Find all connectors

### Task: Select All in Category

```
Press '/' → Type category → Enter → Press 'a'
```

### Task: Select Everything Except X

```
Press 'A' → Press '/' → Type X → Enter → Press 'n' → Press '/' → Esc
```

Example: Select all except Media Server
```
A → / → media → Enter → n → / → Esc → Enter
```

### Task: Cancel and Start Over

```
Press 'q' to quit without processing
```

Run the command again to start fresh.

## Understanding the Output

### File Structure

After processing, your `md/` directory will contain:

```
md/
├── Content_25.4_Documentation.md          # Full documentation in one file
├── Content_25.4_Documentation_assets/     # All images
│   ├── image1.png
│   ├── image2.jpg
│   └── ...
├── Community_25.4_Documentation.md
├── Community_25.4_Documentation_assets/
└── ...
```

### Reading the Markdown

Open any `.md` file with:
- **Text editor**: VS Code, Sublime, Vim, etc.
- **Markdown viewer**: Obsidian, Typora, Marked, etc.
- **Browser**: Use a Markdown extension
- **Command line**: `less file.md` or `cat file.md`

### Images

Images are automatically:
- Copied to the `_assets/` directory
- Referenced in the Markdown file
- Named to avoid collisions

## Customization

### Change Output Directory

```bash
python 04_pipeline.py [URL] --output_md_dir ~/Documents/idol-docs
```

### Adjust Processing Speed

```bash
python 04_pipeline.py [URL] --max_workers 20
```

More workers = faster, but uses more CPU/memory.

### Force Re-download

```bash
python 04_pipeline.py [URL] --force
```

Useful if documentation was updated online.

### Include All Images

```bash
python 04_pipeline.py [URL] --copy_all_images_to_assets
```

Copies all images, even those not referenced in text.

## Troubleshooting

### Problem: "No items found"

**Cause**: URL might be incorrect or site structure changed

**Solution**:
1. Check URL in browser
2. Ensure it's a documentation index page
3. Try parent URL (remove version number)

---

### Problem: TUI doesn't display correctly

**Cause**: Terminal too small or doesn't support curses

**Solution**:
1. Resize terminal to at least 80x24
2. Or use `--no-tui` flag:
   ```bash
   python 04_pipeline.py [URL] --no-tui
   ```

---

### Problem: Conversion fails for specific item

**Cause**: Network issue, malformed ZIP, or conversion error

**Solution**:
1. Check error message
2. Try converting that item alone:
   ```bash
   python 03_fetch_extract_convert.py [SPECIFIC_ZIP_URL]
   ```
3. Report issue with error details

---

### Problem: Out of disk space

**Cause**: Large documentation sets use significant space

**Solution**:
1. Check disk space: `df -h`
2. Clean temporary directories:
   ```bash
   rm -rf tmp_downloads/ tmp_extracts/
   ```
3. Process fewer items at once

---

### Problem: Downloads are slow

**Cause**: Network bandwidth or server speed

**Solution**:
1. Be patient (large ZIPs take time)
2. Process during off-peak hours
3. Use `--force` only when necessary (uses cache by default)

## Tips for Beginners

### Tip 1: Start Small
Try converting just 1-2 items first to get familiar with the process.

### Tip 2: Use Search
The search function (`/`) is your friend. It's faster than scrolling.

### Tip 3: Check Selection Before Confirming
Press `/` then `Esc` to clear any filters and see your full selection.

### Tip 4: Cache is Your Friend
Downloaded ZIPs are cached. Rerunning is fast if you don't use `--force`.

### Tip 5: Read the Docs
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Keep handy
- [TUI_GUIDE.md](TUI_GUIDE.md) - Detailed interface guide
- [EXAMPLES.md](EXAMPLES.md) - More examples

## Next Steps

### Level 2: Intermediate Usage

Once comfortable with basics:
1. Read [TUI_GUIDE.md](TUI_GUIDE.md) for advanced navigation
2. Try bulk selection techniques
3. Experiment with different filters

### Level 3: Advanced Usage

When you're ready:
1. Read [EXAMPLES.md](EXAMPLES.md) for real-world scenarios
2. Set up automation (cron jobs, scripts)
3. Integrate with your documentation workflow

### Level 4: Expert Mode

For power users:
1. Review [WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md)
2. Use [Workflow B or C](README.md) for special cases
3. Contribute improvements to the project

## Quick Reference Card

Print or bookmark this:

| Action | Keys |
|--------|------|
| **Navigation** | |
| Move up/down | ↑ / ↓ |
| Page up/down | PgUp / PgDn |
| First/last item | Home / End |
| **Selection** | |
| Toggle current | Space |
| Select all filtered | a |
| Deselect all filtered | n |
| Select all | A (Shift+A) |
| Deselect all | N (Shift+N) |
| **Search** | |
| Enter search | / |
| Clear filter | Esc |
| Apply filter | Enter |
| **Control** | |
| Start processing | Enter |
| Quit | q |

## Getting Help

If you're stuck:

1. **Check documentation**:
   - This guide for basics
   - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for commands
   - [TUI_GUIDE.md](TUI_GUIDE.md) for TUI details
   - [EXAMPLES.md](EXAMPLES.md) for use cases

2. **Review error messages**:
   - Most errors explain what went wrong
   - Check logs in `tmp_extracts/` if needed

3. **Try simpler approach**:
   - Use `--no-tui` for automation
   - Use `03_fetch_extract_convert.py` for single items
   - Use Workflow C for local files

## Summary

You've learned:
- ✅ How to install and run the pipeline
- ✅ How to navigate the TUI
- ✅ How to select items (individual, bulk, filtered)
- ✅ How to find your output
- ✅ Basic troubleshooting
- ✅ Where to find more help

**Ready to convert documentation? Start with:**

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

Happy converting! 🚀


