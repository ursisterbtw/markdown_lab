import argparse
import logging
import os
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import time
import re

import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin

from chunk_utils import create_semantic_chunks, ContentChunker
from throttle import RequestThrottler

# Configure logging with more detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("markdown_scraper.log", mode="a")
    ]
)

logger = logging.getLogger("markdown_scraper")


class MarkdownScraper:
    """Scrapes websites and converts content to markdown with chunking support."""
    
    def __init__(self, 
                 requests_per_second: float = 1.0, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """
        Initialize the scraper with configurable parameters.
        
        Args:
            requests_per_second: Maximum number of requests per second
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            chunk_size: Maximum size of content chunks in characters
            chunk_overlap: Overlap between consecutive chunks in characters
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.throttler = RequestThrottler(requests_per_second)
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunker = ContentChunker(chunk_size, chunk_overlap)
        
    def scrape_website(self, url: str) -> str:
        """
        Scrape a website with retry logic and rate limiting.
        
        Args:
            url: The URL to scrape
            
        Returns:
            The HTML content as a string
            
        Raises:
            requests.exceptions.RequestException: If the request fails after retries
        """
        logger.info(f"Attempting to scrape the website: {url}")
        
        for attempt in range(self.max_retries):
            try:
                self.throttler.throttle()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"Successfully retrieved the website content (status code: {response.status_code}).")
                return response.text
            except requests.exceptions.HTTPError as http_err:
                logger.warning(f"HTTP error on attempt {attempt+1}/{self.max_retries}: {http_err}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to retrieve {url} after {self.max_retries} attempts.")
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
            except requests.exceptions.ConnectionError as conn_err:
                logger.warning(f"Connection error on attempt {attempt+1}/{self.max_retries}: {conn_err}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Connection error persisted for {url} after {self.max_retries} attempts.")
                    raise
                time.sleep(2 ** attempt)
            except requests.exceptions.Timeout as timeout_err:
                logger.warning(f"Timeout on attempt {attempt+1}/{self.max_retries}: {timeout_err}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Request to {url} timed out after {self.max_retries} attempts.")
                    raise
                time.sleep(2 ** attempt)
            except Exception as err:
                logger.error(f"An unexpected error occurred: {err}")
                raise

    def _get_text_from_element(self, element: Optional[Tag]) -> str:
        """Extract clean text from a BeautifulSoup element."""
        if element is None:
            return ""
        return re.sub(r'\s+', ' ', element.get_text().strip())
    
    def _get_element_markdown(self, element: Tag, base_url: str) -> str:
        """Convert a single HTML element to markdown."""
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element.name[1])
            return f"{'#' * level} {self._get_text_from_element(element)}"
        
        elif element.name == "p":
            return self._get_text_from_element(element)
        
        elif element.name == "a" and element.get("href"):
            href = element.get("href", "")
            if href and not (href.startswith("http://") or href.startswith("https://")):
                href = urljoin(base_url, href)
            return f"[{self._get_text_from_element(element)}]({href})"
        
        elif element.name == "img" and element.get("src"):
            src = element.get("src", "")
            if src and not (src.startswith("http://") or src.startswith("https://")):
                src = urljoin(base_url, src)
            alt = element.get("alt", "image")
            return f"![{alt}]({src})"
        
        elif element.name == "ul":
            items = []
            for li in element.find_all("li", recursive=False):
                items.append(f"- {self._get_text_from_element(li)}")
            return "\n".join(items)
        
        elif element.name == "ol":
            items = []
            for i, li in enumerate(element.find_all("li", recursive=False), 1):
                items.append(f"{i}. {self._get_text_from_element(li)}")
            return "\n".join(items)
        
        elif element.name == "blockquote":
            lines = self._get_text_from_element(element).split("\n")
            return "\n".join([f"> {line}" for line in lines])
        
        elif element.name in ["pre", "code"]:
            code = self._get_text_from_element(element)
            lang = element.get("class", [""])[0] if element.get("class") else ""
            if lang.startswith("language-"):
                lang = lang[9:]
            return f"```{lang}\n{code}\n```"
        
        else:
            return self._get_text_from_element(element)

    def convert_to_markdown(self, html_content: str, url: str = "") -> str:
        """
        Convert HTML content to well-structured Markdown.
        
        Args:
            html_content: The HTML content to convert
            url: The source URL for resolving relative links
            
        Returns:
            The converted Markdown content
        """
        logger.info("Converting HTML content to Markdown.")
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract base URL for resolving relative links
        base_url = url
        if not base_url and soup.find("base") and soup.find("base").get("href"):
            base_url = soup.find("base").get("href")
        
        # Extract page title
        title = self._get_text_from_element(soup.title) if soup.title else "No Title"
        
        # Initialize markdown content with the title
        markdown_content = f"# {title}\n\n"
        
        # Get the main content area (try common content containers)
        main_content = soup.find("main") or soup.find("article") or soup.find(id="content") or soup.find(class_="content") or soup.body
        
        if main_content:
            # Process each element in the main content
            for element in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "blockquote", "pre", "img"], recursive=True):
                element_markdown = self._get_element_markdown(element, base_url)
                if element_markdown:
                    markdown_content += element_markdown + "\n\n"
        
        logger.info("Conversion to Markdown completed.")
        return markdown_content.strip()

    def save_markdown(self, markdown_content: str, output_file: str) -> None:
        """
        Save markdown content to a file.
        
        Args:
            markdown_content: The markdown content to save
            output_file: The output file path
        """
        try:
            # Create directories if they don't exist
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"Markdown file '{output_file}' has been created successfully.")
        except IOError as e:
            logger.error(f"Failed to save markdown to {output_file}: {e}")
            raise

    def create_chunks(self, markdown_content: str, source_url: str):
        """
        Create chunks from the markdown content using the chunk_utils module.
        
        Args:
            markdown_content: The markdown content to chunk
            source_url: The source URL of the content
            
        Returns:
            List of chunks for RAG
        """
        return create_semantic_chunks(
            content=markdown_content,
            source_url=source_url,
            chunk_size=self.chunker.chunk_size,
            chunk_overlap=self.chunker.chunk_overlap
        )

    def save_chunks(self, chunks, output_dir, output_format="jsonl"):
        """
        Save content chunks using the chunk_utils module.
        
        Args:
            chunks: The chunks to save
            output_dir: Directory to save chunks to
            output_format: Format to save chunks (json or jsonl)
        """
        self.chunker.save_chunks(chunks, output_dir, output_format)


def main(url: str, output_file: str, save_chunks: bool = True, 
         chunk_dir: str = "chunks", chunk_format: str = "jsonl",
         chunk_size: int = 1000, chunk_overlap: int = 200,
         requests_per_second: float = 1.0) -> None:
    """
    Main entry point for the scraper.
    
    Args:
        url: The URL to scrape
        output_file: Path to save the markdown output
        save_chunks: Whether to save chunks for RAG
        chunk_dir: Directory to save chunks
        chunk_format: Format to save chunks (json or jsonl)
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        requests_per_second: Maximum number of requests per second
    """
    scraper = MarkdownScraper(
        requests_per_second=requests_per_second,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    try:
        html_content = scraper.scrape_website(url)
        markdown_content = scraper.convert_to_markdown(html_content, url)
        scraper.save_markdown(markdown_content, output_file)
        
        if save_chunks:
            chunks = scraper.create_chunks(markdown_content, url)
            scraper.save_chunks(chunks, chunk_dir, chunk_format)
            
        logger.info("Process completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the process: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a website and convert it to Markdown with RAG chunking support.")
    parser.add_argument("url", type=str, help="The URL of the website to scrape")
    parser.add_argument("-o", "--output", type=str, default="output.md", help="The output Markdown file name")
    parser.add_argument("--save-chunks", action="store_true", help="Save content chunks for RAG")
    parser.add_argument("--chunk-dir", type=str, default="chunks", help="Directory to save content chunks")
    parser.add_argument("--chunk-format", type=str, choices=["json", "jsonl"], default="jsonl", help="Format to save chunks")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Maximum chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Overlap between chunks in characters")
    parser.add_argument("--requests-per-second", type=float, default=1.0, help="Maximum requests per second")
    
    args = parser.parse_args()
    
    main(
        url=args.url,
        output_file=args.output,
        save_chunks=args.save_chunks,
        chunk_dir=args.chunk_dir,
        chunk_format=args.chunk_format,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        requests_per_second=args.requests_per_second
    )
