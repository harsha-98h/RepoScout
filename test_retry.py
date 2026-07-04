"""
Retry Manager for ReAct Agent
"""

import time
import random
from utils.logger import setup_logger
from utils.error_handler import ErrorDetector

logger = setup_logger(__name__)

class RetryManager:
    """
    Manages retry logic with exponential backoff
    """
    
    def __init__(self, max_retries=3, base_delay=1, max_delay=60):
        """
        Initialize retry manager
        
        Args:
            max_retries: Maximum retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.detector = ErrorDetector()
    
    def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises exception
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{self.max_retries}")
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success!
                if attempt > 0:
                    logger.info(f"✅ Success on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_error = e
                
                # Classify error
                error_info = self.detector.classify_network_error(e)
                
                logger.warning(f"⚠️  {error_info.get('message', str(e))}")
                
                # Should we retry?
                if not error_info.get("retry", False):
                    logger.error("❌ Non-retryable error. Stopping.")
                    raise
                
                # Last attempt?
                if attempt == self.max_retries - 1:
                    logger.error(f"❌ Max retries ({self.max_retries}) reached")
                    raise
                
                # Calculate wait time
                wait_time = self._calculate_backoff(attempt)
                logger.info(f"⏳ Waiting {wait_time:.2f}s before retry...")
                time.sleep(wait_time)
        
        # Should never reach here
        raise last_error
    
    def _calculate_backoff(self, attempt):
        """
        Calculate backoff time with jitter
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Wait time in seconds
        """
        # Exponential backoff
        exponential = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        # Add jitter (0-50%)
        jitter = random.uniform(0, exponential * 0.5)
        
        return exponential + jitter