# Link Validation Guide

## Quick Start

### Validate all files (5 random links per file)
```bash
python3 validate_links.py md/
```

### Validate specific files
```bash
python3 validate_links.py md/ --file-pattern "DataAdmin*.md"
```

### Check only Micro Focus documentation links
```bash
python3 validate_links.py md/ --url-filter "microfocus.com"
```

### Check more links per file
```bash
python3 validate_links.py md/ --num-links 10
```

### Faster validation (more concurrent requests)
```bash
python3 validate_links.py md/ --max-workers 10
```

### Interrupt safely
Press **Ctrl-C** to stop gracefully - partial results will be shown

## Common Use Cases

### 1. Quick validation of a single document
```bash
python3 validate_links.py md/ --file-pattern "DIH_25.4_Documentation.md" --num-links 10
```

### 2. Validate only SDK documentation
```bash
python3 validate_links.py md/ --file-pattern "*SDK*.md"
```

### 3. Check external links only
```bash
# First, check what external domains exist
python3 analyze_link_errors.py md/

# Then validate specific external domain
python3 validate_links.py md/ --url-filter "docs.oracle.com"
```

### 4. Full validation (many links, faster)
```bash
python3 validate_links.py md/ --num-links 20 --max-workers 20
```

## Understanding Results

### Success (Green ✓)
```
✓ [200] https://www.microfocus.com/documentation/...
```
Link is working correctly

### Failure (Red ✗)
```
✗ [404] https://www.example.com/page
```
Link returns 404 Not Found

```
✗ [Connection Error] http://localhost:1234/
```
Cannot connect (expected for localhost/example URLs)

```
✗ [Timeout] http://slow-server.com/
```
Server took too long to respond

## Expected "Errors"

These are **NOT actual errors** - they are intentional example URLs in the documentation:

- ❌ `localhost` URLs
- ❌ IP addresses (e.g., `12.3.4.56`)
- ❌ `example.com` domains
- ❌ `host:port` placeholders
- ❌ `myvault.example.com`

These are placeholder URLs that users should replace with their actual values.

## Analyze Link Patterns

Before validating, analyze link patterns to understand what's in your docs:

```bash
python3 analyze_link_errors.py md/ --show-examples 5
```

This shows:
- Total links by category
- External documentation links
- URL patterns used
- Potential issues to investigate

## Exit Codes

- `0` - All links valid
- `1` - Some links failed validation
- `130` - User interrupted (Ctrl-C)

## Tips

1. **Start small**: Test one file first before validating all files
2. **Use filters**: Focus on the links you care about with `--url-filter`
3. **Parallelize**: Use more workers for faster results (but don't overwhelm servers)
4. **Be patient**: Validating 47,000+ links takes time
5. **Ignore examples**: Don't worry about localhost/example.com errors

## Performance

Typical validation times:
- Single file (5 links): < 1 second
- 10 files (50 links): ~5-10 seconds
- All files (490 links at 5/file): ~5-10 minutes
- Full validation (1000+ links): 15-30 minutes

Faster with more workers, but be respectful of the documentation server.

## Troubleshooting

### "No markdown files found"
- Check your directory path
- Use `--file-pattern` with correct glob pattern
- Example: `--file-pattern "*.md"` or `--file-pattern "DIH*.md"`

### Too many timeout errors
- Reduce `--max-workers` (try 3-5)
- Some servers rate-limit requests

### Connection errors
- Check your internet connection
- Some example URLs (localhost, etc.) will always fail - this is expected

## Examples

### Validate DataAdmin and DIH only
```bash
python3 validate_links.py md/ --file-pattern "{DataAdmin,DIH}*.md" --num-links 10
```

### Quick smoke test (1 link per file)
```bash
python3 validate_links.py md/ --num-links 1 --max-workers 10
```

### Thorough validation of Micro Focus links
```bash
python3 validate_links.py md/ --num-links 20 --url-filter "microfocus.com" --max-workers 15
```

