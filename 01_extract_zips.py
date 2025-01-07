import sys
import argparse
import zipfile
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from bs4 import BeautifulSoup
import shutil
import logging
import tempfile

# Setup logging
logging.basicConfig(
    filename='extract_zip_errors.log',
    filemode='w',
    level=logging.INFO,  # Changed to INFO to capture more details
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Extract specific folders from ZIP files based on pattern.")
    parser.add_argument('input', type=str, help='Input directory containing ZIP files.')
    parser.add_argument('-o', '--output', type=str, default='mfdocs', help='Output directory. Defaults to ./mfdocs')
    return parser.parse_args()

def find_base_paths(zip_path):
    base_paths = set()
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            dirs_with_content = set()
            dirs_with_data = set()
            for file in z.namelist():
                # Normalize to use forward slashes
                file = file.replace('\\', '/')
                if file.endswith('/'):
                    # It's a directory
                    parts = Path(file).parts
                    if len(parts) >= 1:
                        parent = Path(*parts[:-1]) if len(parts) > 1 else Path('.')
                        folder = parts[-1].lower()
                        if folder == 'content':
                            dirs_with_content.add(str(parent))
                        elif folder == 'data':
                            dirs_with_data.add(str(parent))
            # Identify base paths that have 'Content/' (and optionally 'Data/')
            base_paths = dirs_with_content.copy()
            # If 'Data/' is mandatory, uncomment the following line
            # base_paths = dirs_with_content & dirs_with_data

            # Log found base paths
            logging.info(f"Found base paths in ZIP '{zip_path}': {base_paths}")

    except zipfile.BadZipFile:
        logging.error(f"Bad ZIP file: '{zip_path}'")
    except Exception as e:
        logging.error(f"Error reading ZIP file '{zip_path}': {e}")
    return list(base_paths)

def extract_specific(z, base_path, temp_dir):
    # Define the paths to extract
    to_extract = []
    for member in z.namelist():
        if member.startswith(base_path + '/'):
            relative_path = member[len(base_path) + 1:]
            if relative_path:
                to_extract.append(member)
                
    return to_extract


def safe_extract(z, members, extract_path):
    for member in members:
        # Prevent Zip Slip
        member_path = Path(member)
        if '..' in member_path.parts:
            logging.error(f"Potential Zip Slip detected and skipped: '{member}'")
            continue
        try:
            z.extract(member, path=extract_path)
        except FileExistsError:
            logging.error(f"Failed to extract '{member}': File exists at destination.")
        except Exception as e:
            logging.error(f"Failed to extract '{member}': {e}")

def resolve_folder_conflict(target_path):
    """
    Checks if the target_path exists. If it does, appends a postfix to create a unique folder name.
    """
    if not target_path.exists():
        return target_path

    postfix = 1
    while True:
        temp_name = f"{target_path.name}_{postfix}"
        temp_path = target_path.parent / temp_name
        if not temp_path.exists():
            logging.warning(f"Folder '{target_path.name}' already exists. Renamed to '{temp_name}'")
            return temp_path
        postfix += 1

def rename_extracted_folder(target_path, product_name, product_version):
    parent = target_path.parent
    # Replace spaces with underscores in product_name
    product_name_clean = product_name.replace(' ', '_')
    new_name = f"{product_name_clean}_{product_version}"
    new_path = parent / new_name

    # Resolve folder conflicts by appending postfix if necessary
    new_path = resolve_folder_conflict(new_path)

    try:
        if target_path.exists():
            target_path.rename(new_path)
            logging.info(f"Successfully renamed '{target_path}' to '{new_path}'")
        else:
            logging.error(f"Source path '{target_path}' does not exist. Cannot rename.")
            return target_path
    except Exception as e:
        logging.error(f"Failed to rename '{target_path}' to '{new_path}': {e}")
        return target_path
    return new_path

def parse_html_for_vars(content_path):
    """
    Parses HTML files to extract the product name and version.

    Priority:
    1. Extract from the first '_FT_SideNav_Startup.htm' file's 'Topic Title' span.
    2. If not found, extract from other 'Topic Title' spans in any .htm/.html files.
    3. If still not found, extract from 'Product Name' and 'Product Version' spans.

    Returns:
        Tuple of (product_name, product_version)
    """
    content_dir = Path(content_path)
    product_name = None
    product_version = None

    # Priority 1: Search for the first '_FT_SideNav_Startup.htm' file
    startup_files = list(content_dir.rglob('_FT_SideNav_Startup.htm'))
    if startup_files:
        startup_file = startup_files[0]
        try:
            with open(startup_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')

                # Priority 1a: Extract from 'Topic Title'
                topic_title_span = soup.find('span', class_='mc-variable System.Title variable')
                if topic_title_span:
                    topic_title = topic_title_span.get_text(strip=True)
                    if topic_title:
                        product_name = topic_title
                        logging.info(f"Extracted Product Name from '_FT_SideNav_Startup.htm' Topic Title: '{product_name}' in '{startup_file}'")

                # Priority 1b: Extract from 'Product Version' if available
                product_version_span = soup.find('span', class_=lambda x: x and '_FT_Product_Version' in x)
                if product_version_span:
                    product_version = product_version_span.get_text(strip=True)
                    logging.info(f"Extracted Product Version from '_FT_SideNav_Startup.htm': '{product_version}' in '{startup_file}'")

                # If both are found, return immediately
                if product_name and product_version:
                    return product_name, product_version

        except Exception as e:
            logging.error(f"Error parsing '{startup_file}': {e}")
    else:
        logging.info(f"No '_FT_SideNav_Startup.htm' file found in '{content_dir}'")

    # Priority 2: Proceed with other HTML files
    # First, look for the 'Topic Title' span
    for root, dirs, files in os.walk(content_dir):
        for file in files:
            if file.lower().endswith(('.htm', '.html')):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')

                        # Priority 2a: Extract from 'Topic Title'
                        topic_title_span = soup.find('span', class_='mc-variable System.Title variable')
                        if topic_title_span:
                            topic_title = topic_title_span.get_text(strip=True)
                            if topic_title:
                                product_name = topic_title
                                logging.info(f"Extracted Product Name from Topic Title: '{product_name}' in '{file_path}'")

                        # Priority 2b: Extract from 'Product Version' if available
                        if not product_version:
                            product_version_span = soup.find('span', class_=lambda x: x and '_FT_Product_Version' in x)
                            if product_version_span:
                                product_version = product_version_span.get_text(strip=True)
                                logging.info(f"Extracted Product Version from '{file_path}': '{product_version}'")

                        # If both are found, return immediately
                        if product_name and product_version:
                            return product_name, product_version

                except Exception as e:
                    logging.error(f"Error parsing '{file_path}': {e}")

    # Priority 3: If still not found, extract from 'Product Name' and 'Product Version' spans
    # This is handled within the same loop above

    if not product_name or not product_version:
        logging.error(f"Product variables not found in content path: '{content_path}'")
    return product_name, product_version

def process_base_path(zip_path, base_path, output_dir):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            members = extract_specific(z, base_path, output_dir)
            if not members:
                logging.error(f"No members to extract for base path: '{base_path}' in ZIP '{zip_path}'")
                return

            # Create a temporary directory for extraction to avoid conflicts
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                safe_extract(z, members, temp_path)

                # Define the target path in the output directory
                base_folder_name = Path(base_path).parts[-1] if Path(base_path).parts else "base"
                target_path = output_dir / base_folder_name

                # Handle duplicate folder names by appending postfix
                target_path = resolve_folder_conflict(target_path)

                # Move extracted 'Content' and 'Data/Tocs' to the target path
                content_extracted = temp_path / base_path / 'Content'
                data_tocs_extracted = temp_path / base_path / 'Data' / 'Tocs'

                if not content_extracted.exists():
                    logging.error(f"'Content' directory not found for base path: '{base_folder_name}' in ZIP '{zip_path}'")
                else:
                    shutil.move(str(content_extracted), str(target_path / 'Content'))
                    logging.info(f"Moved 'Content' to '{target_path / 'Content'}'")

                if not data_tocs_extracted.exists():
                    logging.error(f"'Data/Tocs' directory not found for base path: '{base_folder_name}' in ZIP '{zip_path}'")
                else:
                    # Ensure 'Data' directory exists in target_path
                    (target_path / 'Data').mkdir(parents=True, exist_ok=True)
                    shutil.move(str(data_tocs_extracted), str(target_path / 'Data' / 'Tocs'))
                    logging.info(f"Moved 'Data/Tocs' to '{target_path / 'Data' / 'Tocs'}'")

                # Remove any 'Resources' directories if extracted
                for root_dir, dirs, files in os.walk(target_path, topdown=True):
                    dirs_lower = [d.lower() for d in dirs]
                    if 'resources' in dirs_lower:
                        index = dirs_lower.index('resources')
                        resources_dir = Path(root_dir) / dirs[index]
                        try:
                            shutil.rmtree(resources_dir)
                            logging.info(f"Removed 'Resources' directory: '{resources_dir}'")
                        except Exception as e:
                            logging.error(f"Failed to remove 'Resources' directory '{resources_dir}': {e}")
                        dirs.pop(index)  # Prevent walking into it

                # Parse HTML files to get product name and version from 'Content' directory
                content_extracted_path = target_path / 'Content'
                product_name, product_version = parse_html_for_vars(content_extracted_path)
                if not product_name:
                    logging.error(f"Product name not found in base folder: '{base_folder_name}'. Using default naming.")
                    product_name = base_folder_name
                if not product_version:
                    logging.warning(f"Product version not found in base folder: '{base_folder_name}'. Using 'unknown'.")
                    product_version = "unknown"

                # Rename the extracted folder
                new_path = rename_extracted_folder(target_path, product_name, product_version)
                logging.info(f"Renamed folder to '{new_path}'")

    except zipfile.BadZipFile:
        logging.error(f"Bad ZIP file: '{zip_path}'")
    except Exception as e:
        logging.error(f"Error processing base path '{base_path}' in ZIP '{zip_path}': {e}")

def main():
    # Check if no arguments were provided
    if len(sys.argv) == 1:
        parser = argparse.ArgumentParser(description="Extract specific folders from ZIP files based on pattern.")
        parser.add_argument('input', type=str, help='Input directory containing ZIP files.')
        parser.add_argument('-o', '--output', type=str, default='mfdocs', help='Output directory. Defaults to ./mfdocs')
        parser.print_help()
        return

    args = parse_arguments()
    input_dir = Path(args.input)
    output_dir = Path(args.output)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all ZIP files in the input directory
    zip_files = list(input_dir.rglob('*.zip'))
    if not zip_files:
        print("No ZIP files found in the input directory.")
        return

    # Collect all base paths from all ZIP files
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 20) as executor:
        futures = {}
        for zip_path in zip_files:
            base_paths = find_base_paths(zip_path)
            if not base_paths:
                logging.error(f"No base paths found in ZIP file: '{zip_path}'")
            else:
                for base_path in base_paths:
                    future = executor.submit(process_base_path, zip_path, base_path, output_dir)
                    futures[future] = (zip_path, base_path)

        # Use tqdm to show progress
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Processing ZIP files"):
            pass

    print("Extraction completed. Check 'extract_zip_errors.log' for any errors.")

if __name__ == "__main__":
    main()
