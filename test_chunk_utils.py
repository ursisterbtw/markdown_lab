import json
import shutil
import tempfile
import unittest
from pathlib import Path

from chunk_utils import Chunk, ContentChunker, create_semantic_chunks


class TestChunkUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.chunker = ContentChunker()
        self.test_url = "https://example.com/test"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_create_chunks_from_markdown(self):
        """Test chunk creation from markdown content."""
        # Test markdown with multiple sections
        test_markdown = """# Title

## Section 1
This is content for section 1.
It has multiple lines.

## Section 2
This is content for section 2.
It also has multiple lines.
"""

        chunks = self.chunker.create_chunks_from_markdown(test_markdown, self.test_url)

        # Check we got the right number of chunks
        self.assertEqual(len(chunks), 2)

        # Check chunk contents
        self.assertIn("# Title", chunks[0].content)
        self.assertIn("## Section 1", chunks[0].content)
        self.assertIn("## Section 2", chunks[1].content)

        # Check metadata
        self.assertEqual(chunks[0].metadata["heading"], "# Title")
        self.assertEqual(chunks[1].metadata["heading"], "## Section 2")
        self.assertEqual(chunks[0].source_url, self.test_url)
        self.assertEqual(chunks[0].chunk_type, "section")

    def test_create_large_chunks(self):
        """Test handling of sections larger than chunk_size."""
        # Create a very large section
        large_section = "# Large Section\n" + "This is a word. " * 500

        # Use a smaller chunk size to force chunking
        small_chunker = ContentChunker(chunk_size=100, chunk_overlap=20)
        chunks = small_chunker.create_chunks_from_markdown(large_section, self.test_url)

        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)

        # All chunks should have the same heading in metadata
        self.assertTrue(all(chunk.metadata["heading"] == "# Large Section" for chunk in chunks))
        self.assertTrue(all(chunk.source_url == self.test_url for chunk in chunks))

    def test_save_chunks_jsonl(self):
        """Test saving chunks to JSONL format."""
        chunks = [
            Chunk(
                id="123",
                content="Test content 1",
                metadata={"heading": "Test", "domain": "example.com"},
                source_url=self.test_url,
                created_at="2023-01-01T00:00:00",
                chunk_type="section",
            ),
            Chunk(
                id="456",
                content="Test content 2",
                metadata={"heading": "Test 2", "domain": "example.com"},
                source_url=self.test_url,
                created_at="2023-01-01T00:00:00",
                chunk_type="section",
            ),
        ]

        # Save chunks
        self.chunker.save_chunks(chunks, self.test_dir, "jsonl")

        # Check the file exists
        jsonl_path = Path(self.test_dir) / "chunks.jsonl"
        self.assertTrue(jsonl_path.exists())

        # Check file contents
        with open(jsonl_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)

            # Parse and check contents
            chunk1 = json.loads(lines[0])
            self.assertEqual(chunk1["id"], "123")
            self.assertEqual(chunk1["content"], "Test content 1")

    def test_create_semantic_chunks(self):
        """Test the create_semantic_chunks convenience function."""
        # Test with markdown
        markdown_content = "# Test\n\nThis is a test."
        chunks = create_semantic_chunks(markdown_content, self.test_url)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["heading"], "# Test")

        # Test with plain text
        text_content = "This is just plain text without any markdown headers."
        chunks = create_semantic_chunks(text_content, self.test_url)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, "text_chunk")


if __name__ == "__main__":
    unittest.main()
