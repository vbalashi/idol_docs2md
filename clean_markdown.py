#!/usr/bin/env python3
"""
Standalone script to clean unwanted elements from markdown files.

This script post-processes markdown files to remove:
1. BEGIN_FILE comments at the beginning with their following content
2. Search/navigation artifacts at the end
3. Unwanted navigation elements (Previous/Next links)
4. Embedded JavaScript code blocks
5. Excessive blank lines

Can be used to clean existing concatenated markdown files that were generated before
the cleanup functionality was added to the main conversion pipeline.

Usage:
    python clean_markdown.py <input_file> [output_file]
    
    If output_file is not specified, the input file will be overwritten.
"""

import argparse
import re
import sys
import os


def clean_markdown_content(content):
    """
    Post-processes markdown content to remove unwanted elements:
    1. Removes all BEGIN_FILE HTML comments (debugging markers)
    2. Removes anchor tags immediately before headers
    3. Removes search/navigation artifacts at the end
    4. Removes unwanted navigation elements (Previous/Next links)
    5. Removes embedded JavaScript code blocks
    """
    
    # Pattern 1: Remove sections starting with blacklisted files that appear near the end
    # Look for _FT_SideNav_Startup specifically (the most common footer marker)
    # Use a negative lookbehind to ensure we don't match within other paths
    sidenav_footer = re.compile(
        r'<!--\s*BEGIN_FILE:\s*[^>]*?[/\\]_FT_SideNav_Startup\.md\s*-->\s*\n'
        r'.*$',  # Everything from here to end
        re.MULTILINE | re.DOTALL
    )
    
    # Find the last occurrence (in case there are multiple)
    matches = list(sidenav_footer.finditer(content))
    if matches:
        last_match = matches[-1]
        # Only remove if in the last 5% of the document (to be safe)
        threshold = int(len(content) * 0.95)
        if last_match.start() >= threshold:
            content = content[:last_match.start()]
    
    # Pattern 2: Remove footer sections with index.md or index_CSH.md near the end
    index_footer = re.compile(
        r'<!--\s*BEGIN_FILE:\s*[^>]*?[/\\]index(?:_CSH)?\.md\s*-->\s*\n'
        r'.*$',
        re.MULTILINE | re.DOTALL
    )
    matches = list(index_footer.finditer(content))
    if matches:
        last_match = matches[-1]
        threshold = int(len(content) * 0.95)
        if last_match.start() >= threshold:
            content = content[:last_match.start()]
    
    # Pattern 3: Remove index_CSH sections with JavaScript (can appear anywhere)
    js_csh_pattern = re.compile(
        r'<!--\s*BEGIN_FILE:.*?index_CSH\.md\s*-->\s*\n'
        r'<a\s+id=["\'].*?["\'].*?>\s*</a>\s*\n'
        r'.*?'
        r'//\]\]>\s*\n',
        re.MULTILINE | re.DOTALL
    )
    content = js_csh_pattern.sub('', content)
    
    # Pattern 4: Remove ALL BEGIN_FILE comments throughout the document
    # These are debugging markers that editors don't recognize as markdown
    begin_file_pattern = re.compile(r'<!--\s*BEGIN_FILE:.*?-->\s*\n', re.MULTILINE)
    content = begin_file_pattern.sub('', content)
    
    # Pattern 5: Remove anchor tags that immediately precede headers
    # This cleans up <a id="..."></a> tags that appear right before # headers
    anchor_before_header = re.compile(
        r'<a\s+id=["\']([^"\']+)["\'](?:\s+[^>]*)?>(?:</a>)?\s*\n'
        r'(#+\s+)',
        re.MULTILINE
    )
    content = anchor_before_header.sub(r'\2', content)
    
    # Pattern 5b: Remove standalone anchor tags (not followed by headers)
    # These can appear at the start of files or standalone in content
    standalone_anchor = re.compile(
        r'<a\s+id=["\']([^"\']+)["\'](?:\s+[^>]*)?>(?:</a>)?\s*\n',
        re.MULTILINE
    )
    content = standalone_anchor.sub('', content)
    
    # Pattern 6: Remove footer artifacts that include search results and navigation
    footer_pattern = re.compile(
        r'\n---\s*\n'                                   # Starting horizontal rule
        r'#\s+Your search for.*?returned result.*?\n'  # Search results header
        r'.*?'                                          # Any content
        r'\[Previous\]\(#\)\[Next\]\(#\)\s*\n'         # Navigation links
        r'.*$',                                         # Everything to the end
        re.MULTILINE | re.DOTALL
    )
    content = footer_pattern.sub('', content)
    
    # Pattern 7: Remove standalone search/navigation sections
    search_nav_pattern = re.compile(
        r'---\s*\n'
        r'#\s+Your search for.*?returned result.*?\n'
        r'.*?'
        r'\[Previous\]\(#\)\[Next\]\(#\)',
        re.MULTILINE | re.DOTALL
    )
    content = search_nav_pattern.sub('', content)
    
    # Pattern 7b: Remove "Your search for" headers at the end (without --- prefix)
    search_header_pattern = re.compile(
        r'\n#\s+Your search for.*?returned result.*?\s*$',
        re.MULTILINE | re.DOTALL
    )
    content = search_header_pattern.sub('', content)
    
    # Pattern 8: Remove orphaned navigation links
    orphan_nav_pattern = re.compile(r'\[Previous\]\(#\)\s*\[Next\]\(#\)', re.MULTILINE)
    content = orphan_nav_pattern.sub('', content)
    
    # Pattern 9: Remove excessive blank lines (more than 2 consecutive)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Pattern 10: Clean up trailing horizontal rules and whitespace
    content = re.sub(r'\n---\s*$', '', content)
    
    # Trim leading and trailing whitespace
    content = content.strip()
    
    return content


