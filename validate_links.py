#!/usr/bin/env python3
"""
Validate random links from markdown files.
Picks 5 random links from each .md file and checks if they return 200 OK.
"""

import os
import re
import random
import requests
from pathlib import Path
from urllib.parse import urlparse
import sys
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
import time

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def extract_links_from_md(md_file: Path) -> List[str]:
    """Extract all HTTP/HTTPS links from a markdown file."""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match markdown links [text](url) and direct URLs
        pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        matches = re.findall(pattern, content)
        
        # Extract just the URLs
        links = [url for _, url in matches]
        
        # Also find direct URLs not in markdown link format
        direct_pattern = r'(?<!\()(https?://[^\s\)<>]+)'
        direct_links = re.findall(direct_pattern, content)
        
        all_links = list(set(links + direct_links))  # Remove duplicates
        return all_links
    
    except Exception as e:
        print(f"{RED}Error reading {md_file}: {e}{RESET}")
        return []

def check_url(url: str, timeout: int = 10) -> Tuple[str, int, str]:
    """
    Check if a URL returns 200 OK.
    Returns (url, status_code, error_message)
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        # If HEAD doesn't work, try GET
        if response.status_code == 405 or response.status_code == 404:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
        return (url, response.status_code, "")
    except requests.exceptions.Timeout:
        return (url, 0, "Timeout")
    except requests.exceptions.ConnectionError:
        return (url, 0, "Connection Error")
    except requests.exceptions.TooManyRedirects:
        return (url, 0, "Too Many Redirects")
    except requests.exceptions.RequestException as e:
        return (url, 0, str(e))
    except Exception as e:
        return (url, 0, f"Unknown Error: {str(e)}")

def validate_file_links(md_file: Path, num_links: int = 5, max_workers: int = 5, url_filter: str = None, exclude_known_broken: bool = False) -> Dict:
    """
    Validate random links from a markdown file.
    Returns a dictionary with validation results.
    """
    links = extract_links_from_md(md_file)
    
    # Apply URL filter if provided
    if url_filter:
        links = [url for url in links if url_filter in url]
    
    # Exclude known broken patterns if requested
    if exclude_known_broken:
        known_broken_patterns = [
            '/Shared_Admin/',  # Shared content not published online
            '/ENCODINGS/',     # Encoding reference pages
            'localhost',       # Example URLs
            '127.0.0.1',
            'example.com',
            'host:port',
        ]
        links = [url for url in links if not any(pattern in url for pattern in known_broken_patterns)]
    
    if not links:
        return {
            'file': md_file,
            'total_links': 0,
            'checked_links': 0,
            'results': [],
            'has_errors': False
        }
    
    # Pick random links (or all if fewer than num_links)
    sample_size = min(num_links, len(links))
    sampled_links = random.sample(links, sample_size)
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in sampled_links}
        
        for future in as_completed(future_to_url):
            url, status_code, error = future.result()
            results.append({
                'url': url,
                'status_code': status_code,
                'error': error,
                'success': status_code == 200
            })
    
    has_errors = any(not r['success'] for r in results)
    
    return {
        'file': md_file,
        'total_links': len(links),
        'checked_links': len(results),
        'results': results,
        'has_errors': has_errors
    }

def print_file_results(file_result: Dict):
    """Print results for a single file."""
    file_path = file_result['file']
    has_errors = file_result['has_errors']
    
    # File header
    if has_errors:
        print(f"\n{BOLD}{RED}✗ {file_path}{RESET}")
    else:
        print(f"\n{BOLD}{GREEN}✓ {file_path}{RESET}")
    
    print(f"  {CYAN}Total links: {file_result['total_links']}, Checked: {file_result['checked_links']}{RESET}")
    
    # Print individual link results
    for result in file_result['results']:
        url = result['url']
        status = result['status_code']
        error = result['error']
        
        if result['success']:
            print(f"    {GREEN}✓ [200]{RESET} {url}")
        else:
            if status > 0:
                print(f"    {RED}✗ [{status}]{RESET} {url}")
            else:
                print(f"    {RED}✗ [{error}]{RESET} {url}")

def signal_handler(sig, frame):
    """Handle Ctrl-C gracefully."""
    print(f"\n\n{YELLOW}⚠ Interrupted by user. Exiting gracefully...{RESET}")
    sys.exit(130)  # Standard exit code for SIGINT

def main():
    import argparse
    
    # Register signal handler for Ctrl-C
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(
        description='Validate random links from markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s md/
  %(prog)s md/ --num-links 10
  %(prog)s md/ --max-workers 10
  %(prog)s md/ --file-pattern "DataAdmin*.md"
  %(prog)s md/ --url-filter "microfocus.com"
        """
    )
    parser.add_argument('directory', help='Directory containing markdown files')
    parser.add_argument('--num-links', type=int, default=5,
                        help='Number of random links to check per file (default: 5)')
    parser.add_argument('--max-workers', type=int, default=5,
                        help='Maximum concurrent requests (default: 5)')
    parser.add_argument('--file-pattern', default='*.md',
                        help='File glob pattern to match (default: *.md)')
    parser.add_argument('--url-filter', default=None,
                        help='Only check URLs containing this string (optional)')
    parser.add_argument('--exclude-known-broken', action='store_true',
                        help='Exclude known broken URL patterns (Shared_Admin, ENCODINGS, etc.)')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"{RED}Error: Directory {directory} does not exist{RESET}")
        sys.exit(1)
    
    # Find all markdown files
    md_files = sorted(directory.glob(args.file_pattern))
    
    if not md_files:
        print(f"{YELLOW}No markdown files found in {directory} matching pattern '{args.file_pattern}'{RESET}")
        print(f"{CYAN}Tip: Use --file-pattern to specify a different glob pattern{RESET}")
        sys.exit(0)
    
    print(f"{BOLD}{BLUE}Link Validation Report{RESET}")
    print(f"{CYAN}Directory: {directory}{RESET}")
    print(f"{CYAN}File pattern: {args.file_pattern}{RESET}")
    print(f"{CYAN}Files found: {len(md_files)}{RESET}")
    print(f"{CYAN}Links per file: {args.num_links}{RESET}")
    if args.url_filter:
        print(f"{CYAN}URL filter: {args.url_filter}{RESET}")
    if args.exclude_known_broken:
        print(f"{CYAN}Excluding: Shared_Admin, ENCODINGS, localhost, example.com{RESET}")
    print("=" * 80)
    
    start_time = time.time()
    
    # Process each file
    all_results = []
    files_with_errors = []
    
    try:
        for md_file in md_files:
            print(f"\n{BLUE}Processing: {md_file.name}...{RESET}", end='', flush=True)
            result = validate_file_links(md_file, args.num_links, args.max_workers, args.url_filter, args.exclude_known_broken)
            all_results.append(result)
            
            if result['has_errors']:
                files_with_errors.append(md_file)
            
            # Clear the "Processing..." line
            print(f"\r{' ' * 100}\r", end='', flush=True)
            
            # Print results
            print_file_results(result)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Interrupted by user during processing{RESET}")
        print(f"{CYAN}Partial results processed: {len(all_results)}/{len(md_files)} files{RESET}")
        # Continue to summary with partial results
    
    elapsed_time = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 80)
    print(f"{BOLD}{BLUE}Summary{RESET}")
    print(f"  Total files processed: {len(all_results)}")
    print(f"  Files with errors: {len(files_with_errors)}")
    print(f"  Files without errors: {len(all_results) - len(files_with_errors)}")
    
    total_links_checked = sum(r['checked_links'] for r in all_results)
    total_links_found = sum(r['total_links'] for r in all_results)
    total_errors = sum(len([x for x in r['results'] if not x['success']]) for r in all_results)
    
    print(f"  Total links found: {total_links_found}")
    print(f"  Total links checked: {total_links_checked}")
    print(f"  Total errors: {total_errors}")
    print(f"  Time elapsed: {elapsed_time:.2f}s")
    
    if files_with_errors:
        print(f"\n{BOLD}{RED}Files with errors:{RESET}")
        for file_path in files_with_errors:
            print(f"  {RED}✗ {file_path}{RESET}")
        sys.exit(1)
    else:
        print(f"\n{BOLD}{GREEN}All links are valid! ✓{RESET}")
        sys.exit(0)

if __name__ == '__main__':
    main()

