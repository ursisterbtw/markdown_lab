"""
Unit tests for thread pool singleton implementation.
"""

import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from markdown_lab.utils.thread_pool import SharedThreadPool


class TestSharedThreadPool(unittest.TestCase):
    """Test cases for SharedThreadPool singleton."""

    def setUp(self):
        """Reset singleton state before each test."""
        # Reset the singleton state
        SharedThreadPool._instance = None
        SharedThreadPool._executor = None

    def tearDown(self):
        """Clean up after each test."""
        # Shutdown executor if it exists
        if SharedThreadPool._executor:
            SharedThreadPool._executor.shutdown(wait=False)
        SharedThreadPool._instance = None
        SharedThreadPool._executor = None

    def test_singleton_pattern(self):
        """Test that only one instance is created."""
        executor1 = SharedThreadPool.get_executor()
        executor2 = SharedThreadPool.get_executor()

        # Should be the same object
        self.assertIs(executor1, executor2)

    def test_thread_safety(self):
        """Test thread-safe singleton creation."""
        executors = []
        barrier = threading.Barrier(10)

        def get_executor_with_barrier():
            barrier.wait()  # Ensure all threads start at the same time
            executors.append(SharedThreadPool.get_executor())

        threads = [
            threading.Thread(target=get_executor_with_barrier)
            for _ in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All executors should be the same instance
        first_executor = executors[0]
        for executor in executors[1:]:
            self.assertIs(executor, first_executor)

    def test_custom_max_workers(self):
        """Test custom max_workers parameter."""
        # First call with max_workers=2
        executor1 = SharedThreadPool.get_executor(max_workers=2)
        self.assertIsInstance(executor1, ThreadPoolExecutor)

        # Second call with different max_workers should return same executor
        executor2 = SharedThreadPool.get_executor(max_workers=5)
        self.assertIs(executor1, executor2)

    def test_executor_functionality(self):
        """Test that the executor actually works."""
        executor = SharedThreadPool.get_executor(max_workers=2)

        def task(n):
            time.sleep(0.01)
            return n * 2

        # Submit tasks
        futures = [executor.submit(task, i) for i in range(5)]

        # Get results
        results = [f.result() for f in futures]

        # Check results
        expected = [0, 2, 4, 6, 8]
        self.assertEqual(results, expected)

    def test_executor_reuse_performance(self):
        """Test performance benefit of reusing executor."""
        # Time creating new executors
        start = time.perf_counter()
        for _ in range(10):
            executor = ThreadPoolExecutor(max_workers=4)
            executor.shutdown(wait=False)
        new_executor_time = time.perf_counter() - start

        # Time reusing singleton executor
        start = time.perf_counter()
        for _ in range(10):
            executor = SharedThreadPool.get_executor(max_workers=4)
            # No shutdown, reusing same instance
        singleton_time = time.perf_counter() - start

        # Singleton should be faster (or at least not much slower)
        # Due to system variability, we just check it's not significantly slower
        self.assertLess(singleton_time, new_executor_time * 2)

    def test_shutdown_method(self):
        """Test the shutdown method."""
        executor = SharedThreadPool.get_executor()

        # Submit a task
        future = executor.submit(lambda: 42)
        result = future.result()
        self.assertEqual(result, 42)

        # Shutdown
        SharedThreadPool.shutdown()

        # Executor should be None
        self.assertIsNone(SharedThreadPool._executor)

        # Getting executor again should create a new one
        new_executor = SharedThreadPool.get_executor()
        self.assertIsNotNone(new_executor)
        self.assertIsNot(new_executor, executor)

    def test_concurrent_task_execution(self):
        """Test concurrent execution of tasks."""
        executor = SharedThreadPool.get_executor(max_workers=4)

        task_count = 20
        sleep_time = 0.05

        def slow_task(i):
            time.sleep(sleep_time)
            return i

        # Sequential execution time estimate
        sequential_estimate = task_count * sleep_time

        # Execute tasks in parallel
        start = time.perf_counter()
        futures = [executor.submit(slow_task, i) for i in range(task_count)]
        results = [f.result() for f in futures]
        parallel_time = time.perf_counter() - start

        # Check results are correct
        self.assertEqual(results, list(range(task_count)))

        # Parallel execution should be faster than sequential
        # With 4 workers, should take roughly task_count/4 * sleep_time
        self.assertLess(parallel_time, sequential_estimate / 2)

    def test_error_handling(self):
        """Test error handling in tasks."""
        executor = SharedThreadPool.get_executor()

        def failing_task():
            raise ValueError("Test error")

        # Submit failing task
        future = executor.submit(failing_task)

        # Should raise the exception when getting result
        with self.assertRaises(ValueError) as cm:
            future.result()

        self.assertEqual(str(cm.exception), "Test error")

    def test_multiple_shutdown_calls(self):
        """Test that multiple shutdown calls are handled gracefully."""
        SharedThreadPool.get_executor()

        # Multiple shutdowns should not raise errors
        SharedThreadPool.shutdown()
        SharedThreadPool.shutdown()  # Should handle gracefully

        self.assertIsNone(SharedThreadPool._executor)

    @patch('markdown_lab.utils.thread_pool.ThreadPoolExecutor')
    def test_executor_creation_parameters(self, mock_executor_class):
        """Test that ThreadPoolExecutor is created with correct parameters."""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Get executor with specific max_workers
        result = SharedThreadPool.get_executor(max_workers=8)

        # Check ThreadPoolExecutor was called with correct params
        mock_executor_class.assert_called_once_with(max_workers=8, thread_name_prefix='MarkdownLab')

        # Result should be the mock executor
        self.assertEqual(result, mock_executor)


if __name__ == "__main__":
    unittest.main()
