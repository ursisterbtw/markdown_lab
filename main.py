import argparse
import logging

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class MarkdownScraper:
    def __init__(self):
        self.session = requests.Session()

    def scrape_website(self, url):
        logging.info(f"Attempting to scrape the website: {url}")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            logging.info("Successfully retrieved the website content.")
            return response.text
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            raise

    def convert_to_markdown(self, html_content):
        logging.info("Converting HTML content to Markdown.")
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string if soup.title else 'No Title'
        headers = [f"## {header.get_text()}" for header in soup.find_all(
            ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        paragraphs = [p.get_text() for p in soup.find_all('p')]
        links = [f"[{a.get_text()}]({a['href']})" for a in soup.find_all(
            'a', href=True)]
        images = [f"![{img.get('alt', 'image')}]({
            img['src']})" for img in soup.find_all('img', src=True)]
        lists = []
        for ul in soup.find_all('ul'):
            lists.append(
                "\n".join([f"- {li.get_text()}" for li in ul.find_all('li')]))
        markdown_content = f"# {
            title}\n\n" + "\n\n".join(headers + paragraphs + links + images + lists)
        logging.info("Conversion to Markdown completed.")
        return markdown_content

    def save_markdown(self, markdown_content, output_file):
        with open(output_file, 'w') as f:
            f.write(markdown_content)
        logging.info(f"Markdown file '{
                     output_file}' has been created successfully.")


def main(url, output_file):
    scraper = MarkdownScraper()
    try:
        html_content = scraper.scrape_website(url)
        markdown_content = scraper.convert_to_markdown(html_content)
        scraper.save_markdown(markdown_content, output_file)
    except Exception as e:
        logging.error(f"An error occurred during the process: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scrape a website and convert it to Markdown.')
    parser.add_argument(
        'url', type=str, help='The URL of the website to scrape')
    parser.add_argument('-o', '--output', type=str,
                        default='output.md', help='The output Markdown file name')
    args = parser.parse_args()
    main(args.url, args.output)
