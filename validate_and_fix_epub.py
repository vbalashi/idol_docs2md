import os
import zipfile
import shutil
import tempfile
import fnmatch
import sys
from pathlib import Path
from lxml import etree
from lxml.etree import XMLParser
import re

def user_input(prompt, default=None):
    """
    Helper function to request input from user,
    returning 'default' if user just presses enter.
    """
    if default:
        prompt = f"{prompt} (Press Enter for default: {default}): "
    val = input(prompt)
    return val if val.strip() else default

def find_file_recursively(root_folder, filename):
    """
    Recursively search 'root_folder' for a file named 'filename'.
    Return the full path if found, otherwise None.
    """
    for dirpath, dirnames, files in os.walk(root_folder):
        if filename in files:
            return os.path.join(dirpath, filename)
    return None

def fix_path(path, base_dir):
    """
    Fix path issues in resource references:
    1. Convert absolute paths to relative
    2. Normalize path separators
    3. Remove any problematic path components
    4. Maintain consistent directory structure
    """
    # Remove any drive letters and absolute path components
    path = re.sub(r'^[A-Za-z]:|^/+', '', path)
    # Convert backslashes to forward slashes
    path = path.replace('\\', '/')
    # Remove any '..' components that might go above root
    path = '/'.join([p for p in path.split('/') if p and p != '..'])
    
    # Define standard directory mappings
    dir_mappings = {
        'images/': ['images/', 'EPUB/images/', 'media/'],
        'text/': ['text/', 'EPUB/text/'],
        'styles/': ['styles/', 'EPUB/styles/'],
        'Improve/': ['Improve/', 'improve/'],
        'Inquire/': ['Inquire/', 'inquire/'],
        'Languages/': ['Languages/', 'languages/'],
        'Components/': ['Components/', 'components/'],
        'Distribution/': ['Distribution/', 'distribution/'],
        'IndexProcess/': ['IndexProcess/', 'indexprocess/'],
        'RetrieveContent/': ['RetrieveContent/', 'retrievecontent/'],
        'Interact/': ['Interact/', 'interact/'],
        'Fields/': ['Fields/', 'fields/'],
        'Security/': ['Security/', 'security/'],
        'Investigate/': ['Investigate/', 'investigate/'],
        'ImprovePerformance/': ['ImprovePerformance/', 'improveperformance/'],
        'IntroductionTopics/': ['IntroductionTopics/', 'introductiontopics/'],
        'Configure/': ['Configure/', 'configure/'],
        'View/': ['View/', 'view/'],
        'Maintenance/': ['Maintenance/', 'maintenance/'],
        'EnrichContent/': ['EnrichContent/', 'enrichcontent/']
    }
    
    # First check if this is a file in a known directory
    for standard_dir, variants in dir_mappings.items():
        for variant in variants:
            if path.lower().startswith(variant.lower()):
                # Extract the filename and use the standard directory
                filename = os.path.basename(path)
                return f"{standard_dir}{filename}"
            elif os.path.exists(os.path.join(base_dir, standard_dir, os.path.basename(path))):
                return f"{standard_dir}{os.path.basename(path)}"
    
    # If not in a known directory, keep the original path structure if it exists
    if '/' in path and os.path.exists(os.path.join(base_dir, os.path.dirname(path))):
        return path
    
    # For files not in any specific directory, keep them at root
    return os.path.basename(path)

def validate_and_fix_xml(xml_path):
    """
    Validate XML/XHTML content and attempt to fix common issues.
    Returns True if file was modified, False otherwise.
    """
    try:
        parser = XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        tree = etree.parse(xml_path, parser=parser)
        
        # Check for and fix common issues
        modified = False
        root = tree.getroot()
        
        # Fix SVG references
        for elem in root.xpath('//*[@src or @href or @xlink:href]', 
                             namespaces={'xlink': 'http://www.w3.org/1999/xlink'}):
            for attr in ['src', 'href', '{http://www.w3.org/1999/xlink}href']:
                if attr in elem.attrib:
                    old_path = elem.get(attr)
                    if old_path and not old_path.lower().startswith(('http:', 'https:')):
                        new_path = fix_path(old_path, os.path.dirname(xml_path))
                        if new_path != old_path:
                            elem.set(attr, new_path)
                            modified = True
        
        if modified:
            # Write back the fixed content
            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            return True
            
    except Exception as e:
        print(f"Warning: Could not fully validate/fix {xml_path}: {str(e)}")
    
    return False

