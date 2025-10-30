# MadCap Flare to Markdown Converter

This project contains a set of Python scripts designed to convert MadCap Flare documentation (in ZIP format) to Markdown and other document formats (EPUB, HTML, PDF).

## Prerequisites

- Python 3.x
- Required Python packages (install via `pip`):
  - beautifulsoup4
  - bleach
  - js2py
  - markdownify
  - tqdm
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

The conversion process is split into four main scripts that should be run in sequence:

### 1. Extract ZIPs (`01_extract_zips.py`)
Extracts content from MadCap Flare ZIP files, focusing on the 'Content' and 'Data' directories.

```bash
python 01_extract_zips.py <zip_or_dir> [<zip_or_dir> ...] [-o <output_directory>]
```
- `zip_or_dir`: One or more paths; each can be a `.zip` file or a directory containing ZIPs
- `output_directory`: Optional. Where to extract the files. If omitted, you will be prompted (default: `./mfdocs`).

Interactive behavior:
- When directories are provided, the script lists discovered ZIPs and allows you to select which ones to process (e.g., `1,3-5`). Press Enter to select all, or `0` to skip directory ZIPs.

### 2. Convert to Markdown (`02_convert_to_md.py`)
Converts the extracted HTML files to Markdown format while preserving the document structure.

```bash
python 02_convert_to_md.py <input_folder> [--max_workers <num>] [--image_extensions <ext1> <ext2> ...]
```
- `input_folder`: Directory containing the extracted documentation
- `max_workers`: Optional. Maximum number of worker threads (default: 10)
- `image_extensions`: Optional. List of image extensions to process (default: .jpg .jpeg .png .gif .bmp)

### 3. Generate Documents (`03_generate_documents.py`)
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

### 4. Copy MD Files (`04_copy_md_files.py`)
Copies all concatenated Markdown files (starting with '__') to a specified destination.

```bash
python 04_copy_md_files.py <source_folder> [--destination_folder <path>]
```
- `source_folder`: Directory to search for Markdown files
- `destination_folder`: Optional. Where to copy the files (defaults to current directory)

## Features

- Maintains document hierarchy and structure
- Preserves images and internal links
- Generates table of contents
- Supports concurrent processing for better performance
- Handles multiple documentation sets in parallel
- Comprehensive error logging
- Automatic metadata extraction from folder names

## Output Structure

Each processed documentation set will have:
- A `md` folder containing:
  - Individual Markdown files
  - Images folder
  - `__toc.txt` (table of contents)
  - `__hierarchy.txt` (document structure)
  - Concatenated Markdown file (`__<DocName>.md`)
- Generated documents (EPUB/HTML/PDF) in the specified output location

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