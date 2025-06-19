# Markdown Lab Phase 2 Task List

## Phase 2 Priority Tasks: Architecture & Performance

Building on Phase 1 foundation to complete the architectural transformation and achieve major performance gains.

### 🏗️ Async Foundation (Week 1-2)

#### TASK-2.01: Implement Async HTTP Client
**File:** `markdown_lab/network/async_client.py`  
**Impact:** High - Enables 300% improvement in multi-URL processing  
**Dependencies:** Phase 1 HTTP client foundation  
**Estimated Performance Gain:** 300% for batch operations  
**Status:** ✅ Completed

**Implementation Target:**
```python
import asyncio
import httpx
from typing import List, Dict, Optional
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.errors import NetworkError

class AsyncHttpClient:
    """High-performance async HTTP client with connection pooling"""
    
    def __init__(self, config: MarkdownLabConfig):
        self.config = config
        self.session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=self.config.timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            )
        )
        return self
    
    async def fetch_multiple(self, urls: List[str]) -> Dict[str, str]:
        """Fetch multiple URLs in parallel with connection pooling"""
        semaphore = asyncio.Semaphore(self.config.parallel_workers)
        
        async def fetch_single(url: str) -> tuple[str, str]:
            async with semaphore:
                response = await self.session.get(url)
                return url, response.text
        
        tasks = [fetch_single(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {url: content for url, content in results 
                if not isinstance(content, Exception)}
```

**Expected Benefits:**
- Process 10-50 URLs in parallel instead of sequentially
- Connection pooling reduces overhead
- Semaphore controls concurrency to respect rate limits
- Exception handling preserves partial results

#### TASK-2.02: Advanced Rate Limiting with Token Bucket
**File:** `markdown_lab/network/throttle.py`  
**Impact:** Medium - Better request pattern management  
**Dependencies:** TASK-2.01  
**Estimated Improvement:** More stable and efficient request patterns  
**Status:** ✅ Completed

**Replace simple sleep-based throttling:**
```python
import time
import asyncio
from typing import Dict, Optional

class TokenBucketThrottler:
    """Advanced rate limiting with burst support and per-domain limits"""
    
    def __init__(self, rate: float, burst_size: int = 10):
        self.rate = rate  # tokens per second
        self.bucket_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._domain_buckets: Dict[str, 'DomainBucket'] = {}
    
    async def acquire(self, tokens: int = 1, domain: Optional[str] = None) -> None:
        """Acquire tokens with optional per-domain limiting"""
        # Global rate limiting
        await self._acquire_global(tokens)
        
        # Per-domain rate limiting if specified
        if domain:
            await self._acquire_domain(domain, tokens)
    
    async def _acquire_global(self, tokens: int) -> None:
        while True:
            now = time.time()
            time_passed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on time passed
            self.tokens = min(
                self.bucket_size,
                self.tokens + time_passed * self.rate
            )
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            
            # Wait for enough tokens to become available
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
```

**Benefits:**
- Supports burst traffic patterns
- Per-domain rate limiting prevents overwhelming specific servers
- More efficient than simple sleep-based approaches
- Configurable burst size for different use cases

### 🧠 Memory & Caching Optimization (Week 3-4)

#### TASK-2.03: Implement Hierarchical Caching System
**File:** `markdown_lab/network/cache.py`  
**Impact:** High - Improves performance and reduces memory usage  
**Dependencies:** TASK-2.01  
**Estimated Memory Reduction:** 30-40%  
**Expected Cache Hit Rate:** 90%  
**Status:** ✅ Completed

