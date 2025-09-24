import argparse
from bs4 import BeautifulSoup
import os
import html2text
import bleach  # Add this import
import re  # Add this import

def process_html_file(input_file, output_file=None):
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as html_file:
        html_content = html_file.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = extract_main_content(soup)
    
    print(f"Type of main_content: {type(main_content)}")
    print(f"Content of main_content: {str(main_content)[:500]}...")  # Print first 500 characters

    if main_content is None:
        print(f"Error: Could not extract main content from {input_file}")
        return

    # Sanitize the HTML content using Bleach
    sanitized_content = sanitize_html(str(main_content))

    if output_file is None:
        base_name, ext = os.path.splitext(input_file)
        output_file = f"{base_name}_main-content{ext}"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sanitized_content)
    
    print(f"Extracted and sanitized main content saved to {output_file}")
    
    # Convert to Markdown using html2text
    md_output = os.path.splitext(output_file)[0] + '.md'
    convert_to_markdown(sanitized_content, md_output)
    
    print(f"Converted HTML to Markdown: {md_output}")
    return output_file  # Return the output file name

def extract_main_content(soup):
    main_content = soup.find('div', {'role': 'main', 'id': 'mc-main-content'})
    if not main_content:
        main_content = soup.find('div', {'class': 'main-content'})
    return main_content

def sanitize_html(html_content):
    # Define allowed tags and attributes
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'ol', 'ul', 'li', 'a', 'img', 'blockquote', 'code', 'pre', 'hr', 'div', 'span']
    allowed_attributes = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        'div': ['class'],
        'span': ['class']
    }

    # Sanitize the HTML content
    clean_html = bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    return clean_html

def convert_to_markdown(html_content, md_file):
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    markdown_content = h.handle(html_content)
    
    # Fix list item formatting
    def fix_list_item(match):
        indent = match.group(1)
        content = match.group(2)
        # Remove surrounding backticks if present
        if content.startswith('`') and content.endswith('`'):
            content = content[1:-1]
        return f"{indent}* {content}"
    
    markdown_content = re.sub(r'^(\s*)\*\s+`?(.+?)`?$', fix_list_item, markdown_content, flags=re.MULTILINE)
    
    # Remove extra newlines
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract main content from HTML file and convert to Markdown")
    parser.add_argument("input_file", help="Input HTML file")
    parser.add_argument("-o", "--output", help="Output file name (optional)")
    args = parser.parse_args()

    # Process the HTML file and convert to Markdown
    processed_html_file = process_html_file(args.input_file, args.output)
