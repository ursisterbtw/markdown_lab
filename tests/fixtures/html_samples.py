"""Real HTML samples for testing without generic placeholders."""

GITHUB_README_STYLE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>markdown_lab - Fast Markdown Conversion Library</title>
</head>
<body>
    <article class="markdown-body">
        <h1>markdown_lab</h1>
        <p>A high-performance library for converting HTML to Markdown, JSON, and XML formats.</p>

        <h2>Features</h2>
        <ul>
            <li>⚡ Rust-powered HTML parsing with Python bindings</li>
            <li>🔄 Multiple output formats (Markdown, JSON, XML)</li>
            <li>📦 Content chunking for RAG applications</li>
            <li>🌐 Batch processing with parallel execution</li>
            <li>💾 Request caching and rate limiting</li>
        </ul>

        <h2>Installation</h2>
        <pre><code class="language-bash">pip install markdown-lab</code></pre>

        <h2>Quick Start</h2>
        <pre><code class="language-python">from markdown_lab import MarkdownScraper

scraper = MarkdownScraper()
markdown = scraper.convert_url_to_markdown("https://docs.python.org/3/")</code></pre>

        <h2>Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Operation</th>
                    <th>Time (ms)</th>
                    <th>Memory (MB)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Parse 1MB HTML</td>
                    <td>12.5</td>
                    <td>8.2</td>
                </tr>
                <tr>
                    <td>Convert to Markdown</td>
                    <td>3.8</td>
                    <td>2.1</td>
                </tr>
                <tr>
                    <td>Generate JSON</td>
                    <td>5.2</td>
                    <td>4.5</td>
                </tr>
            </tbody>
        </table>

        <footer>
            <p>© 2024 markdown_lab contributors. Licensed under MIT.</p>
        </footer>
    </article>
</body>
</html>"""

DOCUMENTATION_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>API Reference - HttpClient | markdown_lab</title>
    <meta name="description" content="Comprehensive API documentation for the HttpClient class">
</head>
<body>
    <nav class="sidebar">
        <h3>Navigation</h3>
        <ul>
            <li><a href="#overview">Overview</a></li>
            <li><a href="#methods">Methods</a></li>
            <li><a href="#examples">Examples</a></li>
        </ul>
    </nav>

    <main>
        <h1 id="overview">HttpClient Class</h1>
        <p class="lead">The HttpClient class provides a robust interface for making HTTP requests with automatic retries, rate limiting, and connection pooling.</p>

        <h2 id="methods">Methods</h2>

        <h3>__init__(config: MarkdownLabConfig)</h3>
        <p>Initialize a new HttpClient instance with the specified configuration.</p>
        <h4>Parameters:</h4>
        <dl>
            <dt>config</dt>
            <dd>Configuration object containing timeout, retry, and rate limit settings</dd>
        </dl>

        <h3>get(url: str, **kwargs) -> str</h3>
        <p>Perform a GET request to the specified URL.</p>
        <h4>Parameters:</h4>
        <dl>
            <dt>url</dt>
            <dd>The URL to fetch</dd>
            <dt>**kwargs</dt>
            <dd>Additional arguments to pass to requests</dd>
        </dl>
        <h4>Returns:</h4>
        <p>The response body as a string</p>

        <h2 id="examples">Usage Examples</h2>
        <pre><code class="language-python"># Basic usage
from markdown_lab.network.client import HttpClient
from markdown_lab.core.config import MarkdownLabConfig

config = MarkdownLabConfig(timeout=30, max_retries=3)
client = HttpClient(config)

# Fetch a webpage
html = client.get("https://api.github.com/repos/rust-lang/rust")

# With custom headers
html = client.get(
    "https://api.example.com/data",
    headers={"Authorization": "Bearer token123"}
)</code></pre>

        <aside class="warning">
            <h4>⚠️ Rate Limiting</h4>
            <p>The client automatically respects rate limits. Default is 10 requests per second.</p>
        </aside>
    </main>
</body>
</html>"""

