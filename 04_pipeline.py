#!/usr/bin/env python3
"""
Pipeline script for batch downloading and converting IDOL documentation.

Scans documentation site, provides TUI for selection, and processes multiple items.
"""

import argparse
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# For TUI
try:
    import curses
except ImportError:
    print("Error: curses module not available. This script requires a Unix-like system.")
    sys.exit(1)


class DocItem:
    """Represents a documentation item with ZIP download link."""
    
    def __init__(self, name: str, zip_url: str, category: str = ""):
        self.name = name
        self.zip_url = zip_url
        self.category = category
        self.selected = False
    
    def __repr__(self):
        return f"DocItem({self.name}, {self.zip_url})"


def fetch_page(url: str) -> str:
    """Fetch HTML content from a URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return ""


def extract_zip_links(html: str, base_url: str) -> List[Tuple[str, str]]:
    """
    Extract all ZIP download links from HTML.
    Returns list of (name, absolute_url) tuples.
    """
    soup = BeautifulSoup(html, 'html.parser')
    zip_links = []
    
    # Look for download links in the documentation tables
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.zip'):
            abs_url = urljoin(base_url, href)
            # Extract name from text or from URL
            name = link.get_text(strip=True)
            if not name or name.lower() in ['download zip file', 'download', 'zip']:
                # Fallback: extract from filename
                name = Path(urlparse(abs_url).path).stem
            zip_links.append((name, abs_url))
    
    return zip_links


def scan_documentation_site(start_url: str) -> List[DocItem]:
    """
    Scan documentation site and extract all available documentation items.
    
    Returns a list of DocItem objects with their ZIP URLs.
    """
    print(f"🔍 Scanning documentation site: {start_url}")
    
    html = fetch_page(start_url)
    if not html:
        print("✗ Failed to fetch page")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Strategy 1: Find tables with documentation links
    tables = soup.find_all('table')
    for table in tables:
        # Get table header/category if available
        category = ""
        prev_elem = table.find_previous(['h1', 'h2', 'h3', 'h4'])
        if prev_elem:
            category = prev_elem.get_text(strip=True)
        
        # Extract rows
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # First cell usually contains the name/link to view
            name_cell = cells[0]
            name = name_cell.get_text(strip=True)
            
            # Look for ZIP download link in this row
            zip_link = None
            for cell in cells:
                for link in cell.find_all('a', href=True):
                    href = link['href']
                    if '.zip' in href.lower():
                        zip_link = urljoin(start_url, href)
                        break
                if zip_link:
                    break
            
            if zip_link and name:
                items.append(DocItem(name, zip_link, category))
    
    # Strategy 2: Direct ZIP links if no tables found
    if not items:
        zip_links = extract_zip_links(html, start_url)
        for name, url in zip_links:
            items.append(DocItem(name, url, ""))
    
    # Remove exact duplicates only (same name AND same ZIP URL)
    # Keep rows that share a ZIP but represent different guides (e.g., C, C++, Java)
    seen: set = set()
    unique_items: List[DocItem] = []
    for item in items:
        key = (item.name, item.zip_url)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    print(f"✓ Found {len(unique_items)} documentation items")
    return unique_items


class DocSelectorTUI:
    """Terminal UI for selecting documentation items."""
    
    def __init__(self, items: List[DocItem]):
        self.all_items = items
        self.filtered_items = items[:]
        self.current_idx = 0
        self.scroll_offset = 0
        self.filter_text = ""
        self.mode = "normal"  # "normal" or "search"
        self.message = "Press '/' to search, SPACE to toggle, 'a' to select all, 'n' to select none, ENTER to confirm, 'q' to quit"
    
    def filter_items(self):
        """Filter items based on current filter text."""
        if not self.filter_text:
            self.filtered_items = self.all_items[:]
        else:
            pattern = self.filter_text.lower()
            self.filtered_items = [
                item for item in self.all_items
                if pattern in item.name.lower() or pattern in item.category.lower()
            ]
        self.current_idx = 0
        self.scroll_offset = 0
    
    def draw(self, stdscr):
        """Draw the TUI."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Title
        title = "IDOL Documentation Selector"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Stats line
        selected_count = sum(1 for item in self.all_items if item.selected)
        stats = f"Selected: {selected_count}/{len(self.all_items)} | Showing: {len(self.filtered_items)}"
        stdscr.addstr(1, 2, stats)
        
        # Filter/search line
        if self.mode == "search":
            filter_line = f"Search: {self.filter_text}_"
        elif self.filter_text:
            filter_line = f"Filter: {self.filter_text} (press '/' to modify)"
        else:
            filter_line = "No filter (press '/' to search)"
        stdscr.addstr(2, 2, filter_line)
        
        # Draw items
        list_start = 4
        list_height = height - list_start - 2  # Reserve 2 lines for help
        
        for i in range(list_height):
            item_idx = self.scroll_offset + i
            if item_idx >= len(self.filtered_items):
                break
            
            item = self.filtered_items[item_idx]
            line_y = list_start + i
            
            # Cursor indicator
            if item_idx == self.current_idx:
                stdscr.addstr(line_y, 0, ">", curses.A_BOLD)
            
            # Checkbox
            checkbox = "[X]" if item.selected else "[ ]"
            stdscr.addstr(line_y, 2, checkbox)
            
            # Item name with category
            display_name = item.name
            if item.category:
                display_name = f"{item.category}: {display_name}"
            
            # Truncate if too long
            max_name_len = width - 10
            if len(display_name) > max_name_len:
                display_name = display_name[:max_name_len-3] + "..."
            
            # Highlight current item
            if item_idx == self.current_idx:
                stdscr.addstr(line_y, 6, display_name, curses.A_REVERSE)
            else:
                stdscr.addstr(line_y, 6, display_name)
        
        # Help line
        help_y = height - 2
        stdscr.addstr(help_y, 0, "─" * width)
        stdscr.addstr(help_y + 1, 2, self.message[:width-4])
        
        stdscr.refresh()
    
    def handle_input(self, key):
        """Handle keyboard input. Returns True to continue, False to exit."""
        height, width = curses.LINES, curses.COLS
        list_height = height - 6
        
        if self.mode == "search":
            # Search mode
            if key == 27:  # ESC
                self.mode = "normal"
                self.filter_text = ""
                self.filter_items()
            elif key == 10:  # ENTER
                self.mode = "normal"
                self.filter_items()
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.filter_text = self.filter_text[:-1]
                self.filter_items()
            elif 32 <= key <= 126:  # Printable characters
                self.filter_text += chr(key)
                self.filter_items()
        else:
            # Normal mode
            if key == ord('q'):
                return False
            elif key == ord('/'):
                self.mode = "search"
                self.filter_text = ""
            elif key == ord(' '):
                if self.filtered_items:
                    self.filtered_items[self.current_idx].selected = not self.filtered_items[self.current_idx].selected
            elif key == ord('a'):
                for item in self.filtered_items:
                    item.selected = True
                self.message = f"Selected all {len(self.filtered_items)} filtered items"
            elif key == ord('n'):
                for item in self.filtered_items:
                    item.selected = False
                self.message = f"Deselected all {len(self.filtered_items)} filtered items"
            elif key == ord('A'):  # Shift+A - select all globally
                for item in self.all_items:
                    item.selected = True
                self.message = f"Selected all {len(self.all_items)} items"
            elif key == ord('N'):  # Shift+N - deselect all globally
                for item in self.all_items:
                    item.selected = False
                self.message = f"Deselected all {len(self.all_items)} items"
            elif key == 10:  # ENTER
                selected = [item for item in self.all_items if item.selected]
                if selected:
                    return False  # Exit and proceed
                else:
                    self.message = "⚠ No items selected! Press 'a' to select all or 'q' to quit"
            elif key == curses.KEY_UP:
                if self.current_idx > 0:
                    self.current_idx -= 1
                    if self.current_idx < self.scroll_offset:
                        self.scroll_offset = self.current_idx
            elif key == curses.KEY_DOWN:
                if self.current_idx < len(self.filtered_items) - 1:
                    self.current_idx += 1
                    if self.current_idx >= self.scroll_offset + list_height:
                        self.scroll_offset = self.current_idx - list_height + 1
            elif key == curses.KEY_PPAGE:  # Page Up
                self.current_idx = max(0, self.current_idx - list_height)
                self.scroll_offset = max(0, self.scroll_offset - list_height)
            elif key == curses.KEY_NPAGE:  # Page Down
                self.current_idx = min(len(self.filtered_items) - 1, self.current_idx + list_height)
                self.scroll_offset = min(
                    len(self.filtered_items) - list_height,
                    self.scroll_offset + list_height
                )
            elif key == curses.KEY_HOME:
                self.current_idx = 0
                self.scroll_offset = 0
            elif key == curses.KEY_END:
                self.current_idx = len(self.filtered_items) - 1
                self.scroll_offset = max(0, len(self.filtered_items) - list_height)
        
        return True
    
    def run(self, stdscr):
        """Main TUI loop."""
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)
        
        while True:
            self.draw(stdscr)
            key = stdscr.getch()
            if not self.handle_input(key):
                break


