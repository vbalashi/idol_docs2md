# Pipeline Fixes Summary

## Changes Made to Fix Documentation Generation Issues

### 1. **Merge Multiple Subfolders** (`03_fetch_extract_convert.py`)
**Problem:** When processing ZIPs with multiple HTML subfolders (e.g., expert, documentsecurity, gettingstarted), only the LAST folder was kept in the output.

**Fix:** Lines 313-371
- Collect all markdown contents in `all_md_contents` list instead of overwriting
- Merge assets from all subfolders into single assets directory
- Write combined markdown file at the end with proper separators between guides
- Add guide section headers to separate different guides

### 2. **Header Format** (`02_convert_to_md.py`)
**Problem:** Headers were formatted as `## [Title](url)` which breaks anchor linking

**Fix:** Line 697
- Changed from: `## [Title](url)`
- Changed to: `## Title [↗](url)`
- Headers now work as clean anchors
- External link symbol (↗) is adjacent to header, not embedded

### 3. **URL Path Generation** (`02_convert_to_md.py`)
**Problem:** All URLs hardcoded to use `/Help/` path, but actual docs are at `/Guides/html/{subfolder}/`

**Fix:** Lines 681-688
- Accept `subfolder_name` parameter to determine correct subfolder
- Generate URL as: `.../Guides/html/{subfolder}/{path}`
- Extract subfolder name (e.g., "gettingstarted") from full path
- Fallback to `/Help/` only if subfolder not provided (backward compatibility)

### 4. **SVG Image Support** (`02_convert_to_md.py`, `03_fetch_extract_convert.py`)
**Problem:** SVG images not copied because `.svg` not in default image extensions

**Fix:**
- `02_convert_to_md.py` line 1214: Added `.svg` to default extensions
- `03_fetch_extract_convert.py` line 73: Added `.svg` to default extensions

### 5. **Anchor Generation Consistency** (Already Correct)
The `generate_markdown_anchor()` function already produces lowercase-with-hyphens anchors following GitHub markdown conventions.

### 6. **Cross-Reference Link Conversion** (`02_convert_to_md.py`)
**Problem:** Links to external documents (e.g., `../../Shared_Admin/_ADM_Config.htm`, `../../Actions/Query/_IDOL_QUERY.htm`) were not converted to external URLs.

**Fix:** New `fix_cross_references()` function (lines 727-784)
- Detects all `../../` relative path links
- Converts to online documentation URLs with correct subfolder
- Preserves anchor fragments (#section)
- Example: `../../Shared_Admin/_ADM_Config.htm#Section` → `https://.../Guides/html/{subfolder}/Shared_Admin/_ADM_Config.htm#Section`

### 7. **Preserve Navigation Markers** (`02_convert_to_md.py`)
**Problem:** Previous `clean_markdown_content()` removed ALL `<!-- BEGIN_FILE: -->` comments and `<a id="">` anchor tags, breaking navigation.

**Fix:** Modified `clean_markdown_content()` (lines 1095-1192)
- Only removes the FIRST `BEGIN_FILE` comment (at top of file)
- Keeps all other `BEGIN_FILE` comments for reference
- Keeps ALL `<a id="">` anchor tags for internal navigation
- Still removes footer artifacts, search results, and orphaned nav links

## Files Modified

1. **03_fetch_extract_convert.py**
   - Modified `main()` function to collect and merge all subfolder contents
   - Pass `subfolder_name` to `process_base_folder()`
   - Merge assets from all subfolders
   - Added `.svg` to default image extensions

2. **02_convert_to_md.py**
   - Modified `process_base_folder()` to accept `subfolder_name` parameter
   - Modified `generate_concatenated_md()` to accept `subfolder_name` parameter
   - Fixed URL generation to use correct `/Guides/html/{subfolder}/` path
   - Fixed header format to use `## Title [↗](url)` instead of `## [Title](url)`
   - Added `.svg` to default image extensions
   - **NEW**: Added `fix_cross_references()` function to convert `../../` links to external URLs
   - **NEW**: Modified `clean_markdown_content()` to keep BEGIN_FILE comments and anchors (only removes first BEGIN_FILE)
   - **CRITICAL**: Preserves `<!-- BEGIN_FILE: -->` comments and `<a id="">` anchor tags for navigation

## Testing

To test the fixes, run:

```bash
./04_pipeline.py https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/
```

Select "IDOLServer_25.4_Documentation" and verify:
1. ✅ Output contains all 3 guides (expert, documentsecurity, gettingstarted)
2. ✅ Headers use format: `## Title [↗](url)`
3. ✅ External URLs use correct path: `.../Guides/html/{subfolder}/...`
4. ✅ SVG images are copied and referenced correctly
5. ✅ Internal anchor links work (lowercase-with-hyphens)

## Expected Output

After running the pipeline, you should see:
- Single markdown file with ~10,000+ lines (all 3 guides merged)
- Guide separators showing section transitions
- All external links working
- All images (including SVGs) displaying correctly
- Clean header anchors for internal navigation

