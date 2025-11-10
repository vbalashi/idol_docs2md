#!/usr/bin/env python3
"""
Analyze link errors from markdown files to identify patterns and fix them.
"""

import re
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
import sys

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def extract_links_from_md(md_file: Path):
    """Extract all HTTP/HTTPS links from a markdown file."""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match markdown links [text](url)
        pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        matches = re.findall(pattern, content)
        
        return [(text, url, md_file) for text, url in matches]
    except Exception as e:
        print(f"{RED}Error reading {md_file}: {e}{RESET}")
        return []

def categorize_url(url: str):
    """Categorize URLs by their pattern."""
    parsed = urlparse(url)
    
    # Check for common error patterns
    if parsed.netloc == 'localhost' or parsed.netloc.startswith('localhost:'):
        return 'localhost'
    
    if re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc):
        return 'ip_address'
    
    if parsed.netloc.endswith('.example.com') or 'example.com' in parsed.netloc:
        return 'example_domain'
    
    if parsed.netloc.startswith('host:') or parsed.netloc == 'host':
        return 'placeholder_host'
    
    if not parsed.netloc:
        return 'malformed'
    
    # Check for Micro Focus documentation links
    if 'microfocus.com/documentation' in url:
        # Check for specific patterns in the path
        if '/Guides/html/' in url:
            return 'microfocus_guides_html'
        elif '/html/' in url:
            return 'microfocus_html'
        elif '/Help/' in url:
            return 'microfocus_help'
        elif '/user/' in url or '/admin/' in url:
            return 'microfocus_user_admin'
        else:
            return 'microfocus_other'
    
    # External documentation sites
    external_docs = [
        'docs.oracle.com',
        'www.vertica.com',
        'www.googleapis.com',
        'docs.microsoft.com',
    ]
    
    for domain in external_docs:
        if domain in parsed.netloc:
            return f'external_{domain}'
    
    return 'other'

