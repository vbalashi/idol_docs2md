# Markdown Cleanup Guide

This guide explains the automatic cleanup features added to the markdown conversion pipeline and how to use the standalone cleanup script.

## Overview

The markdown conversion process now includes automatic post-processing to remove unwanted elements from the generated files:

1. **Navigation artifacts** - Previous/Next links, search forms
2. **Header metadata** - BEGIN_FILE comments and cover page content at the start
3. **Footer artifacts** - Search results, navigation elements at the end
4. **JavaScript blocks** - Embedded CSH (Context-Sensitive Help) redirect scripts
5. **Blacklisted files** - System files like `index.md`, `index_CSH.md`, navigation sidebars

## Automatic Cleanup (Built into Pipeline)

### During Conversion (`02_convert_to_md.py`)

The cleanup happens automatically as the final step when processing HTML to Markdown:

1. **Blacklist Filtering**: Certain files are excluded from the TOC during parsing
2. **Post-Processing**: After all links and assets are processed, unwanted elements are removed

### Blacklisted Files

The following files are automatically excluded from concatenated documents:

- `_FT_SideNav_Startup.md` - Navigation sidebar
- `index.md` - Generic index pages
- `index_CSH.md` - Context-sensitive help index
- `Default.md` - Default landing pages
- `Default_CSH.md` - CSH default pages
- `search-results.md` - Search results pages
- `search.md` - Search pages
- Files in `Shared_*` directories that start with `_`, or contain "Cover" or "Nav" in the name

### What Gets Cleaned

#### 1. Header Artifacts (Beginning of File)

Removes patterns like:
```markdown
---

<!-- BEGIN_FILE: Content/Shared_Admin/_ADM_HTML_Cover.md -->

<a id="license-server"></a>

Knowledge Discovery

---
```

#### 2. Footer Artifacts (End of File)

Removes patterns like:
```markdown
---

# Your search for returned result(s).

[Previous](#)[Next](#)

<!-- BEGIN_FILE: Content/_FT_SideNav_Startup.md -->

<a id="-ft-sidenav-startup"></a>

Getting Started Guide

Filter: 

* All Files

Submit Search

<!-- BEGIN_FILE: index.md -->

<a id="index"></a>

<!-- BEGIN_FILE: index_CSH.md -->

<a id="index-csh"></a>

// JavaScript code...
//]]>

---
```

#### 3. JavaScript Blocks

Removes embedded CSH redirect scripts that appear in the content.

#### 4. Orphaned Navigation

Removes standalone `[Previous](#)[Next](#)` links that appear in content.

#### 5. Excessive Whitespace

Consolidates more than 2 consecutive blank lines into 2 blank lines.

## Manual Cleanup (Standalone Script)

For files that were converted before the cleanup feature was added, or for custom cleanup needs, use the `clean_markdown.py` script.

### Usage

#### Basic Usage (In-place Cleaning)

Clean a file and overwrite it:
```bash
python clean_markdown.py document.md
```

#### Save to Different File

Clean and save to a new file:
```bash
python clean_markdown.py document.md cleaned_document.md
```

#### With Backup

Create a backup before overwriting:
```bash
python clean_markdown.py --backup document.md
```
This creates `document.md.backup` before cleaning.

#### Verbose Output

See detailed processing information:
```bash
python clean_markdown.py -v document.md
```

#### Batch Processing

Clean all concatenated markdown files in a directory:
```bash
find . -name "__*.md" -exec python clean_markdown.py {} \;
```

Clean with verbose output and backups:
```bash
find . -name "__*.md" -exec python clean_markdown.py -v --backup {} \;
```

#### Using the Pipeline Script

The easiest way is to use `03_fetch_extract_convert.py` which includes the cleanup automatically:
```bash
python 03_fetch_extract_convert.py <url> [options]
```

### Script Options

```
positional arguments:
  input_file      Path to the markdown file to clean
  output_file     Path to save the cleaned file (optional, defaults to overwriting input)

optional arguments:
  -h, --help      Show help message
  -v, --verbose   Print verbose output
  --backup        Create a backup of the original file (only when overwriting)
```

### Example Output

```
✓ Cleaned and overwrote: __Content_25.4_Documentation.md
  Original size: 1,543,892 bytes
  Cleaned size:  1,521,045 bytes
  Reduction:     22,847 bytes (1.5%)
```

## Customizing the Blacklist

To add more files to the blacklist, edit `02_convert_to_md.py`:

```python
# Near the top of the file (around line 21)
BLACKLISTED_FILES = [
    '_FT_SideNav_Startup.md',
    'index.md',
    'index_CSH.md',
    'Default.md',
    'Default_CSH.md',
    'search-results.md',
    'search.md',
    # Add your custom patterns here:
    'my_unwanted_file.md',
]
```

You can also modify the `is_blacklisted()` function to add custom logic:

```python
def is_blacklisted(filepath):
    basename = os.path.basename(filepath)
    
    # Exact matches
    if basename in BLACKLISTED_FILES:
        return True
    
    # Custom pattern matching
    if 'unwanted_pattern' in filepath:
        return True
    
    return False
```

## Customizing Cleanup Patterns

To modify what gets cleaned, edit the `clean_markdown_content()` function in either:
- `02_convert_to_md.py` (for pipeline integration)
- `clean_markdown.py` (for standalone script)

The function uses regular expressions to match and remove patterns. Each pattern is documented with comments explaining what it matches.

### Example: Adding a New Cleanup Pattern

```python
def clean_markdown_content(content):
    # ... existing patterns ...
    
    # New pattern: Remove custom footer
    custom_footer = re.compile(
        r'Generated by MyTool\s*\n'
        r'Copyright.*?\n',
        re.MULTILINE
    )
    content = custom_footer.sub('', content)
    
    return content
```

## Troubleshooting

### Content is Being Removed That Shouldn't Be

1. Check if the file is in the blacklist
2. Review the regex patterns in `clean_markdown_content()`
3. Use the `--verbose` flag to see what's being processed
4. Test the pattern against your specific content

### Files Still Contain Unwanted Content

1. Check if the content matches the existing patterns
2. Add new patterns to `clean_markdown_content()`
3. Verify the cleanup is running (check logs for "Cleaned unwanted elements")

### Need to Restore Original Content

If you used `--backup`:
```bash
cp document.md.backup document.md
```

If you didn't create a backup, the original HTML files should still be in the extraction directory.

## Integration with Other Tools

### Using with Pandoc

The cleaned markdown files work seamlessly with Pandoc:
```bash
pandoc cleaned_document.md -o output.pdf
```

### Using with Jekyll/GitHub Pages

The cleaned files are valid GitHub-Flavored Markdown and work with Jekyll:
```bash
cp cleaned_document.md _posts/2024-01-01-my-document.md
```

### Using with MkDocs

Add the cleaned markdown files to your MkDocs project:
```bash
cp cleaned_document.md docs/
```

## See Also

- [Main README](README.md) - Project overview
- [Pipeline README](PIPELINE_README.md) - Full pipeline documentation
- [Quick Reference](QUICK_REFERENCE.md) - Quick command reference

