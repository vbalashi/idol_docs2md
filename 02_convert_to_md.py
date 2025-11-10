import os
import shutil
import argparse
import concurrent.futures
from tqdm import tqdm
from bs4 import BeautifulSoup
import bleach
import re
import json
import logging
import traceback
from markdownify import markdownify as md
import hashlib
from utils.link_normalization import (
    detect_doc_family_from_site_dir,
    strip_rel_and_ext,
    normalize_target_path,
    build_online_url,
)

# Set up logging for the converter module.
# Avoid propagating to the root logger so console output stays quiet unless explicitly enabled.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    logger.addHandler(logging.NullHandler())

# Blacklist patterns for files that should be excluded from concatenation
# These files typically contain navigation elements, search forms, or other non-content pages
BLACKLISTED_FILES = [
    '_FT_SideNav_Startup.md',
    'index.md',
    'index_CSH.md',
    'Default.md',
    'Default_CSH.md',
    'search-results.md',
    'search.md',
]

def is_blacklisted(filepath):
    """
    Check if a filepath should be excluded from the TOC based on blacklist patterns.
    
    Args:
        filepath: The relative markdown file path (e.g., 'Content/Shared_Admin/index.md')
    
    Returns:
        True if the file should be excluded, False otherwise
    """
    # Get the basename of the file
    basename = os.path.basename(filepath)
    
    # Check exact matches
    if basename in BLACKLISTED_FILES:
        logger.info(f"Blacklisted file excluded: {filepath}")
        return True
    
    # Check for files in Shared_* directories (often contain cover pages/navigation)
    if 'Shared_' in filepath or '/Shared_' in filepath or '\\Shared_' in filepath:
        # Allow some shared content but exclude covers and navigation
        if ('Cover' in basename or 'Nav' in basename) and basename.startswith('_'):
            logger.info(f"Blacklisted shared file excluded: {filepath}")
            return True
    
    return False