def analyze_microfocus_links(links):
    """Analyze Micro Focus documentation link patterns."""
    patterns = defaultdict(list)
    
    for text, url, file_path in links:
        if 'microfocus.com/documentation' not in url:
            continue
        
        # Extract the path after 'knowledge-discovery-25.4/'
        match = re.search(r'knowledge-discovery-25\.4/([^/]+)/(.+)', url)
        if match:
            doc_name = match.group(1)
            path_part = match.group(2)
            
            # Identify the pattern
            if '/Guides/html/' in path_part:
                # Extract what comes after Guides/html/
                after_guides = path_part.split('/Guides/html/', 1)[1]
                patterns['guides_html'].append({
                    'doc': doc_name,
                    'after_guides': after_guides,
                    'url': url,
                    'file': file_path.name
                })
            elif '/html/' in path_part:
                after_html = path_part.split('/html/', 1)[1]
                patterns['html'].append({
                    'doc': doc_name,
                    'after_html': after_html,
                    'url': url,
                    'file': file_path.name
                })
            elif path_part.startswith('Help/'):
                patterns['help'].append({
                    'doc': doc_name,
                    'path': path_part,
                    'url': url,
                    'file': file_path.name
                })
            elif '/user/' in path_part or '/admin/' in path_part:
                patterns['user_admin'].append({
                    'doc': doc_name,
                    'path': path_part,
                    'url': url,
                    'file': file_path.name
                })
            else:
                patterns['other'].append({
                    'doc': doc_name,
                    'path': path_part,
                    'url': url,
                    'file': file_path.name
                })
    
    return patterns

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze link patterns in markdown files')
    parser.add_argument('directory', help='Directory containing markdown files')
    parser.add_argument('--pattern', default='*.md', help='File pattern to match (default: *.md)')
    parser.add_argument('--show-examples', type=int, default=3, help='Number of examples to show per category')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"{RED}Error: Directory {directory} does not exist{RESET}")
        sys.exit(1)
    
    # Find all markdown files
    md_files = sorted(directory.glob(args.pattern))
    
    if not md_files:
        print(f"{YELLOW}No markdown files found in {directory}{RESET}")
        sys.exit(0)
    
    print(f"{BOLD}{BLUE}Link Pattern Analysis{RESET}")
    print(f"{CYAN}Directory: {directory}{RESET}")
    print(f"{CYAN}Files: {len(md_files)}{RESET}")
    print("=" * 80)
    
    # Collect all links
    all_links = []
    for md_file in md_files:
        links = extract_links_from_md(md_file)
        all_links.extend(links)
    
    print(f"\n{BOLD}Total links found: {len(all_links)}{RESET}\n")
    
    # Categorize links
    categories = defaultdict(list)
    for text, url, file_path in all_links:
        category = categorize_url(url)
        categories[category].append((text, url, file_path))
    
    # Print category statistics
    print(f"{BOLD}{BLUE}Link Categories:{RESET}\n")
    sorted_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    
    for category, links in sorted_categories:
        count = len(links)
        print(f"{CYAN}{category:30s}{RESET} {count:5d} links")
        
        # Show examples
        if args.show_examples > 0:
            examples = links[:args.show_examples]
            for text, url, file_path in examples:
                short_url = url if len(url) <= 100 else url[:97] + '...'
                print(f"  {YELLOW}→{RESET} {short_url}")
                print(f"    {MAGENTA}from: {file_path.name}{RESET}")
    
    # Detailed analysis of Micro Focus links
    print(f"\n{BOLD}{BLUE}Micro Focus Documentation Link Patterns:{RESET}\n")
    
    microfocus_links = []
    for text, url, file_path in all_links:
        if 'microfocus.com/documentation' in url:
            microfocus_links.append((text, url, file_path))
    
    patterns = analyze_microfocus_links(microfocus_links)
    
    for pattern_name, items in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{CYAN}{pattern_name:20s}{RESET} {len(items):5d} links")
        
        if args.show_examples > 0 and items:
            for item in items[:args.show_examples]:
                print(f"  {YELLOW}Doc:{RESET} {item['doc']}")
                if 'after_guides' in item:
                    print(f"  {GREEN}After /Guides/html/:{RESET} {item['after_guides']}")
                elif 'after_html' in item:
                    print(f"  {GREEN}After /html/:{RESET} {item['after_html']}")
                elif 'path' in item:
                    print(f"  {GREEN}Path:{RESET} {item['path']}")
                print(f"  {MAGENTA}File:{RESET} {item['file']}")
                print()
    
    # Identify problematic patterns
    print(f"\n{BOLD}{RED}Potentially Problematic Links:{RESET}\n")
    
    problematic = ['localhost', 'ip_address', 'example_domain', 'placeholder_host', 'malformed']
    
    total_problematic = 0
    for category in problematic:
        if category in categories:
            count = len(categories[category])
            total_problematic += count
            print(f"{RED}{category:20s}{RESET} {count:5d} links")
            
            # Show unique domains/patterns
            if category == 'localhost':
                urls = set(url for _, url, _ in categories[category])
                for url in sorted(urls)[:5]:
                    print(f"  {YELLOW}→{RESET} {url}")
    
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Total links: {len(all_links)}")
    print(f"  Problematic (test/example): {total_problematic}")
    print(f"  Micro Focus docs: {len(microfocus_links)}")
    print(f"  Other external: {len(all_links) - total_problematic - len(microfocus_links)}")
    
    # Check for /Guides/html/ pattern that should be fixed
    guides_html_count = len(patterns.get('guides_html', []))
    html_count = len(patterns.get('html', []))
    
    if guides_html_count > 0 or html_count > 0:
        print(f"\n{BOLD}{RED}⚠ WARNING: Found links with HTML path patterns:{RESET}")
        print(f"  Links with /Guides/html/: {guides_html_count}")
        print(f"  Links with /html/: {html_count}")
        print(f"\n{YELLOW}These links may need the sed fix applied!{RESET}")
        
        # Suggest fix
        if guides_html_count > 0:
            print(f"\n{GREEN}Suggested fix:{RESET}")
            print(f"  find {directory} -name '*.md' -type f -exec sed -i 's|/Guides/html/|/|g' {{}} +")
        if html_count > 0:
            print(f"  find {directory} -name '*.md' -type f -exec sed -i 's|/html/|/|g' {{}} +")

if __name__ == '__main__':
    main()