**L1/L2/L3 Cache Architecture:**
```python
import asyncio
import hashlib
import pickle
import gzip
from typing import Optional, Dict, Any
from cachetools import LRUCache
import diskcache
from markdown_lab.core.config import MarkdownLabConfig

class HierarchicalCache:
    """Multi-level cache: L1 (Memory) → L2 (Disk) → L3 (Network)"""
    
    def __init__(self, config: MarkdownLabConfig):
        self.config = config
        
        # L1: Memory cache (fastest)
        self.memory_cache = LRUCache(maxsize=1000)
        
        # L2: Disk cache (persistent)
        self.disk_cache = diskcache.Cache(
            directory=config.cache_dir,
            size_limit=config.cache_max_disk
        )
        
        # L3: Network cache (optional, for distributed setups)
        self.network_cache = None  # Configure if needed
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache hierarchy"""
        cache_key = self._hash_key(key)
        
        # L1: Check memory cache first (fastest)
        if result := self.memory_cache.get(cache_key):
            return self._decompress(result)
        
        # L2: Check disk cache
        if result := self.disk_cache.get(cache_key):
            # Promote to memory cache
            self.memory_cache[cache_key] = result
            return self._decompress(result)
        
        # L3: Network cache (if configured)
        if self.network_cache:
            result = await self.network_cache.get(cache_key)
            if result:
                await self.set(key, result)
                return result
        
        return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache hierarchy"""
        cache_key = self._hash_key(key)
        compressed_value = self._compress(value)
        
        # Store in both L1 and L2
        self.memory_cache[cache_key] = compressed_value
        self.disk_cache.set(
            cache_key, 
            compressed_value, 
            expire=ttl or self.config.cache_ttl
        )
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Batch retrieval for better performance"""
        results = {}
        cache_keys = {self._hash_key(key): key for key in keys}
        
        # Batch L1 lookup
        for cache_key, original_key in cache_keys.items():
            if result := self.memory_cache.get(cache_key):
                results[original_key] = self._decompress(result)
        
        # Batch L2 lookup for remaining keys
        remaining_keys = [key for key in keys if key not in results]
        if remaining_keys:
            # Disk cache batch operation would go here
            pass
        
        return results
    
    def _hash_key(self, key: str) -> str:
        """Create consistent hash for cache key"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _compress(self, value: str) -> bytes:
        """Compress value for storage efficiency"""
        return gzip.compress(value.encode('utf-8'))
    
    def _decompress(self, value: bytes) -> str:
        """Decompress stored value"""
        return gzip.decompress(value).decode('utf-8')
```

**Features:**
- **L1 Memory Cache**: LRU cache for fastest access
- **L2 Disk Cache**: Persistent storage with size limits
- **L3 Network Cache**: Optional for distributed deployments
- **Compression**: Reduces memory/disk usage
- **Batch Operations**: Reduces I/O overhead
- **TTL Support**: Automatic expiration

#### TASK-2.04: Optimize Rust Memory Usage
**Files:** `src/html_parser.rs`, `src/chunker.rs`  
**Impact:** High - Reduces memory allocations and copies  
**Dependencies:** None (Rust optimization)  
**Estimated Memory Reduction:** 30%  
**Status:** ✅ Completed

**Memory Optimization Strategies:**

1. **Zero-Copy String Processing:**
```rust
use std::borrow::Cow;

pub fn clean_text(input: &str) -> Cow<str> {
    // Only allocate if cleaning is needed
    if input.chars().all(|c| !c.is_whitespace() || c == ' ') {
        Cow::Borrowed(input)  // No allocation
    } else {
        let cleaned = input
            .chars()
            .map(|c| if c.is_whitespace() { ' ' } else { c })
            .collect::<String>();
        Cow::Owned(cleaned)   // Allocate only when necessary
    }
}
```

2. **Stream-Based Chunking:**
```rust
use std::collections::VecDeque;

pub struct StreamingChunker {
    window: VecDeque<String>,
    chunk_size: usize,
    overlap: usize,
}

impl StreamingChunker {
    pub fn new(chunk_size: usize, overlap: usize) -> Self {
        Self {
            window: VecDeque::with_capacity(chunk_size + overlap),
            chunk_size,
            overlap,
        }
    }
    
    pub fn add_text(&mut self, text: &str) -> Option<String> {
        // Process text in streaming fashion without loading entire document
        // Return chunk when ready, None if more text needed
    }
}
```

3. **Optimized Regex Caching:**
```rust
use std::sync::OnceLock;
use regex::RegexSet;

static CLEANUP_PATTERNS: OnceLock<RegexSet> = OnceLock::new();

pub fn get_cleanup_patterns() -> &'static RegexSet {
    CLEANUP_PATTERNS.get_or_init(|| {
        RegexSet::new(&[
            r"\s+",           // Multiple whitespace
            r"<script[^>]*>.*?</script>", // Script tags
            r"<style[^>]*>.*?</style>",   // Style tags
        ]).unwrap()
    })
}
```

### 🏗️ Architecture Consolidation (Week 5-6)

#### TASK-2.05: Create Modern Converter Pipeline
**Files:** `markdown_lab/processing/converter.py`, `markdown_lab/processing/pipeline.py`  
**Impact:** High - Central conversion orchestration  
**Dependencies:** TASK-2.01, TASK-2.03  
**Estimated LOC Reduction:** 200+ lines