def collect_epub_resources(epub_root):
    """
    - Parse the OPF file (to find manifest references).
    - Gather references in xhtml files (optional but often needed).
    - Return a set of resource paths (relative to epub_root).
    """
    content_opf = None
    # Often the OPF is in a folder named 'OEBPS/' or at root. We'll do a naive search.
    for root, dirs, files in os.walk(epub_root):
        for f in files:
            if f.endswith('.opf'):
                content_opf = os.path.join(root, f)
                break
        if content_opf:
            break

    if not content_opf:
        print("No OPF file found. This EPUB might be invalid.")
        return set()

    manifest_resources = set()
    
    # First validate and fix the OPF file
    if validate_and_fix_xml(content_opf):
        print(f"Fixed issues in OPF file: {content_opf}")

    parser = XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    try:
        tree = etree.parse(content_opf, parser=parser)
        root = tree.getroot()
        
        # Handle namespaces properly
        nsmap = root.nsmap.copy()
        if None in nsmap:
            nsmap['def'] = nsmap.pop(None)
        
        # Try multiple namespace approaches
        for xpath in ['//def:manifest/def:item', '//manifest/item', '//*[local-name()="item"]']:
            try:
                for item in root.xpath(xpath, namespaces=nsmap):
                    href = item.get('href')
                    if href and not href.lower().startswith(('http:', 'https:')):
                        manifest_resources.add(fix_path(href, os.path.dirname(content_opf)))
            except:
                continue

    except Exception as e:
        print(f"Warning: Error parsing OPF file: {str(e)}")

    # Process all XHTML files
    for root_dir, dirs, files in os.walk(epub_root):
        for file in files:
            if file.endswith(('.xhtml', '.html', '.htm')):
                xhtml_path = os.path.join(root_dir, file)
                
                # Validate and fix the XHTML file
                if validate_and_fix_xml(xhtml_path):
                    print(f"Fixed issues in XHTML file: {xhtml_path}")
                
                try:
                    tree = etree.parse(xhtml_path, parser=parser)
                    root = tree.getroot()
                    
                    # Find all elements with src, href, or xlink:href attributes
                    for elem in root.xpath('//*[@src or @href or @xlink:href]',
                                         namespaces={'xlink': 'http://www.w3.org/1999/xlink'}):
                        for attr in ['src', 'href', '{http://www.w3.org/1999/xlink}href']:
                            if attr in elem.attrib:
                                href = elem.get(attr)
                                if href and not href.lower().startswith(('http:', 'https:')):
                                    manifest_resources.add(fix_path(href, root_dir))
                
                except Exception as e:
                    print(f"Warning: Error processing XHTML file {xhtml_path}: {str(e)}")
                    continue

    return manifest_resources

