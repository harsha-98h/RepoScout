"""
Enhanced GitHub Search Tool with Error Handling
"""

import requests
import config
from utils.logger import setup_logger
from utils.error_handler import ErrorDetector
from utils.retry_manager import RetryManager

logger = setup_logger(__name__)

class GitHubSearchTool:
    """
    Search GitHub repositories with robust error handling
    """
    
    def __init__(self):
        self.base_url = config.GITHUB_API_BASE
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if config.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {config.GITHUB_TOKEN}"
        
        self.detector = ErrorDetector()
        self.retry_manager = RetryManager(max_retries=3, base_delay=1, max_delay=30)
        
        # Simple cache for fallback
        self.cache = {}
    
    def search_repositories(self, query, max_results=5):
        """
        Search GitHub repositories with error handling
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of repositories or error dict
        """
        logger.info(f"🔍 Searching GitHub for: {query}")
        
        # Try with retry
        try:
            result = self.retry_manager.execute_with_retry(
                self._search_api,
                query,
                max_results
            )
            
            # Cache successful result
            self.cache[query] = result
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Search failed after retries: {e}")
            
            # Try cache as fallback
            if query in self.cache:
                logger.info(f"✅ Returning cached result for: {query}")
                return self.cache[query]
            
            # Return empty with error info
            return {
                "error": True,
                "message": "GitHub search unavailable. Please try again later or add a GitHub token to increase rate limits.",
                "repositories": []
            }
    
    def _search_api(self, query, max_results):
        """
        Internal API call (can raise exceptions)
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of repositories
        """
        url = f"{self.base_url}/search/repositories"
        
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results
        }
        
        # Make request with timeout
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )
        
        # Check for errors
        error_info = self.detector.classify_api_error(response)
        
        if error_info["is_error"]:
            error_message = self.detector.get_user_message(error_info)
            
            # Raise appropriate exception
            if error_info.get("type") == "RATE_LIMIT":
                raise Exception(f"Rate Limit: {error_message}")
            else:
                raise Exception(error_message)
        
        # Parse response
        data = response.json()
        
        repositories = []
        for item in data.get("items", [])[:max_results]:
            repo = {
                "name": item.get("full_name"),
                "description": item.get("description", "No description"),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "language": item.get("language", "Unknown"),
                "url": item.get("html_url"),
                "topics": item.get("topics", []),
                "last_updated": item.get("updated_at", "Unknown"),
                "license": item.get("license", {}).get("name", "No license") if item.get("license") else "No license"
            }
            repositories.append(repo)
        
        logger.info(f"✅ Found {len(repositories)} repositories")
        
        return repositories
    
    def get_repository_details(self, repo_name):
        """
        Get repository details with error handling
        
        Args:
            repo_name: Repository name (owner/repo)
            
        Returns:
            Repository details or error dict
        """
        logger.info(f"📊 Getting details for: {repo_name}")
        
        try:
            result = self.retry_manager.execute_with_retry(
                self._get_details_api,
                repo_name
            )
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to get details: {e}")
            
            return {
                "error": True,
                "message": f"Unable to fetch details for {repo_name}. Repository might not exist or API is unavailable."
            }
    
    def _get_details_api(self, repo_name):
        """Internal API call for repository details"""
        url = f"{self.base_url}/repos/{repo_name}"
        
        response = requests.get(
            url,
            headers=self.headers,
            timeout=10
        )
        
        # Check for errors
        error_info = self.detector.classify_api_error(response)
        
        if error_info["is_error"]:
            raise Exception(self.detector.get_user_message(error_info))
        
        data = response.json()
        
        return {
            "name": data.get("full_name"),
            "description": data.get("description", "No description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language", "Unknown"),
            "license": data.get("license", {}).get("name", "No license") if data.get("license") else "No license",
            "topics": data.get("topics", []),
            "created_at": data.get("created_at", "Unknown"),
            "updated_at": data.get("updated_at", "Unknown"),
            "url": data.get("html_url")
        }