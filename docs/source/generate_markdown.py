import os
import sys
from bs4 import BeautifulSoup


def process_html_file(file_path, output_dir, markdown_dir):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    footers = soup.find_all('footer')
    for footer in footers:
        footer.decompose()

    navigations = soup.find_all('nav')
    for navigation in navigations:
        navigation.decompose()

    hr = soup.find('hr')
    if hr:
        hr.decompose()

    ul = soup.find('ul', class_='wy-breadcrumbs')
    if ul:
        ul.decompose()

    headerlinks = soup.find_all('a', class_='headerlink')
    for headerlink in headerlinks:
        headerlink.decompose()

    code_blocks = soup.find_all('div', class_='highlight-default notranslate')
    for block in code_blocks:
        pre_tag = soup.new_tag("p")
        pre_tag.append("start ")
        pre_tag.append(block.get_text().strip())
        pre_tag.append(" finish")
        block.replace_with(pre_tag)

    clean_html = str(soup)

    base_filename = os.path.basename(file_path)
    output_path = os.path.join(output_dir, base_filename)

    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(clean_html)
    print(f"Processed: {file_path} -> {output_path}")

    clean_filename = os.path.splitext(base_filename)[0] + ".md"
    md_output_path = os.path.join(markdown_dir, clean_filename)

    os.system(f"html2text --ignore-images {output_path} > {md_output_path}")

    with open(md_output_path, 'r', encoding='utf-8') as file:
        md_content = file.read()

    clean_md = md_content.replace("start ", "```sh\n\t") \
                         .replace("finish", "\n```")

    with open(md_output_path, 'w', encoding='utf-8') as file:
        file.write(clean_md)

    print(f"Processed: {output_path} -> {md_output_path}\n")


def process_html_files_in_directory(directory, output_dir, markdown_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(markdown_dir):
        os.makedirs(markdown_dir)

    for file in os.listdir(directory):
        if file.endswith('.html'):
            file_path = os.path.join(directory, file)
            process_html_file(file_path, output_dir, markdown_dir)


def main():
    if len(sys.argv) == 4:
        input_directory: str = sys.argv[1]
        output_directory: str = sys.argv[2]
        md_directory: str = sys.argv[3]
    else:
        raise Exception("""
            You can only pass 3 parameters:
            - input_directory
            - output_directory
            - md_directory
        """)

    process_html_files_in_directory(input_directory, output_directory, md_directory)


if __name__ == "__main__":
    main()
