"""
Shared thread pool utilities for optimal parallel processing performance.
Eliminates ThreadPoolExecutor recreation overhead across batch operations.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional


class SharedThreadPool:
    """
    Singleton thread pool for reusing worker threads across multiple operations.
    Provides significant performance improvement by avoiding pool recreation overhead.
    """

    _instance: Optional['SharedThreadPool'] = None
    _executor: Optional[ThreadPoolExecutor] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'SharedThreadPool':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_executor(cls, max_workers: Optional[int] = None) -> ThreadPoolExecutor:
        """
        Get the shared ThreadPoolExecutor instance, creating it if necessary.
        
        Args:
            max_workers: Maximum number of worker threads. If None, uses default.
                        Note: This is only used for initial creation.
        
        Returns:
            Shared ThreadPoolExecutor instance
        """
        if cls._executor is None:
            with cls._lock:
                if cls._executor is None:
                    # Use provided max_workers or default to optimal thread count
                    # Default to 2 * cpu_count + 1 for I/O bound tasks, capped at 32
                    default_workers = min(32, (os.cpu_count() or 1) * 2 + 1)
                    workers = max_workers or default_workers
                    cls._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="MarkdownLab")
        return cls._executor

    @classmethod
    def shutdown(cls, wait: bool = True) -> None:
        """
        Shutdown the shared thread pool.
        
        Args:
            wait: If True, wait for all threads to complete
        """
        if cls._executor is not None:
            with cls._lock:
                if cls._executor is not None:
                    cls._executor.shutdown(wait=wait)
                    cls._executor = None

    @classmethod
    def resize_pool(cls, max_workers: int) -> ThreadPoolExecutor:
        """
        Resize the thread pool by recreating it with new worker count.
        
        Args:
            max_workers: New maximum number of worker threads
            
        Returns:
            New ThreadPoolExecutor instance with updated worker count
        """
        cls.shutdown(wait=True)
        with cls._lock:
            cls._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="MarkdownLab")
        return cls._executor


def get_shared_executor(max_workers: Optional[int] = None) -> ThreadPoolExecutor:
    """
    Convenience function to get the shared ThreadPoolExecutor.
    
    Args:
        max_workers: Maximum number of worker threads (only used for initial creation)
        
    Returns:
        Shared ThreadPoolExecutor instance
    """
    return SharedThreadPool.get_executor(max_workers)


def shutdown_shared_pool(wait: bool = True) -> None:
    """
    Convenience function to shutdown the shared thread pool.
    
    Args:
        wait: If True, wait for all threads to complete
    """
    SharedThreadPool.shutdown(wait)