BLOG_POST_WITH_IMAGES = """<!DOCTYPE html>
<html>
<head>
    <title>Building Fast Web Scrapers with Rust and Python</title>
    <meta property="og:image" content="https://blog.example.com/images/rust-python-header.jpg">
</head>
<body>
    <article>
        <header>
            <h1>Building Fast Web Scrapers with Rust and Python</h1>
            <div class="meta">
                <time datetime="2024-01-15">January 15, 2024</time>
                <span class="author">By Sarah Chen</span>
                <span class="reading-time">8 min read</span>
            </div>
            <img src="https://blog.example.com/images/rust-python-header.jpg"
                 alt="Rust and Python logos combined"
                 width="1200" height="630">
        </header>

        <section>
            <p>When building web scrapers, performance matters. Processing thousands of pages requires efficient parsing, and that's where Rust comes in.</p>

            <h2>Why Rust for HTML Parsing?</h2>
            <p>Rust offers memory safety without garbage collection, making it ideal for high-performance parsing tasks.</p>

            <figure>
                <img src="https://blog.example.com/images/performance-chart.png"
                     alt="Performance comparison chart showing Rust 5x faster than pure Python">
                <figcaption>Benchmark results: Rust vs Python HTML parsing</figcaption>
            </figure>

            <h2>Architecture Overview</h2>
            <p>Our scraper uses a hybrid approach:</p>
            <ol>
                <li>Rust for CPU-intensive HTML parsing</li>
                <li>Python for high-level orchestration</li>
                <li>PyO3 for seamless interop</li>
            </ol>

            <h2>Implementation Details</h2>
            <pre><code class="language-rust">use scraper::{Html, Selector};

pub fn extract_content(html: &str) -> Vec<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("p, h1, h2, h3").unwrap();

    document.select(&selector)
        .map(|el| el.text().collect::<String>())
        .collect()
}</code></pre>

            <blockquote>
                <p>"The combination of Rust's performance and Python's ecosystem gives us the best of both worlds."</p>
                <cite>- Tech Lead at DataCorp</cite>
            </blockquote>
        </section>

        <footer>
            <h3>Related Posts</h3>
            <ul>
                <li><a href="/posts/async-rust-scrapers">Async Web Scraping in Rust</a></li>
                <li><a href="/posts/python-rust-ffi">Deep Dive: Python-Rust FFI</a></li>
            </ul>
        </footer>
    </article>
</body>
</html>"""

ECOMMERCE_PRODUCT_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>Professional Web Scraping Toolkit - TechStore</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Professional Web Scraping Toolkit",
        "price": "299.99",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock"
    }
    </script>
</head>
<body>
    <div class="product-page">
        <nav class="breadcrumb">
            <a href="/">Home</a> &gt;
            <a href="/software">Software</a> &gt;
            <a href="/software/development">Development Tools</a> &gt;
            <span>Web Scraping Toolkit</span>
        </nav>

        <div class="product-main">
            <div class="gallery">
                <img src="/products/scraper-toolkit/main.jpg" alt="Scraping toolkit interface">
                <div class="thumbnails">
                    <img src="/products/scraper-toolkit/thumb1.jpg" alt="Dashboard view">
                    <img src="/products/scraper-toolkit/thumb2.jpg" alt="Code editor">
                    <img src="/products/scraper-toolkit/thumb3.jpg" alt="Data export">
                </div>
            </div>

            <div class="product-info">
                <h1>Professional Web Scraping Toolkit</h1>
                <div class="rating">
                    <span class="stars">★★★★★</span>
                    <span class="count">(127 reviews)</span>
                </div>

                <div class="price">
                    <span class="currency">$</span>
                    <span class="amount">299.99</span>
                    <span class="original">$399.99</span>
                    <span class="discount">-25%</span>
                </div>

                <div class="features">
                    <h3>Key Features:</h3>
                    <ul>
                        <li>✓ Multi-threaded scraping engine</li>
                        <li>✓ JavaScript rendering support</li>
                        <li>✓ Automatic proxy rotation</li>
                        <li>✓ Data export to CSV, JSON, Excel</li>
                        <li>✓ Visual scraping rule builder</li>
                    </ul>
                </div>

                <button class="add-to-cart">Add to Cart</button>
            </div>
        </div>

        <div class="product-details">
            <h2>Product Description</h2>
            <p>The Professional Web Scraping Toolkit is a comprehensive solution for data extraction from websites. Built with performance in mind, it combines the power of Rust-based parsing with an intuitive Python API.</p>

            <h3>Technical Specifications</h3>
            <table class="specs">
                <tr>
                    <td>Supported OS</td>
                    <td>Windows 10+, macOS 10.15+, Linux</td>
                </tr>
                <tr>
                    <td>Programming Languages</td>
                    <td>Python 3.8+, Rust bindings included</td>
                </tr>
                <tr>
                    <td>Memory Requirements</td>
                    <td>Minimum 4GB, Recommended 8GB+</td>
                </tr>
                <tr>
                    <td>License Type</td>
                    <td>Commercial, per-developer</td>
                </tr>
            </table>
        </div>
    </div>