def verify_and_fix_resources(epub_root, resource_paths, original_epub_dir=None):
    """
    Check each resource path in 'resource_paths' if it exists in the unzipped epub.
    If missing, prompt user for an external folder to try and locate it.
    If found, copy it in place and fix path references if needed.
    """
    # Ask for search folder once at the beginning
    default_search_dir = original_epub_dir if original_epub_dir else os.path.dirname(epub_root)
    print("\nSome resources might be missing. Where should I look for them?")
    folder_to_search = user_input("Enter folder path to locate missing resources", default=default_search_dir)
    if not folder_to_search:
        print("No folder to search. Skipping resource verification.")
        return
    print(f"Will search for all missing resources in: {folder_to_search}\n")

    # Track processed files to avoid redundant moves
    processed_files = set()
    # Track file locations to maintain consistency
    file_locations = {}

    for res in resource_paths:
        # Skip fragment identifiers (e.g., file.html#section)
        if '#' in res:
            continue
            
        normalized_res = fix_path(res, epub_root)
        target_path = os.path.join(epub_root, normalized_res)
        
        # Skip if we've already processed this target path
        if target_path in processed_files:
            continue
        processed_files.add(target_path)
        
        # If the file exists at the normalized path, we're good
        if os.path.isfile(target_path):
            file_locations[os.path.basename(normalized_res)] = normalized_res
            continue
            
        # If we already know where this file should be, use that location
        filename = os.path.basename(normalized_res)
        if filename in file_locations:
            if os.path.exists(os.path.join(epub_root, file_locations[filename])):
                continue
            
        # If not found, try to locate it
        found_in_epub = False
        found_path = None

        # First try to find it anywhere in the epub
        for dirpath, _, files in os.walk(epub_root):
            if filename in files:
                found_path = os.path.join(dirpath, filename)
                if found_path != target_path:
                    found_in_epub = True
                break

        if not found_in_epub:
            # Try to find in the specified search folder
            print(f"Resource missing in EPUB: {normalized_res}")
            print(f"Scanning '{folder_to_search}' recursively...")
            external_path = find_file_recursively(folder_to_search, filename)
            if external_path:
                print(f"Found resource at: {external_path}")
                # Create the target directory if it doesn't exist
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(external_path, target_path)
                print(f"Copied resource into EPUB at: {target_path}")
                file_locations[filename] = normalized_res
            else:
                print(f"Resource not found anywhere under '{folder_to_search}'. Skipping.")
        else:
            # If found in epub but in wrong location, move it
            if found_path != target_path:
                target_dir = os.path.dirname(target_path)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                print(f"Moving resource from {found_path} to {target_path}")
                try:
                    shutil.move(found_path, target_path)
                    file_locations[filename] = normalized_res
                except Exception as e:
                    print(f"Warning: Could not move file: {str(e)}")
                    # If move fails, try copy instead
                    try:
                        shutil.copy2(found_path, target_path)
                        os.remove(found_path)
                        file_locations[filename] = normalized_res
                    except Exception as e2:
                        print(f"Warning: Could not copy file either: {str(e2)}")

def repack_epub(original_epub_path, epub_root, output_epub_path):
    """
    After modifications, rebuild the EPUB zip from 'epub_root' into 'output_epub_path'.
    """
    # If output_epub_path is not given, default to 'fixed_' + original
    if not output_epub_path:
        base_dir = os.path.dirname(original_epub_path)
        base_name = os.path.basename(original_epub_path)
        output_epub_path = os.path.join(base_dir, f"fixed_{base_name}")

    # Remove if already exists
    if os.path.exists(output_epub_path):
        os.remove(output_epub_path)

    # Re-zip everything in epub_root
    with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Important: an EPUB must have the file 'mimetype' at the root with no compression
        mimetype_path = os.path.join(epub_root, 'mimetype')
        if os.path.isfile(mimetype_path):
            # store with no compression
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

        for root, dirs, files in os.walk(epub_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, epub_root)
                # skip 'mimetype' because we already handled it
                if rel_path == 'mimetype':
                    continue
                zf.write(full_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)

    print(f"New EPUB created at: {output_epub_path}")

def main():
    # 1) Get the path to the .epub file from user
    if len(sys.argv) < 2:
        epub_path = user_input("Enter the path to your EPUB file")
        if not epub_path:
            print("No EPUB path provided. Exiting.")
            return
    else:
        epub_path = sys.argv[1]

    epub_path = os.path.abspath(epub_path)
    if not os.path.isfile(epub_path):
        print(f"File not found: {epub_path}")
        return

    # Store the original epub directory for resource searching
    original_epub_dir = os.path.dirname(epub_path)

    # 2) Create a temp directory to unpack
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            zf.extractall(tmpdir)

        # 3) Collect resource references from OPF/HTML
        resources = collect_epub_resources(tmpdir)

        # 4) Verify resources and fix broken links
        verify_and_fix_resources(tmpdir, resources, original_epub_dir)

        # 5) Repack the EPUB
        # We'll default output to same folder with prefix 'fixed_'
        output_epub = None  # or specify a path
        repack_epub(epub_path, tmpdir, output_epub)

if __name__ == "__main__":
    main()
