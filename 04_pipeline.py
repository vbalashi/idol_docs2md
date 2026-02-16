#!/usr/bin/env python3
"""
Pipeline script for batch downloading and converting IDOL documentation.

Scans documentation site, provides TUI for selection, and processes multiple items.
"""

import argparse
import json
import re
import sys
import time
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


DEFAULT_DOC_ROOT = "https://www.microfocus.com/documentation/idol/"
CACHE_DIR = Path.cwd() / ".cache"
CATALOG_CACHE_FILE = CACHE_DIR / "idol_doc_catalog.json"
ITEMS_CACHE_FILE = CACHE_DIR / "idol_doc_items.json"


def _normalize_project_name(project: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", project.strip().lower()).strip("-")


def _version_key(version: str) -> Tuple[int, ...]:
    parts = re.split(r"[._-]", version)
    numeric = []
    for part in parts:
        try:
            numeric.append(int(part))
        except ValueError:
            numeric.append(0)
    return tuple(numeric)


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _cache_is_fresh(created_at: float, ttl_hours: float) -> bool:
    if created_at <= 0:
        return False
    return (time.time() - created_at) < ttl_hours * 3600


def _parse_project_version(segment: str) -> Optional[Tuple[str, str]]:
    """
    Parse a folder segment into (project, version).
    Examples:
      knowledge-discovery-25.4 -> (knowledge-discovery, 25.4)
      IDOL_24_4                -> (IDOL, 24.4)
    """
    clean = segment.strip().strip("/")
    if not clean:
        return None
    match = re.match(r"^(?P<project>.+?)[_-](?P<version>\d+(?:[._-]\d+)+)$", clean)
    if not match:
        return None
    project = match.group("project")
    version = match.group("version").replace("_", ".").replace("-", ".")
    return project, version


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


def _scan_catalog_from_root(root_url: str) -> List[Dict[str, str]]:
    html = fetch_page(root_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    entries: List[Dict[str, str]] = []
    seen = set()
    root_parsed = urlparse(root_url)
    root_path = root_parsed.path.rstrip("/") + "/"
    for link in soup.find_all("a", href=True):
        abs_url = urljoin(root_url, link["href"])
        parsed = urlparse(abs_url)
        if parsed.netloc != root_parsed.netloc:
            continue
        if not parsed.path.startswith(root_path):
            continue
        segment = parsed.path.rstrip("/").split("/")[-1]
        parsed_segment = _parse_project_version(segment)
        if not parsed_segment:
            continue
        project_raw, version = parsed_segment
        project = _normalize_project_name(project_raw)
        canonical_url = abs_url.rstrip("/") + "/"
        key = (project, version, canonical_url)
        if key in seen:
            continue
        seen.add(key)
        entries.append({
            "project": project,
            "project_label": project_raw,
            "version": version,
            "url": canonical_url,
        })
    return entries


def load_catalog(root_url: str, refresh: bool, ttl_hours: float) -> List[Dict[str, str]]:
    if not refresh:
        payload = _load_json(CATALOG_CACHE_FILE)
        if payload.get("root_url") == root_url and _cache_is_fresh(payload.get("created_at", 0), ttl_hours):
            return payload.get("entries", [])

    print(f"🔍 Scanning project/version catalog: {root_url}")
    entries = _scan_catalog_from_root(root_url)
    if entries:
        payload = {
            "created_at": time.time(),
            "root_url": root_url,
            "entries": entries,
        }
        _save_json(CATALOG_CACHE_FILE, payload)
    return entries


def _load_items_cache() -> Dict:
    return _load_json(ITEMS_CACHE_FILE)


def _save_items_cache(cache: Dict) -> None:
    _save_json(ITEMS_CACHE_FILE, cache)


def _items_from_cache(start_url: str, ttl_hours: float) -> Optional[List[DocItem]]:
    cache = _load_items_cache()
    entry = cache.get("pages", {}).get(start_url)
    if not entry:
        return None
    if not _cache_is_fresh(entry.get("created_at", 0), ttl_hours):
        return None
    return [DocItem(x["name"], x["zip_url"], x.get("category", "")) for x in entry.get("items", [])]


def _save_items_for_page(start_url: str, items: List[DocItem]) -> None:
    cache = _load_items_cache()
    pages = cache.setdefault("pages", {})
    pages[start_url] = {
        "created_at": time.time(),
        "items": [{"name": i.name, "zip_url": i.zip_url, "category": i.category} for i in items],
    }
    _save_items_cache(cache)


def scan_documentation_site(start_url: str, refresh: bool = False, ttl_hours: float = 24.0) -> List[DocItem]:
    """
    Scan documentation site and extract all available documentation items.
    
    Returns a list of DocItem objects with their ZIP URLs.
    """
    start_url = start_url.rstrip("/") + "/"
    if not refresh:
        cached = _items_from_cache(start_url, ttl_hours)
        if cached is not None:
            print(f"✓ Loaded {len(cached)} documentation items from cache")
            return cached

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
    _save_items_for_page(start_url, unique_items)
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


class CatalogSelectorTUI:
    """Terminal UI for selecting project and version before item scan."""

    def __init__(
        self,
        entries: List[Dict[str, str]],
        refresh_callback,
        initial_project: Optional[str] = None,
        initial_version: Optional[str] = None,
    ):
        self.entries = entries
        self.refresh_callback = refresh_callback
        self.initial_project = initial_project
        self.initial_version = initial_version
        self.mode = "project"
        self.message = "ENTER select, r refresh versions, q quit"
        self.cancelled = False
        self.selected_entry: Optional[Dict[str, str]] = None
        self.project_idx = 0
        self.version_idx = 0
        self._rebuild_indices(keep_project=initial_project, keep_version=initial_version)
        if initial_project and initial_project in self.grouped:
            self.mode = "version"

    def _rebuild_indices(self, keep_project: Optional[str] = None, keep_version: Optional[str] = None):
        self.grouped = _group_catalog_entries(self.entries)
        self.projects = sorted(self.grouped.keys())
        if not self.projects:
            self.project_idx = 0
            self.version_idx = 0
            return

        if keep_project in self.projects:
            self.project_idx = self.projects.index(keep_project)
        else:
            self.project_idx = min(self.project_idx, len(self.projects) - 1)
        versions = self._versions_for_current_project()
        if not versions:
            self.version_idx = 0
            return
        version_values = [v["version"] for v in versions]
        if keep_version in version_values:
            self.version_idx = version_values.index(keep_version)
        else:
            self.version_idx = min(self.version_idx, len(versions) - 1)

    def _current_project(self) -> Optional[str]:
        if not self.projects:
            return None
        return self.projects[self.project_idx]

    def _versions_for_current_project(self) -> List[Dict[str, str]]:
        project = self._current_project()
        if not project:
            return []
        return self.grouped.get(project, [])

    def draw(self, stdscr):
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        title = "IDOL Project/Version Selector"
        stdscr.addstr(0, max(0, (width - len(title)) // 2), title, curses.A_BOLD)
        stdscr.addstr(1, 2, f"Projects: {len(self.projects)} | Entries: {len(self.entries)}")

        project = self._current_project() or "-"
        versions = self._versions_for_current_project()
        selected_version = versions[self.version_idx]["version"] if versions else "-"
        stdscr.addstr(2, 2, f"Project: {project} | Version: {selected_version}")

        if self.mode == "project":
            stdscr.addstr(3, 2, "Mode: Project selection")
            rows = self.projects
            cursor = self.project_idx
        else:
            stdscr.addstr(3, 2, "Mode: Version selection (press 'b' to go back)")
            rows = [v["version"] for v in versions]
            cursor = self.version_idx

        list_start = 5
        list_height = max(1, height - list_start - 2)
        scroll_offset = max(0, cursor - list_height + 1)
        scroll_offset = min(scroll_offset, max(0, len(rows) - list_height))

        for i in range(list_height):
            row_idx = scroll_offset + i
            if row_idx >= len(rows):
                break
            y = list_start + i
            row = rows[row_idx]
            if row_idx == cursor:
                stdscr.addstr(y, 2, f"> {row}"[: width - 4], curses.A_REVERSE)
            else:
                stdscr.addstr(y, 2, f"  {row}"[: width - 4])

        help_y = height - 2
        stdscr.addstr(help_y, 0, "─" * width)
        stdscr.addstr(help_y + 1, 2, self.message[: max(0, width - 4)])
        stdscr.refresh()

    def handle_input(self, key):
        if key == ord("q"):
            self.cancelled = True
            return False
        if key == ord("r"):
            self.message = "Refreshing catalog..."
            refreshed_entries = self.refresh_callback()
            if refreshed_entries:
                current_project = self._current_project()
                current_version = None
                versions = self._versions_for_current_project()
                if versions:
                    current_version = versions[self.version_idx]["version"]
                self.entries = refreshed_entries
                self._rebuild_indices(current_project, current_version)
                self.message = f"Catalog refreshed ({len(self.entries)} entries)"
            else:
                self.message = "Refresh failed or no entries returned"
            return True

        if self.mode == "project":
            if key == curses.KEY_UP and self.project_idx > 0:
                self.project_idx -= 1
            elif key == curses.KEY_DOWN and self.project_idx < len(self.projects) - 1:
                self.project_idx += 1
            elif key == 10 and self.projects:
                self.version_idx = 0
                self.mode = "version"
        else:
            versions = self._versions_for_current_project()
            if key == ord("b"):
                self.mode = "project"
            elif key == curses.KEY_UP and self.version_idx > 0:
                self.version_idx -= 1
            elif key == curses.KEY_DOWN and self.version_idx < len(versions) - 1:
                self.version_idx += 1
            elif key == 10 and versions:
                self.selected_entry = versions[self.version_idx]
                return False

        return True

    def run(self, stdscr):
        curses.curs_set(0)
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


def _group_catalog_entries(entries: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for entry in entries:
        grouped.setdefault(entry["project"], []).append(entry)
    for project_entries in grouped.values():
        project_entries.sort(key=lambda x: _version_key(x["version"]), reverse=True)
    return grouped


def _choose_from_list(prompt: str, options: List[str]) -> str:
    print(prompt)
    for idx, option in enumerate(options, 1):
        print(f"  {idx}. {option}")
    while True:
        value = input("Select number: ").strip()
        if value.isdigit():
            index = int(value) - 1
            if 0 <= index < len(options):
                return options[index]
        print("Invalid choice, try again.")


def _is_url(value: Optional[str]) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _find_catalog_entry(
    grouped: Dict[str, List[Dict[str, str]]],
    project: Optional[str],
    version: Optional[str],
) -> Optional[Dict[str, str]]:
    if not project or not version:
        return None
    entries = grouped.get(project, [])
    for entry in entries:
        if entry["version"] == version:
            return entry
    return None


def _select_catalog_entry_tui(
    entries: List[Dict[str, str]],
    args: argparse.Namespace,
    initial_project: Optional[str],
    initial_version: Optional[str],
) -> Optional[Dict[str, str]]:
    holder: Dict[str, Optional[Dict[str, str]]] = {"entry": None}

    def refresh_callback():
        return load_catalog(
            root_url=args.doc_root.rstrip("/") + "/",
            refresh=True,
            ttl_hours=args.catalog_ttl_hours,
        )

    def _wrapped(stdscr):
        selector = CatalogSelectorTUI(
            entries=entries,
            refresh_callback=refresh_callback,
            initial_project=initial_project,
            initial_version=initial_version,
        )
        selector.run(stdscr)
        if not selector.cancelled:
            holder["entry"] = selector.selected_entry

    curses.wrapper(_wrapped)
    return holder["entry"]


def resolve_doc_url(args: argparse.Namespace) -> Optional[str]:
    target = args.doc_target
    if _is_url(target):
        return target.rstrip("/") + "/"

    catalog_entries = load_catalog(
        root_url=args.doc_root.rstrip("/") + "/",
        refresh=args.refresh_catalog,
        ttl_hours=args.catalog_ttl_hours,
    )
    if not catalog_entries:
        print("✗ Could not load project/version catalog from documentation root")
        return None

    grouped = _group_catalog_entries(catalog_entries)
    requested_version = args.version or (target if target else None)
    requested_project = _normalize_project_name(args.project) if args.project else None

    exact = _find_catalog_entry(grouped, requested_project, requested_version)
    if exact:
        return exact["url"]

    if not sys.stdin.isatty():
        if not requested_project:
            print("✗ Project is required in non-interactive mode. Use --project <name>.")
            return None
        if requested_project not in grouped:
            print(f"✗ Project '{requested_project}' not found in catalog")
            return None
        if not requested_version:
            print("✗ Version is required in non-interactive mode. Use --version <x.y>.")
            return None
        print(f"✗ Version '{requested_version}' not found for project '{requested_project}'")
        return None

    if not args.no_tui:
        selected = _select_catalog_entry_tui(
            entries=catalog_entries,
            args=args,
            initial_project=requested_project,
            initial_version=requested_version,
        )
        if selected:
            return selected["url"]
        print("✗ Project/version selection cancelled")
        return None

    if not requested_project:
        projects = sorted(grouped.keys())
        requested_project = _choose_from_list("Available projects:", projects)
    if requested_project not in grouped:
        print(f"✗ Project '{requested_project}' not found in catalog")
        return None
    if not requested_version:
        versions = [x["version"] for x in grouped[requested_project]]
        requested_version = _choose_from_list(f"Available versions for '{requested_project}':", versions)

    fallback = _find_catalog_entry(grouped, requested_project, requested_version)
    if fallback:
        return fallback["url"]
    print(f"✗ Version '{requested_version}' not found for project '{requested_project}'")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Batch download and convert IDOL documentation with TUI selection."
    )
    parser.add_argument(
        "doc_target",
        nargs='?',
        default=None,
        help="Documentation URL or version (e.g. 25.4).",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Project folder name (e.g. knowledge-discovery).",
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Documentation version (e.g. 25.4).",
    )
    parser.add_argument(
        "--doc-root",
        type=str,
        default=DEFAULT_DOC_ROOT,
        help=f"Root URL used to discover projects/versions (default: {DEFAULT_DOC_ROOT})",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Refresh project/version catalog cache from doc root.",
    )
    parser.add_argument(
        "--refresh-items",
        action="store_true",
        help="Refresh per-page documentation item cache.",
    )
    parser.add_argument(
        "--catalog-ttl-hours",
        type=float,
        default=24.0,
        help="Catalog cache TTL in hours (default: 24).",
    )
    parser.add_argument(
        "--items-ttl-hours",
        type=float,
        default=24.0,
        help="Per-page item cache TTL in hours (default: 24).",
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

    if not args.no_tui and not _is_url(args.doc_target):
        print("🖥️  Launching project/version selector (ENTER choose, r refresh, q quit)")
    
    resolved_doc_url = resolve_doc_url(args)
    if not resolved_doc_url:
        return 1

    print(f"Using documentation URL: {resolved_doc_url}")
    items = scan_documentation_site(
        resolved_doc_url,
        refresh=args.refresh_items,
        ttl_hours=args.items_ttl_hours,
    )
    
    if not items:
        print("\n✗ No documentation items found")
        print("\n💡 Tip: choose by project+version:")
        print("   python 04_pipeline.py --project knowledge-discovery --version 25.4")
        print("   python 04_pipeline.py 25.4 --project knowledge-discovery")
        print("\n   Or provide a full URL directly:")
        print("   python 04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/")
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
