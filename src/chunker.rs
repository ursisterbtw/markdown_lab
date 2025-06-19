use once_cell::sync::Lazy;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::borrow::Cow;
use std::collections::VecDeque;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ChunkerError {
    #[error("Regex error: {0}")]
    RegexError(#[from] regex::Error),

    #[error("Parsing error: {0}")]
    ParsingError(String),

    #[error("Other error: {0}")]
    Other(String),
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Chunk {
    pub content: String,
    pub metadata: ChunkMetadata,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChunkMetadata {
    pub heading: Option<String>,
    pub level: usize,
    pub position: usize,
    pub word_count: usize,
    pub char_count: usize,
    pub semantic_density: f32, // A measure of the information density
}

// Cache commonly used regexes for better performance
static HEADING_REGEX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^(#{1,6})\s+(.+)$").expect("Invalid heading regex"));

#[allow(dead_code)]
static SENTENCE_SPLIT_REGEX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"[.!?]+\s+").expect("Invalid sentence split regex"));

#[allow(dead_code)]
static PARAGRAPH_SPLIT_REGEX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\n\s*\n").expect("Invalid paragraph split regex"));

/// Creates semantically meaningful chunks from markdown content with improved handling of document structure.
/// Uses cached regex patterns and memory-efficient processing for better performance.
pub fn create_semantic_chunks(
    markdown: &str,
    chunk_size: usize,
    chunk_overlap: usize,
) -> Result<Vec<String>, ChunkerError> {
    let chunks = semantic_chunking_optimized(markdown, chunk_size, chunk_overlap)?;

    // Return just the content strings for Python integration
    Ok(chunks.into_iter().map(|chunk| chunk.content).collect())
}

/// Memory-optimized semantic chunking using cached patterns and streaming approach.
fn semantic_chunking_optimized(
    markdown: &str,
    chunk_size: usize,
    chunk_overlap: usize,
) -> Result<Vec<Chunk>, ChunkerError> {
    let mut chunker = StreamingChunker::new(chunk_size, chunk_overlap);

    // Process in lines to maintain semantic boundaries
    for line in markdown.lines() {
        if let Some(_chunk) = chunker.add_line(line)? {
            // Chunk is complete, could yield it here if needed
            // For now, we'll collect all at the end
        }
    }

    // Get final chunks
    chunker.finalize()
}

/// Internal function that does the actual semantic chunking
#[allow(dead_code)]
fn semantic_chunking(
    markdown: &str,
    chunk_size: usize,
    chunk_overlap: usize,
    heading_regex: &Regex,
) -> Result<Vec<Chunk>, ChunkerError> {
    let lines: Vec<&str> = markdown.lines().collect();
    let mut chunks: Vec<Chunk> = Vec::new();

    let mut current_chunk = String::new();
    let mut current_heading: Option<String> = None;
    let mut current_level = 0;
    let mut current_position = 0;

    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];

        // Check if this is a heading
        if let Some(captures) = heading_regex.captures(line) {
            let heading_level = captures[1].len();
            let heading_text = &captures[2];

            // If we've accumulated content, save it as a chunk before starting a new section
            if !current_chunk.is_empty() {
                chunks.push(create_chunk_object(
                    &current_chunk,
                    current_heading.clone(),
                    current_level,
                    current_position,
                ));
                current_position += 1;
            }

            // Set the new heading info
            current_heading = Some(heading_text.to_string());
            current_level = heading_level;
            current_chunk = line.to_string();
        } else {
            // Add line to current chunk
            if !current_chunk.is_empty() {
                current_chunk.push('\n');
            }
            current_chunk.push_str(line);

            // Check if current chunk is too large
            if current_chunk.len() > chunk_size {
                let split_point = find_good_split_point(&current_chunk, chunk_size - chunk_overlap);

                let (first_part, remaining) = current_chunk.split_at(split_point);

                // Save the first part as a chunk
                chunks.push(create_chunk_object(
                    first_part,
                    current_heading.clone(),
                    current_level,
                    current_position,
                ));
                current_position += 1;

                // Start a new chunk with the overlap
                current_chunk = remaining.trim().to_string();
            }
        }

        i += 1;
    }

    // Add the final chunk
    if !current_chunk.is_empty() {
        chunks.push(create_chunk_object(
            &current_chunk,
            current_heading,
            current_level,
            current_position,
        ));
    }

    Ok(chunks)
}

