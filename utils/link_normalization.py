import os
import re
from typing import Optional, Tuple

# Canonical casing for known documentation path segments so that we do not
# inadvertently downcase directories like Content or GrammarReference when
# reconstructing online URLs.
CANONICAL_SEGMENTS = {
    'content': 'Content',
    'actions': 'Actions',
    'shared_admin': 'Shared_Admin',
    'grammarreference': 'GrammarReference',
    'guides': 'Guides',
    'html': 'html',
}


def detect_doc_family_from_site_dir(site_dir: str) -> str:
    """Return 'idolserver' if site_dir denotes IDOLServer doc, else 'standard'."""
    return 'idolserver' if 'IDOLServer' in (site_dir or '') else 'standard'


def strip_rel_and_ext(path: str) -> tuple[str, str, str]:
    """
    Strips ../ prefixes and file extensions from a path, returning the cleaned path,
    the anchor (if present), and the original file extension (including the dot).
    Example: ../../Shared_Admin/_ADM_Config.htm#My_Anchor -> ('Shared_Admin/_ADM_Config', '#My_Anchor', '.htm')
    Missing extensions default to '.htm'; '.md' inputs are normalized to '.htm'
    """
    # Split anchor first
    parts = path.split('#')
    p = parts[0]
    anchor = f'#{parts[1]}' if len(parts) > 1 else ''
    p, ext = os.path.splitext(p)
    ext = (ext or '').lower()
    if not ext:
        ext = '.htm'
    elif ext == '.md':
        ext = '.htm'
    elif ext not in ('.htm', '.html'):
        # retain uncommon extensions as-is (already includes dot from splitext)
        pass
    
    # Normalize path separators for consistent processing
    p = p.replace('\\', '/')
    
    # Remove leading relative path segments, but keep the rest of the path intact
    # This avoids issues where paths don't start with '../' but are still valid
    if p.startswith('../'):
        p = re.sub(r'^(\.\./)+', '', p)
    
    return p, anchor, ext


def _apply_canonical_segment_case(path: str) -> str:
    """Rewrite known path segments to the casing published online."""
    if not path:
        return path
    pieces = []
    for segment in path.split('/'):
        lower = segment.lower()
        pieces.append(CANONICAL_SEGMENTS.get(lower, segment))
    return '/'.join(pieces)


def normalize_target_path(path: str, family: str, idol_subfolder: Optional[str] = None) -> str:
    """Apply ordered normalization rules to a target path (no host/doc shell)."""
    path = (path or '').replace('\\', '/')
    path = _apply_canonical_segment_case(path)

    # Rule 1: Shared_Admin → ensure under Content/
    if path.startswith('Shared_Admin/'):
        path = f'Content/{path}'

    # Rule 2: ENCODINGS reference page variations → ensure Content/Actions/ENCODINGS
    if 'ENCODINGS/_IDOL_ENCODINGS' in path:
        if path.startswith('ENCODINGS/'):
            path = f'Content/Actions/{path}'
        elif path.startswith('Actions/ENCODINGS/'):
            path = f'Content/{path}'

    # Rule 3: Plain Actions/ → ensure under Content/
    if path.startswith('Actions/') and not path.startswith('Actions/ENCODINGS/'):
        path = f'Content/{path}'

    # Rule 4: Standard family fallback → ensure path starts with Content/
    if family != 'idolserver' and not path.startswith('Content/'):
        path = f'Content/{path}'

    # Rule 5: IDOLServer safety — ensure Content/ exists for idolserver too
    if family == 'idolserver' and not path.startswith('Content/'):
        path = f'Content/{path}'

    # Rule 6: IDOLServer expert — ensure Content/IDOLExpert/ prefix when missing
    if family == 'idolserver' and (idol_subfolder or '').lower() == 'expert':
        if path.startswith('Content/') and not path.startswith('Content/IDOLExpert/') \
           and not path.startswith('Content/Shared_Admin/') \
           and not path.startswith('Content/OmniGroupServer/') \
           and not path.startswith('Content/IAS/'):
            path = 'Content/IDOLExpert/' + path[len('Content/'):]

    # Rule 7: IDOLServer documentsecurity — remap legacy MappedSecurity tree
    if family == 'idolserver' and path.startswith('Content/MappedSecurity/'):
        path = 'Content/OmniGroupServer/' + path[len('Content/MappedSecurity/'):] 

    return path


def _normalize_online_subfolder(site_dir: Optional[str], subfolder: Optional[str]) -> str:
    """Normalize a subfolder hint to the portion expected in the published URL."""
    if not subfolder:
        return ''
    sub = subfolder.replace('\\', '/').strip('/')
    if not sub:
        return ''
    site = (site_dir or '').strip('/')
    if site and sub.startswith(site):
        sub = sub[len(site):].lstrip('/')
    if sub.lower() == 'help':
        return 'Help'
    if sub.lower().endswith('/help'):
        return 'Help'
    return sub


def build_online_url(base_url: str,
                     site_dir: str,
                     path: str,
                     anchor: str = '',
                     family: Optional[str] = None,
                     subfolder: Optional[str] = None) -> str:
    """Build final online URL for the given normalized path and doc family."""
    fam = family or detect_doc_family_from_site_dir(site_dir)
    path = path.lstrip('/')
    sub = _normalize_online_subfolder(site_dir, subfolder)

    if 'Content/Shared_Admin/' in path:
        license_site = re.sub(r'IDOLServer', 'LicenseServer', site_dir, flags=re.IGNORECASE)
        target_site = license_site or site_dir
        return f"{base_url.rstrip('/')}/{target_site.strip('/')}/Help/{path}{anchor}"

    if fam == 'idolserver':
        sub_idol = sub.split('/')[-1] if sub else ''
        if sub_idol:
            return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Guides/html/{sub_idol}/{path}{anchor}"
        # Fallback without subfolder (should be rare)
        return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Guides/html/{path}{anchor}"
    # standard
    if sub and sub.lower() != 'help':
        return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/{sub}/{path}{anchor}"
    return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Help/{path}{anchor}"