**Unified Conversion Pipeline:**
```python
from abc import ABC, abstractmethod
from typing import Union, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

class OutputFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"

@dataclass
class ConversionResult:
    content: str
    format: OutputFormat
    metadata: Dict[str, Any]
    processing_time: float
    backend_used: str

class ProcessingPipeline:
    """Orchestrates the entire conversion pipeline"""
    
    def __init__(self, config: MarkdownLabConfig):
        self.config = config
        self.cache = HierarchicalCache(config) if config.cache_enabled else None
        self.http_client = AsyncHttpClient(config)
        self.rust_backend = RustBackend()
        self.python_backend = PythonBackend()
    
    async def convert_url(
        self,
        url: str,
        format: OutputFormat = OutputFormat.MARKDOWN,
        options: Optional[Dict[str, Any]] = None
    ) -> ConversionResult:
        """Convert single URL through complete pipeline"""
        
        start_time = time.time()
        
        # Step 1: Check cache
        if self.cache:
            cache_key = f"{url}:{format.value}:{hash(str(options))}"
            if cached := await self.cache.get(cache_key):
                return ConversionResult(
                    content=cached,
                    format=format,
                    metadata={"cache_hit": True},
                    processing_time=time.time() - start_time,
                    backend_used="cache"
                )
        
        # Step 2: Fetch content
        async with self.http_client as client:
            html_content = await client.fetch_single(url)
        
        # Step 3: Convert with preferred backend
        try:
            content = await self.rust_backend.convert(html_content, format, options)
            backend_used = "rust"
        except Exception:
            content = await self.python_backend.convert(html_content, format, options)
            backend_used = "python"
        
        # Step 4: Cache result
        if self.cache:
            await self.cache.set(cache_key, content)
        
        return ConversionResult(
            content=content,
            format=format,
            metadata={"cache_hit": False, "url": url},
            processing_time=time.time() - start_time,
            backend_used=backend_used
        )
    
    async def convert_batch(
        self,
        urls: List[str],
        format: OutputFormat = OutputFormat.MARKDOWN,
        options: Optional[Dict[str, Any]] = None
    ) -> List[ConversionResult]:
        """Convert multiple URLs in parallel"""
        
        tasks = [
            self.convert_url(url, format, options)
            for url in urls
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
```

#### TASK-2.06: Implement Format System
**Files:** `markdown_lab/formats/base.py`, `markdown_lab/formats/markdown.py`, `markdown_lab/formats/json.py`, `markdown_lab/formats/xml.py`  
**Impact:** Medium - Pluggable output formats  
**Dependencies:** TASK-2.05  
**Estimated LOC Reduction:** 150+ lines

**Pluggable Format System:**
```python
# base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseFormatter(ABC):
    """Base class for all output formatters"""
    
    @abstractmethod
    def format(self, document: ParsedDocument) -> str:
        """Format parsed document to target format"""
        pass
    
    @abstractmethod
    def get_extension(self) -> str:
        """Get file extension for this format"""
        pass
    
    @abstractmethod
    def get_mime_type(self) -> str:
        """Get MIME type for this format"""
        pass

# markdown.py
class MarkdownFormatter(BaseFormatter):
    def format(self, document: ParsedDocument) -> str:
        # Delegate to Rust backend for performance
        return rust_backend.to_markdown(document.html, document.options)
    
    def get_extension(self) -> str:
        return ".md"
    
    def get_mime_type(self) -> str:
        return "text/markdown"

# json.py
class JSONFormatter(BaseFormatter):
    def format(self, document: ParsedDocument) -> str:
        # Delegate to Rust backend for performance
        return rust_backend.to_json(document.html, document.options)
    
    def get_extension(self) -> str:
        return ".json"
    
    def get_mime_type(self) -> str:
        return "application/json"

# Format registry
FORMATTERS = {
    OutputFormat.MARKDOWN: MarkdownFormatter(),
    OutputFormat.JSON: JSONFormatter(),
    OutputFormat.XML: XMLFormatter(),
}
```

#### TASK-2.07: Module Restructuring & Migration
**Impact:** High - Long-term maintainability  
**Dependencies:** TASK-2.05, TASK-2.06  
**Estimated Complexity:** Major (affects imports)

**Migration Strategy:**

1. **Create New Module Structure** (Week 5)
   - Implement new modules alongside existing code
   - No breaking changes initially

2. **Compatibility Layer** (Week 5-6)
   ```python
   # Old location: markdown_lab/core/scraper.py
   import warnings
   from markdown_lab.scrapers.web_scraper import WebScraper as NewWebScraper
   
   class MarkdownScraper(NewWebScraper):
       def __init__(self, *args, **kwargs):
           warnings.warn(
               "MarkdownScraper is deprecated. Use WebScraper from "
               "markdown_lab.scrapers.web_scraper instead.",
               DeprecationWarning,
               stacklevel=2
           )
           super().__init__(*args, **kwargs)
   ```

3. **Gradual Migration** (Week 6)
   - Update internal imports to new structure
   - Maintain external compatibility

