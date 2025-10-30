import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from tqdm import tqdm

# Reuse processing functions from existing converter
import importlib.util
import logging

# Dynamically load functions from '02_convert_to_md.py' (filename starts with a digit)
_converter_path = Path(__file__).with_name("02_convert_to_md.py")
_spec = importlib.util.spec_from_file_location("converter02", str(_converter_path))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load converter module from {_converter_path}")
_converter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_converter)
process_base_folder = _converter.process_base_folder

# Reduce console noise: keep detailed logs in file via converter's FileHandler
logging.root.handlers.clear()
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
logging.getLogger().addHandler(console_handler)
logging.getLogger().setLevel(logging.WARNING)
try:
    # Ensure converter logger does not propagate to root console
    _converter.logger.propagate = False
except Exception:
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download a documentation ZIP, extract, convert to Markdown, and build a single MD with online header links."
    )
    parser.add_argument("zip_url", help="URL to the online documentation ZIP file")
    parser.add_argument(
        "--temp_download_dir",
        type=str,
        default=str(Path.cwd() / "tmp_downloads"),
        help="Directory to store downloaded ZIPs (default: ./tmp_downloads)",
    )
    parser.add_argument(
        "--temp_extract_dir",
        type=str,
        default=str(Path.cwd() / "tmp_extracts"),
        help="Directory to extract ZIPs (default: ./tmp_extracts)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download of the ZIP even if it already exists",
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=10,
        help="Maximum worker threads for conversion (default: 10)",
    )
    parser.add_argument(
        "--image_extensions",
        nargs="+",
        default=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
        help="Image file extensions to include",
    )
    parser.add_argument(
        "--output_md_dir",
        type=str,
        default=str(Path.cwd() / "md"),
        help="Directory to place the final single MD and assets (default: ./md)",
    )
    parser.add_argument(
        "--copy_all_images_to_assets",
        action="store_true",
        help="If assets miss some source images, copy the remaining ones into the assets folder.",
    )
    return parser.parse_args()


def derive_base_and_site(zip_url: str):
    """
    Given a ZIP URL like:
      https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/Content_25.4_Documentation.zip
    Return:
      base_url: https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4
      site_dir: Content_25.4_Documentation
    """
    parsed = urlparse(zip_url)
    path = parsed.path.rstrip("/")
    filename = os.path.basename(path)
    site_dir = re.sub(r"\.zip$", "", filename, flags=re.IGNORECASE)
    base_path = os.path.dirname(path)
    base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}"
    return base_url, site_dir


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p


def short_path(path: Path, max_len: int = 50) -> str:
    """
    Shorten a path for display by using relative path from cwd if shorter.
    """
    try:
        rel = path.relative_to(Path.cwd())
        rel_str = str(rel)
        if len(rel_str) < len(str(path)):
            return rel_str
    except ValueError:
        pass
    return str(path)


def print_section(title: str = ""):
    """Print a section separator."""
    if title:
        print(f"\n{title}")
    else:
        print()


def format_bold(text: str) -> str:
    """Format text as bold for terminal if supported."""
    return f"\033[1m{text}\033[0m"


def format_green(text: str) -> str:
    """Format text as green for terminal if supported."""
    return f"\033[92m{text}\033[0m"


def format_yellow(text: str) -> str:
    """Format text as yellow for terminal if supported."""
    return f"\033[93m{text}\033[0m"


