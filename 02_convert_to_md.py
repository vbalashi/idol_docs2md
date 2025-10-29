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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

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

def process_base_folder(base_folder, image_extensions, max_workers):
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

    # Copy images
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(lambda img: copy_image(img, images_dir),
                        images),
            total=len(images),
            desc=f'Copying images in {base_folder}'
        ))

    # Convert HTML files to Markdown
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(lambda html: convert_html_to_md(html, base_folder, md_dir),
                        html_files),
            total=len(html_files),
            desc=f'Converting HTML to Markdown in {base_folder}'
        ))

    # Parse TOC files
    toc_pairs = extract_tocs(base_folder)
    if toc_pairs:
        parse_toc_files(toc_pairs, base_folder, md_dir)
        # Adjust headers after TOC parsing
        adjust_headers(md_dir)
        # Generate concatenated Markdown file
        concatenated_md_path = generate_concatenated_md(base_folder, md_dir)
        # Update internal links in the concatenated file
        if concatenated_md_path:
            update_internal_links(concatenated_md_path)
            # Centralize assets into md/assets and rewrite references
            unify_assets(concatenated_md_path, md_dir)
    else:
        logger.warning(f"No TOC files found in {base_folder}")

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

def convert_html_to_md(input_file, base_folder, md_dir):
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as html_file:
            html_content = html_file.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = extract_main_content(soup)

        if main_content is None:
            logger.warning(f"Warning: Could not extract main content from {input_file}")
            main_content = soup  # Use entire content if main content not found

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

def extract_main_content(soup):
    main_content = soup.find('div', {'role': 'main', 'id': 'mc-main-content'})
    if not main_content:
        main_content = soup.find('div', {'class': 'main-content'})
    return main_content

def sanitize_html(html_content):
    # Define allowed tags and attributes
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ol', 'ul', 'li', 'a', 'img', 'blockquote', 'code', 'pre', 'hr', 'div', 'span',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'col', 'colgroup'
    ]
    allowed_attributes = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        'div': ['class'],
        'span': ['class'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan']
    }

    # Sanitize the HTML content
    clean_html = bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    return clean_html

def convert_to_markdown(html_content, input_file, base_folder, md_dir):
    # Convert HTML to Markdown using markdownify
    markdown_content = md(html_content, heading_style="ATX")

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

    # Resolve the target HTML file path
    target_html_path = os.path.normpath(os.path.join(os.path.dirname(input_file), href))
    if not os.path.isfile(target_html_path):
        logger.warning(f"Linked HTML file {target_html_path} not found. Leaving the original link.")
        return match.group(0)

    # Determine the corresponding Markdown file path
    relative_target_path = os.path.relpath(target_html_path, base_folder)
    target_md_path = os.path.splitext(os.path.join(md_dir, relative_target_path))[0] + '.md'

    # Compute the relative path from the current Markdown file to the target Markdown file
    current_md_path = get_md_path(input_file, base_folder, md_dir)
    relative_path = os.path.relpath(target_md_path, os.path.dirname(current_md_path))

    # Replace backslashes with forward slashes for Markdown
    relative_path = relative_path.replace('\\', '/')

    return f'[{link_text}]({relative_path})'

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

def generate_concatenated_md(base_folder, md_dir):
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
                if first_header_title:
                    anchor = unique_anchor_for_title(first_header_title)
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
                    if base_name not in anchors_by_base_name:
                        anchors_by_base_name[base_name] = unique_fallback

                # Optionally add a marker for easier debugging
                concatenated_file.write(f"<!-- BEGIN_FILE: {md_file} -->\n")
                # If we created a headerless fallback anchor for this file, inject it here
                rel_key_check = md_file.replace('\\', '/')
                if rel_key_check in anchors_by_rel_path and not first_header_title:
                    concatenated_file.write(f"<a id=\"{anchors_by_rel_path[rel_key_check]}\"></a>\n")
                concatenated_file.write(content)
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

        # We now rewrite links in a context-aware manner: for each block beginning with
        # <!-- BEGIN_FILE: relative/path.md --> we resolve relative hrefs from that path
        begin_marker_re = re.compile(r'<!--\s*BEGIN_FILE:\s*(.*?)\s*-->')
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)(#[^)]+)?\)')

        new_parts = []
        last_pos = 0
        for match in begin_marker_re.finditer(content):
            # Append any text before this marker unchanged
            if match.start() > last_pos:
                new_parts.append(content[last_pos:match.start()])

            marker_text = match.group(0)
            source_rel = match.group(1).replace('\\', '/')
            new_parts.append(marker_text)

            # Determine the end of this block (next marker or EOF)
            block_start = match.end()
            next_match = begin_marker_re.search(content, block_start)
            block_end = next_match.start() if next_match else len(content)
            block_text = content[block_start:block_end]

            def replace_link_ctx(m):
                link_text = m.group(1)
                href = m.group(2)
                # Resolve href relative to the source file's directory
                href_norm = href.replace('\\', '/')
                # If already absolute (unlikely in our md), just normalize
                rel_base = os.path.dirname(source_rel)
                resolved = os.path.normpath(os.path.join(rel_base, href_norm))
                resolved = resolved.replace('\\', '/')

                anchor = anchors_by_rel.get(resolved)
                if not anchor:
                    base_name = os.path.splitext(os.path.basename(resolved))[0]
                    anchor = anchors_by_base.get(base_name)

                if anchor:
                    return f'[{link_text}](#{anchor})'
                else:
                    logger.warning(f"No anchor mapping for link to '{href}' (resolved from '{source_rel}' -> '{resolved}'). Leaving link unchanged.")
                    return m.group(0)

            new_parts.append(link_pattern.sub(replace_link_ctx, block_text))
            last_pos = block_end

        # Append any trailing content after the last marker
        if last_pos < len(content):
            new_parts.append(content[last_pos:])

        updated_content = ''.join(new_parts)

        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

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

        # Find image references ![alt](path)
        img_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

        def is_external(path):
            return re.match(r'^(?:http|https|data|mailto):', path, re.IGNORECASE) is not None

        def rewrite_img(match):
            src = match.group(1)
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

            return match.group(0).replace(src, f"{assets_dirname}/{name}")

        updated_content = img_pattern.sub(rewrite_img, content)

        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        logger.info(f"Assets unified under {assets_dir}")
    except Exception as e:
        logger.error(f"Error unifying assets for {concatenated_md_path}: {e}\n{traceback.format_exc()}")

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

def main():
    parser = argparse.ArgumentParser(description='Process folders to copy images and convert HTML to Markdown.')
    parser.add_argument('input_folder', help='The input folder path.')
    parser.add_argument('--max_workers', type=int, default=10, help='Maximum number of worker threads per base folder.')
    parser.add_argument('--image_extensions', nargs='+', default=['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
                        help='List of image file extensions to include.')
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
            executor.submit(process_base_folder, base_folder, args.image_extensions, args.max_workers): base_folder
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
