import os
import sys
import re
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

    if sys.platform.startswith('win'):
        with open(md_output_path, 'r') as file:
            md_content = file.read()
    else:
        with open(md_output_path, 'r', encoding='utf-8') as file:
            md_content = file.read()

    # clean_md = md_content.replace("start ", "```sh\n\t") \
    #                      .replace("finish", "\n```")

    clean_md = format_code_elements(md_content)
    clean_md = clean_md.replace("\n### ", "\n## ")
    clean_md = clean_md.replace("<", "\<") # fix tags errors
    clean_md = clean_md.replace(">", "\>") # fix tags errors
    clean_md = clean_md.replace("````", "```")
    clean_md = delete_beginning(clean_md)
    
    with open(md_output_path, 'w', encoding='utf-8') as file:
        file.write(clean_md)

    print(f"Processed: {output_path} -> {md_output_path}\n")


def format_code_elements(text: str):
    substrings = []
    start_index = 0
    while True:
        start_index = text.find("start", start_index)
        if start_index == -1:
            break

        end_index = text.find("finish", start_index + 5)
        if end_index == -1:
            break

        substrings.append(text[start_index+5:end_index])
        start_index = end_index + 6

    results = []
    for code in substrings:
        # print(code)

        # после этого всё с одну строку
        res = re.sub(r'\s+', ' ', code).strip()
        # print(res)

        res_split = list(res.split())
        length = len(res_split[0]) + len(res_split[1]) + len(res_split[2]) + 3
        ind = ' ' * length
        res = res.replace('] [', ']\n' + ind + '[')

        results.append(res)

    for i in range(len(results)):
        text = text.replace("start" + substrings[i] + "finish", "```sh\n" +  results[i] + "\n```")

    return text


def delete_beginning(text: str):
    start_index = text.find("## Commands")
    end_index = text.find("## Sub-commands")
    if start_index == -1 or end_index == -1:
        return text

    return text.replace(text[start_index + 11:end_index + 15], "")

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
        input_html_directory: str = sys.argv[1]
        output_html_directory: str = sys.argv[2]
        output_md_directory: str = sys.argv[3]
    else:
        raise Exception("""
            You can only pass 3 parameters:
            - input_html_directory
            - output_html_directory
            - output_md_directory
        """)

    process_html_files_in_directory(
        input_html_directory,
        output_html_directory,
        output_md_directory
    )


if __name__ == "__main__":
    main()
