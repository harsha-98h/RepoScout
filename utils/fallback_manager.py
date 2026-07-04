"""
Fallback Manager for ReAct Agent
"""

from utils.logger import setup_logger
from utils.retry_manager import RetryManager

logger = setup_logger(__name__)

class FallbackManager:
    """
    Manages fallback strategies when primary tools fail
    """
    
    def __init__(self):
        self.fallback_chain = {}
        self.retry_manager = RetryManager(max_retries=2, base_delay=1)
    
    def register_fallback(self, primary_tool, fallback_tool, description=""):
        """
        Register a fallback tool for a primary tool
        
        Args:
            primary_tool: Name of primary tool
            fallback_tool: Fallback function/tool
            description: Description of fallback
        """
        if primary_tool not in self.fallback_chain:
            self.fallback_chain[primary_tool] = []
        
        self.fallback_chain[primary_tool].append({
            "tool": fallback_tool,
            "description": description
        })
        
        logger.info(f"🔄 Registered fallback for '{primary_tool}': {description}")
    
    def execute_with_fallback(self, primary_tool_name, primary_func, *args, **kwargs):
        """
        Execute primary tool with fallback chain
        
        Args:
            primary_tool_name: Name of primary tool
            primary_func: Primary function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result from primary or fallback tool
        """
        logger.info(f"🎯 Executing: {primary_tool_name}")
        
        # Try primary tool with retry
        try:
            result = self.retry_manager.execute_with_retry(
                primary_func, *args, **kwargs
            )
            logger.info(f"✅ Primary tool succeeded")
            return {
                "success": True,
                "data": result,
                "source": "primary"
            }
        
        except Exception as primary_error:
            logger.warning(f"⚠️  Primary tool failed: {primary_error}")
            
            # Try fallback chain
            if primary_tool_name in self.fallback_chain:
                fallbacks = self.fallback_chain[primary_tool_name]
                
                for i, fallback_info in enumerate(fallbacks):
                    fallback_func = fallback_info["tool"]
                    fallback_desc = fallback_info["description"]
                    
                    logger.info(f"🔄 Trying fallback {i+1}/{len(fallbacks)}: {fallback_desc}")
                    
                    try:
                        result = fallback_func(*args, **kwargs)
                        logger.info(f"✅ Fallback succeeded!")
                        
                        return {
                            "success": True,
                            "data": result,
                            "source": "fallback",
                            "fallback_used": fallback_desc
                        }
                    
                    except Exception as fallback_error:
                        logger.warning(f"⚠️  Fallback {i+1} failed: {fallback_error}")
                        continue
            
            # All fallbacks failed
            logger.error(f"❌ All attempts failed for {primary_tool_name}")
            
            return {
                "success": False,
                "error": str(primary_error),
                "message": self._get_user_friendly_message(primary_tool_name)
            }
    
    def _get_user_friendly_message(self, tool_name):
        """
        Get user-friendly error message
        
        Args:
            tool_name: Name of the tool that failed
            
        Returns:
            User-friendly message
        """
        messages = {
            "search_github": "Unable to search GitHub at the moment. This could be due to rate limits or connectivity issues. Please try again in a few minutes or use a GitHub token for higher rate limits.",
            "get_repo_details": "Unable to fetch repository details. The repository might not exist or GitHub API is temporarily unavailable.",
        }
        
        return messages.get(
            tool_name,
            f"The {tool_name} service is temporarily unavailable. Please try again later."
        )