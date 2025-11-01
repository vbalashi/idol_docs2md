# Workflow Diagrams

Visual representation of the three conversion workflows.

## Workflow A: Batch Pipeline (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                    04_pipeline.py                               │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 1. SCAN DOCUMENTATION SITE                             │   │
│  │    • Fetch HTML from URL                               │   │
│  │    • Parse tables and links                            │   │
│  │    • Extract ZIP URLs                                  │   │
│  │    • Categorize items                                  │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 2. INTERACTIVE TUI SELECTION                           │   │
│  │    • Display all found items                           │   │
│  │    • Search/filter with '/'                            │   │
│  │    • Multi-select with Space/a/n                       │   │
│  │    • Confirm with Enter                                │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 3. BATCH PROCESSING                                    │   │
│  │    For each selected item:                             │   │
│  │      ┌──────────────────────────────┐                  │   │
│  │      │ Call 03_fetch_extract_       │                  │   │
│  │      │      convert.py               │                  │   │
│  │      │   • Download ZIP             │                  │   │
│  │      │   • Extract                  │                  │   │
│  │      │   • Convert to MD            │                  │   │
│  │      │   • Copy to output           │                  │   │
│  │      └──────────────────────────────┘                  │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 4. SUMMARY REPORT                                      │   │
│  │    • Total processed                                   │   │
│  │    • Successes / Failures                              │   │
│  │    • Output location                                   │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

INPUT:   Documentation index URL
OUTPUT:  Multiple .md files + assets directories
```

## Workflow B: Single Document (Quick)

```
┌─────────────────────────────────────────────────────────────────┐
│              03_fetch_extract_convert.py                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 1. DOWNLOAD                                            │   │
│  │    • Check cache (tmp_downloads/)                      │   │
│  │    • Download ZIP if needed                            │   │
│  │    • Show progress bar                                 │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 2. EXTRACT                                             │   │
│  │    • Unzip to tmp_extracts/                            │   │
│  │    • Find base folder (Content/Data)                   │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 3. CONVERT                                             │   │
│  │    • Parse TOC structure                               │   │
│  │    • Convert HTML → Markdown (parallel)                │   │
│  │    • Copy images → assets                              │   │
│  │    • Generate concatenated MD                          │   │
│  │    • Add online header links                           │   │
│  └─────────────┬──────────────────────────────────────────┘   │
│                ▼                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 4. OUTPUT                                              │   │
│  │    • Copy MD to output_md_dir/                         │   │
│  │    • Copy assets directory                             │   │
│  │    • Verify image coverage                             │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

INPUT:   Single ZIP URL
OUTPUT:  One .md file + one assets directory
```

## Workflow C: Step-by-Step (Advanced)

```
┌────────────────────┐
│ 01_extract_zips.py │
│                    │
│  • Extract ZIPs    │
│  • Interactive     │
│    selection       │
└─────────┬──────────┘
          │
          ▼
┌─────────────────────┐
│ 02_convert_to_md.py │
│                     │
│  • HTML → Markdown  │
│  • Parse TOC        │
│  • Copy images      │
│  • Concatenate      │
└─────────┬───────────┘
          │
          ▼
┌──────────────────────────┐
│ 03_generate_documents.py │
│                          │
│  • MD → EPUB/HTML/PDF    │
│  • Use pandoc            │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────┐
│ 04_copy_md_files.py  │
│                      │
│  • Copy final MDs    │
└──────────────────────┘

INPUT:   Local ZIP files or directories
OUTPUT:  MD files + EPUB/HTML/PDF (optional)
```

## Comparison Table

| Feature | Workflow A<br>(Pipeline) | Workflow B<br>(Single) | Workflow C<br>(Step-by-Step) |
|---------|-------------------------|------------------------|------------------------------|
| **Multiple ZIPs** | ✅ Yes (batch) | ❌ No (one at a time) | ⚠️ Manual iteration |
| **Interactive Selection** | ✅ TUI with search | ❌ No | ⚠️ Per-script |
| **Online ZIPs** | ✅ Yes | ✅ Yes | ❌ No (local only) |
| **Local ZIPs** | ❌ No | ❌ No | ✅ Yes |
| **Auto-discovery** | ✅ Scans site | ❌ Manual URL | ❌ Manual paths |
| **Output Format** | 📝 Markdown | 📝 Markdown | 📝 MD + 📚 EPUB/HTML/PDF |
| **Progress Tracking** | ✅ Per-item + summary | ✅ Single item | ⚠️ Per-script |
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Flexibility** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Decision Tree

```
Need to convert documentation?
    │
    ├─→ Multiple documents from online site?
    │       │
    │       └─→ YES: Use Workflow A (04_pipeline.py)
    │              • Best for: Downloading multiple docs
    │              • TUI makes selection easy
    │              • Batch processing saves time
    │
    ├─→ Single document from online URL?
    │       │
    │       └─→ YES: Use Workflow B (03_fetch_extract_convert.py)
    │              • Best for: Quick single conversions
    │              • Simpler than pipeline
    │              • Good for automation/scripting
    │
    └─→ Local ZIPs or need EPUB/PDF output?
            │
            └─→ YES: Use Workflow C (01, 02, 03, 04 scripts)
                   • Best for: Advanced use cases
                   • Full control over each step
                   • Supports additional output formats
