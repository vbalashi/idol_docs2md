# Subfolder Inference Scope Fix

## Problem Discovered

The subfolder inference logic was being applied to **ALL documentation**, not just IDOLServer merged documents. This caused incorrect URL generation for standard documentation.

### Examples of Broken URLs

**Content Component Documentation:**
```
❌ Generated: .../Content_25.4_Documentation/documentsecurity/Content/Appendixes/Part_Appendixes.htm
✅ Should be:  .../Content_25.4_Documentation/Help/Content/Appendixes/Part_Appendixes.htm
```

**ENCODINGS pages:**
```
❌ Generated: .../Content_25.4_Documentation/Help/Actions/ENCODINGS/_IDOL_ENCODINGS.htm
✅ Should be:  .../Content_25.4_Documentation/Help/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm
```

## Root Cause

The `infer_subfolder_from_path()` function was designed for IDOLServer's merged document structure, where:
- `Content/Appendixes/` → documentsecurity subfolder
- `Content/IDOLExpert/` → expert subfolder  
- `Content/Install_Run_IDOL/` → gettingstarted subfolder

But this logic was being applied to **standard documentation** like Content Component, where:
- `Content/Appendixes/` is just a regular directory
- Should use `/Help/Content/` structure
- Should NOT have subfolder segments

The inference function saw `Appendixes` in `documentsecurity_dirs` list and incorrectly mapped it to the `documentsecurity` subfolder, creating invalid URLs.

## Solution

**Restricted subfolder inference to IDOLServer ONLY:**

### In `generate_concatenated_md()` (lines 715-723):
```python
# Try to infer subfolder from file path (ONLY for merged documents like IDOLServer)
# For other docs, subfolder inference would incorrectly map standard directories
if 'IDOLServer' in online_site_dir:
    inferred_subfolder = infer_subfolder_from_path(md_file)
    effective_subfolder = inferred_subfolder if inferred_subfolder else subfolder_name
else:
    # Standard docs: use provided subfolder_name only
    effective_subfolder = subfolder_name
```

### In `fix_cross_references()` (lines 837-848):
```python
# Try to infer subfolder from the cross-reference path
# ONLY for IDOLServer merged documents - standard docs don't use subfolders
if is_shared_admin:
    # For Shared_Admin, use the context subfolder
    effective_subfolder = get_context_subfolder(link_position) if 'IDOLServer' in online_site_dir else subfolder_name
elif 'IDOLServer' in online_site_dir:
    # For IDOLServer, try to infer subfolder from path
    inferred_subfolder = infer_subfolder_from_path(clean_path)
    effective_subfolder = inferred_subfolder if inferred_subfolder else subfolder_name
else:
    # Standard docs: use provided subfolder_name only
    effective_subfolder = subfolder_name
```

## Documentation Structure Clarification

### Standard IDOL Documentation (Content, Category, Community, etc.)
```
{base_url}/{DOC_NAME}/Help/Content/{path}
```
Example:
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/Content_25.4_Documentation/Help/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm
```

### IDOLServer (Merged Multi-Guide Documentation)
```
{base_url}/IDOLServer_25.4_Documentation/Guides/html/{subfolder}/Content/{path}
```
Where subfolder is one of: expert, gettingstarted, documentsecurity

Example:
```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/expert/Content/IDOLExpert/Components/IDOLComponents.htm
```

## Additional Fix: ENCODINGS Cross-References

### Problem
ENCODINGS reference pages use various relative path patterns in the original HTML:
- `../../ENCODINGS/_IDOL_ENCODINGS.htm`
- `../Actions/ENCODINGS/_IDOL_ENCODINGS.htm`

After stripping `../`, these become:
- `ENCODINGS/_IDOL_ENCODINGS.htm` (missing `Content/Actions/`)
- `Actions/ENCODINGS/_IDOL_ENCODINGS.htm` (missing `Content/`)

But should all resolve to:
```
.../Help/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm
```

### Solution
Added special ENCODINGS path normalization in `fix_cross_references()`:
```python
if 'ENCODINGS/_IDOL_ENCODINGS.htm' in clean_path:
    if clean_path.startswith('ENCODINGS/'):
        # Missing both Content/ and Actions/
        clean_path = f'Content/Actions/{clean_path}'
    elif clean_path.startswith('Actions/ENCODINGS/'):
        # Missing Content/
        clean_path = f'Content/{clean_path}'
```

## Files Modified

- `02_convert_to_md.py`:
  - Lines 715-723: Added IDOLServer check in `generate_concatenated_md()`
  - Lines 837-848: Added ENCODINGS path normalization in `fix_cross_references()`
  - Lines 850-861: Added IDOLServer check for subfolder inference in `fix_cross_references()`

## Impact

This fix ensures that:
- ✅ IDOLServer continues to use subfolder inference correctly
- ✅ Standard docs (Content, Category, Community, etc.) use proper `/Help/Content/` structure
- ✅ No false subfolder detection for standard directory names
- ✅ All ENCODINGS links now have correct `/Help/Content/Actions/ENCODINGS/` path

## Testing

After regenerating Content Component documentation, all links should be valid:
```bash
python3 validate_links.py md/ --file-pattern "Content_25*.md" --url-filter "microfocus.com" --num-links 40
```

Expected result: All checked links return 200 OK status.