### 🚀 Performance Validation (Week 7-8)

#### TASK-2.08: Comprehensive Performance Benchmarking
**File:** `scripts/performance_validation.py`  
**Impact:** Critical - Validates all improvements  
**Dependencies:** All optimization tasks  
**Success Criteria:** Meet all performance targets

**Benchmark Suite:**
```python
import asyncio
import time
import psutil
import statistics
from typing import List, Dict

class PerformanceBenchmark:
    """Comprehensive performance validation suite"""
    
    async def benchmark_single_conversion(self, url: str) -> Dict[str, float]:
        """Benchmark single URL conversion"""
        process = psutil.Process()
        
        # Memory before
        memory_before = process.memory_info().rss
        
        start_time = time.time()
        result = await converter.convert_url(url)
        end_time = time.time()
        
        # Memory after
        memory_after = process.memory_info().rss
        
        return {
            "processing_time": end_time - start_time,
            "memory_delta": memory_after - memory_before,
            "content_length": len(result.content),
            "backend_used": result.backend_used
        }
    
    async def benchmark_batch_conversion(self, urls: List[str]) -> Dict[str, Any]:
        """Benchmark parallel batch conversion"""
        start_time = time.time()
        results = await converter.convert_batch(urls)
        end_time = time.time()
        
        return {
            "total_time": end_time - start_time,
            "urls_per_second": len(urls) / (end_time - start_time),
            "successful_conversions": len([r for r in results if not isinstance(r, Exception)]),
            "average_content_length": statistics.mean([len(r.content) for r in results if not isinstance(r, Exception)])
        }
    
    async def benchmark_cache_performance(self, urls: List[str]) -> Dict[str, float]:
        """Benchmark cache hit rates and performance"""
        # First run (populate cache)
        await converter.convert_batch(urls)
        
        # Second run (should hit cache)
        start_time = time.time()
        results = await converter.convert_batch(urls)
        end_time = time.time()
        
        cache_hits = sum(1 for r in results if r.metadata.get("cache_hit", False))
        
        return {
            "cache_hit_rate": cache_hits / len(results),
            "cached_processing_time": end_time - start_time,
            "speedup_factor": "calculated based on comparison"
        }
```

**Performance Targets Validation:**
- Multi-URL processing: 300% improvement (10-50 URLs in parallel)
- Memory usage: 30% reduction (70-85MB typical vs 100-120MB current)
- Cache hit rate: 90% for repeated operations
- Build time: <25 seconds

#### TASK-2.09: Integration Test Suite
**File:** `tests/integration/test_phase2_integration.py`  
**Impact:** High - Ensures correctness  
**Dependencies:** All Phase 2 tasks

**Test Coverage:**
- Full async pipeline validation
- Error handling and recovery
- Performance under load
- Memory usage patterns
- Cache behavior validation
- Multi-format conversion accuracy

## Task Dependencies & Sequencing

```
Phase 1 Foundation ✅
       ↓
   TASK-2.01 (Async HTTP)
       ↓
   TASK-2.02 (Rate Limiting)
       ↓
   TASK-2.03 (Hierarchical Cache) ← TASK-2.04 (Rust Memory Opt)
       ↓
   TASK-2.05 (Converter Pipeline)
       ↓
   TASK-2.06 (Format System)
       ↓
   TASK-2.07 (Module Restructuring)
       ↓
   TASK-2.08 (Performance Benchmarking) ← TASK-2.09 (Integration Tests)
```

## Success Validation Criteria

### Performance Benchmarks
- [ ] Multi-URL processing: 300% improvement validated
- [ ] Memory usage: 30% reduction confirmed  
- [ ] Cache hit rate: 90% achieved
- [ ] Build time: <25 seconds
- [ ] All existing functionality maintained

### Code Quality Metrics
- [ ] LOC reduction: 25-35% total (complete 2,400-2,600 line target)
- [ ] Code duplication: <5% (from current ~20%)
- [ ] Test coverage: 90% line coverage, 80% branch coverage
- [ ] Cyclomatic complexity: <10 for all functions

### Architecture Goals
- [ ] Clean module separation implemented
- [ ] Async/sync compatibility maintained
- [ ] Backward compatibility preserved during transition
- [ ] Comprehensive documentation updated

## Risk Mitigation

### Breaking Changes
- Compatibility layer maintains existing APIs
- Gradual migration with deprecation warnings
- Comprehensive migration documentation

### Performance Risks
- Benchmark every change against baseline
- Circuit breakers for cache/async failures
- Rollback procedures for performance regressions

This Phase 2 task list builds directly on Phase 1 achievements to complete the architectural transformation while delivering the targeted performance improvements and code quality gains.