def main():
    parser = argparse.ArgumentParser(
        description='Clean unwanted elements from markdown files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean a file in-place:
  python clean_markdown.py document.md
  
  # Clean a file and save to a different location:
  python clean_markdown.py document.md cleaned_document.md
  
  # Clean all concatenated markdown files in a directory:
  find . -name "__*.md" -exec python clean_markdown.py {} \\;
        """
    )
    parser.add_argument('input_file', help='Path to the markdown file to clean')
    parser.add_argument('output_file', nargs='?', help='Path to save the cleaned file (optional, defaults to overwriting input)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--backup', action='store_true', help='Create a backup of the original file (only when overwriting)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist.", file=sys.stderr)
        return 1
    
    # Determine output file
    output_file = args.output_file if args.output_file else args.input_file
    overwriting = (output_file == args.input_file)
    
    # Create backup if requested and overwriting
    if args.backup and overwriting:
        backup_file = args.input_file + '.backup'
        if args.verbose:
            print(f"Creating backup: {backup_file}")
        try:
            import shutil
            shutil.copy2(args.input_file, backup_file)
        except Exception as e:
            print(f"Warning: Failed to create backup: {e}", file=sys.stderr)
    
    try:
        # Read input file
        if args.verbose:
            print(f"Reading: {args.input_file}")
        
        with open(args.input_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_size = len(content)
        
        # Clean the content
        if args.verbose:
            print("Cleaning content...")
        
        cleaned_content = clean_markdown_content(content)
        cleaned_size = len(cleaned_content)
        
        # Write output file
        if args.verbose:
            print(f"Writing: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        # Report results
        reduction = original_size - cleaned_size
        percent = (reduction / original_size * 100) if original_size > 0 else 0
        
        print(f"✓ Cleaned {'and overwrote' if overwriting else 'to'}: {output_file}")
        print(f"  Original size: {original_size:,} bytes")
        print(f"  Cleaned size:  {cleaned_size:,} bytes")
        print(f"  Reduction:     {reduction:,} bytes ({percent:.1f}%)")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