/// Helper function to create a chunk object with metadata
fn create_chunk_object(
    content: &str,
    heading: Option<String>,
    level: usize,
    position: usize,
) -> Chunk {
    let words = content.split_whitespace().count();
    let chars = content.chars().count();

    // Calculate a very basic semantic density score
    // Higher score = more semantic meaning relative to length
    let semantic_density = calculate_semantic_density(content);

    Chunk {
        content: content.to_string(),
        metadata: ChunkMetadata {
            heading,
            level,
            position,
            word_count: words,
            char_count: chars,
            semantic_density,
        },
    }
}

/// Find a good split point that doesn't break in the middle of a sentence or paragraph
#[allow(dead_code)]
fn find_good_split_point(text: &str, approximate_position: usize) -> usize {
    if approximate_position >= text.len() {
        return text.len();
    }

    // Look forward for paragraph break (double newline)
    if let Some(pos) = text[approximate_position..].find("\n\n") {
        return approximate_position + pos + 2; // Include both newlines
    }

    // Look forward for single newline
    if let Some(pos) = text[approximate_position..].find('\n') {
        return approximate_position + pos + 1; // Include the newline
    }

    // Look forward for sentence break
    for (i, c) in text[approximate_position..].char_indices() {
        if c == '.' || c == '!' || c == '?' {
            // Find next non-whitespace or end of string
            let mut end_pos = approximate_position + i + 1;
            while end_pos < text.len()
                && text.chars().nth(end_pos).is_some_and(|c| c.is_whitespace())
            {
                end_pos += 1;
            }
            return end_pos;
        }
    }

    // Fall back to word boundary
    for (i, c) in text[approximate_position..].char_indices() {
        if c.is_whitespace() {
            return approximate_position + i + 1;
        }
    }

    // Last resort
    approximate_position
}

/// Calculate semantic density score
/// This is a simple implementation that can be enhanced later
fn calculate_semantic_density(text: &str) -> f32 {
    let word_count = text.split_whitespace().count() as f32;
    if word_count == 0.0 {
        return 0.0;
    }

    // Count semantic indicators like entity names, numbers, special terms
    let mut semantic_indicators = 0.0;

    // Check for specialized keywords
    let keywords = [
        "function",
        "class",
        "method",
        "algorithm",
        "process",
        "system",
        "data",
        "model",
        "analysis",
        "implementation",
    ];

    for word in text.split_whitespace() {
        // Count words that start with uppercase (potential named entities)
        if word.chars().next().is_some_and(|c| c.is_uppercase()) {
            semantic_indicators += 0.5;
        }

        // Count numbers (dates, quantities, etc.)
        if word.chars().any(|c| c.is_numeric()) {
            semantic_indicators += 0.3;
        }

        // Count domain keywords
        if keywords.iter().any(|&k| word.to_lowercase().contains(k)) {
            semantic_indicators += 0.7;
        }
    }

    // Calculate ratio (scale it between 0.0-1.0)
    let density = (semantic_indicators / word_count).min(1.0);

    // Weight longer chunks slightly higher (they're more coherent if they stay together)
    let length_bonus = (word_count / 100.0).min(0.2); // Max 0.2 bonus

    density + length_bonus
}

/// Trait for chunking implementations to enable polymorphism and testing.
pub trait Chunker {
    /// Add a line to the chunker and return a completed chunk if ready.
    fn add_line(&mut self, line: &str) -> Result<Option<&Chunk>, ChunkerError>;

    /// Finalize processing and return all completed chunks.
    fn finalize(self) -> Result<Vec<Chunk>, ChunkerError>;

