import os
import re
from typing import Optional, Tuple


def detect_doc_family_from_site_dir(site_dir: str) -> str:
    """Return 'idolserver' if site_dir denotes IDOLServer doc, else 'standard'."""
    return 'idolserver' if 'IDOLServer' in (site_dir or '') else 'standard'


def strip_rel_and_ext(path: str) -> tuple[str, str]:
    """
    Strips ../ prefixes and file extensions from a path, returning the cleaned path and any anchor.
    Example: ../../Shared_Admin/_ADM_Config.htm#My_Anchor -> ('Shared_Admin/_ADM_Config', '#My_Anchor')
    """
    # Split anchor first
    parts = path.split('#')
    p = parts[0]
    anchor = f'#{parts[1]}' if len(parts) > 1 else ''
    
    # Remove extension
    p = os.path.splitext(p)[0]
    
    # Normalize path separators for consistent processing
    p = p.replace('\\', '/')
    
    # Remove leading relative path segments, but keep the rest of the path intact
    # This avoids issues where paths don't start with '../' but are still valid
    if p.startswith('../'):
        p = re.sub(r'^(\.\./)+', '', p)
    
    return p, anchor


def normalize_target_path(path: str, family: str, idol_subfolder: Optional[str] = None) -> str:
    """Apply ordered normalization rules to a target path (no host/doc shell)."""
    # Rule 1: Shared_Admin → ensure under Content/
    if path.startswith('Shared_Admin/'):
        path = f'Content/{path}'

    # Rule 2: ENCODINGS reference page variations → ensure Content/Actions/ENCODINGS
    if 'ENCODINGS/_IDOL_ENCODINGS.htm' in path:
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


def build_online_url(base_url: str,
                     site_dir: str,
                     path: str,
                     anchor: str = '',
                     family: Optional[str] = None,
                     subfolder: Optional[str] = None) -> str:
    """Build final online URL for the given normalized path and doc family."""
    fam = family or detect_doc_family_from_site_dir(site_dir)
    if fam == 'idolserver':
        sub = (subfolder or '').split('/')[-1] if subfolder else ''
        if sub:
            return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Guides/html/{sub}/{path}{anchor}"
        # Fallback without subfolder (should be rare)
        return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Guides/html/{path}{anchor}"
    # standard
    return f"{base_url.rstrip('/')}/{site_dir.strip('/')}/Help/{path}{anchor}"


