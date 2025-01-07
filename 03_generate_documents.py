#!/usr/bin/env python3
import os
import argparse
import concurrent.futures
import subprocess
from tqdm import tqdm
import logging
import shutil

# Configure logging to output to both console and a log file
def setup_logging(log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')

    # Create formatters and add them to handlers
    c_format = logging.Formatter('%(levelname)s: %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate EPUB, HTML, and/or PDF files from concatenated Markdown files in subfolders.'
    )
    parser.add_argument(
        'input_folder',
        type=str,
        help='Path to the input base folder containing subfolders with concatenated Markdown files.'
    )
    parser.add_argument(
        '--output_folder',
        type=str,
        default=None,
        help='Path to the output folder where generated files will be saved. If not specified, files are saved in each subfolder.'
    )
    parser.add_argument(
        '--formats',
        nargs='+',
        choices=['epub', 'html', 'pdf'],
        default=['epub', 'html', 'pdf'],
        help='Formats to generate. Choose from epub, html, pdf. Default is all three.'
    )
    return parser.parse_args()

def find_concatenated_md(subfolder):
    """
    Identifies the concatenated Markdown file in the 'md' subfolder.
    Assumes the file starts with '__' and ends with '.md'.
    """
    md_subfolder = os.path.join(subfolder, 'md')
    if not os.path.isdir(md_subfolder):
        return None

    for file in os.listdir(md_subfolder):
        if file.startswith('__') and file.endswith('.md'):
            return os.path.join(md_subfolder, file)
    return None

def extract_metadata(base_folder_name):
    """
    Extracts document name and version from the base folder name.
    Example:
        Input: 'Find_Administration_Guide_24.3'
        Output: ('Find Administration Guide', '24.3')
    """
    parts = base_folder_name.rsplit('_', 1)
    if len(parts) == 2:
        name_part, version = parts
        document_name = name_part.replace('_', ' ')
        return document_name, version
    else:
        # If unable to split, use the entire name as document name and set version as 'Unknown'
        document_name = base_folder_name.replace('_', ' ')
        version = 'Unknown'
        return document_name, version

def convert_markdown(md_file, output_dir, formats, metadata, logger):
    """
    Converts a Markdown file to specified formats using pandoc with metadata.
    """
    basename = os.path.basename(md_file)
    base_name_no_ext = os.path.splitext(basename)[0]
    # Remove '__' prefix from the concatenated markdown filename
    if base_name_no_ext.startswith('__'):
        base_name_no_ext = base_name_no_ext[2:]

    # Prepare conversion commands
    conversion_commands = {
        'epub': [
            'pandoc', '-f', 'gfm', md_file,
            '--toc',
            '--metadata', f'title={metadata["title"]}',
            '--metadata', f'version={metadata["version"]}',
            '-o', os.path.join(output_dir, f"{base_name_no_ext}.epub")
        ],
        'html': [
            'pandoc', '-f', 'gfm', md_file,
            '--toc',
            '--self-contained',
            '--metadata', f'title={metadata["title"]}',
            '--metadata', f'version={metadata["version"]}',
            '-o', os.path.join(output_dir, f"{base_name_no_ext}.html")
        ],
        'pdf': [
            'pandoc', '-f', 'gfm', md_file,
            '--toc',
            '--metadata', f'title={metadata["title"]}',
            '--metadata', f'version={metadata["version"]}',
            '--pdf-engine=xelatex',
            '-V', 'geometry:margin=0.75in',  # Smaller margins to ensure tables fit
            '-V', 'longtable=true',  # Use longtable package for better table handling
            '-o', os.path.join(output_dir, f"{base_name_no_ext}.pdf")
        ]
    }

    for fmt in formats:
        cmd = conversion_commands.get(fmt)
        if cmd:
            try:
                # Change directory to output_dir (md folder) to correctly reference images
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=output_dir)
                logger.info(f"Converted '{md_file}' to {fmt.upper()}.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error converting '{md_file}' to {fmt.upper()}:\n{e.stderr.decode().strip()}")

def move_generated_files(output_dir, final_output_dir, formats, base_name_no_ext, logger):
    """
    Moves the generated files from the md folder to the final output folder.
    """
    for fmt in formats:
        generated_file = os.path.join(output_dir, f"{base_name_no_ext}.{fmt}")
        if os.path.exists(generated_file):
            final_location = os.path.join(final_output_dir, f"{base_name_no_ext}.{fmt}")
            shutil.move(generated_file, final_location)
            logger.info(f"Moved '{generated_file}' to '{final_location}'.")

