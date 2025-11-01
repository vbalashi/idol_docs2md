# Link Conversion Rules and Exceptions

## Ground truth (online structure)

- Standard docs (Content, Category, Community, most connectors):
  - {base}/{Doc}/Help/Content/{path}
  - Example: `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/Content_25.4_Documentation/Help/Content/Actions/Query/Query.htm`

- IDOLServer (merged, 3 subfolders):
  - {base}/IDOLServer_25.4_Documentation/Guides/html/{subfolder}/Content/{path}
  - Getting Started example: `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/gettingstarted/Content/Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm`
  - Expert example: `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/expert/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm`

## Current implementation locations

- `02_convert_to_md.py`
  - `generate_concatenated_md()` — rewrites first header link (Standard → `/Help/Content/…`; IDOLServer → `/Guides/html/{subfolder}/Content/…`).
  - `fix_cross_references()` — context-aware rewrite using BEGIN_FILE mapping; special handling for Shared_Admin and ENCODINGS; subfolder inference gated to IDOLServer.
- `validate_links.py` — random spot checker.

## Problem patterns seen (and status)

- Missing `/Help/` on standard docs → fixed by always using `/Help/Content/`.
- IDOLServer missing `/Guides/html/` prefix → fixed (gated on family detection).
- Shared_Admin links missing `Content/` and wrong subfolder → fixed with context-aware handling.
- ENCODINGS links missing `Content/` and/or `Actions/` → normalized to `/Help/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm`.
- Over-broad subfolder inference on standard docs → fixed (inference gated to IDOLServer only).

## Normalization pipeline (apply in order on target path)

Given a relative href after stripping `../` and converting `.md`→`.htm`:

1. If path starts with `Shared_Admin/` → prefix `Content/`.
2. If path contains `ENCODINGS/_IDOL_ENCODINGS.htm`:
   - If starts with `ENCODINGS/` → `Content/Actions/{path}`.
   - If starts with `Actions/ENCODINGS/` → `Content/{path}`.
3. If path starts with `Actions/` (and not matched by 2) → prefix `Content/`.
4. If family is Standard (not IDOLServer) and path does not start with `Content/` → prefix `Content/`.
5. Build the final URL shell:
   - Standard: `/{Doc}/Help/{path}` (path includes `Content/...`).
   - IDOLServer: `/{Doc}/Guides/html/{subfolder}/{path}` (subfolder from BEGIN_FILE context: expert/gettingstarted/documentsecurity).

Notes:
- Keep case-sensitive segments: `Content`, `Actions`, `ENCODINGS`.
- Preserve anchors exactly as in source.

## Detect merged vs single-bundle (scanner heuristics)

- Merged (IDOLServer-like): `{doc}/Guides/html/{expert|gettinstarted|documentsecurity}/(Content|Data|Resources|Skins)` present.
- Single-bundle: `{doc}/Help/(Content|Data|Resources|Skins)` present directly.
- Else: mark exceptional; scan to depth≤3 for triad and record layout.

## Optional: process IDOLServer subfolders independently

- Feasibility check: per-subfolder, scan links for `../../` that resolve outside the subfolder.
- If no cross-subfolder refs, optionally emit three outputs; else keep merged.

## Tests (table-driven)

Cover at least:
- Shared_Admin variants → `/Content/Shared_Admin/...` under correct shell.
- ENCODINGS variants → `/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm`.
- Plain `Actions/...` → `/Content/Actions/...`.
- Already-correct `Content/...` → unchanged shelling.
- IDOLServer three subfolders + Standard family.

## Citations

- Getting Started, Search and Retrieval: `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/gettingstarted/Content/Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm`
- Expert, Categorize Documents: `https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/IDOLServer_25.4_Documentation/Guides/html/expert/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm`


