# MadCap Flare→Markdown

## Setup
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`

## Quick Start (Recommended)
Use only `04_pipeline.py` for normal work.

1. Run interactive mode (project/version picker + document selector):
   `python 04_pipeline.py`
2. Or run directly by project/version:
   `python 04_pipeline.py --project knowledge-discovery --version 25.4`
3. Or run from an explicit docs URL:
   `python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/`

## What `04_pipeline.py` does
- Finds available documentation ZIPs
- Lets you select what to process (unless `--no-tui`)
- Downloads ZIPs to `tmp_downloads/`
- Extracts to `tmp_extracts/`
- Converts to Markdown and fixes links/anchors
- Writes final outputs to `md/`

## Useful Options
- `--no-tui`: process all found items without UI
- `--force`: re-download ZIPs even if cached
- `--output_md_dir <path>`: change output folder
- `--refresh-catalog --refresh-items`: refresh cached site metadata

## Notes
- `03_fetch_extract_convert.py` is a lower-level script used by `04_pipeline.py`.
- Most users should not run other numbered scripts directly.
