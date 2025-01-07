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
  - pandoc (system requirement for document generation)

## Scripts Overview

The conversion process is split into four main scripts that should be run in sequence:

### 1. Extract ZIPs (`01_extract_zips.py`)
Extracts content from MadCap Flare ZIP files, focusing on the 'Content' and 'Data' directories.

```bash
python 01_extract_zips.py <input_directory> [-o <output_directory>]
```
- `input_directory`: Directory containing the ZIP files
- `output_directory`: Optional. Where to extract the files (defaults to ./mfdocs)

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
python 03_generate_documents.py <input_folder> [--output_folder <path>] [--formats <format1> <format2> ...]
```
- `input_folder`: Base folder containing the converted Markdown files
- `output_folder`: Optional. Where to save the generated files
- `formats`: Optional. Output formats to generate (choices: epub, html, pdf; default: all)

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

## Notes

- The scripts assume a specific MadCap Flare documentation structure
- Large documentation sets may require significant processing time
- Pandoc must be installed separately for document generation
- Some complex HTML elements may require manual review after conversion 