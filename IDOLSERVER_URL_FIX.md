# IDOLServer Special URL Structure Fix

## Problem Discovered

IDOLServer documentation has a **completely different URL structure** from all other IDOL documentation:

### Standard Documentation
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/{DOC_NAME}/Help/Content/...
```

### Documentation with Subfolders (most cases)
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/{DOC_NAME}/{subfolder}/Content/...
```

### IDOLServer (SPECIAL CASE)
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/{subfolder}/Content/...
```

Notice the **`/Guides/html/`** prefix that only IDOLServer uses!

## Browser Verification

Verified with actual browser tests:

✅ **Works:**
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/expert/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm
```

❌ **Fails (404):**
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/expert/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm
```

## Solution Implemented

Updated `02_convert_to_md.py` to detect IDOLServer documentation and insert the `/Guides/html/` prefix:

### In `generate_concatenated_md()` function (lines 726-732):
```python
# Special case: IDOLServer has a unique URL structure with /Guides/html/ prefix
if 'IDOLServer' in online_site_dir:
    # IDOLServer structure: {base_url}/{doc_name}/Guides/html/{subfolder}/{rel_html_path}
    online_url = f"{online_base_url.rstrip('/')}/{online_site_dir.strip('/')}/Guides/html/{subfolder}/{rel_html_path}"
else:
    # Standard structure: {base_url}/{doc_name}/{subfolder}/{rel_html_path}
    online_url = f"{online_base_url.rstrip('/')}/{online_site_dir.strip('/')}/{subfolder}/{rel_html_path}"
```

### In `fix_cross_references()` function (lines 815-821):
Same logic applied to cross-reference URL conversion.

## Test Results

All test cases pass with correct URL generation:

✅ **Expert subfolder:**
```
Input:  Content/IDOLExpert/EnrichContent/Categorize_Documents.md
Output: .../IDOLServer_25.4_Documentation/Guides/html/expert/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm
```

✅ **Getting Started subfolder:**
```
Input:  Content/Install_Run_IDOL/Query/IDOL ACI Responses.md
Output: .../IDOLServer_25.4_Documentation/Guides/html/gettingstarted/Content/Install_Run_IDOL/Query/IDOL ACI Responses.htm
```

✅ **Document Security subfolder:**
```
Input:  Content/Resources/MasterPages/_FT_Legal_Notices.md
Output: .../IDOLServer_25.4_Documentation/Guides/html/documentsecurity/Content/Resources/MasterPages/_FT_Legal_Notices.htm
```

## Additional Fix: Shared_Admin Cross-References

### Problem
Shared_Admin content (shared across all guides) uses relative paths like `../../Shared_Admin/...` which need to resolve to the correct subfolder based on WHERE the link appears in the merged document.

Example:
- Link from gettingstarted guide: `../../Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm`
- Should resolve to: `.../Guides/html/gettingstarted/Content/Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm`

### Solution
Made `fix_cross_references()` context-aware:
1. Scans document for all BEGIN_FILE markers
2. Builds a position map of which subfolder each section belongs to
3. When processing Shared_Admin links, uses the context to determine the correct subfolder
4. Prepends `Content/` to Shared_Admin paths

## Files Modified

- `02_convert_to_md.py`:
  - Updated `infer_subfolder_from_path()` to include 'Resources' in documentsecurity dirs (line 586)
  - Updated `generate_concatenated_md()` with IDOLServer special case (lines 726-732)
  - **Rewrote `fix_cross_references()`** to be context-aware (lines 773-865)
    - Added context tracking via BEGIN_FILE markers
    - Added Shared_Admin special handling with Content/ prefix
    - Uses position-based subfolder detection

## Additional Notes

This is a **documentation-specific quirk** where MicroFocus published IDOLServer with a different directory structure than all other IDOL documentation. The fix detects "IDOLServer" in the documentation name and applies the special URL pattern automatically.

The detection is simple and reliable:
```python
if 'IDOLServer' in online_site_dir:
    # Apply special /Guides/html/ structure
```

## Next Steps

Re-run the IDOLServer conversion to apply the fix:
```bash
./04_pipeline.py
# Select "Getting Started Guide" (IDOLServer)
```

Then validate:
```bash
python3 validate_links.py md/ --file-pattern "IDOLServer*.md" --url-filter "microfocus.com" --num-links 20
```