    /// Get the current chunk size configuration.
    fn chunk_size(&self) -> usize;

    /// Get the current chunk overlap configuration.
    fn chunk_overlap(&self) -> usize;
}

/// Streaming chunker for memory-efficient processing of large documents.
/// Uses a sliding window approach with semantic boundary detection.
pub struct StreamingChunker {
    chunk_size: usize,
    chunk_overlap: usize,
    #[allow(dead_code)]
    window: VecDeque<String>,
    current_chunk: String,
    current_heading: Option<String>,
    current_level: usize,
    position: usize,
    completed_chunks: Vec<Chunk>,
}

impl StreamingChunker {
    /// Create a new streaming chunker with specified parameters.
    pub fn new(chunk_size: usize, chunk_overlap: usize) -> Self {
        Self {
            chunk_size,
            chunk_overlap,
            window: VecDeque::with_capacity(100), // Reasonable buffer size
            current_chunk: String::with_capacity(chunk_size + chunk_overlap),
            current_heading: None,
            current_level: 0,
            position: 0,
            completed_chunks: Vec::new(),
        }
    }

    /// Add a line to the chunker and return a completed chunk if ready.
    pub fn add_line(&mut self, line: &str) -> Result<Option<&Chunk>, ChunkerError> {
        // Check if this is a heading using cached regex
        if let Some(captures) = HEADING_REGEX.captures(line) {
            let heading_level = captures[1].len();
            let heading_text = &captures[2];

            // If we've accumulated content, finalize current chunk
            if !self.current_chunk.is_empty() {
                self.finalize_current_chunk();
            }

            // Start new section with heading
            self.current_heading = Some(heading_text.to_string());
            self.current_level = heading_level;
            self.current_chunk = line.to_string();
        } else {
            // Add line to current chunk
            if !self.current_chunk.is_empty() {
                self.current_chunk.push('\n');
            }
            self.current_chunk.push_str(line);

            // Check if current chunk exceeds size limit
            if self.current_chunk.len() > self.chunk_size {
                self.split_large_chunk()?;
            }
        }

        // Return the most recently completed chunk if any
        Ok(self.completed_chunks.last())
    }

    /// Finalize processing and return all completed chunks.
    pub fn finalize(mut self) -> Result<Vec<Chunk>, ChunkerError> {
        // Add any remaining content as final chunk
        if !self.current_chunk.is_empty() {
            self.finalize_current_chunk();
        }

        Ok(self.completed_chunks)
    }

    fn finalize_current_chunk(&mut self) {
        let chunk = create_chunk_object(
            &self.current_chunk,
            self.current_heading.clone(),
            self.current_level,
            self.position,
        );

        self.completed_chunks.push(chunk);
        self.position += 1;
        self.current_chunk.clear();
    }

    fn split_large_chunk(&mut self) -> Result<(), ChunkerError> {
        let split_point = self.find_optimal_split_point(&self.current_chunk);

        let (first_part, remaining) = self.current_chunk.split_at(split_point);

        // Create chunk from first part
        let chunk = create_chunk_object(
            first_part,
            self.current_heading.clone(),
            self.current_level,
            self.position,
        );

        self.completed_chunks.push(chunk);
        self.position += 1;

        // Prepare next chunk with overlap
        let overlap_start = if first_part.len() > self.chunk_overlap {
            first_part.len() - self.chunk_overlap
        } else {
            0
        };

        let overlap_text = &first_part[overlap_start..];

        // Start new chunk with overlap + remaining content
        self.current_chunk = format!("{}{}", overlap_text, remaining.trim());

        Ok(())
    }

