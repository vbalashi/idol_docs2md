# MadCap Flare→Markdown

## Setup
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`

## Usage
- Convert a local ZIP: `python 03_fetch_extract_convert.py <zip_path>`
- Run the full picker pipeline: `python 04_pipeline.py`

## Notes
- Outputs land in `md/`
- Large docs and all legacy notes now live under `archive/`