```

## Data Flow

### Pipeline Flow (Workflow A)

```
Documentation Index Page
         │
         │ [Scan]
         ▼
  ┌─────────────┐
  │ DocItem[]   │  (List of available docs)
  └──────┬──────┘
         │ [TUI Selection]
         ▼
  ┌─────────────┐
  │ Selected[]  │  (User-chosen items)
  └──────┬──────┘
         │ [For Each]
         ▼
  ┌──────────────┐
  │ Download ZIP │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Extract      │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Convert      │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │ Output:          │
  │  • DocName.md    │
  │  • DocName_assets│
  └──────────────────┘
```

### Single Document Flow (Workflow B)

```
ZIP URL → Download → Extract → Convert → Output
   │          │          │         │        │
   │          │          │         │        ├─ .md file
   │          │          │         │        └─ _assets/
   │          │          │         │
   │          │          │         └─ HTML → Markdown
   │          │          │           Copy images
   │          │          │           Generate TOC
   │          │          │
   │          │          └─ Find base folder
   │          │             (Content + Data/Tocs)
   │          │
   │          └─ Unzip to temp directory
   │
   └─ Cache in tmp_downloads/
```

### Step-by-Step Flow (Workflow C)

```
ZIP Files
    │
    │ [01_extract_zips.py]
    ▼
Extracted HTML
    │
    │ [02_convert_to_md.py]
    ▼
Markdown Files
    │
    │ [03_generate_documents.py]
    ▼
EPUB/HTML/PDF
    │
    │ [04_copy_md_files.py]
    ▼
Final Output Directory
```

## Processing Details

### How 04_pipeline.py Works Internally

```
1. scan_documentation_site(url)
   ├─ Fetch HTML
   ├─ Parse with BeautifulSoup
   ├─ Find tables with documentation
   ├─ Extract ZIP links
   └─ Return List[DocItem]

2. DocSelectorTUI(items)
   ├─ Initialize curses
   ├─ Display items
   ├─ Handle keyboard input
   │  ├─ Navigation (↑↓, PgUp/PgDn)
   │  ├─ Selection (Space, a, n, A, N)
   │  └─ Search (/, Esc, type)
   └─ Return selected items

3. For each selected item:
   run_conversion(item.zip_url, args)
   ├─ Call 03_fetch_extract_convert.py
   │  as subprocess
   ├─ Wait for completion
   └─ Track success/failure

4. Print summary
   ├─ Total selected
   ├─ Successes
   ├─ Failures (with names)
   └─ Output directory
```

## Directory Structure During Processing

```
Project Root
├── 04_pipeline.py              [Entry point]
├── 03_fetch_extract_convert.py [Called by pipeline]
├── 02_convert_to_md.py         [Called by 03]
│
├── tmp_downloads/              [Cached ZIPs]
│   ├── Content_25.4.zip
│   ├── Community_25.4.zip
│   └── ...
│
├── tmp_extracts/               [Temporary extraction]
│   ├── Content_25.4/
│   │   ├── Content/
│   │   ├── Data/
│   │   └── md/
│   │       ├── __concat.md     [Intermediate]
│   │       └── Content_25.4_assets/
│   └── ...
│
└── md/                         [Final output]
    ├── Content_25.4_Documentation.md
    ├── Content_25.4_Documentation_assets/
    ├── Community_25.4_Documentation.md
    ├── Community_25.4_Documentation_assets/
    └── ...
```

## Tips for Choosing a Workflow

### Use Workflow A when:
- ✅ Converting multiple documents from OpenText/MicroFocus site
- ✅ You don't know all the exact ZIP URLs
- ✅ You want to select specific items visually
- ✅ You want a single command to do everything

### Use Workflow B when:
- ✅ Converting a single document
- ✅ You have the exact ZIP URL
- ✅ You want the simplest command
- ✅ You're scripting/automating

### Use Workflow C when:
- ✅ Working with local ZIP files
- ✅ Need EPUB, HTML, or PDF output
- ✅ Want maximum control over each step
- ✅ Troubleshooting conversion issues
- ✅ Custom processing requirements

## Performance Characteristics

| Aspect | Workflow A | Workflow B | Workflow C |
|--------|-----------|-----------|-----------|
| **Setup Time** | Low (auto-discover) | Very Low (direct URL) | Medium (manual paths) |
| **Processing Speed** | Medium (sequential items) | Fast (single item) | Slow (manual steps) |
| **Parallelism** | ✅ Within each item | ✅ Yes | ⚠️ Manual |
| **Memory Usage** | Medium | Low | Low-Medium |
| **Disk I/O** | High (batch) | Medium | Medium |
| **Network** | Sequential downloads | Single download | No network |

---

For detailed usage instructions, see:
- [README.md](README.md) - Project overview
- [PIPELINE_README.md](PIPELINE_README.md) - Pipeline documentation
- [EXAMPLES.md](EXAMPLES.md) - Real-world examples
- [TUI_GUIDE.md](TUI_GUIDE.md) - TUI interface guide