</body>
</html>"""

NEWS_ARTICLE = """<!DOCTYPE html>
<html>
<head>
    <title>Tech Giants Invest Billions in AI Infrastructure - TechNews Daily</title>
    <meta property="article:published_time" content="2024-01-20T10:30:00Z">
    <meta property="article:author" content="Michael Rodriguez">
</head>
<body>
    <header class="site-header">
        <div class="logo">TechNews Daily</div>
        <nav>
            <a href="/tech">Technology</a>
            <a href="/business">Business</a>
            <a href="/science">Science</a>
        </nav>
    </header>

    <article class="news-article">
        <h1>Tech Giants Invest Billions in AI Infrastructure</h1>

        <div class="article-meta">
            <time>January 20, 2024 10:30 AM EST</time>
            <span class="author">By Michael Rodriguez</span>
            <span class="category">Technology</span>
        </div>

        <div class="lead">
            <p><strong>Major technology companies announced unprecedented investments in AI infrastructure, totaling over $100 billion for 2024, as the race for artificial intelligence supremacy intensifies.</strong></p>
        </div>

        <figure class="main-image">
            <img src="/images/2024/01/ai-datacenter.jpg" alt="Modern AI datacenter with rows of servers">
            <figcaption>AI-optimized datacenters are being built at record pace. Photo: TechNews/J. Smith</figcaption>
        </figure>

        <div class="article-body">
            <p>In a series of announcements that underscore the critical importance of artificial intelligence to the future of technology, leading tech companies have committed to massive infrastructure investments.</p>

            <h2>Breaking Down the Numbers</h2>
            <p>The investments include:</p>
            <ul>
                <li>MegaCorp: $35 billion for new AI research facilities</li>
                <li>TechGiant Inc: $28 billion for GPU clusters</li>
                <li>CloudLeader: $25 billion for global AI datacenters</li>
                <li>InnovateTech: $15 billion for quantum-AI hybrid systems</li>
            </ul>

            <blockquote class="expert-quote">
                <p>"This level of investment signals a fundamental shift in how companies view AI - not as an experiment, but as core infrastructure."</p>
                <cite>Dr. Lisa Wang, AI Industry Analyst</cite>
            </blockquote>

            <h2>Impact on the Industry</h2>
            <p>These investments are expected to accelerate AI development across multiple sectors, from healthcare to autonomous vehicles.</p>

            <div class="infographic">
                <h3>AI Investment Timeline</h3>
                <dl>
                    <dt>2020</dt><dd>$15 billion total industry investment</dd>
                    <dt>2022</dt><dd>$45 billion total industry investment</dd>
                    <dt>2024</dt><dd>$100+ billion projected investment</dd>
                </dl>
            </div>
        </div>

        <aside class="related-articles">
            <h3>Related Stories</h3>
            <ul>
                <li><a href="/2024/01/19/ai-chip-shortage">Global AI Chip Shortage Drives Innovation</a></li>
                <li><a href="/2024/01/18/startup-funding">AI Startups Secure Record Funding</a></li>
            </ul>
        </aside>
    </article>

    <section class="comments">
        <h3>Reader Comments (42)</h3>
        <p class="comment-cta">Join the discussion about AI infrastructure investments</p>
    </section>
</body>
</html>"""