def parse_js_define_call(js_content):
    """
    Parse JavaScript files that contain define() calls with JSON-like objects.
    This replaces the js2py functionality for parsing TOC files.
    """
    try:
        # Remove comments and clean up the JavaScript content
        # Remove single-line comments
        js_content = re.sub(r'//.*', '', js_content)
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Find the define() call and extract the object
        # Look for define({ ... }) or define( { ... } )
        define_pattern = r'define\s*\(\s*(\{.*\})\s*\)'
        match = re.search(define_pattern, js_content, re.DOTALL)
        
        if not match:
            return None
            
        obj_str = match.group(1)
        
        # Convert JavaScript object notation to JSON
        # Replace single quotes with double quotes
        obj_str = re.sub(r"'([^']*)'", r'"\1"', obj_str)
        
        # Handle unquoted property names (convert to quoted)
        obj_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', obj_str)
        
        # Handle trailing commas
        obj_str = re.sub(r',\s*}', '}', obj_str)
        obj_str = re.sub(r',\s*]', ']', obj_str)
        
        # Try to parse as JSON
        try:
            return json.loads(obj_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, try a more aggressive cleanup
            # Remove any remaining JavaScript-specific syntax
            obj_str = re.sub(r'undefined', 'null', obj_str)
            obj_str = re.sub(r'\btrue\b', 'true', obj_str)
            obj_str = re.sub(r'\bfalse\b', 'false', obj_str)
            
            return json.loads(obj_str)
            
    except Exception as e:
        logger.warning(f"Failed to parse JavaScript define call: {e}")
        return None

def process_base_folder(base_folder, image_extensions, max_workers, online_base_url=None, online_site_dir=None, assets_dirname=None, subfolder_name=None):
    images = []
    html_files = []

    # Step 1 and 2: Collect images and HTML files
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if file.lower().endswith(tuple(image_extensions)):
                images.append(file_path)
            elif file.lower().endswith(('.htm', '.html')):
                html_files.append(file_path)

    # Create target directories
    md_dir = os.path.join(base_folder, 'md')
    images_dir = os.path.join(md_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # Attach a per-base-folder file logger and ensure cleanup
    file_handler = None
    try:
        log_path = os.path.join(md_dir, 'generate_documents.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
        logger.addHandler(file_handler)

        # Copy images
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(tqdm(
                executor.map(lambda img: copy_image(img, images_dir),
                            images),
                total=len(images),
                desc='  Copying images',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]'
            ))

        # Convert HTML files to Markdown
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(tqdm(
                executor.map(lambda html: convert_html_to_md(html, base_folder, md_dir),
                            html_files),
                total=len(html_files),
                desc='  Converting to MD',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]'
            ))

        # Parse TOC files
        toc_pairs = extract_tocs(base_folder)
        if toc_pairs:
            parse_toc_files(toc_pairs, base_folder, md_dir)
            # Adjust headers after TOC parsing
            adjust_headers(md_dir)
            # Generate concatenated Markdown file
            concatenated_md_path = generate_concatenated_md(base_folder, md_dir, online_base_url=online_base_url, online_site_dir=online_site_dir, subfolder_name=subfolder_name)
            external_md_path = None
            if concatenated_md_path and online_base_url and online_site_dir:
                external_md_path = create_external_version(
                    concatenated_md_path,
                    base_folder,
                    md_dir,
                    online_base_url,
                    online_site_dir,
                    subfolder_name,
                )
            # Update internal links in the concatenated file
            if concatenated_md_path:
                update_internal_links(concatenated_md_path)
                # Fix cross-references to external documents
                fix_cross_references(concatenated_md_path, online_base_url, online_site_dir, subfolder_name)
                # Re-run link normalization to clean up any fragments reintroduced by cross-reference handling
                update_internal_links(concatenated_md_path)
                # Validate anchors used vs available
                validate_internal_anchors(concatenated_md_path)
                # Centralize assets into md/assets and rewrite references
                unify_assets(concatenated_md_path, md_dir, assets_dirname=assets_dirname or "assets")
                if external_md_path and os.path.exists(external_md_path):
                    unify_assets(external_md_path, md_dir, assets_dirname=assets_dirname or "assets")

                def clean_and_finalize(md_path, refresh_internal_links):
                    if not md_path or not os.path.exists(md_path):
                        return
                    try:
                        with open(md_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        cleaned_content = clean_markdown_content(content)
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_content)
                        logger.info(f"Cleaned unwanted elements from {md_path}")
                        if refresh_internal_links and dedupe_global_anchors(md_path):
                            update_internal_links(md_path)
                            validate_internal_anchors(md_path)
                    except Exception as clean_error:
                        logger.warning(f"Error during post-processing cleanup for {md_path}: {clean_error}")

                clean_and_finalize(concatenated_md_path, refresh_internal_links=True)
                clean_and_finalize(external_md_path, refresh_internal_links=False)
        else:
            logger.warning(f"No TOC files found in {base_folder}")
    finally:
        if file_handler is not None:
            try:
                logger.removeHandler(file_handler)
                file_handler.close()
            except Exception:
                pass

def copy_image(src, images_dir):
    try:
        filename = os.path.basename(src)
        dest_path = os.path.join(images_dir, filename)

        # Handle duplicate filenames by appending a unique suffix
        if os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            counter = 1
            while True:
                new_filename = f"{name}_{counter}{ext}"
                new_dest_path = os.path.join(images_dir, new_filename)
                if not os.path.exists(new_dest_path):
                    dest_path = new_dest_path
                    break
                counter += 1

        shutil.copy2(src, dest_path)
    except Exception as e:
        logger.error(f"Error copying image {src}: {e}")

def extract_main_content(soup):
    main_content = soup.find('div', {'role': 'main', 'id': 'mc-main-content'})
    if not main_content:
        main_content = soup.find('div', {'class': 'main-content'})
    return main_content

def hoist_named_anchors(root):
    """Move <a name|id="..."></a> out of heading tags and insert a single standalone anchor before the heading.
    Preference order:
        1. First non-kanchor anchor appearing in the heading.
        2. Generated slug from the heading text when no friendly anchor exists.
    """
    if root is None:
        return
    try:
        headings = root.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    except Exception:
        return

    slug_counts = {}
    used_ids = set()

    def next_slug(text):
        base = generate_markdown_anchor(text) if text else ''
        if not base:
            base = 'section'
        count = slug_counts.get(base, 0)
        candidate = base if count == 0 else f"{base}-{count}"
        slug_counts[base] = count + 1
        while candidate in used_ids:
            count = slug_counts.get(base, 0)
            candidate = f"{base}-{count}"
            slug_counts[base] = count + 1
        return candidate

    for h in headings:
        try:
            anchors = h.find_all('a')
        except Exception:
            anchors = []
        if not anchors:
            continue

        heading_text = h.get_text(separator=' ', strip=True)
        candidate_ids = []
        for a in anchors:
            name_or_id = a.get('name') or a.get('id')
            if name_or_id:
                candidate_ids.append(name_or_id)

        # Determine preferred anchor id
        preferred = None
        for aid in candidate_ids:
            if not re.match(r'^kanchor\d+$', aid, re.IGNORECASE):
                preferred = aid
                break
        if preferred and preferred in used_ids:
            preferred = None

        if not preferred:
            preferred = next_slug(heading_text)

        # Insert the chosen anchor before the heading
        new_a = root.new_tag('a')
        new_a['id'] = preferred
        h.insert_before(new_a)
        used_ids.add(preferred)

        # Remove legacy anchors from inside the heading to keep the header clean
        for a in anchors:
            try:
                if (not a.text or not a.text.strip()) and len(a.contents) == 0:
                    a.decompose()
                else:
                    a.unwrap()
            except Exception:
                pass

def sanitize_html(html_content):
    # Define allowed tags and attributes
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ol', 'ul', 'li', 'a', 'img', 'blockquote', 'code', 'pre', 'hr', 'div', 'span',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'col', 'colgroup'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'id', 'name'],
        'img': ['src', 'alt', 'title'],
        'div': ['class'],
        'span': ['class'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan']
    }

    # Sanitize the HTML content
    clean_html = bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    return clean_html

def convert_html_to_md(input_file, base_folder, md_dir):
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as html_file:
            html_content = html_file.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = extract_main_content(soup)

        if main_content is None:
            logger.warning(f"Warning: Could not extract main content from {input_file}")
            main_content = soup  # Use entire content if main content not found

        # Preserve legacy anchors: hoist <a name>/<a id> out of headings
        try:
            hoist_named_anchors(main_content)
        except Exception:
            pass

        # Sanitize the HTML content using Bleach
        sanitized_content = sanitize_html(str(main_content))

        # Convert to Markdown using markdownify and adjust links
        markdown_content = convert_to_markdown(sanitized_content, input_file, base_folder, md_dir)

        # Determine the output markdown file path, preserving directory structure
        relative_md_path = os.path.relpath(input_file, base_folder)
        md_output_path = os.path.splitext(os.path.join(md_dir, relative_md_path))[0] + '.md'
        md_output_dir = os.path.dirname(md_output_path)
        os.makedirs(md_output_dir, exist_ok=True)

        # Write the markdown file
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

    except Exception as e:
        logger.error(f"Error converting {input_file} to Markdown: {e}\n{traceback.format_exc()}")

def convert_to_markdown(html_content, input_file, base_folder, md_dir):
    # Preserve empty anchor tags by converting them to placeholders pre-conversion
    def anchor_to_placeholder(match):
        aid = match.group(1)
        return f'[[ANCHOR::{aid}]]'

    html_with_placeholders = re.sub(
        r'<a\s+(?:id|name)=["\']([^"\']+)["\'][^>]*>\s*</a>',
        anchor_to_placeholder,
        html_content,
        flags=re.IGNORECASE
    )

    # Convert HTML to Markdown using markdownify
    markdown_content = md(html_with_placeholders, heading_style="ATX")

    # Restore placeholders back to HTML anchors
    def placeholder_to_anchor(match):
        aid = match.group(1)
        return f'<a id="{aid}"></a>'

    markdown_content = re.sub(r'\[\[ANCHOR::([^\]]+)\]\]', placeholder_to_anchor, markdown_content)

    # Adjust image links
    markdown_content = re.sub(
        r'!\[(.*?)\]\((.*?)\)',
        lambda m: adjust_image_link(m, md_dir),
        markdown_content
    )

    # Adjust internal links
    markdown_content = re.sub(
        r'\[(.*?)\]\((.*?)\)',
        lambda m: adjust_internal_link(m, input_file, base_folder, md_dir),
        markdown_content
    )

    return markdown_content

def adjust_image_link(match, images_dir):
    alt_text = match.group(1)
    src = match.group(2)

    filename = os.path.basename(src)
    new_src = f"images/{filename}"

    return f'![{alt_text}]({new_src})'

def adjust_internal_link(match, input_file, base_folder, md_dir):
    link_text = match.group(1)
    href = match.group(2)

    # Ignore external links
    if re.match(r'^(http|https|mailto):', href):
        return match.group(0)

    # Only process .htm and .html links
    if not href.lower().endswith(('.htm', '.html')):
        return match.group(0)

    # Resolve the target HTML file path from the base_folder
    # This correctly handles ../ patterns by resolving from the documentation root
    href_no_anchor = href.split('#')[0]
    anchor_suffix = ''
    if '#' in href:
        anchor_suffix = '#' + href.split('#', 1)[1]
    current_dir = os.path.dirname(os.path.relpath(input_file, base_folder))
    target_rel_path = os.path.normpath(os.path.join(current_dir, href_no_anchor))
    target_html_path = os.path.join(base_folder, target_rel_path)

    if not os.path.isfile(target_html_path):
        logger.warning(f"Linked HTML file {target_html_path} not found (from {input_file} with href {href}). Leaving original link.")
        return match.group(0)

    # Determine the corresponding Markdown file path
    relative_target_path = os.path.relpath(target_html_path, base_folder)
    target_md_path = os.path.splitext(os.path.join(md_dir, relative_target_path))[0] + '.md'

    # Compute the relative path from the current Markdown file to the target Markdown file
    current_md_path = get_md_path(input_file, base_folder, md_dir)
    relative_path = os.path.relpath(target_md_path, os.path.dirname(current_md_path))

    # Replace backslashes with forward slashes for Markdown
    relative_path = relative_path.replace('\\', '/')

    return f'[{link_text}]({relative_path}{anchor_suffix})'

def get_md_path(html_path, base_folder, md_dir):
    """
    Given an HTML file path, return the corresponding Markdown file path in the md_dir.
    """
    relative_path = os.path.relpath(html_path, base_folder)
    md_path = os.path.splitext(os.path.join(md_dir, relative_path))[0] + '.md'
    return md_path

def extract_tocs(folder_path):
    """
    Extracts TOC files from the 'Data/Tocs' directory within the given folder.
    Returns a list of tuples: (hierarchy_js_relative_path, list_of_chunk_js_relative_paths)
    """
    tocs_dir = os.path.join(folder_path, 'Data', 'Tocs')
    if not os.path.exists(tocs_dir):
        logger.warning(f"'Data/Tocs' directory not found in {folder_path}")
        return []

    toc_files = {}
    for file in os.listdir(tocs_dir):
        if file.endswith('.js'):
            if '_Chunk' in file:
                # It's a chunk file
                base_name = file.split('_Chunk')[0]
                chunk_list = toc_files.get(base_name, {}).get('chunks', [])
                chunk_list.append(file)
                if base_name not in toc_files:
                    toc_files[base_name] = {'hierarchy': None, 'chunks': chunk_list}
                else:
                    toc_files[base_name]['chunks'] = chunk_list
            else:
                # It's a hierarchy file
                base_name = file.replace('.js', '')
                if base_name not in toc_files:
                    toc_files[base_name] = {'hierarchy': file, 'chunks': []}
                else:
                    toc_files[base_name]['hierarchy'] = file

    toc_pairs = []
    for base_name, files in toc_files.items():
        hierarchy_file = files['hierarchy']
        chunk_files = files['chunks']
        if hierarchy_file and chunk_files:
            hierarchy_rel = os.path.relpath(os.path.join(tocs_dir, hierarchy_file), folder_path)
            chunk_rels = [os.path.relpath(os.path.join(tocs_dir, chunk), folder_path) for chunk in chunk_files]
            toc_pairs.append((hierarchy_rel, chunk_rels))
            logger.info(f"Found TOC pair: {hierarchy_rel}, {chunk_rels}")
        else:
            logger.warning(f"Hierarchy or chunk files missing for base {base_name}")
    return toc_pairs

def parse_toc_files(toc_pairs, base_path, md_folder):
    """
    Parses TOC JavaScript files and builds __toc.txt and __hierarchy.txt.
    """
    id_to_info = {}
    toc_filenames = []
    hierarchy_entries = []

    for hierarchy_js_rel, chunk_js_rels in toc_pairs:
        hierarchy_full_path = os.path.join(base_path, hierarchy_js_rel)
        chunk_full_paths = [os.path.join(base_path, chunk_js_rel) for chunk_js_rel in chunk_js_rels]

        if not os.path.exists(hierarchy_full_path):
            logger.error(f"Hierarchy file not found: {hierarchy_full_path}")
            continue

        # Parse chunk files
        for chunk_full_path in chunk_full_paths:
            if not os.path.exists(chunk_full_path):
                logger.error(f"Chunk file not found: {chunk_full_path}")
                continue

            try:
                with open(chunk_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    js_content_chunk = f.read()

                toc_chunk = parse_js_define_call(js_content_chunk)
                if toc_chunk is None:
                    logger.error(f"Could not parse {chunk_full_path}")
                    continue
            except Exception as e:
                logger.error(f"Error parsing {chunk_full_path}: {e}\n{traceback.format_exc()}")
                continue

            # Build ID to info mapping
            for filepath, info in toc_chunk.items():
                ids = info.get('i', [])
                titles = info.get('t', [])
                for id_, title in zip(ids, titles):
                    id_to_info[id_] = {'filename': filepath, 'title': title}

        # Parse Hierarchy.js
        try:
            with open(hierarchy_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                js_content_hierarchy = f.read()

            toc = parse_js_define_call(js_content_hierarchy)
            if toc is None:
                logger.error(f"Could not parse Hierarchy.js ({hierarchy_full_path})")
                continue
        except Exception as e:
            logger.error(f"Error parsing Hierarchy.js ({hierarchy_full_path}): {e}\n{traceback.format_exc()}")
            continue

        # Traverse the tree and build TOC structure
        tree_nodes = toc.get('tree', {}).get('n', [])
        traverse_tree(tree_nodes, id_to_info, toc_filenames, hierarchy_entries, base_path, md_folder)

    # Write __toc.txt (deduplicated, preserve first occurrence order)
    toc_txt_path = os.path.join(md_folder, '__toc.txt')
    seen_toc = set()
    with open(toc_txt_path, 'w', encoding='utf-8') as toc_file:
        for filename in toc_filenames:
            if filename in seen_toc:
                logger.info(f"Duplicate TOC entry skipped: {filename}")
                continue
            seen_toc.add(filename)
            toc_file.write(f"{filename}\n")

    # Write __hierarchy.txt (deduplicated on filename, keep first occurrence's level)
    hierarchy_txt_path = os.path.join(md_folder, '__hierarchy.txt')
    seen_h = set()
    with open(hierarchy_txt_path, 'w', encoding='utf-8') as hierarchy_file:
        for filename, level in hierarchy_entries:
            if filename in seen_h:
                logger.info(f"Duplicate hierarchy entry skipped: {filename}")
                continue
            seen_h.add(filename)
            hashes = '#' * level
            hierarchy_file.write(f"{hashes} {filename}\n")

def traverse_tree(nodes, id_to_info, toc_filenames, hierarchy_entries, base_path, md_folder, level=1):
    """
    Recursively traverses the TOC tree and collects filenames and their levels.
    """
    for node in nodes:
        id_ = node.get('i', '')
        info = id_to_info.get(id_, {})
        title = info.get('title', 'Unknown Title')
        filepath = info.get('filename', 'Unknown Filename')

        if filepath.startswith('/'):
            # Remove leading slash to make it relative
            filepath = filepath[1:]

        target_html_path = os.path.normpath(os.path.join(base_path, filepath))
        if not os.path.isfile(target_html_path):
            logger.warning(f"Target HTML file {target_html_path} does not exist. Skipping.")
            continue

        # Determine the corresponding Markdown file path
        relative_md_path = os.path.relpath(target_html_path, base_path)
        filename_normalized = os.path.splitext(os.path.join(md_folder, relative_md_path))[0] + '.md'
        filename_normalized = os.path.relpath(filename_normalized, md_folder).replace('\\', '/')

        # Check if this file should be blacklisted
        if is_blacklisted(filename_normalized):
            # Skip this file but continue with children
            child_nodes = node.get('n', [])
            if child_nodes:
                traverse_tree(child_nodes, id_to_info, toc_filenames, hierarchy_entries, base_path, md_folder, level + 1)
            continue

        # Append to TOC lists
        toc_filenames.append(filename_normalized)
        hierarchy_entries.append((filename_normalized, level))

        # Recursively traverse child nodes
        child_nodes = node.get('n', [])
        if child_nodes:
            traverse_tree(child_nodes, id_to_info, toc_filenames, hierarchy_entries, base_path, md_folder, level + 1)

def adjust_headers(md_dir):
    """
    Adjusts header levels in markdown files based on __hierarchy.txt.
    """
    hierarchy_txt_path = os.path.join(md_dir, '__hierarchy.txt')
    if not os.path.exists(hierarchy_txt_path):
        logger.warning(f"__hierarchy.txt not found in {md_dir}. Skipping header adjustment.")
        return

    # Build a mapping of filename to header level
    filename_to_level = {}
    with open(hierarchy_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                hashes, filename = match.groups()
                level = len(hashes)
                filename_to_level[filename] = level

    # Process each markdown file
    for filename, desired_level in filename_to_level.items():
        md_file_path = os.path.join(md_dir, filename)
        if not os.path.exists(md_file_path):
            logger.warning(f"Markdown file {md_file_path} does not exist. Skipping header adjustment.")
            continue

        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            adjusted_lines = []
            header_adjustment = None  # To store the difference in levels

            for line in lines:
                header_match = re.match(r'^(#+)\s+(.*)', line)
                if header_match:
                    current_hashes, header_text = header_match.groups()
                    current_level = len(current_hashes)

                    if header_adjustment is None:
                        # First header determines the adjustment
                        header_adjustment = desired_level - current_level

                    # Adjust the number of hashes
                    new_level = current_level + header_adjustment
                    new_level = max(1, new_level)  # Ensure at least one '#'
                    new_hashes = '#' * new_level
                    adjusted_line = f"{new_hashes} {header_text}\n"
                    adjusted_lines.append(adjusted_line)
                else:
                    adjusted_lines.append(line)

            # Write back the adjusted content
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.writelines(adjusted_lines)

        except Exception as e:
            logger.error(f"Error adjusting headers in {md_file_path}: {e}\n{traceback.format_exc()}")

def infer_subfolder_from_path(file_path):
    """
    Infers the documentation subfolder from the file path for merged documents.
    Used for IDOLServer documentation which combines expert, gettingstarted, and documentsecurity.
    
    Returns: subfolder name (expert, gettingstarted, documentsecurity) or None
    """
    # Normalize path
    path_normalized = file_path.replace('\\', '/')
    
    # Extract the directory structure after "Content/"
    if 'Content/' in path_normalized:
        after_content = path_normalized.split('Content/', 1)[1]
        parts = after_content.split('/')
        if len(parts) > 0:
            first_dir = parts[0]
            
            # Mapping based on observed patterns in IDOLServer documentation
            expert_dirs = ['IDOLExpert', 'DocMap', 'Amazon EFS', 'FunctionalityView']
            documentsecurity_dirs = ['IAS', 'StandardSecurity', 'OmniGroupServer', 'Appendixes', 'GenericSecurity', 'Resources', 'MappedSecurity']
            gettingstarted_dirs = ['Install_Run_IDOL', 'IDOL_Systems']
            
            if first_dir in expert_dirs or 'Expert' in first_dir:
                return 'expert'
            elif first_dir in documentsecurity_dirs:
                return 'documentsecurity'
            elif first_dir in gettingstarted_dirs:
                return 'gettingstarted'
    
    return None

def detect_source_extension(base_folder: str, rel_path_no_ext: str):
    """
    Determine whether the original HTML file used .html or .htm by inspecting the source tree.
    Returns '.html' / '.htm' when a matching file is found, else None.
    """
    if not rel_path_no_ext:
        return None
    rel_norm = rel_path_no_ext.replace('\\', '/').strip('/')
    if not rel_norm:
        return None
    rel_parts = rel_norm.split('/')
    html_candidate = os.path.join(base_folder, *rel_parts) + '.html'
    htm_candidate = os.path.join(base_folder, *rel_parts) + '.htm'
    if os.path.exists(html_candidate):
        return '.html'
    if os.path.exists(htm_candidate):
        return '.htm'
    return None

def create_external_version(concatenated_md_path,
                            base_folder,
                            md_dir,
                            online_base_url,
                            online_site_dir,
                            subfolder_name):
    """
    Create a copy of the concatenated markdown with all cross-reference links rewritten
    to point directly at the online documentation. Returns the path to the new file.
    """
    try:
        base_name = os.path.basename(concatenated_md_path)
        stem, ext = os.path.splitext(base_name)
        external_name = f"{stem}__external{ext}"
        external_path = os.path.join(md_dir, external_name)
        shutil.copy2(concatenated_md_path, external_path)
        fix_cross_references(
            external_path,
            online_base_url,
            online_site_dir,
            subfolder_name,
            force_external=True,
            source_root_override=base_folder,
        )
        logger.info(f"External-link markdown created at: {external_path}")
        return external_path
    except Exception as e:
        logger.error(f"Failed to create external version for {concatenated_md_path}: {e}")
        return None

def generate_concatenated_md(base_folder, md_dir, online_base_url=None, online_site_dir=None, subfolder_name=None):
    """
    Generates a concatenated Markdown file named __<Base_Dir_Name>.md
    by concatenating all Markdown files listed in __toc.txt in order.
    - Skips duplicate entries as a safeguard
    - Builds an anchor mapping for each file's first header, handling duplicate headers by adding numeric suffixes
    Persists anchor mapping to md/__anchors.json for later link rewriting.
    Returns the path to the concatenated file if successful, else None.
    """
    try:
        base_dir_name = os.path.basename(base_folder.rstrip('/\\'))
        concatenated_filename = f"__{base_dir_name}.md"
        concatenated_file_path = os.path.join(md_dir, concatenated_filename)

        toc_txt_path = os.path.join(md_dir, '__toc.txt')
        if not os.path.exists(toc_txt_path):
            logger.warning(f"__toc.txt not found in {md_dir}. Skipping concatenated Markdown generation.")
            return None

        with open(toc_txt_path, 'r', encoding='utf-8') as toc_file:
            md_files = [line.strip() for line in toc_file if line.strip()]

        # Include additional markdown files not present in __toc.txt to ensure
        # anchors exist for pages referenced but not listed in the TOC
        all_md_files = []
        for root, dirs, files in os.walk(md_dir):
            for file in files:
                if file.lower().endswith('.md') and not file.startswith('__'):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, md_dir).replace('\\', '/')
                    if rel_path == concatenated_filename:
                        continue
                    # Skip blacklisted files
                    if is_blacklisted(rel_path):
                        continue
                    all_md_files.append(rel_path)
        missing_md_files = [p for p in sorted(set(all_md_files)) if p not in md_files]
        for extra in missing_md_files:
            logger.info(f"Appending non-TOC markdown file to concatenation: {extra}")
        md_files = md_files + missing_md_files

        # Safeguard dedupe
        seen_concat = set()

        # For building anchors consistent with GitHub duplicate heading behavior
        header_pattern = re.compile(r'^(#+)\s+(.*)')
        title_counts = {}
        anchors_by_rel_path = {}
        anchors_by_base_name = {}

        def base_anchor_from_title(title):
            return generate_markdown_anchor(title)

        def unique_anchor_for_title(title):
            base = base_anchor_from_title(title)
            count = title_counts.get(base, 0)
            anchor = base if count == 0 else f"{base}-{count}"
            title_counts[base] = count + 1
            return anchor

        with open(concatenated_file_path, 'w', encoding='utf-8') as concatenated_file:
            for md_file in md_files:
                if md_file in seen_concat:
                    logger.info(f"Duplicate entry in __toc.txt skipped during concatenation: {md_file}")
                    continue
                seen_concat.add(md_file)

                md_file_path = os.path.join(md_dir, md_file)
                if not os.path.exists(md_file_path):
                    logger.warning(f"Markdown file {md_file_path} listed in __toc.txt does not exist. Skipping.")
                    continue

                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Determine first header title for this file to compute anchor
                first_header_title = None
                for line in content.splitlines():
                    m = header_pattern.match(line)
                    if m:
                        first_header_title = m.group(2).strip()
                        break
                anchor_for_file = None
                if first_header_title:
                    anchor = unique_anchor_for_title(first_header_title)
                    anchor_for_file = anchor
                    rel_key = md_file.replace('\\', '/')
                    anchors_by_rel_path[rel_key] = anchor
                    base_name = os.path.splitext(os.path.basename(rel_key))[0]
                    # Only set base_name mapping if unseen to prefer first occurrence
                    if base_name not in anchors_by_base_name:
                        anchors_by_base_name[base_name] = anchor
                else:
                    # Headerless page: fallback to filename-based anchor and inject an anchor tag
                    rel_key = md_file.replace('\\', '/')
                    base_name = os.path.splitext(os.path.basename(rel_key))[0]
                    # Create a filename-based anchor
                    fallback_anchor = generate_markdown_anchor(base_name)
                    # Ensure uniqueness across the doc
                    base = fallback_anchor
                    count = title_counts.get(base, 0)
                    unique_fallback = base if count == 0 else f"{base}-{count}"
                    title_counts[base] = count + 1
                    anchors_by_rel_path[rel_key] = unique_fallback
                    anchor_for_file = unique_fallback
                    if base_name not in anchors_by_base_name:
                        anchors_by_base_name[base_name] = unique_fallback

                # Optionally add a marker for easier debugging
                concatenated_file.write(f"<!-- BEGIN_FILE: {md_file} -->\n")
                # Inject an explicit anchor for this file's entry to guarantee linkability
                if anchor_for_file:
                    concatenated_file.write(f"<a id=\"{anchor_for_file}\"></a>\n")
                # If online URL info is provided, rewrite the first header of this block to link to the online source
                if online_base_url and online_site_dir:
                    # Derive normalized path from the md_file (per-file context)
                    fam = detect_doc_family_from_site_dir(online_site_dir)
                    rel_no_ext = md_file.replace('\\', '/').rsplit('.', 1)[0]
                    detected_ext = detect_source_extension(base_folder, rel_no_ext) or '.htm'
                    rel_html_path = rel_no_ext + detected_ext
                    
                    # If the path is in Shared_Admin, it should be prefixed correctly
                    # to resolve from the root of the documentation content.
                    if 'Shared_Admin' in rel_html_path:
                        rel_html_path = re.sub(r'.*?(Shared_Admin)', r'Content/\1', rel_html_path)
                    
                    norm_path = normalize_target_path(rel_html_path, fam, infer_subfolder_from_path(md_file) if fam == 'idolserver' else None)
                    # Subfolder: only relevant for IDOLServer; infer when available
                    eff_sub = infer_subfolder_from_path(md_file) if fam == 'idolserver' else subfolder_name
                    online_url = build_online_url(
                        online_base_url,
                        online_site_dir,
                        norm_path,
                        family=fam,
                        subfolder=eff_sub,
                    )
                    rewritten = []
                    header_rewritten = False
                    for line in content.splitlines():
                        m = header_pattern.match(line)
                        if not header_rewritten and m:
                            hashes = m.group(1)
                            title = m.group(2).strip()
                            # New format: ## Title [↗](url) instead of ## [Title](url)
                            rewritten.append(f"{hashes} {title} [↗]({online_url})")
                            header_rewritten = True
                        else:
                            rewritten.append(line)
                    content_to_write = "\n".join(rewritten)
                else:
                    content_to_write = content
                concatenated_file.write(content_to_write)
                concatenated_file.write('\n\n')  # Add separation between files

        # Persist anchor mapping
        anchors_path = os.path.join(md_dir, '__anchors.json')
        try:
            with open(anchors_path, 'w', encoding='utf-8') as af:
                json.dump({
                    'by_rel_path': anchors_by_rel_path,
                    'by_base_name': anchors_by_base_name
                }, af, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write anchor mapping to {anchors_path}: {e}")

        logger.info(f"Concatenated Markdown file created at: {concatenated_file_path}")
        return concatenated_file_path

    except Exception as e:
        logger.error(f"Error generating concatenated Markdown file: {e}\n{traceback.format_exc()}")
        return None

def fix_cross_references(concatenated_md_path,
                         online_base_url=None,
                         online_site_dir=None,
                         subfolder_name=None,
                         output_path=None,
                         force_external=False,
                         source_root_override=None):
    """
    Fixes cross-reference links to external documents (e.g., ../../Shared_Admin/..., ../../Actions/...).
    Converts them to online documentation URLs, but only if the target is not part of the current bundle.
    """
    try:
        target_path = output_path or concatenated_md_path
        if not os.path.exists(concatenated_md_path):
            logger.error(f"Concatenated Markdown file {concatenated_md_path} does not exist.")
            return
        # We can still convert internal cross-refs to anchors even without online URL
        skip_external = not (online_base_url and online_site_dir)
        
        md_dir = os.path.dirname(concatenated_md_path)
        source_root = source_root_override or os.path.normpath(os.path.join(md_dir, os.pardir))
        anchors_path = os.path.join(md_dir, '__anchors.json')
        anchors_by_rel = {}
        if os.path.exists(anchors_path):
            try:
                with open(anchors_path, 'r', encoding='utf-8') as af:
                    anchor_data = json.load(af)
                    anchors_by_rel = anchor_data.get('by_rel_path', {})
            except Exception as e:
                logger.error(f"Failed to read anchor mapping at {anchors_path}: {e}")

        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        cross_ref_pattern = re.compile(
            r'\[([^\]]+)\]\(((?!https?://|mailto:)[^)\s]+?\.(?:htm|md)(?:#[^)]*)?)\)',
            re.IGNORECASE
        )
        hash_link_pattern = re.compile(r'\[([^\]]+)\]\(#([^)#\s]+)\)')
        
        begin_file_pattern = re.compile(r'<!--\s*BEGIN_FILE:\s*(.*?)\s*-->')
        context_map = [(match.start(), match.group(1)) for match in begin_file_pattern.finditer(content)]
        
        def get_context_info(pos):
            """Get the file path and subfolder context for a given position in the document."""
            current_file_path = None
            current_subfolder = subfolder_name
            for start_pos, file_path in context_map:
                if start_pos <= pos:
                    current_file_path = file_path
                    inferred_sub = infer_subfolder_from_path(file_path)
                    if inferred_sub:
                        current_subfolder = inferred_sub
                else:
                    break
            return current_file_path, current_subfolder
        
        def replace_cross_ref(match):
            link_text = match.group(1)
            rel_path_href = match.group(2).strip()
            link_position = match.start()
            
            source_file, context_subfolder = get_context_info(link_position)
            resolved_rel_path = None
            
            if source_file:
                source_dir = os.path.dirname(source_file)
                target_path_no_anchor = rel_path_href.split('#')[0]
                
                resolved_path = os.path.normpath(os.path.join(source_dir, target_path_no_anchor))
                resolved_rel_path = resolved_path.replace('\\', '/')
                resolved_path_md = os.path.splitext(resolved_rel_path)[0] + '.md'
                
                if resolved_path_md in anchors_by_rel and not force_external:
                    # Convert to an internal anchor link using the target file's anchor id
                    anchor_id = anchors_by_rel[resolved_path_md]
                    return f'[{link_text}](#{anchor_id})'

            path_parts = rel_path_href.split('#')
            file_path = path_parts[0]
            anchor = f'#{path_parts[1]}' if len(path_parts) > 1 else ''

            if anchor:
                anchor = f'#{normalize_fragment_value(anchor[1:])}'
            
            # External conversion only when we have an online URL context
            if skip_external:
                return match.group(0)

            fam = detect_doc_family_from_site_dir(online_site_dir)
            target_rel_path = resolved_rel_path or file_path
            clean_path, anchor2, ext = strip_rel_and_ext(target_rel_path)
            
            inferred_sub = infer_subfolder_from_path(clean_path) if fam == 'idolserver' else None
            eff_sub = inferred_sub or (context_subfolder if fam == 'idolserver' else subfolder_name)
            norm_path = normalize_target_path(clean_path, fam, eff_sub)
            final_ext = ext or '.htm'
            if final_ext in ('.htm', '.html'):
                detected_ext = detect_source_extension(source_root, norm_path)
                if detected_ext:
                    final_ext = detected_ext
            norm_path_with_ext = f"{norm_path}{final_ext}"
            
            online_url = build_online_url(
                online_base_url,
                online_site_dir,
                norm_path_with_ext,
                anchor or (f"#{normalize_fragment_value(anchor2[1:])}" if anchor2 else ''),
                fam,
                eff_sub,
            )
            
            return f'[{link_text}]({online_url})'
        
        updated_content = cross_ref_pattern.sub(replace_cross_ref, content)

        def replace_hash_link(match):
            if not force_external or skip_external:
                return match.group(0)
            link_text = match.group(1)
            fragment = normalize_fragment_value(match.group(2))
            link_position = match.start()
            source_file, context_subfolder = get_context_info(link_position)
            if not source_file:
                return match.group(0)
            fam = detect_doc_family_from_site_dir(online_site_dir)
            rel_md = source_file.replace('\\', '/')
            rel_no_ext = os.path.splitext(rel_md)[0]
            eff_sub = infer_subfolder_from_path(source_file) if fam == 'idolserver' else subfolder_name
            norm_path = normalize_target_path(rel_no_ext, fam, eff_sub)
            detected_ext = detect_source_extension(source_root, rel_no_ext) or '.htm'
            norm_with_ext = f"{norm_path}{detected_ext}"
            anchor = f"#{fragment}" if fragment else ''
            online_url = build_online_url(
                online_base_url,
                online_site_dir,
                norm_with_ext,
                anchor,
                fam,
                eff_sub,
            )
            return f'[{link_text}]({online_url})'

        updated_content = hash_link_pattern.sub(replace_hash_link, updated_content)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
    
    except Exception as e:
        logger.error(f"Error fixing cross-references in {concatenated_md_path}: {e}\n{traceback.format_exc()}")

def normalize_fragment_value(fragment: str) -> str:
    """
    Normalizes malformed anchor fragments generated during conversion.
    Removes placeholder patterns like a-idkanchor###a..., strips leading kanchor identifiers,
    and trims redundant leading 'a' characters introduced by anchor collapsing.
    """
    if fragment is None:
        return fragment

    s = fragment
    changed = False

    # Remove repeated a-idkanchor###a sequences anywhere in the fragment
    new_s = re.sub(r'a-idkanchor\d+a', '', s, flags=re.IGNORECASE)
    if new_s != s:
        changed = True
        s = new_s

    # Remove leading a-id prefix
    new_s = re.sub(r'^a-id', '', s, flags=re.IGNORECASE)
    if new_s != s:
        changed = True
        s = new_s

    # Remove leading kanchor### pattern
    new_s = re.sub(r'^kanchor\d+', '', s, flags=re.IGNORECASE)
    if new_s != s:
        changed = True
        s = new_s

    s = s.strip()
    return s or fragment

def dedupe_global_anchors(concatenated_md_path):
    """
    Ensures anchor ids in the concatenated markdown file are globally unique.
    Subsequent duplicate anchors are suffixed with -2, -3, ... and stray kanchor anchors are removed.
    """
    if not os.path.exists(concatenated_md_path):
        return False
    try:
        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        anchor_re = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>', re.IGNORECASE)
        used_ids = set()
        pieces = []
        replacements = []
        last = 0

        for match in anchor_re.finditer(content):
            start, end = match.span()
            aid = match.group(1)
            new_tag = None

            if re.match(r'^kanchor\d+$', aid, re.IGNORECASE):
                new_tag = ''
            elif aid in used_ids:
                suffix = 2
                while True:
                    candidate = f"{aid}-{suffix}"
                    if candidate not in used_ids:
                        break
                    suffix += 1
                used_ids.add(candidate)
                replacements.append((aid, candidate))
                new_tag = f'<a id="{candidate}"></a>'
            else:
                used_ids.add(aid)

            if new_tag is not None:
                pieces.append(content[last:start])
                pieces.append(new_tag)
                last = end

        if not pieces:
            return False

        pieces.append(content[last:])
        updated_content = ''.join(pieces)

        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return True
    except Exception as e:
        logger.error(f"Error deduplicating anchors in {concatenated_md_path}: {e}\n{traceback.format_exc()}")
        return False

def update_internal_links(concatenated_md_path):
    """
    Updates internal links in the concatenated Markdown file to point to internal headers.
    Uses md/__anchors.json (built during concatenation) to map .md links to anchors.
    Example: [User Roles](../User_Roles.md) -> [User Roles](#user-roles)
    """
    try:
        if not os.path.exists(concatenated_md_path):
            logger.error(f"Concatenated Markdown file {concatenated_md_path} does not exist.")
            return

        md_dir = os.path.dirname(concatenated_md_path)
        anchors_path = os.path.join(md_dir, '__anchors.json')
        anchors_by_rel = {}
        anchors_by_base = {}
        if os.path.exists(anchors_path):
            try:
                with open(anchors_path, 'r', encoding='utf-8') as af:
                    anchor_data = json.load(af)
                    anchors_by_rel = anchor_data.get('by_rel_path', {})
                    anchors_by_base = anchor_data.get('by_base_name', {})
            except Exception as e:
                logger.error(f"Failed to read anchor mapping at {anchors_path}: {e}")

        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pre-normalize malformed fragments embedded in markdown links globally
        # Example: ](#a-idkanchor96adih-distribution-mode-features) -> ](#dih-distribution-mode-features)
        def strip_ai_kanchor_fragment(m):
            tail = m.group(1)
            tail_norm = normalize_fragment_value(tail)
            return f'](#{tail_norm})'
        content = re.sub(r'\]\(#a-idkanchor\d+a([^)#\s]+)\)', strip_ai_kanchor_fragment, content, flags=re.IGNORECASE)

        # We now rewrite links in a context-aware manner: for each block beginning with
        # <!-- BEGIN_FILE: relative/path.md --> we resolve relative hrefs from that path
        begin_marker_re = re.compile(r'<!--\s*BEGIN_FILE:\s*(.*?)\s*-->')
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)(#[^)]+)?\)')
        html_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.html?)(#[^)]+)?\)')
        hashlink_pattern = re.compile(r'\[([^\]]+)\]\(#([^)#\s]+)\)')

        # Path normalization to handle URL-encoding and non-breaking spaces in converted content
        def normalize_path_for_lookup(p: str) -> str:
            try:
                from urllib.parse import unquote
            except Exception:
                unquote = None
            if p is None:
                return p
            p = p.replace('\\', '/')
            if unquote:
                try:
                    p = unquote(p)
                except Exception:
                    pass
            # Replace NBSP and collapse all whitespace to a single space
            p = p.replace('\u00A0', ' ')
            p = p.replace('\xa0', ' ')
            p = re.sub(r'\s+', ' ', p)
            return p.strip()

        # Precompute header anchors across the whole document (positions and ids)
        # so we can later remap in-document anchor links to the correct unique ids.
        header_re_all = re.compile(r'^(#+)\s+(.*)$', re.MULTILINE)
        title_counts_all = {}
        anchor_positions = []  # list of (pos, anchor_id)
        for m in header_re_all.finditer(content):
            title = m.group(2).strip()
            base = generate_markdown_anchor(title)
            count = title_counts_all.get(base, 0)
            anchor_id = base if count == 0 else f"{base}-{count}"
            title_counts_all[base] = count + 1
            anchor_positions.append((m.start(), anchor_id))

        # Include explicitly injected anchors as well
        for m in re.finditer(r'<a\s+(?:id|name)=\"([^\"]+)\"[^>]*>\s*</a>', content):
            anchor_positions.append((m.start(), m.group(1)))

        # Build lookup by base -> sorted list of (pos, anchor_id)
        def anchor_base(a: str) -> str:
            return re.sub(r'-\d+$', '', a)

        anchors_by_base = {}
        for pos, aid in anchor_positions:
            b = anchor_base(aid)
            lst = anchors_by_base.get(b, [])
            lst.append((pos, aid))
            anchors_by_base[b] = lst
        for b in anchors_by_base:
            anchors_by_base[b].sort(key=lambda x: x[0])

        available_anchor_ids = set(aid for _, aid in anchor_positions)

        new_parts = []
        last_pos = 0
        for match in begin_marker_re.finditer(content):
            # Append any text before this marker unchanged
            if match.start() > last_pos:
                new_parts.append(content[last_pos:match.start()])

            marker_text = match.group(0)
            source_rel = normalize_path_for_lookup(match.group(1))
            new_parts.append(marker_text)

            # Determine the end of this block (next marker or EOF)
            block_start = match.end()
            next_match = begin_marker_re.search(content, block_start)
            block_end = next_match.start() if next_match else len(content)
            block_text = content[block_start:block_end]

            def replace_link_ctx(m):
                link_text = m.group(1)
                href_md = m.group(2)
                frag = m.group(3)  # like '#Section'
                # If an explicit fragment exists, prefer using it as an in-document anchor
                if frag:
                    return f'[{link_text}]({frag})'

                # Resolve href relative to the source file's directory
                href_norm = normalize_path_for_lookup(href_md)
                # If already absolute (unlikely in our md), just normalize
                rel_base = normalize_path_for_lookup(os.path.dirname(source_rel))
                resolved = os.path.normpath(os.path.join(rel_base, href_norm))
                resolved = normalize_path_for_lookup(resolved)

                anchor = anchors_by_rel.get(resolved)
                if not anchor:
                    base_name = os.path.splitext(os.path.basename(resolved))[0]
                    anchor = anchors_by_base.get(base_name)

                if anchor:
                    return f'[{link_text}](#{anchor})'
                else:
                    logger.warning(f"No anchor mapping for link to '{href_md}' (resolved from '{source_rel}' -> '{resolved}'). Leaving link unchanged.")
                    return m.group(0)

            def replace_html_link_ctx(m):
                link_text = m.group(1)
                href_html = m.group(2)
                frag = m.group(3)  # like '#Section'

                # Resolve href relative to the source file's directory
                href_norm = normalize_path_for_lookup(href_html)
                rel_base = normalize_path_for_lookup(os.path.dirname(source_rel))
                resolved_html = os.path.normpath(os.path.join(rel_base, href_norm))
                resolved_html = normalize_path_for_lookup(resolved_html)

                # Try file-level anchor mapping (map .html -> .md key)
                resolved_md = re.sub(r'(?i)\.html?$', '.md', resolved_html)
                file_anchor = anchors_by_rel.get(resolved_md)

                # If we have a fragment, normalize to an actual heading anchor id
                if frag:
                    ref = frag[1:]
                    ref_norm = normalize_fragment_value(ref)
                    base = anchor_base(generate_markdown_anchor(ref_norm))
                    candidates = anchors_by_base.get(base, [])
                    if candidates:
                        # Prefer nearest to this block for stability
                        def dist(t):
                            return abs(t[0] - block_abs_start)
                        chosen = min(candidates, key=dist)[1]
                        return f'[{link_text}](#{chosen})'
                    # Fallback to file-level anchor if fragment not found
                    if file_anchor:
                        return f'[{link_text}](#{file_anchor})'
                    return m.group(0)

                # No fragment: use file-level anchor if available
                if file_anchor:
                    return f'[{link_text}](#{file_anchor})'

                logger.warning(f"No anchor mapping for HTML link to '{href_html}' (resolved '{resolved_html}' -> '{resolved_md}'). Leaving unchanged.")
                return m.group(0)

            block_after_md = link_pattern.sub(replace_link_ctx, block_text)
            block_after_html = html_link_pattern.sub(replace_html_link_ctx, block_after_md)

            # Remap in-document hash links to the correct unique anchor ids present in the doc
            block_abs_start = match.end()
            block_abs_end = next_match.start() if next_match else len(content)

            def replace_hashlink_ctx(m):
                link_text = m.group(1)
                ref = m.group(2)
                # Normalize malformed fragments (e.g., a-idkanchor12aadvanced-distribution-modes)
                ref_norm = normalize_fragment_value(ref)
                # If already a valid anchor id, rewrite to the normalized id
                if ref_norm in available_anchor_ids:
                    return f'[{link_text}](#{ref_norm})'
                # Normalize to base
                base = anchor_base(generate_markdown_anchor(ref_norm))
                base = anchor_base(base)
                candidates = anchors_by_base.get(base, [])
                if not candidates:
                    return m.group(0)
                # Prefer anchors within the same block
                in_block = [(pos, aid) for (pos, aid) in candidates if block_abs_start <= pos < block_abs_end]
                chosen = None
                if in_block:
                    chosen = in_block[0][1]
                else:
                    # Choose nearest by absolute position to the start of the block
                    def dist(t):
                        return abs(t[0] - block_abs_start)
                    chosen = min(candidates, key=dist)[1]
                return f'[{link_text}](#{chosen})'

            block_after_hash = hashlink_pattern.sub(replace_hashlink_ctx, block_after_html)
            new_parts.append(block_after_hash)
            last_pos = block_end

        # Append any trailing content after the last marker
        if last_pos < len(content):
            new_parts.append(content[last_pos:])

        updated_content = ''.join(new_parts)

        # Final global fallback pass: attempt to resolve any remaining .md links
        # by trying common-normalized candidates against anchors_by_rel and by_base.
        # This helps when a block could not be context-resolved for any reason.
        def global_replace(m):
            link_text = m.group(1)
            href = m.group(2)
            frag = m.group(3)
            if frag:
                return f'[{link_text}]({frag})'
            href_norm = normalize_path_for_lookup(href)

            # If we can find an exact rel match, use it
            if href_norm in anchors_by_rel:
                return f'[{link_text}](#{anchors_by_rel[href_norm]})'

            # Try stripping leading ./ and ../ segments progressively and prefixing with 'Content/'
            candidate = href_norm
            while candidate.startswith('../'):
                candidate = candidate[3:]
            candidate = candidate.lstrip('./')

            # Try with and without 'Content/' prefix
            possible_keys = [candidate]
            if not candidate.startswith('Content/'):
                possible_keys.append(f'Content/{candidate}')

            for key in possible_keys:
                key = normalize_path_for_lookup(os.path.normpath(key))
                if key in anchors_by_rel:
                    return f'[{link_text}](#{anchors_by_rel[key]})'

            # Fallback to basename mapping
            base_name = os.path.splitext(os.path.basename(href_norm))[0]
            anchor = anchors_by_base.get(base_name)
            if anchor:
                return f'[{link_text}](#{anchor})'

            logger.warning(f"Global fallback could not map link '{href}'. Leaving unchanged.")
            return m.group(0)

        updated_content = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)(#[^)]+)?\)', global_replace, updated_content)

        # Global fallback for .htm/.html links
        def global_replace_html(m):
            link_text = m.group(1)
            href = m.group(2)
            frag = m.group(3)
            href_norm = normalize_path_for_lookup(href)
            # Map to md key
            candidate = re.sub(r'(?i)\.html?$', '.md', href_norm)
            candidate = candidate.lstrip('./')
            while candidate.startswith('../'):
                candidate = candidate[3:]
            if not candidate.startswith('Content/'):
                cand2 = f'Content/{candidate}'
            else:
                cand2 = candidate
            if cand2 in anchors_by_rel and not frag:
                return f'[{link_text}](#{anchors_by_rel[cand2]})'
            # If a fragment exists, normalize and resolve via anchors_by_base
            if frag:
                ref = frag[1:]
                ref_norm = normalize_fragment_value(ref)
                base = anchor_base(generate_markdown_anchor(ref_norm))
                candidates = anchors_by_base.get(base, [])
                if candidates:
                    return f'[{link_text}](#{candidates[0][1]})'
            return m.group(0)

        updated_content = re.sub(r'\[([^\]]+)\]\(([^)]+\.html?)(#[^)]+)?\)', global_replace_html, updated_content)

        # Global pass to remap any remaining in-document anchor links to the nearest matching heading id
        # Useful for content that appears before the first BEGIN_FILE marker or edge cases
        def replace_hashlink_global(m):
            link_text = m.group(1)
            ref = m.group(2)
            # Normalize malformed fragments globally
            ref_norm = normalize_fragment_value(ref)
            if ref_norm in available_anchor_ids:
                return f'[{link_text}](#{ref_norm})'
            base = anchor_base(generate_markdown_anchor(ref_norm))
            candidates = anchors_by_base.get(base, [])
            if not candidates:
                return m.group(0)
            # Without precise position context, choose the first occurrence
            return f'[{link_text}](#{candidates[0][1]})'

        updated_content = hashlink_pattern.sub(replace_hashlink_global, updated_content)

        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        # Emit a report of any remaining .md links that were not converted
        unresolved = set(m.group(2) for m in re.finditer(r'\[[^\]]+\]\(([^)]+\.md)(#[^)]+)?\)', updated_content))
        report_path = os.path.join(md_dir, '__link_warnings.txt')
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write(f"Unresolved .md links remaining: {len(unresolved)}\n")
            for href in sorted(unresolved):
                rf.write(f"- {href}\n")
        if unresolved:
            logger.warning(f"Unresolved .md links reported to {report_path}")
        else:
            logger.info("All .md links successfully converted to anchors.")

        logger.info(f"Internal links updated in concatenated Markdown file: {concatenated_md_path}")

    except Exception as e:
        logger.error(f"Error updating internal links in {concatenated_md_path}: {e}\n{traceback.format_exc()}")

def unify_assets(concatenated_md_path, md_dir, assets_dirname="assets"):
    """
    Copies all local image assets referenced in the concatenated markdown file into md/assets/
    and rewrites image references to point to that directory. Handles name collisions with a
    short content-hash suffix.
    """
    try:
        if not os.path.exists(concatenated_md_path):
            logger.error(f"Concatenated Markdown file {concatenated_md_path} does not exist.")
            return

        assets_dir = os.path.join(md_dir, assets_dirname)
        os.makedirs(assets_dir, exist_ok=True)

        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find image references ![alt](url "optional title")
        # Updated pattern to handle paths with spaces
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)\s]+(?:\s+[^)\s]+)*?)(?:\s+\"([^\"]*)\")?\)')

        def is_external(path):
            return re.match(r'^(?:http|https|data|mailto):', path, re.IGNORECASE) is not None

        def rewrite_img(match):
            alt_text = match.group(1)
            src = match.group(2)
            title = match.group(3)
            src_norm = src.replace('\\', '/')
            if is_external(src_norm):
                return match.group(0)

            # Resolve source path relative to md_dir (where concatenated file lives)
            src_abs = os.path.normpath(os.path.join(md_dir, src_norm))
            if not os.path.isfile(src_abs):
                logger.warning(f"Image not found for assets unification: {src_abs}")
                return match.group(0)

            # Determine destination filename, handle collisions by content hash
            name = os.path.basename(src_abs)
            dest_path = os.path.join(assets_dir, name)
            if os.path.exists(dest_path):
                # Compare content; if different, append short hash
                with open(src_abs, 'rb') as rf:
                    data = rf.read()
                h = hashlib.sha1(data).hexdigest()[:8]
                stem, ext = os.path.splitext(name)
                name = f"{stem}-{h}{ext}"
                dest_path = os.path.join(assets_dir, name)

            try:
                shutil.copy2(src_abs, dest_path)
            except Exception as e:
                logger.warning(f"Failed to copy image {src_abs} -> {dest_path}: {e}")
                return match.group(0)

            # Reconstruct the image markdown preserving alt and title
            if title is not None and title != '':
                return f'![{alt_text}]({assets_dirname}/{name} "{title}")'
            else:
                return f'![{alt_text}]({assets_dirname}/{name})'

        updated_content = img_pattern.sub(rewrite_img, content)

        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        logger.info(f"Assets unified under {assets_dir}")
    except Exception as e:
        logger.error(f"Error unifying assets for {concatenated_md_path}: {e}\n{traceback.format_exc()}")

def validate_internal_anchors(concatenated_md_path):
    """
    Validates that all in-document anchor links point to existing anchors.
    Writes a report to md/__anchor_warnings.txt with any missing anchors.
    """
    try:
        if not os.path.exists(concatenated_md_path):
            logger.error(f"Concatenated Markdown file {concatenated_md_path} does not exist.")
            return

        md_dir = os.path.dirname(concatenated_md_path)
        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Collect explicit anchors from <a id="..."></a>
        explicit_ids = set(m.group(1) for m in re.finditer(r'<a\s+id=\"([^\"]+)\"\s*>\s*</a>', content))

        # Collect anchors from headers, applying GitHub-style slug and duplicate suffixing
        header_re = re.compile(r'^(#+)\s+(.*)$', re.MULTILINE)
        title_counts = {}
        header_ids = set()
        for m in header_re.finditer(content):
            title = m.group(2).strip()
            base = generate_markdown_anchor(title)
            count = title_counts.get(base, 0)
            anchor = base if count == 0 else f"{base}-{count}"
            title_counts[base] = count + 1
            header_ids.add(anchor)

        available = explicit_ids.union(header_ids)

        # Find all #anchor references in links
        ref_re = re.compile(r'\[[^\]]*\]\(#([^)#\s]+)\)')
        referenced = set(m.group(1) for m in ref_re.finditer(content))

        missing = sorted(ref for ref in referenced if ref not in available)
        report_path = os.path.join(md_dir, '__anchor_warnings.txt')
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write(f"Missing anchors: {len(missing)}\n")
            for a in missing:
                rf.write(f"- #{a}\n")
        if missing:
            logger.warning(f"Missing anchors reported to {report_path}")
        else:
            logger.info("All anchor links resolve to existing anchors.")
    except Exception as e:
        logger.error(f"Error validating anchors for {concatenated_md_path}: {e}\n{traceback.format_exc()}")

def generate_markdown_anchor(title):
    """
    Generates a GitHub-style markdown anchor from a header title.
    Example: "User Roles" -> "user-roles"
    """
    # Convert to lowercase
    anchor = title.lower()
    # Remove all characters except alphanumerics and spaces
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    # Replace spaces and underscores with hyphens
    anchor = re.sub(r'[\s_]+', '-', anchor)
    return anchor

def clean_markdown_content(content):
    """
    Post-processes markdown content to remove unwanted elements:
    1. Removes ONLY the first BEGIN_FILE comment (at top of file)
    2. Keeps all anchor tags for navigation
    3. Removes search/navigation artifacts at the end
    4. Removes orphaned navigation links (Previous/Next)
    5. DOES NOT remove BEGIN_FILE comments or anchors in the middle of content
    """
    
    # Step A: Remove obviously malformed anchors produced by bad placeholder merges
    content = re.sub(r'^\s*<a\s+id="a-id[^"]*"\s*>\s*</a>\s*\n?', '', content, flags=re.MULTILINE)

    # Step A2: Normalize anchor ids that still contain legacy fragments and deduplicate consecutive copies
    anchor_tag_re = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>', re.IGNORECASE)

    def normalize_anchor_tag(m):
        original = m.group(1)
        if re.match(r'^kanchor\d+$', original, re.IGNORECASE):
            return ''
        normalized = normalize_fragment_value(original)
        if not normalized:
            return ''
        if normalized != original:
            return f'<a id="{normalized}"></a>'
        return m.group(0)

    content = anchor_tag_re.sub(normalize_anchor_tag, content)

    def dedupe_anchor_block(m):
        block = m.group(0)
        ids = []
        for aid in anchor_tag_re.findall(block):
            if aid not in ids:
                ids.append(aid)
        if not ids:
            return ''
        return ''.join(f'<a id="{aid}"></a>\n' for aid in ids)

    content = re.sub(r'((?:<a\s+id="[^"]+"\s*>\s*</a>\s*\n)+)', dedupe_anchor_block, content, flags=re.IGNORECASE)

    # Step B: For headers that contain inline anchors, hoist a single preferred anchor above the header
    slug_counts = {}
    used_header_ids = set()

    def next_slug(text):
        base = generate_markdown_anchor(text) if text else ''
        if not base:
            base = 'section'
        count = slug_counts.get(base, 0)
        candidate = base if count == 0 else f"{base}-{count}"
        slug_counts[base] = count + 1
        while candidate in used_header_ids:
            count = slug_counts.get(base, 0)
            candidate = f"{base}-{count}"
            slug_counts[base] = count + 1
        used_header_ids.add(candidate)
        return candidate

    header_line_re = re.compile(r'^(?P<hashes>#{1,6})\s+(?P<body>.*)$', re.MULTILINE)
    inline_anchor_re = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>', re.IGNORECASE)

    def rewrite_header(m):
        hashes = m.group('hashes')
        body = m.group('body')
        anchors = inline_anchor_re.findall(body)
        if not anchors:
            return m.group(0)
        # Prefer first non-kanchor anchor, else the first
        preferred = None
        for a in anchors:
            if not re.match(r'^kanchor\d+$', a, re.IGNORECASE):
                preferred = a
                break
        if preferred is None:
            clean_text = inline_anchor_re.sub('', body).strip()
            preferred = next_slug(clean_text)
        else:
            if preferred in used_header_ids:
                clean_text = inline_anchor_re.sub('', body).strip()
                preferred = next_slug(clean_text)
            else:
                used_header_ids.add(preferred)
        # Remove all inline anchors from the header text
        clean_text = inline_anchor_re.sub('', body).strip()
        # Emit anchor on its own line, then clean header
        return f'<a id="{preferred}"></a>\n{hashes} {clean_text}'

    content = header_line_re.sub(rewrite_header, content)

    # Dedupe anchors again in case header rewriting introduced duplicates
    content = re.sub(r'((?:<a\s+id="[^"]+"\s*>\s*</a>\s*\n)+)', dedupe_anchor_block, content, flags=re.IGNORECASE)

    # Pattern 1: Remove ONLY the very first BEGIN_FILE comment at the start of the file
    # This is typically at the top and not needed, but keep all others for reference
    first_begin_file = re.compile(r'^<!--\s*BEGIN_FILE:.*?-->\s*\n', re.MULTILINE)
    # Only replace the first occurrence
    content = first_begin_file.sub('', content, count=1)
    
    # Pattern 2: Remove sections starting with blacklisted files that appear near the end
    # Look for _FT_SideNav_Startup specifically (the most common footer marker)
    sidenav_footer = re.compile(
        r'<!--\s*BEGIN_FILE:\s*[^>]*?[/\\]_FT_SideNav_Startup\.md\s*-->\s*\n'
        r'.*$',  # Everything from here to end
        re.MULTILINE | re.DOTALL
    )
    
    # Find the last occurrence (in case there are multiple)
    matches = list(sidenav_footer.finditer(content))
    if matches:
        last_match = matches[-1]
        # Only remove if in the last 5% of the document (to be safe)
        threshold = int(len(content) * 0.95)
        if last_match.start() >= threshold:
            content = content[:last_match.start()]
    
    # Pattern 3: Remove footer sections with index.md or index_CSH.md near the end
    index_footer = re.compile(
        r'<!--\s*BEGIN_FILE:\s*[^>]*?[/\\]index(?:_CSH)?\.md\s*-->\s*\n'
        r'.*$',
        re.MULTILINE | re.DOTALL
    )
    matches = list(index_footer.finditer(content))
    if matches:
        last_match = matches[-1]
        threshold = int(len(content) * 0.95)
        if last_match.start() >= threshold:
            content = content[:last_match.start()]
    
    # Pattern 4: Remove index_CSH sections with JavaScript (can appear anywhere)
    js_csh_pattern = re.compile(
        r'<!--\s*BEGIN_FILE:.*?index_CSH\.md\s*-->\s*\n'
        r'<a\s+id=["\'].*?["\'].*?>\s*</a>\s*\n'
        r'(?:.*?\n)*?'
        r'//\]\]>\s*\n',
        re.MULTILINE | re.DOTALL
    )
    content = js_csh_pattern.sub('', content)
    
    # Pattern 5: Remove footer artifacts that include search results and navigation
    footer_pattern = re.compile(
        r'\n---\s*\n'                                   # Starting horizontal rule
        r'#\s+Your search for.*?returned result.*?\n'  # Search results header
        r'.*?'                                          # Any content
        r'\[Previous\]\(#\)\[Next\]\(#\)\s*\n'         # Navigation links
        r'.*$',                                         # Everything to the end
        re.MULTILINE | re.DOTALL
    )
    content = footer_pattern.sub('', content)
    
    # Pattern 6: Remove standalone search/navigation sections
    search_nav_pattern = re.compile(
        r'---\s*\n'
        r'#\s+Your search for.*?returned result.*?\n'
        r'.*?'
        r'\[Previous\]\(#\)\[Next\]\(#\)',
        re.MULTILINE | re.DOTALL
    )
    content = search_nav_pattern.sub('', content)
    
    # Pattern 7: Remove "Your search for" headers at the end (without --- prefix)
    search_header_pattern = re.compile(
        r'\n#\s+Your search for.*?returned result.*?\s*$',
        re.MULTILINE | re.DOTALL
    )
    content = search_header_pattern.sub('', content)
    
    # Pattern 8: Remove orphaned navigation links
    orphan_nav_pattern = re.compile(r'\[Previous\]\(#\)\s*\[Next\]\(#\)', re.MULTILINE)
    content = orphan_nav_pattern.sub('', content)
    
    # Pattern 9: Remove excessive blank lines (more than 2 consecutive)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Pattern 10: Clean up trailing horizontal rules and whitespace
    content = re.sub(r'\n---\s*$', '', content)
    
    # Trim leading and trailing whitespace
    content = content.strip()
    
    return content

def main():
    parser = argparse.ArgumentParser(description='Process folders to copy images and convert HTML to Markdown.')
    parser.add_argument('input_folder', help='The input folder path.')
    parser.add_argument('--max_workers', type=int, default=10, help='Maximum number of worker threads per base folder.')
    parser.add_argument('--image_extensions', nargs='+', default=['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
                        help='List of image file extensions to include.')
    parser.add_argument('--online_base_url', type=str, default=None,
                        help='Base URL of the online documentation site (e.g., https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4)')
    parser.add_argument('--online_site_dir', type=str, default=None,
                        help='Site directory segment for the ZIP (e.g., Content_25.4_Documentation)')
    args = parser.parse_args()

    # Only process the input folder itself as a base folder.
    # The recursive walkers inside processing will handle all nested content.
    base_folders = [args.input_folder]

    if not base_folders:
        logger.error(f"No folders found to process in {args.input_folder}. Exiting.")
        return

    # Determine the number of workers for processing base folders
    # You can adjust this based on your system's capabilities
    base_folder_workers = min(4, len(base_folders))  # Example: up to 4 base folders in parallel

    with concurrent.futures.ThreadPoolExecutor(max_workers=base_folder_workers) as executor:
        # Use tqdm to show progress of base folder processing
        futures = {
            executor.submit(
                process_base_folder,
                base_folder,
                args.image_extensions,
                args.max_workers,
                args.online_base_url,
                args.online_site_dir
            ): base_folder
            for base_folder in base_folders
        }

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Processing base folders'):
            base_folder = futures[future]
            try:
                future.result()
                logger.info(f"Completed processing base folder: {base_folder}")
            except Exception as e:
                logger.error(f"Error processing base folder {base_folder}: {e}\n{traceback.format_exc()}")

if __name__ == '__main__':
    main()
