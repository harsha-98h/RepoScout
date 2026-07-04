"""
Performance monitoring for ReAct agents
"""

import time
from functools import wraps
from utils.logger import setup_logger

logger = setup_logger(__name__)

class PerformanceMonitor:
    """
    Monitor and track agent performance
    """
    
    def __init__(self):
        self.metrics = {
            "llm_calls": 0,
            "llm_total_time": 0,
            "tool_calls": 0,
            "tool_total_time": 0,
            "total_queries": 0,
            "total_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def track_llm_call(self, func):
        """Decorator to track LLM calls"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            self.metrics["llm_calls"] += 1
            self.metrics["llm_total_time"] += duration
            
            logger.debug(f"⚡ LLM call: {duration:.2f}s")
            
            return result
        return wrapper
    
    def track_tool_call(self, func):
        """Decorator to track tool calls"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            self.metrics["tool_calls"] += 1
            self.metrics["tool_total_time"] += duration
            
            logger.debug(f"🔧 Tool call: {duration:.2f}s")
            
            return result
        return wrapper
    
    def track_query(self, func):
        """Decorator to track entire query"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            self.metrics["total_queries"] += 1
            self.metrics["total_time"] += duration
            
            logger.info(f"⏱️  Query completed in {duration:.2f}s")
            
            return result
        return wrapper
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1
    
    def get_stats(self):
        """Get performance statistics"""
        stats = self.metrics.copy()
        
        # Calculate averages
        if stats["llm_calls"] > 0:
            stats["avg_llm_time"] = stats["llm_total_time"] / stats["llm_calls"]
        else:
            stats["avg_llm_time"] = 0
        
        if stats["tool_calls"] > 0:
            stats["avg_tool_time"] = stats["tool_total_time"] / stats["tool_calls"]
        else:
            stats["avg_tool_time"] = 0
        
        if stats["total_queries"] > 0:
            stats["avg_query_time"] = stats["total_time"] / stats["total_queries"]
        else:
            stats["avg_query_time"] = 0
        
        # Calculate cache hit rate
        total_cache_attempts = stats["cache_hits"] + stats["cache_misses"]
        if total_cache_attempts > 0:
            stats["cache_hit_rate"] = (stats["cache_hits"] / total_cache_attempts) * 100
        else:
            stats["cache_hit_rate"] = 0
        
        return stats
    
    def print_stats(self):
        """Print performance statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("📊 PERFORMANCE STATISTICS")
        print("="*60)
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Total Time: {stats['total_time']:.2f}s")
        print(f"Avg Query Time: {stats['avg_query_time']:.2f}s")
        print()
        print(f"LLM Calls: {stats['llm_calls']}")
        print(f"LLM Total Time: {stats['llm_total_time']:.2f}s")
        print(f"Avg LLM Time: {stats['avg_llm_time']:.2f}s")
        print()
        print(f"Tool Calls: {stats['tool_calls']}")
        print(f"Tool Total Time: {stats['tool_total_time']:.2f}s")
        print(f"Avg Tool Time: {stats['avg_tool_time']:.2f}s")
        print()
        print(f"Cache Hits: {stats['cache_hits']}")
        print(f"Cache Misses: {stats['cache_misses']}")
        print(f"Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
        print("="*60)
    
    def reset(self):
        """Reset all metrics"""
        for key in self.metrics:
            self.metrics[key] = 0