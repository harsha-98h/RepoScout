"""
Parallel execution for tool calls
"""

import concurrent.futures
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ParallelExecutor:
    """
    Execute multiple tool calls in parallel
    """
    
    def __init__(self, max_workers=3):
        """
        Initialize parallel executor
        
        Args:
            max_workers: Maximum concurrent workers
        """
        self.max_workers = max_workers
    
    def execute_parallel(self, tasks):
        """
        Execute multiple tasks in parallel
        
        Args:
            tasks: List of (function, args, kwargs) tuples
            
        Returns:
            List of results in same order as tasks
        """
        logger.info(f"⚡ Executing {len(tasks)} tasks in parallel...")
        
        results = [None] * len(tasks)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {}
            
            for i, (func, args, kwargs) in enumerate(tasks):
                future = executor.submit(func, *args, **kwargs)
                future_to_index[future] = i
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                
                try:
                    result = future.result()
                    results[index] = {
                        "success": True,
                        "data": result
                    }
                    logger.debug(f"✅ Task {index + 1} completed")
                
                except Exception as e:
                    results[index] = {
                        "success": False,
                        "error": str(e)
                    }
                    logger.warning(f"❌ Task {index + 1} failed: {e}")
        
        logger.info(f"✅ All {len(tasks)} tasks completed")
        
        return results
    
    def execute_batch_search(self, search_func, queries):
        """
        Execute multiple searches in parallel
        
        Args:
            search_func: Search function
            queries: List of search queries
            
        Returns:
            Dict mapping queries to results
        """
        logger.info(f"🔍 Batch searching {len(queries)} queries...")
        
        # Build tasks
        tasks = [(search_func, (query,), {}) for query in queries]
        
        # Execute in parallel
        results = self.execute_parallel(tasks)
        
        # Map queries to results
        query_results = {}
        for query, result in zip(queries, results):
            query_results[query] = result
        
        return query_results