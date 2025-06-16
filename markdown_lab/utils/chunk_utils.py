"""
Utility module for chunking text content for RAG (Retrieval Augmented Generation).
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


@dataclass
class Chunk:
    """Represents a chunk of content for RAG processing."""

    id: str
    content: str
    metadata: Dict[str, Any]
    source_url: str
    created_at: str
    chunk_type: str


class ContentChunker:
    """Handles chunking of content for RAG systems."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the chunker.

        Args:
            chunk_size: Maximum size of content chunks in characters
            chunk_overlap: Overlap between consecutive chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks_from_markdown(
        self, markdown_content: str, source_url: str
    ) -> List[Chunk]:
        """
        Split the markdown content into chunks for RAG processing.

        Args:
            markdown_content: The markdown content to chunk
            source_url: The URL the content was scraped from

        Returns:
            A list of Chunk objects
        """
        # Split markdown into sections based on headers
        sections = []
        current_section = ""
        current_heading = ""

        for line in markdown_content.split("\n"):
            # Check if the line is a header
            if line.startswith("#"):
                # If we have content in the current section, save it
                if current_section:
                    sections.append((current_heading, current_section))

                current_heading = line
                current_section = line + "\n"
            else:
                current_section += line + "\n"

        # Add the last section if it has content
        if current_section:
            sections.append((current_heading, current_section))

        # Now create chunks from sections
        chunks = []

        # Parse domain for metadata
        domain = urlparse(source_url).netloc

        for section_heading, section_content in sections:
            # If the section is smaller than chunk_size, keep it as one chunk
            if len(section_content) <= self.chunk_size:
                chunk_id = hashlib.md5(
                    f"{source_url}:{section_heading}".encode()
                ).hexdigest()
                chunk = Chunk(
                    id=chunk_id,
                    content=section_content,
                    metadata={
                        "heading": section_heading,
                        "domain": domain,
                        "word_count": len(section_content.split()),
                        "char_count": len(section_content),
                    },
                    source_url=source_url,
                    created_at=datetime.now().isoformat(),
                    chunk_type="section",
                )
                chunks.append(chunk)
            else:
                # Split into overlapping chunks
                words = section_content.split()
                words_per_chunk = (
                    self.chunk_size // 5
                )  # Approximate words per character
                overlap_words = self.chunk_overlap // 5

                for i in range(0, len(words), words_per_chunk - overlap_words):
                    chunk_words = words[i : i + words_per_chunk]
                    if not chunk_words:
                        continue

                    chunk_content = " ".join(chunk_words)
                    chunk_id = hashlib.md5(
                        f"{source_url}:{section_heading}:{i}".encode()
                    ).hexdigest()

                    chunk = Chunk(
                        id=chunk_id,
                        content=chunk_content,
                        metadata={
                            "heading": section_heading,
                            "domain": domain,
                            "position": i // (words_per_chunk - overlap_words),
                            "word_count": len(chunk_words),
                            "char_count": len(chunk_content),
                        },
                        source_url=source_url,
                        created_at=datetime.now().isoformat(),
                        chunk_type="content_chunk",
                    )
                    chunks.append(chunk)

        return chunks

    def save_chunks(
        self, chunks: List[Chunk], output_dir: str, output_format: str = "jsonl"
    ) -> None:
        """
        Saves a list of content chunks to disk in either JSON Lines or individual JSON files.

        Args:
            chunks: The content chunks to save.
            output_dir: Directory where the chunk files will be written.
            output_format: File format for saving chunks; "jsonl" for a single JSON Lines file, "json" for separate JSON files per chunk.
        """
        # Create the output directory if it doesn't exist
        chunk_dir = Path(output_dir)
        chunk_dir.mkdir(parents=True, exist_ok=True)

        if output_format == "jsonl":
            # Save all chunks to a single JSONL file
            output_file = chunk_dir / "chunks.jsonl"
            with open(output_file, "w", encoding="utf-8") as f:
                for chunk in chunks:
                    f.write(json.dumps(asdict(chunk)) + "\n")
            return
        # Save each chunk as a separate JSON file
        for chunk in chunks:
            output_file = chunk_dir / f"{chunk.id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(asdict(chunk), f, indent=2)


def create_semantic_chunks(
    content: str, source_url: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[Chunk]:
    """
    Creates semantic chunks from content, handling both markdown and plain text.

    If the content contains markdown headers, it is split into chunks using markdown-aware logic. Otherwise, the content is divided into overlapping text chunks based on approximate word count. Each chunk includes metadata such as domain, position, word count, and character count.

    Args:
        content: The text to be chunked.
        source_url: The URL associated with the content.

    Returns:
        A list of Chunk objects representing the segmented content.
    """
    chunker = ContentChunker(chunk_size, chunk_overlap)

    # Check if content is likely markdown
    if re.search(r"^#+ ", content, re.MULTILINE):
        return chunker.create_chunks_from_markdown(content, source_url)

    # For non-markdown text, create simple overlapping chunks
    chunks = []
    domain = urlparse(source_url).netloc
    words = content.split()
    words_per_chunk = chunk_size // 5  # Approximate words per character
    overlap_words = chunk_overlap // 5

    for i in range(0, len(words), words_per_chunk - overlap_words):
        chunk_words = words[i : i + words_per_chunk]
        if not chunk_words:
            continue

        chunk_content = " ".join(chunk_words)
        chunk_id = hashlib.md5(f"{source_url}:text:{i}".encode()).hexdigest()

        chunk = Chunk(
            id=chunk_id,
            content=chunk_content,
            metadata={
                "domain": domain,
                "position": i // (words_per_chunk - overlap_words),
                "word_count": len(chunk_words),
                "char_count": len(chunk_content),
            },
            source_url=source_url,
            created_at=datetime.now().isoformat(),
            chunk_type="text_chunk",
        )
        chunks.append(chunk)

    return chunks