def generate_concatenated_md(base_folder, md_dir, logger):
    """
    Generates a concatenated Markdown file named __<Base_Dir_Name>.md
    by concatenating all Markdown files listed in __toc.txt in order.
    """
    try:
        base_dir_name = os.path.basename(base_folder.rstrip('/\\'))
        concatenated_filename = f"__{base_dir_name}.md"
        concatenated_file_path = os.path.join(md_dir, concatenated_filename)

        toc_txt_path = os.path.join(md_dir, '__toc.txt')
        if not os.path.exists(toc_txt_path):
            logger.warning(f"__toc.txt not found in {md_dir}. Skipping concatenated Markdown generation.")
            return

        with open(toc_txt_path, 'r', encoding='utf-8') as toc_file:
            md_files = [line.strip() for line in toc_file if line.strip()]

        with open(concatenated_file_path, 'w', encoding='utf-8') as concatenated_file:
            for md_file in md_files:
                md_file_path = os.path.join(md_dir, md_file)
                if not os.path.exists(md_file_path):
                    logger.warning(f"Markdown file '{md_file_path}' listed in __toc.txt does not exist. Skipping.")
                    continue

                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                concatenated_file.write(content)
                concatenated_file.write('\n\n')  # Add separation between files

        logger.info(f"Concatenated Markdown file created at: {concatenated_file_path}")

    except Exception as e:
        logger.error(f"Error generating concatenated Markdown file: {e}")

def generate_documents(args, logger):
    input_folder = os.path.abspath(args.input_folder)
    output_folder = os.path.abspath(args.output_folder) if args.output_folder else None
    formats = args.formats

    if not os.path.isdir(input_folder):
        logger.error(f"Input folder '{input_folder}' does not exist or is not a directory.")
        return

    # Identify all subfolders in the input folder
    subfolders = [
        os.path.join(input_folder, name) for name in os.listdir(input_folder)
        if os.path.isdir(os.path.join(input_folder, name))
    ]

    if not subfolders:
        logger.warning(f"No subfolders found in '{input_folder}'. Exiting.")
        return

    # Prepare a list of tasks
    tasks = []
    for subfolder in subfolders:
        md_file = find_concatenated_md(subfolder)
        if md_file:
            # Extract base folder name for metadata
            base_folder_name = os.path.basename(subfolder.rstrip('/\\'))
            document_name, version = extract_metadata(base_folder_name)
            # Combine document name with version for the title
            combined_title = f"{document_name} {version}".strip()
            metadata = {
                'title': combined_title,
                'version': version
                # 'author' field is omitted as per requirements
            }

            # Generate files inside the md folder where images reside
            md_folder = os.path.join(subfolder, 'md')
            final_output_dir = output_folder if output_folder else subfolder

            # Add to tasks
            tasks.append((md_file, md_folder, final_output_dir, formats, metadata))
        else:
            logger.warning(f"No concatenated Markdown file found in '{subfolder}'. Skipping.")

    if not tasks:
        logger.warning("No Markdown files to process. Exiting.")
        return

    # Use ThreadPoolExecutor for concurrent processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Initialize tqdm progress bar
        futures = [
            executor.submit(
                process_subfolder,
                md_file,
                md_folder,
                final_output_dir,
                fmts,
                metadata,
                logger
            )
            for (md_file, md_folder, final_output_dir, fmts, metadata) in tasks
        ]

        for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Generating Documents'):
            pass  # Progress bar updates automatically

def process_subfolder(md_file, md_folder, final_output_dir, formats, metadata, logger):
    """
    Processes a single subfolder: generates concatenated Markdown, converts to desired formats, and moves files.
    """
    try:
        # Generate concatenated Markdown file
        generate_concatenated_md(os.path.dirname(os.path.dirname(md_file)), os.path.dirname(md_file), logger)

        # Path to the concatenated Markdown file
        base_folder = os.path.dirname(os.path.dirname(md_file))
        concatenated_md_file = os.path.join(os.path.dirname(md_file), f"__{os.path.basename(base_folder)}.md")

        if not os.path.exists(concatenated_md_file):
            logger.warning(f"Concatenated Markdown file '{concatenated_md_file}' does not exist. Skipping conversion.")
            return

        # Convert concatenated Markdown to desired formats
        convert_markdown(concatenated_md_file, md_folder, formats, metadata, logger)

        # Move generated files from md folder to final output folder
        base_name_no_ext = os.path.splitext(os.path.basename(concatenated_md_file))[0][2:]  # Remove '__' prefix
        move_generated_files(md_folder, final_output_dir, formats, base_name_no_ext, logger)

    except Exception as e:
        logger.error(f"Error processing subfolder '{os.path.dirname(os.path.dirname(md_file))}': {e}")

def main():
    args = parse_arguments()

    # Set up logging
    if args.output_folder:
        log_file = os.path.join(args.output_folder, 'generate_documents.log')
    else:
        log_file = os.path.join(args.input_folder, 'generate_documents.log')

    logger = setup_logging(log_file)

    logger.info("Starting document generation process...")
    logger.info(f"Input Folder: {args.input_folder}")
    logger.info(f"Output Folder: {args.output_folder if args.output_folder else 'Same as input subfolders'}")
    logger.info(f"Formats to Generate: {', '.join(args.formats)}")

    generate_documents(args, logger)

    logger.info("Document generation process completed.")

if __name__ == '__main__':
    main()