def format_time(seconds: float) -> str:
    """Format seconds into human readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def download_zip(zip_url: str, download_dir: Path, force: bool) -> Path:
    ensure_dir(download_dir)
    filename = os.path.basename(urlparse(zip_url).path)
    dest = download_dir / filename
    if dest.exists() and not force:
        print(f"✓ Using cached ZIP: {filename}")
        return dest

    print(f"↓ Downloading: {filename}")
    with requests.get(zip_url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, 
            unit="B", 
            unit_scale=True, 
            desc="  Progress",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]'
        ) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    return dest


def extract_zip_to_dir(zip_path: Path, extract_root: Path) -> Path:
    import zipfile

    ensure_dir(extract_root)
    target = extract_root / zip_path.stem
    if target.exists():
        # Fresh extraction for determinism
        shutil.rmtree(target)
    ensure_dir(target)
    print(f"⚙ Extracting ZIP...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target)
    return target


def find_base_folders(extracted_root: Path):
    """
    Return directories that contain a 'Content' subdirectory (and preferably 'Data/Tocs').
    """
    candidates = []
    for root, dirs, files in os.walk(extracted_root):
        root_path = Path(root)
        if (root_path / 'Content').is_dir():
            candidates.append(root_path)
    # Prefer those that also include Data/Tocs
    preferred = [p for p in candidates if (p / 'Data' / 'Tocs').is_dir()]
    return preferred or candidates


def _iter_images_in_dir(root: Path):
    exts = {".png", ".bmp", ".gif", ".jpg", ".jpeg"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def _sha1(path: Path) -> str:
    import hashlib
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_and_fill_assets(md_dir: Path, site_dir: str, output_md_dir: Path, copy_missing: bool):
    source_images_dir = md_dir / 'images'
    assets_dir = output_md_dir / f"{site_dir}_assets"

    if not source_images_dir.is_dir():
        print(f"  ⚠ No source images directory found")
        return
    if not assets_dir.is_dir():
        print(f"  ⚠ No assets directory found")
        return

    source_images = list(_iter_images_in_dir(source_images_dir))
    asset_images = list(_iter_images_in_dir(assets_dir))

    # Build content-hash maps for robust comparison (filenames may change)
    src_hashes = {}
    for p in source_images:
        try:
            src_hashes.setdefault(_sha1(p), []).append(p)
        except Exception:
            pass
    asset_hashes = set()
    for p in asset_images:
        try:
            asset_hashes.add(_sha1(p))
        except Exception:
            pass

    missing_hashes = [h for h in src_hashes.keys() if h not in asset_hashes]

    print(f"  Images: {len(asset_images)} included, "
          f"{len(source_images)} total")
    if missing_hashes:
        print(f"  ⚠ {len(missing_hashes)} unreferenced images "
              f"(not linked in MD)")
        if copy_missing:
            # Copy the first representative of each missing hash
            for h in missing_hashes:
                src_path = src_hashes[h][0]
                target_name = src_path.name
                dest = assets_dir / target_name
                # Avoid name collisions by appending short hash
                if dest.exists():
                    stem, ext = os.path.splitext(target_name)
                    dest = assets_dir / f"{stem}-{h[:8]}{ext}"
                try:
                    shutil.copy2(src_path, dest)
                except Exception:
                    pass
            print(f"  ✓ Copied missing images to assets")
        else:
            print(f"  Tip: Use --copy_all_images_to_assets "
                  f"to include them")


def main():
    start_time = time.time()
    args = parse_args()

    base_url, site_dir = derive_base_and_site(args.zip_url)

    download_dir = ensure_dir(Path(args.temp_download_dir).expanduser().resolve())
    extract_dir = ensure_dir(Path(args.temp_extract_dir).expanduser().resolve())
    output_md_dir = ensure_dir(Path(args.output_md_dir).expanduser().resolve())

    # Step 1: Download
    print_section(format_bold("DOWNLOAD"))
    zip_path = download_zip(args.zip_url, download_dir, args.force)
    
    # Step 2: Extract
    print_section(format_bold("EXTRACT"))
    extracted_root = extract_zip_to_dir(zip_path, extract_dir)

    base_folders = find_base_folders(extracted_root)
    if not base_folders:
        print_section()
        print("✗ No base folders containing 'Content' found")
        sys.exit(1)

    # Step 3: Convert
    print_section(format_bold("CONVERT"))
    all_md_contents = []  # Collect all markdown contents to merge
    target_assets_dir = output_md_dir / f"{site_dir}_assets"
    
    for base in base_folders:
        base_name = base.name if base.name != "Help" else f"{base.parent.name}/Help"
        print(f"📄 Processing: {base_name}")
        
        convert_start = time.time()
        # Pass the subfolder name for correct URL generation
        process_base_folder(
            str(base),
            args.image_extensions,
            args.max_workers,
            online_base_url=base_url,
            online_site_dir=site_dir,
            assets_dirname=f"{site_dir}_assets",
            subfolder_name=base_name,  # Pass subfolder for URL path
        )
        convert_time = time.time() - convert_start

        # Locate concatenated MD and collect content
        md_dir = Path(base) / 'md'
        concat_candidates = sorted(md_dir.glob("__*.md"))
        if not concat_candidates:
            print(f"  ✗ No concatenated MD found")
            continue
        
        concatenated_md = concat_candidates[0]
        with open(concatenated_md, 'r', encoding='utf-8') as f:
            content = f.read()
            # Add a separator between guides
            if all_md_contents:
                all_md_contents.append(f"\n\n---\n\n# {base_name} Guide\n\n")
            all_md_contents.append(content)

        # Merge assets from all subfolders
        assets_dir = md_dir / f"{site_dir}_assets"
        if assets_dir.is_dir():
            if not target_assets_dir.exists():
                target_assets_dir.mkdir(parents=True, exist_ok=True)
            # Copy assets, handling name conflicts
            for asset_file in assets_dir.iterdir():
                if asset_file.is_file():
                    dest = target_assets_dir / asset_file.name
                    if not dest.exists():
                        shutil.copy2(asset_file, dest)

        # Verify that assets contain all source images by content; optionally fill missing
        verify_and_fill_assets(md_dir, site_dir, output_md_dir, args.copy_all_images_to_assets)
        
        print(f"  ✓ Converted in {format_time(convert_time)}")
    
    # Write the merged markdown file
    if all_md_contents:
        final_md_path = output_md_dir / f"{site_dir}.md"
        with open(final_md_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_md_contents))

    # Final output
    print_section(format_bold("OUTPUT"))
    print(f"  Markdown: {format_green(short_path(output_md_dir / f'{site_dir}.md'))}")
    if (output_md_dir / f"{site_dir}_assets").is_dir():
        print(f"  Assets:   {short_path(output_md_dir / f'{site_dir}_assets')}")
    
    total_time = time.time() - start_time
    print_section()
    print(format_green(f"✓ Done in {format_time(total_time)}"))


if __name__ == "__main__":
    main()


