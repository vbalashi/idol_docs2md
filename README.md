# MadCap Flare to Markdown Converter

This project contains a set of Python scripts designed to convert MadCap Flare documentation (in ZIP format) to Markdown and other document formats (EPUB, HTML, PDF).

## Prerequisites

- Python 3.x
- Required Python packages (install via `pip`):
  - beautifulsoup4
  - bleach
  - markdownify
  - tqdm
  - requests
- System tools for document generation:
  - pandoc
  - For PDF output, either:
    - A LaTeX engine (recommended): `xelatex`/`lualatex`/`pdflatex` (via TeX Live), or
    - `wkhtmltopdf` (alternative HTML→PDF engine)

## Environment Setup

Use the provided helper script to create/update a virtual environment, install dependencies, and activate the environment.

```bash
# from the project root
source scripts/activate_env.sh
```

What the script does:
- Creates `.venv` if it does not exist (prefers `uv venv` if available, otherwise uses `python3 -m venv`).
- Ensures `pip` is available and upgrades `pip/setuptools/wheel`.
- Installs `requirements.txt` (prefers `uv pip install`, otherwise uses `pip`).
- Activates the environment so subsequent `python`/`pip` refer to the project venv.

If you prefer manual steps instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
```

## Scripts Overview

The project provides three workflows:

### Workflow A: Batch Pipeline with TUI (Recommended for Multiple Documents)

**`04_pipeline.py`** - Scan documentation site, interactively select items, and batch process:

```bash
python 04_pipeline.py <documentation_index_url> [OPTIONS]
```

**Features:**
- 🔍 Automatically discovers all available documentation ZIPs from a documentation index page
- 🖥️ Interactive TUI (Terminal User Interface) for selecting items
- 🔎 Vi-like search/filter: press `/` to search, filter results instantly
- ⚡ Batch processing: convert multiple documentation packages in one run
- 📊 Progress tracking and summary reports

**Quick Example:**
```bash
# Scan Knowledge Discovery 25.4 documentation
python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/

# TUI will launch - use arrow keys to navigate, Space to select, Enter to confirm
# Or use search: press '/', type "connector", press 'a' to select all connectors
```

**TUI Controls:**
- `↑/↓` - Navigate items
- `Space` - Toggle selection
- `/` - Search/filter
- `a` - Select all filtered items
- `n` - Deselect all filtered items
- `Enter` - Start processing
- `q` - Quit

**Command Options:**
- `--no-tui`: Skip TUI and auto-process all found items
- `--output_md_dir`: Custom output directory (default: `./md`)
- `--force`: Force re-download existing ZIPs
- `--max_workers`: Number of parallel conversion threads (default: 10)
- `--copy_all_images_to_assets`: Include all images, even unreferenced ones

**Documentation:**
- Full guide: [PIPELINE_README.md](PIPELINE_README.md)
- TUI interface guide: [TUI_GUIDE.md](TUI_GUIDE.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Quick reference: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

---

### Workflow B: All-in-One Single Document (Recommended for Individual ZIPs)

**`03_fetch_extract_convert.py`** - Download, extract, and convert in one step:

```bash
python 03_fetch_extract_convert.py <zip_url> \
  [--temp_download_dir <path>] \
  [--temp_extract_dir <path>] \
  [--output_md_dir <path>] \
  [--max_workers <num>] \
  [--force] \
  [--copy_all_images_to_assets]
```

**Arguments:**
- `zip_url`: URL to the online documentation ZIP file
- `--temp_download_dir`: Directory for downloaded ZIPs (default: `./tmp_downloads`)
- `--temp_extract_dir`: Directory to extract ZIPs (default: `./tmp_extracts`)
- `--output_md_dir`: Directory for final Markdown and assets (default: `./md`)
- `--max_workers`: Maximum worker threads for conversion (default: 10)
- `--force`: Force re-download even if ZIP exists
- `--copy_all_images_to_assets`: Include all images, even unreferenced ones

**Example:**
```bash
python 03_fetch_extract_convert.py \
  https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/Content_25.4_Documentation.zip \
  --max_workers 10
```

**Output:**
- Clean, formatted terminal output with progress bars and timing
- Single Markdown file: `md/<DocName>.md`
- Assets directory: `md/<DocName>_assets/`
- Processing logs in the extraction directory

**Terminal Output Features:**
- Organized sections: DOWNLOAD → EXTRACT → CONVERT → OUTPUT
- Real-time progress bars for image copying and HTML conversion
- Processing time tracking (per-stage and total)
- Color-coded output (green for success, yellow for warnings)
- Short relative paths instead of full absolute paths
- Image asset statistics and warnings for unreferenced images
- Unicode icons for better visual feedback (✓, ⚙, 📄, ⚠)

---

### Workflow C: Step-by-Step (For Local ZIPs or Custom Processing)

Use these scripts in sequence for more control:

#### 1. Extract ZIPs (`01_extract_zips.py`)
Extracts content from MadCap Flare ZIP files, focusing on the 'Content' and 'Data' directories.

```bash
python 01_extract_zips.py <zip_or_dir> [<zip_or_dir> ...] [-o <output_directory>]
```
- `zip_or_dir`: One or more paths; each can be a `.zip` file or a directory containing ZIPs
- `output_directory`: Optional. Where to extract the files. If omitted, you will be prompted (default: `./mfdocs`).

Interactive behavior:
- When directories are provided, the script lists discovered ZIPs and allows you to select which ones to process (e.g., `1,3-5`). Press Enter to select all, or `0` to skip directory ZIPs.

#### 2. Convert to Markdown (`02_convert_to_md.py`)
Converts the extracted HTML files to Markdown format while preserving the document structure.

```bash
python 02_convert_to_md.py <input_folder> [--max_workers <num>] [--image_extensions <ext1> <ext2> ...]
```
- `input_folder`: Directory containing the extracted documentation
- `max_workers`: Optional. Maximum number of worker threads (default: 10)
- `image_extensions`: Optional. List of image extensions to process (default: .jpg .jpeg .png .gif .bmp)

#### 3. Generate Documents (`03_generate_documents.py`)
Converts the Markdown files to EPUB, HTML, and/or PDF formats using pandoc.

```bash
python 03_generate_documents.py <input_folder> \
  [--output_folder <path>] \
  [--formats <format1> <format2> ...] \
  [--pdf_engine {auto,xelatex,lualatex,pdflatex,wkhtmltopdf}]
