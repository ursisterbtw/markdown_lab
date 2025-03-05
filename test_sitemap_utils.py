import unittest
from unittest import mock
import xml.etree.ElementTree as ET
from io import StringIO
import tempfile
import shutil
from pathlib import Path

from sitemap_utils import SitemapParser, SitemapURL, discover_site_urls


class TestSitemapUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.parser = SitemapParser()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    @mock.patch("sitemap_utils.SitemapParser._make_request")
    def test_parse_sitemap(self, mock_make_request):
        # Mock a simple sitemap XML
        mock_make_request.return_value = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/</loc>
                <lastmod>2023-05-17</lastmod>
                <changefreq>daily</changefreq>
                <priority>1.0</priority>
            </url>
            <url>
                <loc>https://example.com/about</loc>
                <lastmod>2023-05-16</lastmod>
                <changefreq>weekly</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>https://example.com/contact</loc>
                <changefreq>monthly</changefreq>
                <priority>0.5</priority>
            </url>
        </urlset>
        """
        
        urls = self.parser.parse_sitemap("https://example.com")
        
        # Check that we got the right number of URLs
        self.assertEqual(len(urls), 3)
        
        # Check URL properties
        self.assertEqual(urls[0].loc, "https://example.com/")
        self.assertEqual(urls[0].lastmod, "2023-05-17")
        self.assertEqual(urls[0].changefreq, "daily")
        self.assertEqual(urls[0].priority, 1.0)
        
        self.assertEqual(urls[1].loc, "https://example.com/about")
        self.assertEqual(urls[1].lastmod, "2023-05-16")
        self.assertEqual(urls[1].changefreq, "weekly")
        self.assertEqual(urls[1].priority, 0.8)
        
        self.assertEqual(urls[2].loc, "https://example.com/contact")
        self.assertIsNone(urls[2].lastmod)
        self.assertEqual(urls[2].changefreq, "monthly")
        self.assertEqual(urls[2].priority, 0.5)
        
    @mock.patch("sitemap_utils.SitemapParser._make_request")
    def test_parse_sitemap_index(self, mock_make_request):
        # Mock sitemap index and child sitemaps
        def side_effect(url):
            if url == "https://example.com/sitemap.xml":
                return """<?xml version="1.0" encoding="UTF-8"?>
                <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <sitemap>
                        <loc>https://example.com/sitemap1.xml</loc>
                    </sitemap>
                    <sitemap>
                        <loc>https://example.com/sitemap2.xml</loc>
                    </sitemap>
                </sitemapindex>
                """
            elif url == "https://example.com/sitemap1.xml":
                return """<?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url>
                        <loc>https://example.com/page1</loc>
                        <priority>0.9</priority>
                    </url>
                </urlset>
                """
            elif url == "https://example.com/sitemap2.xml":
                return """<?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url>
                        <loc>https://example.com/page2</loc>
                        <priority>0.7</priority>
                    </url>
                </urlset>
                """
                
        mock_make_request.side_effect = side_effect
        
        urls = self.parser.parse_sitemap("https://example.com/sitemap.xml")
        
        # Check that we got URLs from both child sitemaps
        self.assertEqual(len(urls), 2)
        self.assertEqual({url.loc for url in urls}, {"https://example.com/page1", "https://example.com/page2"})
    
    @mock.patch("sitemap_utils.SitemapParser._make_request")
    def test_robots_txt_parser(self, mock_make_request):
        # Mock robots.txt and sitemap
        def side_effect(url):
            if url == "https://example.com/robots.txt":
                return """
                User-agent: *
                Disallow: /private/
                
                Sitemap: https://example.com/custom_sitemap.xml
                """
            elif url == "https://example.com/custom_sitemap.xml":
                return """<?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url>
                        <loc>https://example.com/home</loc>
                        <priority>1.0</priority>
                    </url>
                </urlset>
                """
                
        mock_make_request.side_effect = side_effect
        
        # Enable respect_robots_txt
        self.parser.respect_robots_txt = True
        urls = self.parser.parse_sitemap("https://example.com")
        
        # Check that we found the URL from the custom sitemap
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0].loc, "https://example.com/home")
        
    def test_filter_urls(self):
        # Create test URLs
        urls = [
            SitemapURL(loc="https://example.com/blog/post1", priority=0.8),
            SitemapURL(loc="https://example.com/blog/post2", priority=0.5),
            SitemapURL(loc="https://example.com/products/item1", priority=0.9),
            SitemapURL(loc="https://example.com/about", priority=0.3),
        ]
        
        # Set up parser with test URLs
        self.parser.discovered_urls = urls
        
        # Filter by priority
        filtered = self.parser.filter_urls(min_priority=0.6)
        self.assertEqual(len(filtered), 2)
        self.assertEqual({url.loc for url in filtered}, 
                         {"https://example.com/blog/post1", "https://example.com/products/item1"})
        
        # Filter by include pattern
        filtered = self.parser.filter_urls(include_patterns=["blog/.*"])
        self.assertEqual(len(filtered), 2)
        self.assertEqual({url.loc for url in filtered}, 
                         {"https://example.com/blog/post1", "https://example.com/blog/post2"})
        
        # Filter by exclude pattern
        filtered = self.parser.filter_urls(exclude_patterns=["blog/.*"])
        self.assertEqual(len(filtered), 2)
        self.assertEqual({url.loc for url in filtered}, 
                         {"https://example.com/products/item1", "https://example.com/about"})
        
        # Combined filtering
        filtered = self.parser.filter_urls(
            min_priority=0.5,
            include_patterns=["blog/.*", "products/.*"],
            exclude_patterns=[".*post2"]
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual({url.loc for url in filtered}, 
                         {"https://example.com/blog/post1", "https://example.com/products/item1"})
        
    def test_export_urls_to_file(self):
        # Create test URLs
        urls = [
            SitemapURL(loc="https://example.com/page1", priority=0.8, lastmod="2023-05-17"),
            SitemapURL(loc="https://example.com/page2", priority=0.5),
        ]
        
        # Set up output file
        output_file = Path(self.test_dir) / "urls.txt"
        
        # Export URLs
        self.parser.export_urls_to_file(urls, str(output_file))
        
        # Check file exists
        self.assertTrue(output_file.exists())
        
        # Check file contents
        with open(output_file, "r") as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].strip(), "https://example.com/page1,0.8,2023-05-17")
        self.assertEqual(lines[1].strip(), "https://example.com/page2,0.5")
        
    @mock.patch("sitemap_utils.SitemapParser.parse_sitemap")
    @mock.patch("sitemap_utils.SitemapParser.filter_urls")
    def test_discover_site_urls(self, mock_filter, mock_parse):
        # Set up mocks
        mock_parse.return_value = [
            SitemapURL(loc="https://example.com/page1"),
            SitemapURL(loc="https://example.com/page2"),
        ]
        mock_filter.return_value = [
            SitemapURL(loc="https://example.com/page1"),
        ]
        
        # Call the convenience function
        urls = discover_site_urls(
            base_url="https://example.com",
            min_priority=0.5,
            include_patterns=["page1"]
        )
        
        # Check results
        self.assertEqual(urls, ["https://example.com/page1"])
        
        # Check the function called the parser methods correctly
        mock_parse.assert_called_once_with("https://example.com")
        mock_filter.assert_called_once()
        mock_filter.assert_called_with(
            min_priority=0.5,
            include_patterns=["page1"],
            exclude_patterns=None,
            limit=None
        )


if __name__ == "__main__":
    unittest.main() 