    fn find_optimal_split_point(&self, text: &str) -> usize {
        let target_position = self.chunk_size.saturating_sub(self.chunk_overlap);

        if target_position >= text.len() {
            return text.len();
        }

        // Try different split strategies in order of preference

        // 1. Paragraph break (double newline)
        if let Some(pos) = text[..target_position].rfind("\n\n") {
            return pos + 2;
        }

        // 2. Single line break
        if let Some(pos) = text[..target_position].rfind('\n') {
            return pos + 1;
        }

        // 3. Sentence ending
        for (i, c) in text[..target_position].char_indices().rev() {
            if matches!(c, '.' | '!' | '?') {
                // Look for whitespace after punctuation
                if let Some(next_char) = text.chars().nth(i + 1) {
                    if next_char.is_whitespace() {
                        return i + 2; // Include punctuation + whitespace
                    }
                }
            }
        }

        // 4. Word boundary
        if let Some(pos) = text[..target_position].rfind(char::is_whitespace) {
            return pos + 1;
        }

        // 5. Fallback to target position
        target_position
    }
}

impl Chunker for StreamingChunker {
    fn add_line(&mut self, line: &str) -> Result<Option<&Chunk>, ChunkerError> {
        self.add_line(line)
    }

    fn finalize(self) -> Result<Vec<Chunk>, ChunkerError> {
        self.finalize()
    }

    fn chunk_size(&self) -> usize {
        self.chunk_size
    }

    fn chunk_overlap(&self) -> usize {
        self.chunk_overlap
    }
}

/// Efficient text cleaning that uses Cow<str> for zero-copy optimization.
/// Only allocates new memory when cleaning is actually needed.
pub fn clean_text_smart(input: &str) -> Cow<'_, str> {
    // Quick check if cleaning is needed
    let needs_cleaning = input.chars().any(|c| {
        c.is_control() && c != '\n' && c != '\t'
            || c.is_whitespace() && c != ' ' && c != '\n' && c != '\t'
    }) || input.contains("  "); // Multiple spaces

    if !needs_cleaning {
        return Cow::Borrowed(input);
    }

    // Clean the text
    let cleaned = input
        .chars()
        .filter_map(|c| {
            if c.is_control() && c != '\n' && c != '\t' {
                None // Remove control characters except newline and tab
            } else if c.is_whitespace() && c != ' ' && c != '\n' {
                Some(' ') // Normalize whitespace to spaces
            } else {
                Some(c)
            }
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");

    Cow::Owned(cleaned)
}

/// Memory-efficient chunk metadata calculation using iterator patterns.
/// Avoids creating intermediate collections when possible.
pub fn calculate_chunk_metadata_efficient(content: &str) -> ChunkMetadata {
    let word_count = content.split_whitespace().count();
    let char_count = content.chars().count();

    // Calculate semantic density using streaming approach
    let semantic_density = calculate_semantic_density_streaming(content);

    ChunkMetadata {
        heading: None, // To be set by caller
        level: 0,      // To be set by caller
        position: 0,   // To be set by caller
        word_count,
        char_count,
        semantic_density,
    }
}

/// Streaming calculation of semantic density to avoid multiple string iterations.
fn calculate_semantic_density_streaming(text: &str) -> f32 {
    let mut word_count = 0;
    let mut semantic_indicators = 0.0;

    // Process words in a single iteration
    for word in text.split_whitespace() {
        word_count += 1;

        // Count semantic indicators
        if word.chars().next().map_or(false, |c| c.is_uppercase()) {
            semantic_indicators += 0.5; // Named entities
        }

        if word.chars().any(|c| c.is_numeric()) {
            semantic_indicators += 0.3; // Numbers, dates, quantities
        }

        // Check for domain keywords (using more efficient approach)
        let word_lower = word.to_lowercase();
        if matches!(
            word_lower.as_str(),
            "function"
                | "class"
                | "method"
                | "algorithm"
                | "process"
                | "system"
                | "data"
                | "model"
                | "analysis"
                | "implementation"
        ) {
            semantic_indicators += 0.7;
        }
    }

    if word_count == 0 {
        return 0.0;
    }

    let word_count_f32 = word_count as f32;
    let density = (semantic_indicators / word_count_f32).min(1.0);
    let length_bonus = (word_count_f32 / 100.0).min(0.2);

    density + length_bonus
}