```
- `input_folder`: Base folder containing the converted Markdown files
- `output_folder`: Optional. Where to save the generated files
- `formats`: Optional. Output formats to generate (choices: epub, html, pdf; default: all)
- `pdf_engine`: Optional. PDF engine to use. `auto` picks the first available engine; default is `xelatex`.

#### 4. Copy MD Files (`04_copy_md_files.py`)
Copies all concatenated Markdown files (starting with '__') to a specified destination.

```bash
python 04_copy_md_files.py <source_folder> [--destination_folder <path>]
```
- `source_folder`: Directory to search for Markdown files
- `destination_folder`: Optional. Where to copy the files (defaults to current directory)

## Features

- **🔄 Batch Pipeline**: Scan documentation sites and process multiple packages at once
- **🖥️ Interactive TUI**: Vi-like interface with search/filter for easy selection
- **📦 All-in-One Conversion**: Download, extract, and convert in a single command
- **🎨 Clean Terminal Output**: Formatted output with progress bars, timing, and color coding
- **⚡ Concurrent Processing**: Multi-threaded conversion for better performance
- **📑 Document Hierarchy**: Maintains document structure and generates table of contents
- **🖼️ Asset Management**: Automatic image handling and reference tracking
- **🔗 Link Preservation**: Maintains internal and external links with online header links
- **📝 Comprehensive Logging**: Detailed logs for troubleshooting
- **🔧 Flexible Workflows**: Choose between batch pipeline, single document, or step-by-step processing
- **🏷️ Metadata Extraction**: Automatic extraction from folder and file names

## Output Structure

### Workflow A Output (Batch Pipeline)
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
├── Category_25.4_Documentation.md
├── Category_25.4_Documentation_assets/
│   └── ...
└── ...
```

### Workflow B Output (Single Document)
```
md/
├── <DocName>.md                    # Single concatenated Markdown file
└── <DocName>_assets/               # All referenced images and assets
    ├── image1.png
    ├── image2.gif
    └── ...
```

### Workflow C Output (Step-by-Step)
```
mfdocs/<DocSet>/
├── Content/                        # Original extracted HTML
├── Data/Tocs/                      # TOC structure files
├── md/
│   ├── __<DocName>.md             # Concatenated Markdown
│   ├── __toc.txt                  # Table of contents
│   ├── __hierarchy.txt            # Document structure
│   ├── __anchors.json             # Internal anchor map
│   ├── Content/                   # Individual MD files
│   ├── images/                    # All source images
│   ├── assets/                    # Referenced assets
│   └── generate_documents.log     # Processing log
├── <DocName>.epub                 # Generated EPUB (if created)
├── <DocName>.html                 # Generated HTML (if created)
└── <DocName>.pdf                  # Generated PDF (if created)
```

## Error Handling

All scripts include error logging:
- `extract_zip_errors.log` for ZIP extraction issues
- `generate_documents.log` for document generation errors

Additionally, `03_generate_documents.py` exits with a non-zero status code if required
system tools are missing or if any conversion fails, and logs a per-format summary
of successes/failures.

## Notes

- The scripts assume a specific MadCap Flare documentation structure
- Large documentation sets may require significant processing time
- Pandoc must be installed separately for document generation
- Some complex HTML elements may require manual review after conversion 

## Installing System Dependencies (Arch Linux)

Install pandoc and LaTeX (recommended for high-quality PDF via XeLaTeX):

```bash
sudo pacman -S --needed pandoc texlive-bin texlive-latex texlive-latexextra texlive-fontsextra
```

Recommended fonts (for better Unicode coverage):

```bash
sudo pacman -S --needed noto-fonts noto-fonts-cjk noto-fonts-emoji
```

Verify tools:

```bash
pandoc --version
xelatex --version
```

Alternative PDF engine (wkhtmltopdf): not always available in official repos. Use AUR:

- With an AUR helper (e.g., `yay` or `paru`):

```bash
yay -S wkhtmltopdf        # or: yay -S wkhtmltopdf-static
# or
paru -S wkhtmltopdf       # or: paru -S wkhtmltopdf-static
```

- Without an AUR helper:

```bash
git clone https://aur.archlinux.org/wkhtmltopdf.git
cd wkhtmltopdf
makepkg -si
```

Then run the generator with `--pdf_engine wkhtmltopdf` or simply use `--pdf_engine auto`.