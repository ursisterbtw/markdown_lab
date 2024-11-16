import requests
from bs4 import BeautifulSoup
import markdown


def scrape_website(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to retrieve content from {url}")


def convert_to_markdown(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert the title, headers, paragraphs, and links to Markdown
    title = soup.title.string if soup.title else 'No Title'
    headers = [f"## {header.get_text()}" for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
    paragraphs = [p.get_text() for p in soup.find_all('p')]
    links = [f"[{a.get_text()}]({a['href']})" for a in soup.find_all('a', href=True)]
    markdown_content = f"# {title}\n\n" + "\n\n".join(headers + paragraphs + links)
    return markdown_content


def main(url):
    try:
        html_content = scrape_website(url)
        markdown_content = convert_to_markdown(html_content)
        with open('output.md', 'w') as f:
            f.write(markdown_content)
        print("Markdown file 'output.md' has been created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Scrape a website and convert it to Markdown.')
    parser.add_argument('url', type=str, help='The URL of the website to scrape')
    args = parser.parse_args()

    main(args.url)