def run_conversion(zip_url: str, args: argparse.Namespace) -> bool:
    """
    Run the conversion script for a single ZIP URL.
    Returns True on success, False on failure.
    """
    import subprocess
    
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "03_fetch_extract_convert.py"),
        zip_url,
        "--temp_download_dir", args.temp_download_dir,
        "--temp_extract_dir", args.temp_extract_dir,
        "--output_md_dir", args.output_md_dir,
        "--max_workers", str(args.max_workers),
    ]
    
    if args.force:
        cmd.append("--force")

    if args.copy_all_images_to_assets:
        cmd.append("--copy_all_images_to_assets")

    if not getattr(args, "show_warnings", False):
        cmd.append("--quiet-warnings")
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"✗ Conversion failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch download and convert IDOL documentation with TUI selection."
    )
    parser.add_argument(
        "doc_url",
        nargs='?',
        default="https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/",
        help="URL to documentation index (default: https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/)"
    )
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
        "--output_md_dir",
        type=str,
        default=str(Path.cwd() / "md"),
        help="Directory to place final MD files and assets (default: ./md)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download of ZIPs even if they exist",
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=10,
        help="Maximum worker threads for conversion (default: 10)",
    )
    parser.add_argument(
        "--copy_all_images_to_assets",
        action="store_true",
        help="Copy all source images to assets, even if not referenced in MD",
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Display detailed warnings from conversion runs (default suppresses known chatter)",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Skip TUI and process all found items automatically",
    )
    
    args = parser.parse_args()
    
    # Step 1: Scan documentation site
    print("=" * 70)
    print("IDOL Documentation Pipeline")
    print("=" * 70)
    
    items = scan_documentation_site(args.doc_url)
    
    if not items:
        print("\n✗ No documentation items found")
        print("\n💡 Tip: This URL appears to be a version index page.")
        print("   Try one of these version-specific URLs instead:")
        print("   • https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/")
        print("   • https://www.microfocus.com/documentation/idol/knowledge-discovery-25.3/")
        print("   • https://www.microfocus.com/documentation/idol/IDOL_24_4/")
        print("\n   Or run without arguments to use the default (25.4):")
        print("   python 04_pipeline.py")
        return 1
    
    # Step 2: Let user select items (or auto-select all with --no-tui)
    if args.no_tui:
        print(f"📋 Auto-selecting all {len(items)} items (--no-tui mode)")
        for item in items:
            item.selected = True
        selected_items = items
    else:
        print("\n🖥️  Launching TUI for selection...")
        print("    (Use arrow keys to navigate, SPACE to select, '/' to search)")
        time.sleep(1)  # Give user time to read
        
        try:
            selector = DocSelectorTUI(items)
            curses.wrapper(selector.run)
            selected_items = [item for item in items if item.selected]
        except KeyboardInterrupt:
            print("\n✗ Selection cancelled")
            return 1
    
    if not selected_items:
        print("\n✗ No items selected")
        return 1
    
    # Step 3: Process selected items
    print("\n" + "=" * 70)
    print(f"PROCESSING {len(selected_items)} SELECTED ITEMS")
    print("=" * 70)
    
    success_count = 0
    failed_items = []
    processed_zip_urls: set = set()
    
    for i, item in enumerate(selected_items, 1):
        print(f"\n[{i}/{len(selected_items)}] {item.name}")
        print("-" * 70)
        
        # Avoid reprocessing the same ZIP multiple times if multiple guides share it
        if item.zip_url in processed_zip_urls:
            print(f"↺ Skipping duplicate ZIP already processed: {item.zip_url}")
            success = True
        else:
            success = run_conversion(item.zip_url, args)
            if success:
                processed_zip_urls.add(item.zip_url)
        
        if success:
            success_count += 1
            print(f"✓ Completed: {item.name}")
        else:
            failed_items.append(item.name)
            print(f"✗ Failed: {item.name}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Total selected: {len(selected_items)}")
    print(f"Successful:     {success_count}")
    print(f"Failed:         {len(failed_items)}")
    
    if failed_items:
        print("\nFailed items:")
        for name in failed_items:
            print(f"  ✗ {name}")
    
    print(f"\n📁 Output directory: {args.output_md_dir}")
    
    return 0 if not failed_items else 1


if __name__ == "__main__":
    sys.exit(main())
