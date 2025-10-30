# Pipeline Examples and Use Cases

This document provides practical examples for using the IDOL documentation pipeline.

## Table of Contents

1. [Basic Workflows](#basic-workflows)
2. [Advanced Selection Techniques](#advanced-selection-techniques)
3. [Automation Scenarios](#automation-scenarios)
4. [Real-World Use Cases](#real-world-use-cases)

## Basic Workflows

### Workflow 1: Convert All Connectors

**Goal**: Download and convert all connector documentation for version 25.4

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

**In TUI**:
1. Press `/` to enter search mode
2. Type `connector`
3. Press `Enter` to apply filter
4. Press `a` to select all filtered items
5. Press `Enter` to start processing

**Result**: All connector documentation converted to individual MD files.

---

### Workflow 2: Select Core Components Only

**Goal**: Get Content, Community, and Category server documentation

```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

**In TUI**:
1. Press `/`, type `content`, press `Enter`
2. Press `Space` on "Content" item to select
3. Press `/`, type `community`, press `Enter`
4. Press `Space` on "Community" item to select
5. Press `/`, type `category`, press `Enter`
6. Press `Space` on "Category" item to select
7. Press `/`, press `Esc` to clear filter and see all selections
8. Press `Enter` to start processing

---

### Workflow 3: Compare Two Versions

**Goal**: Download the same documentation for versions 25.3 and 25.4

**For version 25.4**:
```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --output_md_dir ./docs_v25.4
```

**For version 25.3**:
```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.3/ \
  --output_md_dir ./docs_v25.3
```

Then use `diff` or other comparison tools to see changes between versions.

---

## Advanced Selection Techniques

### Technique 1: Progressive Filtering

Build complex selections by applying multiple filters:

```
1. Start with broad selection
2. Press 'a' to select all
3. Apply specific filter: /database connector
4. Press 'n' to deselect filtered items
5. Clear filter with / + Esc
6. Review final selection
7. Press Enter
```

This technique lets you say "select everything EXCEPT database connectors".

---

### Technique 2: Category-Based Selection

Use category names from the documentation site:

- `/Text` - Find text processing components
- `/Connectors` - Find all connectors
- `/Rich Media` - Find media processing components
- `/Administration` - Find admin tools

---

### Technique 3: Keyboard Efficiency

Fast navigation without leaving home row:

```
/search term<Enter>  - Quick filter
a                    - Select all filtered
/<Esc>              - Clear and return
<Enter>             - Confirm and go
```

---

## Automation Scenarios

### Scenario 1: Nightly Documentation Updates

Create a script to auto-download the latest documentation:

```bash
#!/bin/bash
# update_docs.sh

DATE=$(date +%Y%m%d)
OUTPUT_DIR="./idol_docs_$DATE"

python 04_pipeline.py \
  https://www.microfocus.com/documentation/idol/knowledge-discovery-latest/ \
  --no-tui \
  --output_md_dir "$OUTPUT_DIR" \
  --force

echo "Documentation updated in $OUTPUT_DIR"
```

Run with cron:
```cron
0 2 * * * /path/to/update_docs.sh >> /var/log/idol_docs.log 2>&1
```

---

### Scenario 2: CI/CD Integration

Use in continuous integration to keep documentation in sync:

```yaml
# .github/workflows/update-docs.yml
name: Update Documentation

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Download and convert docs
        run: |
          python 04_pipeline.py \
            https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
            --no-tui \
            --output_md_dir ./docs
      
      - name: Commit changes
        run: |
          git config user.name "Documentation Bot"
          git config user.email "bot@example.com"
          git add docs/
          git commit -m "Update documentation $(date +%Y-%m-%d)" || exit 0
          git push
```

---

### Scenario 3: Selective Batch Processing

Process only specific categories programmatically:

```python
#!/usr/bin/env python3
# selective_batch.py

import subprocess
import sys

# Define which categories to process
WANTED_ITEMS = [
    "Content",
    "Community", 
    "Category",
    "View",
]

BASE_URL = "https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/"

# Import scanning function
from pathlib import Path
import importlib.util

pipeline_path = Path(__file__).parent / "04_pipeline.py"
spec = importlib.util.spec_from_file_location("pipeline", str(pipeline_path))
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

# Scan site
items = pipeline.scan_documentation_site(BASE_URL)

# Filter to wanted items
selected = [item for item in items if any(wanted in item.name for wanted in WANTED_ITEMS)]

print(f"Processing {len(selected)} items...")

# Process each
for item in selected:
    print(f"\n{'='*60}")
    print(f"Processing: {item.name}")
    print(f"{'='*60}")
    
    cmd = [
        sys.executable,
        str(pipeline_path.parent / "03_fetch_extract_convert.py"),
        item.zip_url,
    ]
    
    subprocess.run(cmd)
```

---

## Real-World Use Cases

### Use Case 1: Technical Writer Documentation Set

**Scenario**: A technical writer needs to reference all IDOL connectors for creating integration guides.

**Solution**:
```bash
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --output_md_dir ~/TechDocs/IDOL_Connectors
```

In TUI, filter by "Connector" and select all. Result: All connector docs in Markdown format, easy to search and reference.

---

### Use Case 2: Migration Planning

**Scenario**: Planning migration from IDOL 24.4 to 25.4, need to compare API changes.

**Solution**:
```bash
# Download both versions
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-24.4/ \
  --output_md_dir ./idol_24.4 \
  --no-tui

python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --output_md_dir ./idol_25.4 \
  --no-tui

# Use diff tools
diff -r idol_24.4/ idol_25.4/ > changes.txt
```

Or use tools like Beyond Compare, Meld, or VS Code's diff feature.

---

### Use Case 3: Offline Documentation Archive

**Scenario**: Need offline access to documentation in restricted/airgapped environment.

**Solution**:
```bash
# Download everything
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --no-tui \
  --copy_all_images_to_assets \
  --output_md_dir ~/OfflineDocs/IDOL_25.4

# Package for transfer
tar -czf idol_docs_25.4.tar.gz ~/OfflineDocs/IDOL_25.4

# Transfer to offline system and extract
# View with any Markdown reader (VS Code, Obsidian, etc.)
```

---

### Use Case 4: Custom Documentation Portal

**Scenario**: Build internal documentation portal with search capabilities.

**Solution**:
1. Download all documentation with pipeline
2. Use static site generator (MkDocs, Hugo, Docusaurus)
3. Import converted Markdown files
4. Deploy to internal server

```bash
# Step 1: Download docs
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --no-tui \
  --output_md_dir ./docs_source

# Step 2: Setup MkDocs
pip install mkdocs mkdocs-material
mkdocs new idol-docs
cd idol-docs

# Step 3: Copy converted docs
cp -r ../docs_source/*.md docs/
cp -r ../docs_source/*_assets docs/

# Step 4: Build and serve
mkdocs build
mkdocs serve
```

---

### Use Case 5: AI/LLM Training Data

**Scenario**: Prepare documentation for training or fine-tuning a language model on IDOL knowledge.

**Solution**:
```bash
# Download all documentation in clean Markdown format
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ \
  --no-tui \
  --output_md_dir ./training_data

# Result: Clean, structured Markdown perfect for LLM ingestion
# Each file is a self-contained documentation unit
# Can be processed further for chunking, embedding, etc.
```

---

## Tips and Tricks

### Tip 1: Quick Selection Workflow

Fastest way to select specific items:
```
/keyword<Enter> → a → /<Esc> → <Enter>
```
(Filter, select all filtered, clear filter, confirm)

---

### Tip 2: Preview Before Processing

Want to see what you've selected without starting?
- Select items in TUI
- Press `q` to quit without processing
- The script will show "No items selected" but you've seen your selection

Then run again and make actual selections.

---

### Tip 3: Partial Processing Recovery

If processing fails midway:
- Downloaded ZIPs are cached in `tmp_downloads/`
- Rerun without `--force` to skip re-downloading
- Only failed items need reprocessing

---

### Tip 4: Disk Space Management

```bash
# Clean temp directories after successful processing
rm -rf tmp_downloads/ tmp_extracts/

# Or keep downloads for faster reruns
rm -rf tmp_extracts/  # Only clean extracts
```

---

## Troubleshooting Examples

### Problem: TUI shows garbled characters

**Solution**: Ensure terminal supports UTF-8:
```bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
python 04_pipeline.py [URL]
```

---

### Problem: No items found when scanning

**Solution**: Test URL manually first:
```bash
curl https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/ | grep -i "\.zip"
```

If ZIPs are there but not detected, file an issue with the URL.

---

### Problem: Conversion fails for specific item

**Solution**: Process individually for detailed error:
```bash
# Get ZIP URL from failed item
python 03_fetch_extract_convert.py [SPECIFIC_ZIP_URL]
```

This shows detailed conversion logs.

---

## Best Practices

1. **Start Small**: Test with TUI and a few items before batch processing
2. **Use Filters**: Leverage search to quickly find what you need
3. **Cache Downloads**: Don't use `--force` unless necessary
4. **Organize Output**: Use descriptive `--output_md_dir` paths
5. **Version Control**: Keep different versions in separate directories
6. **Backup**: Archive downloaded docs before major updates

---

## Next Steps

- See [PIPELINE_README.md](PIPELINE_README.md) for detailed documentation
- Check [README.md](README.md) for overall project information
- Report issues or request features on GitHub


