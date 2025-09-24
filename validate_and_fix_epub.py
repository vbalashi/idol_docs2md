import os
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from lxml import etree
from lxml.etree import XMLParser, XMLSyntaxError

################################################################################
# CONFIG
################################################################################

# We'll place missing media in [epub_root]/EPUB/media/<filename>
# Then references in .xhtml become relative paths like ../media/foo.png.
MEDIA_DIR_NAME = "media"  # inside the EPUB/ folder

# We'll skip copying these (core) files so we don’t create duplicates
SKIP_EXTENSIONS = {'.xhtml', '.html', '.htm', '.opf', '.ncx'}
SKIP_FILES = {'container.xml', 'nav.xhtml', 'mimetype', 'toc.ncx', 'content.opf'}

# We'll treat these as "media" that we do want to fix/copy
MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.js', '.ttf', '.otf'}

################################################################################
# Basic I/O
################################################################################

def user_input(prompt, default=None):
    if default:
        prompt = f"{prompt} (Press Enter for default: {default}): "
    val = input(prompt).strip()
    return val if val else default

def extract_epub(epub_path, extract_to):
    with zipfile.ZipFile(epub_path, 'r') as zf:
        zf.extractall(extract_to)

def repack_epub(epub_root, original_epub_path, out_epub=None):
    if not out_epub:
        base_dir = os.path.dirname(original_epub_path)
        base_name = os.path.basename(original_epub_path)
        out_epub = os.path.join(base_dir, f"fixed_{base_name}")

    if os.path.exists(out_epub):
        os.remove(out_epub)

    with zipfile.ZipFile(out_epub, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Store mimetype with no compression
        mimetype_file = os.path.join(epub_root, 'mimetype')
        if os.path.isfile(mimetype_file):
            zf.write(mimetype_file, 'mimetype', compress_type=zipfile.ZIP_STORED)

        for root, dirs, files in os.walk(epub_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, epub_root)
                if rel_path == 'mimetype':
                    continue
                zf.write(full_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)

    print(f"[INFO] New EPUB created at: {out_epub}")

################################################################################
# Gather references from OPF + XHTML
################################################################################

def find_opf_file(epub_root):
    for root, dirs, files in os.walk(epub_root):
        for f in files:
            if f.lower().endswith('.opf'):
                return os.path.join(root, f)
    return None

def parse_opf_for_manifest(opf_path):
    refs = set()
    parser = XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    try:
        tree = etree.parse(opf_path, parser=parser)
        root = tree.getroot()
        nsmap = root.nsmap.copy()
        if None in nsmap:
            nsmap['opf'] = nsmap.pop(None)

        xpaths = [
            '//opf:manifest/opf:item',
            '//manifest/item',
            '//*[local-name()="manifest"]/*[local-name()="item"]'
        ]
        for xp in xpaths:
            items = root.xpath(xp, namespaces=nsmap) or []
            for item in items:
                href = item.get('href')
                if href and not href.lower().startswith(('http:', 'https:')):
                    refs.add(href)
    except Exception as ex:
        print(f"[WARN] parse_opf_for_manifest error: {ex}")
    return refs

def parse_xhtml_for_resources(xhtml_path):
    refs = set()
    parser = XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    try:
        tree = etree.parse(xhtml_path, parser=parser)
        root = tree.getroot()
        if root is None:
            return refs
        elems = root.xpath('//*[@src or @href or @xlink:href]',
                           namespaces={'xlink':'http://www.w3.org/1999/xlink'})
        for el in elems:
            for attr in ['src','href','{http://www.w3.org/1999/xlink}href']:
                val = el.get(attr)
                if val and not val.lower().startswith(('http:', 'https:')):
                    refs.add(val)
    except Exception as ex:
        print(f"[WARN] parse_xhtml_for_resources error: {ex}")
    return refs

def gather_all_references(epub_root):
    all_refs = set()
    opf_file = find_opf_file(epub_root)
    if opf_file:
        all_refs |= parse_opf_for_manifest(opf_file)

    for root, dirs, files in os.walk(epub_root):
        for f in files:
            if f.lower().endswith(('.xhtml','.html','.htm')):
                xhtml_path = os.path.join(root, f)
                all_refs |= parse_xhtml_for_resources(xhtml_path)

    return all_refs

################################################################################
# Deciding skip or media
################################################################################

def is_skip_file(path):
    """
    Return True if path is .xhtml, .opf, etc.
    """
    fn = os.path.basename(path).lower()
    if fn in SKIP_FILES:
        return True
    ext = os.path.splitext(fn)[1]
    if ext in SKIP_EXTENSIONS:
        return True
    return False

def is_media_file(path):
    """
    Return True if extension is in MEDIA_EXTENSIONS
    """
    ext = os.path.splitext(path)[1].lower()
    return (ext in MEDIA_EXTENSIONS)

################################################################################
# Converting angle brackets
################################################################################

def naive_convert_angles(txt):
    result = []
    i = 0
    in_tag = False
    known_starts = (
        '<p','<div','<span','<a','<img','<h1','<h2','<h3','<h4','<h5','<h6',
        '<ul','<ol','<li','<table','<tr','<td','<th','<em','<strong','<b','<i',
        '<br','<hr','<!','<?'
    )
    while i < len(txt):
        c = txt[i]
        if c == '<':
            snippet = txt[i:].lower()
            if any(snippet.startswith(k) for k in known_starts):
                result.append('<')
                in_tag = True
            else:
                result.append('&lt;')
            i += 1
        elif c == '>':
            if in_tag:
                result.append('>')
                in_tag = False
            else:
                result.append('&gt;')
            i += 1
        else:
            result.append(c)
            i += 1
    return ''.join(result)

def fix_angle_brackets_in_element(root):
    changed = False
    for el in root.iter():
        if el.text and ('<' in el.text or '>' in el.text):
            new_text = naive_convert_angles(el.text)
            if new_text != el.text:
                el.text = new_text
                changed = True
        if el.tail and ('<' in el.tail or '>' in el.tail):
            new_tail = naive_convert_angles(el.tail)
            if new_tail != el.tail:
                el.tail = new_tail
                changed = True
    return changed

################################################################################
# PART 6: Actually place missing media in "EPUB/media/"
################################################################################

def find_file_recursively(folder, filename):
    for r, dirs, files in os.walk(folder):
        if filename in files:
            return os.path.join(r, filename)
    return None

def unify_to_epub_media(absolute_epub_root, resource_path):
    """
    1) resource_path might be absolute or local with subfolders or drive letters.
       We'll just keep the final filename.
    2) We'll physically place the file in [absolute_epub_root]/EPUB/media/<filename>.
    3) Return (dest_abs, final_filename) so the caller can do the copy if missing.
    """
    # strip #fragment
    resource_path = resource_path.split('#',1)[0].replace('\\','/')
    # remove drive letter if any
    if ':' in resource_path:
        resource_path = resource_path.split(':',1)[-1]
    resource_path = resource_path.lstrip('/')
    filename = os.path.basename(resource_path)

    # The physical path where we want to store the file
    dest_abs = os.path.join(absolute_epub_root, 'EPUB', MEDIA_DIR_NAME, filename)
    return (dest_abs, filename)

def fix_missing_media(epub_root, references, original_epub_dir):
    """
    Copy only "media" type files (images, css, etc.) into [epub_root]/EPUB/media/<filename>
    if they are missing.
    """
    print("[INFO] Checking for missing media...")

    search_folder = None
    missing_count = 0

    for ref in sorted(references):
        if is_skip_file(ref):
            continue
        if not is_media_file(ref):
            continue

        dest_abs, fname = unify_to_epub_media(epub_root, ref)
        if os.path.isfile(dest_abs):
            continue  # we already have it

        # Not present
        missing_count += 1
        print(f"\n[INFO] Missing resource: {fname}")
        found_in_epub = find_file_recursively(epub_root, fname)
        if found_in_epub:
            os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
            shutil.copy2(found_in_epub, dest_abs)
            print(f"[INFO] Found in epub: {found_in_epub} => {dest_abs}")
            continue

        # Not in epub, ask user
        if not search_folder:
            print("[INFO] Not found in unzipped EPUB.")
            default_search = original_epub_dir
            search_folder = user_input("Enter folder path to locate missing media", default=default_search)
            if not search_folder or not os.path.isdir(search_folder):
                print("[WARN] Invalid folder. No external search.")
                search_folder = None

        if search_folder and os.path.isdir(search_folder):
            found_external = find_file_recursively(search_folder, fname)
            if found_external:
                os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
                shutil.copy2(found_external, dest_abs)
                print(f"[INFO] Copied from {found_external} => {dest_abs}")
            else:
                print(f"[WARN] Could not find {fname} in {search_folder}, skipping.")
        else:
            print(f"[WARN] Resource {fname} still missing, skipping.")

    if missing_count == 0:
        print("[INFO] No missing media found.")
    else:
        print(f"[INFO] Done. {missing_count} missing media resources processed.")

################################################################################
# PART 7: Rewriting xhtml references to "../media/filename"
################################################################################

def compute_relative_path(xhtml_file_abs, media_file_abs):
    """
    xhtml_file_abs = e.g. [epub_root]/EPUB/text/ch003.xhtml
    media_file_abs = e.g. [epub_root]/EPUB/media/file7.png
    We want the relative path from the xhtml folder to the media file.
      e.g. "../media/file7.png"
    """
    xhtml_dir = os.path.dirname(xhtml_file_abs)
    rel_path = os.path.relpath(media_file_abs, xhtml_dir)
    # Convert backslashes to forward slashes
    rel_path = rel_path.replace('\\','/')
    return rel_path

def rewrite_xhtml_references(epub_root):
    """
    - For each .xhtml or .html:
      1) parse
      2) for each src/href with a "media" extension, unify physically to [epub_root]/EPUB/media/<filename>
      3) compute relative path from .xhtml's folder to the media file, e.g. "../media/file.png"
      4) fix angle brackets
      5) write back if changed
    """
    print("[INFO] Rewriting references in XHTML so they're relative to 'EPUB/media/<filename>'...")

    parser = XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    for root, dirs, files in os.walk(epub_root):
        for f in files:
            if not f.lower().endswith(('.xhtml','.html','.htm')):
                continue

            xhtml_abs = os.path.join(root, f)
            changed = False
            try:
                tree = etree.parse(xhtml_abs, parser=parser)
                xroot = tree.getroot()
                if xroot is None:
                    continue

                # find all src/href
                elems = xroot.xpath('//*[@src or @href or @xlink:href]',
                                    namespaces={'xlink':'http://www.w3.org/1999/xlink'})
                for el in elems:
                    for attr in ['src','href','{http://www.w3.org/1999/xlink}href']:
                        val = el.get(attr)
                        if not val or val.lower().startswith(('http:','https:')):
                            continue
                        # skip if it's .xhtml
                        if is_skip_file(val):
                            continue
                        # skip if not a media extension
                        if not is_media_file(val):
                            continue

                        # we unify physically to [epub_root]/EPUB/media/<filename>
                        # then compute relative from xhtml file
                        media_abs, fname = unify_to_epub_media(epub_root, val)
                        if os.path.isfile(media_abs):
                            # compute relative path
                            rel_path = compute_relative_path(xhtml_abs, media_abs)
                            if rel_path != val:
                                el.set(attr, rel_path)
                                changed = True

                # fix angle brackets
                if fix_angle_brackets_in_element(xroot):
                    changed = True

                if changed:
                    tree.write(xhtml_abs, encoding='utf-8', xml_declaration=True, pretty_print=True)

            except Exception as ex:
                print(f"[WARN] Could not rewrite {xhtml_abs}: {ex}")

################################################################################
# MAIN
################################################################################

def main():
    try:
        if len(sys.argv) < 2:
            print("Usage: python validate_and_fix_epub.py <your.epub>")
            sys.exit(0)

        epub_path = os.path.abspath(sys.argv[1])
        if not os.path.isfile(epub_path):
            print(f"[ERROR] File not found: {epub_path}")
            sys.exit(1)

        original_dir = os.path.dirname(epub_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            print("[INFO] Extracting EPUB to temp folder...")
            extract_epub(epub_path, tmpdir)

            print("[INFO] Gathering references from OPF + XHTML...")
            refs = gather_all_references(tmpdir)

            print("[INFO] Copying missing media into [EPUB/media]...")
            fix_missing_media(tmpdir, refs, original_dir)

            print("[INFO] Rewriting .xhtml references => relative to [EPUB/media]...")
            rewrite_xhtml_references(tmpdir)

            print("[INFO] Repacking EPUB...")
            repack_epub(tmpdir, epub_path)

        print("[INFO] Done.")
        print("[INFO] If PNG has CRC errors, re-save or run pngcrush. Check angle brackets in final xhtml.")
    except KeyboardInterrupt:
        print("[INFO] Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
