import os
import shutil
import argparse
import concurrent.futures
from tqdm import tqdm
from bs4 import BeautifulSoup
import bleach
import re
import js2py
import logging
import traceback
from markdownify import markdownify as md

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

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

                context_chunk = js2py.EvalJs()
                context_chunk.execute("""
                var toc_chunk = {};
                function define(obj) {
                    toc_chunk = obj;
                }
                """)
                context_chunk.execute(js_content_chunk)
                toc_chunk = context_chunk.toc_chunk.to_dict()
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

            context_hierarchy = js2py.EvalJs()
            context_hierarchy.execute("""
            var toc_data = {};
            function define(obj) {
                toc_data = obj;
            }
            """)
            context_hierarchy.execute(js_content_hierarchy)
            toc = context_hierarchy.toc_data.to_dict()
        except Exception as e:
            logger.error(f"Error parsing Hierarchy.js ({hierarchy_full_path}): {e}\n{traceback.format_exc()}")
            continue

        # Traverse the tree and build TOC structure
        tree_nodes = toc.get('tree', {}).get('n', [])
        traverse_tree(tree_nodes, id_to_info, toc_filenames, hierarchy_entries, base_path, md_folder)

    # Write __toc.txt
    toc_txt_path = os.path.join(md_folder, '__toc.txt')
    with open(toc_txt_path, 'w', encoding='utf-8') as toc_file:
        for filename in toc_filenames:
            toc_file.write(f"{filename}\n")

    # Write __hierarchy.txt
    hierarchy_txt_path = os.path.join(md_folder, '__hierarchy.txt')
    with open(hierarchy_txt_path, 'w', encoding='utf-8') as hierarchy_file:
        for filename, level in hierarchy_entries:
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

        with open(concatenated_file_path, 'w', encoding='utf-8') as concatenated_file:
            for md_file in md_files:
                md_file_path = os.path.join(md_dir, md_file)
                if not os.path.exists(md_file_path):
                    logger.warning(f"Markdown file {md_file_path} listed in __toc.txt does not exist. Skipping.")
                    continue

                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                concatenated_file.write(content)
                concatenated_file.write('\n\n')  # Add separation between files

        logger.info(f"Concatenated Markdown file created at: {concatenated_file_path}")
        return concatenated_file_path

    except Exception as e:
        logger.error(f"Error generating concatenated Markdown file: {e}\n{traceback.format_exc()}")
        return None

def update_internal_links(concatenated_md_path):
    """
    Updates internal links in the concatenated Markdown file to point to internal headers.
    For example, converts [User Roles](../User_Roles.md) to [User Roles](#user-roles)
    """
    try:
        if not os.path.exists(concatenated_md_path):
            logger.error(f"Concatenated Markdown file {concatenated_md_path} does not exist.")
            return

        with open(concatenated_md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # First pass: Build a mapping of header titles to anchors
        header_pattern = re.compile(r'^(#+)\s+(.*)')
        title_to_anchor = {}
        for line in lines:
            header_match = header_pattern.match(line)
            if header_match:
                hashes, title = header_match.groups()
                # Generate anchor as per GitHub's markdown convention
                anchor = generate_markdown_anchor(title)
                title_to_anchor[title.strip()] = anchor

        # Second pass: Replace links pointing to markdown files with internal anchors
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')

        updated_lines = []
        for line in lines:
            def replace_link(match):
                link_text = match.group(1)
                href = match.group(2)
                # Extract the base filename without path and extension
                base_filename = os.path.splitext(os.path.basename(href))[0]

                # Attempt to find the corresponding header
                # Assumption: Link text matches the header title
                header_title = link_text.strip()
                anchor = title_to_anchor.get(header_title)
                if anchor:
                    return f'[{link_text}](#{anchor})'
                else:
                    logger.warning(f"Could not find header for link text '{link_text}'. Leaving link unchanged.")
                    return match.group(0)

            updated_line = link_pattern.sub(replace_link, line)
            updated_lines.append(updated_line)

        # Write back the updated content
        with open(concatenated_md_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        logger.info(f"Internal links updated in concatenated Markdown file: {concatenated_md_path}")

    except Exception as e:
        logger.error(f"Error updating internal links in {concatenated_md_path}: {e}\n{traceback.format_exc()}")

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

    # Get all subfolders (base folders)
    base_folders = [
        os.path.join(args.input_folder, name) for name in os.listdir(args.input_folder)
        if os.path.isdir(os.path.join(args.input_folder, name))
    ]

    if not base_folders:
        logger.error(f"No base folders found in {args.input_folder}. Exiting.")
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
