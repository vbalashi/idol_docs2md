import argparse
import os
from pathlib import Path
from bs4 import BeautifulSoup
import logging
import re

# Setup logging
logging.basicConfig(
    filename='rename_folders.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Rename folders based on parsed HTML data.")
    parser.add_argument('input', type=str, help='Input directory containing extracted folders.')
    return parser.parse_args()

def normalize_whitespace(text):
    # Replace non-breaking spaces and other variants with regular space
    text = text.replace('&#160;', ' ').replace('\u00A0', ' ')
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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

                # Extract 'Topic Title'
                topic_title_span = soup.find('span', class_='mc-variable System.Title variable')
                if topic_title_span:
                    topic_title = topic_title_span.get_text(strip=True)
                    product_name = normalize_whitespace(topic_title)
                    logging.info(f"Extracted Product Name from '_FT_SideNav_Startup.htm' Topic Title: '{product_name}' in '{startup_file}'")

                # Extract 'Product Version'
                product_version_span = soup.find('span', class_=lambda x: x and '_FT_Product_Version' in x)
                if product_version_span:
                    product_version = product_version_span.get_text(strip=True)
                    logging.info(f"Extracted Product Version from '_FT_SideNav_Startup.htm': '{product_version}' in '{startup_file}'")

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
                            topic_title = topic_title_span.get_text(strip=True).replace('&#160;', ' ')  # Convert &#160; to space
                            if topic_title:
                                product_name = topic_title.replace('&#160;', ' ')  # Ensure any remaining &#160; is replaced
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


def rename_folder(folder_path):
    content_path = folder_path / 'Content'
    if not content_path.exists():
        logging.error(f"No 'Content' folder found in {folder_path}")
        return

    product_name, product_version = parse_html_for_vars(content_path)
    if not product_name or not product_version:
        logging.error(f"Could not find product name or version in {folder_path}")
        return

    # Replace spaces with underscores and remove any special characters
    product_name = re.sub(r'[^\w\-_\. ]', '', product_name).replace(' ', '_')
    new_name = f"{product_name}_{product_version}"
    new_path = folder_path.parent / new_name

    if new_path.exists():
        logging.warning(f"Destination {new_path} already exists. Skipping rename for {folder_path}")
        return

    try:
        folder_path.rename(new_path)
        logging.info(f"Successfully renamed {folder_path} to {new_path}")
    except Exception as e:
        logging.error(f"Failed to rename {folder_path} to {new_path}: {e}")

def main():
    args = parse_arguments()
    input_dir = Path(args.input)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} does not exist or is not a directory.")
        return

    for item in input_dir.iterdir():
        if item.is_dir():
            rename_folder(item)

    print("Renaming completed. Check 'rename_folders.log' for details.")

if __name__ == "__main__":
    main()