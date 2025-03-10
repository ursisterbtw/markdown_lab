# Updates to add to main.py

# Add to imports:
try:
    from markdown_lab_rs import render_js_page
    JS_RENDERING_AVAILABLE = True
except ImportError:
    JS_RENDERING_AVAILABLE = False


# Add to MarkdownScraper.__init__:
def __init__(self,
             requests_per_second: float = 1.0,
             timeout: int = 30,
             max_retries: int = 3,
             chunk_size: int = 1000,
             chunk_overlap: int = 200,
             js_rendering: bool = False,
             js_wait_time: int = 2000) -> None:
    """
    Args:
        requests_per_second: Maximum number of requests per second
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
        chunk_size: Maximum size of content chunks in characters
        chunk_overlap: Overlap between consecutive chunks in characters
        js_rendering: Whether to enable JavaScript rendering
        js_wait_time: Time to wait for JavaScript execution in milliseconds
    """
    self.session = requests.Session()
    self.session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )
    self.throttler = RequestThrottler(requests_per_second)
    self.timeout = timeout
    self.max_retries = max_retries
    self.chunker = ContentChunker(chunk_size, chunk_overlap)
    self.requests_per_second = requests_per_second
    self.js_rendering = js_rendering
    self.js_wait_time = js_wait_time


# Update the scrape_website method:
def scrape_website(self, url: str) -> str:
    """
    Scrape a website with retry logic and rate limiting.
    Supports JavaScript rendering if enabled.

    Args:
        url: The URL to scrape

    Returns:
        The HTML content as a string

    Raises:
        requests.exceptions.RequestException: If the request fails after retries
    """
    import time
    import psutil
    import tracemalloc

    logger.info(f"Attempting to scrape the website: {url}")

    start_time = time.time()
    tracemalloc.start()
    process = psutil.Process()

    # Check if we should use JavaScript rendering
    if self.js_rendering and JS_RENDERING_AVAILABLE:
        logger.info("Using JavaScript rendering mode")
        try:
            html_content = render_js_page(url, self.js_wait_time)
            if html_content:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.info(f"Successfully rendered JavaScript for {url} in {execution_time:.2f} seconds")
                tracemalloc.stop()
                return html_content
            else:
                logger.warning("JavaScript rendering failed, falling back to regular mode")
        except Exception as e:
            logger.warning(f"Error during JavaScript rendering, falling back to regular mode: {e}")
    elif self.js_rendering and not JS_RENDERING_AVAILABLE:
        logger.warning("JavaScript rendering is enabled but not available (Rust extension not built)")

    # Regular scraping logic (existing implementation)
    for attempt in range(self.max_retries):
        try:
            self.throttler.throttle()
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            logger.info(
                f"Successfully retrieved the website content (status code: {response.status_code})."
            )

            end_time = time.time()
            execution_time = end_time - start_time
            memory_usage = tracemalloc.get_traced_memory()
            cpu_usage = process.cpu_percent(interval=0.1)
            network_latency = response.elapsed.total_seconds()

            logger.info(f"Execution time for scraping {url}: {execution_time:.2f} seconds")
            logger.info(f"Memory usage for scraping {url}: {memory_usage[1] / 1024 / 1024:.2f} MB")
            logger.info(f"CPU usage for scraping {url}: {cpu_usage:.2f}%")
            logger.info(f"Network latency for scraping {url}: {network_latency:.2f} seconds")

            tracemalloc.stop()
            return response.text
        except requests.exceptions.HTTPError as http_err:
            logger.warning(
                f"HTTP error on attempt {attempt+1}/{self.max_retries}: {http_err}"
            )
            if attempt == self.max_retries - 1:
                logger.error(
                    f"Failed to retrieve {url} after {self.max_retries} attempts."
                )
                raise
            time.sleep(2**attempt)  # Exponential backoff
        except requests.exceptions.ConnectionError as conn_err:
            logger.warning(
                f"Connection error on attempt {attempt+1}/{self.max_retries}: {conn_err}"
            )
            if attempt == self.max_retries - 1:
                logger.error(
                    f"Connection error persisted for {url} after {self.max_retries} attempts."
                )
                raise
            time.sleep(2**attempt)
        except requests.exceptions.Timeout as timeout_err:
            logger.warning(
                f"Timeout on attempt {attempt+1}/{self.max_retries}: {timeout_err}"
            )
            if attempt == self.max_retries - 1:
                logger.error(
                    f"Request to {url} timed out after {self.max_retries} attempts."
                )
                raise
            time.sleep(2**attempt)
        except Exception as err:
            logger.error(f"An unexpected error occurred: {err}")
            raise

    # This line should never be reached due to the raise statements above,
    # but adding it to satisfy the linter's "missing return statement" warning
    raise requests.exceptions.RequestException(
        f"Failed to retrieve {url} after {self.max_retries} attempts"
    )


# Update main() function to add JS rendering arguments:
def main(
    url: str,
    output_file: str,
    save_chunks: bool = True,
    chunk_dir: str = "chunks",
    chunk_format: str = "jsonl",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    requests_per_second: float = 1.0,
    use_sitemap: bool = False,
    min_priority: Optional[float] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    limit: Optional[int] = None,
    js_rendering: bool = False,
    js_wait_time: int = 2000,
) -> None:
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
        use_sitemap: Whether to use sitemap.xml for discovering URLs
        min_priority: Minimum priority value for sitemap URLs
        include_patterns: Regex patterns for URLs to include
        exclude_patterns: Regex patterns for URLs to exclude
        limit: Maximum number of URLs to scrape from sitemap
        js_rendering: Whether to enable JavaScript rendering
        js_wait_time: Time to wait for JavaScript execution in milliseconds
    """
    scraper = MarkdownScraper(
        requests_per_second=requests_per_second,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        js_rendering=js_rendering,
        js_wait_time=js_wait_time,
    )

    # Rest of the function remains the same


# Update argument parser in __main__:
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a website and convert it to Markdown with RAG chunking support.")
    # ... existing arguments ...

    # Add JS rendering arguments:
    parser.add_argument("--use-js-rendering", action="store_true", help="Enable JavaScript rendering for dynamic content")
    parser.add_argument("--js-wait-time", type=int, default=2000, help="Time to wait for JavaScript execution in milliseconds")

    args = parser.parse_args()
    main(
        url=args.url,
        output_file=args.output,
        save_chunks=args.save_chunks,
        chunk_dir=args.chunk_dir,
        chunk_format=args.chunk_format,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        requests_per_second=args.requests_per_second,
        use_sitemap=args.use_sitemap,
        min_priority=args.min_priority,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        limit=args.limit,
        js_rendering=args.use_js_rendering,
        js_wait_time=args.js_wait_time,
    )
