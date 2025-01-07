import os
import shutil
import argparse

def find_and_copy_md_files(source_folder, destination_folder=None):
    if destination_folder is None:
        destination_folder = os.getcwd()  # Default to current working directory
    else:
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)  # Create destination folder if it doesn't exist

    # Walk through the source folder recursively
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.startswith('__') and file.endswith('.md'):
                # Full path of the source file
                source_file = os.path.join(root, file)
                # Full path of the destination file
                destination_file = os.path.join(destination_folder, file)
                # Copy the file
                shutil.copy2(source_file, destination_file)
                print(f"Copied: {source_file} to {destination_file}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Search and copy __*.md files.')
    parser.add_argument('source_folder', type=str, help='The source folder to search in.')
    parser.add_argument('--destination_folder', type=str, help='The folder to copy files to. Defaults to current folder.', default=None)

    args = parser.parse_args()

    find_and_copy_md_files(args.source_folder, args.destination_folder)
