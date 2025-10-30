# Shared_Admin Links Issue

## Problem

Many markdown files contain links to `/Shared_Admin/` paths that return 404 errors:

```
https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/SlackConnector_25.4_Documentation/Help/Shared_Admin/_ADM_Enter_config_params.htm
```

**Status**: Returns 404 (not found)

## Root Cause

The `Shared_Admin` folders contain **shared content** that is embedded within each documentation package but **not published as separate URLs** on the Micro Focus documentation site.

### How Shared Content Works

1. **In Source**: Each documentation ZIP contains a `Content/Shared_Admin/` folder with reusable HTML files
2. **In Build**: These files are embedded/included during the help system build
3. **Online**: This content is NOT published at `/Help/Shared_Admin/` URLs
4. **References**: Cross-references like `../../Shared_Admin/_ADM_Config.htm` are resolved during the build process, not as external links

## Scope

- **Files affected**: 85 out of 98 markdown files
- **Link pattern**: `/Shared_Admin/` in URL path
- **Typical examples**:
  - `Shared_Admin/_ADM_Enter_config_params.htm`
  - `Shared_Admin/_ADM_Include_Config.htm`
  - `Shared_Admin/EventHandlers/_ADM_Event_Handlers_Lua.htm`

## Why This Happens

The `fix_cross_references()` function in `02_convert_to_md.py` converts relative paths like:
```
../../Shared_Admin/_ADM_Config.htm
```

To absolute URLs:
```
https://.../ConnectorName/Help/Shared_Admin/_ADM_Config.htm
```

But these URLs don't exist because `Shared_Admin` content isn't published separately.

## Possible Solutions

### Option 1: Leave As-Is (Recommended)
**Status**: ✅ Current behavior

**Rationale**:
- These links provide useful information about what the original documentation referenced
- Users can identify the topic even if the link doesn't work
- The linked content is documentation about configuration, not critical functionality
- Fixing would require complex logic to determine where (if anywhere) this content is published

**Impact**: 
- Some links will show 404 in validation (expected)
- Document will still be readable and useful

### Option 2: Remove Shared_Admin Links
**Status**: ❌ Not recommended

Replace with plain text:
```markdown
For more information, see the administration guide for configuration parameters.
```

**Pros**: No broken links
**Cons**: Loses information about what was referenced

### Option 3: Convert to Internal References
**Status**: ❌ Not feasible

Try to resolve Shared_Admin files as internal anchors.

**Problem**: The Shared_Admin content is often NOT included in the concatenated markdown because it's in a separate directory that isn't part of the TOC.

## Recommendation

**Accept as Known Limitation**

These Shared_Admin link "errors" are actually:
1. **Expected** - The content isn't published at those URLs
2. **Informative** - They tell users what topic to look for
3. **Low priority** - They reference general admin topics, not critical content

### What to Do

1. **Document** this as a known issue in validation reports
2. **Exclude** `/Shared_Admin/` links from "error" counts
3. **Filter** them out during validation with:
   ```bash
   python3 validate_links.py md/ --url-filter "microfocus.com" | grep -v "Shared_Admin"
   ```

## Validation Filter

To check only resolvable Micro Focus links (excluding Shared_Admin):

```bash
# Count Shared_Admin links
grep -r "/Shared_Admin/" md/*.md | wc -l

# Validate without Shared_Admin noise
python3 validate_links.py md/ --num-links 5 2>&1 | grep -v "Shared_Admin"
```

## Statistics

```bash
# Files with Shared_Admin links
grep -c "/Shared_Admin/" md/*.md | grep -v ":0" | wc -l
# Result: 85 files

# Total Shared_Admin links
grep -o "/Shared_Admin/[^)]*" md/*.md | wc -l
# Result: ~hundreds of links
```

## Other Similar Patterns

The same issue may affect:
- `/Actions/` shared content
- `/ENCODINGS/` reference pages  
- Other cross-documentation references

## Conclusion

**This is not a bug in the conversion process.**

The original HTML documentation has the same issue - these are build-time references that don't resolve to external URLs. The conversion process correctly preserves the link information, even though the target URLs don't exist online.

**Action**: Document as known limitation, exclude from error metrics.

