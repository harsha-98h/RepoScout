"""
Optimized prompts for better performance
"""

# FASTER: One-shot prompt (tries to get everything in one go)
REPOSCOUT_ONESHOT_PROMPT = """You are RepoScout, a GitHub repository discovery agent.

You have access to: search_github, get_repo_details

USER REQUEST: {question}

Analyze the request and decide:
1. If you need to search GitHub, what's the best search query?
2. How many results do you need?
3. Any filtering criteria?

Then execute and provide final answer in ONE iteration if possible.

Format:
THOUGHT: [Your analysis]
ACTION: [tool: query]
OBSERVATION: [Will be provided]
THOUGHT: [Analysis of results]
FINAL ANSWER: [Your response]

Be efficient - try to complete in 1-2 iterations maximum.
"""

# FASTER: Pre-categorized queries
QUERY_TEMPLATES = {
    "ai_agents": {
        "search_query": "AI agents framework stars:>1000",
        "expected_results": 5,
        "description": "Popular AI agent frameworks"
    },
    "machine_learning": {
        "search_query": "machine learning Python stars:>5000",
        "expected_results": 5,
        "description": "Top ML libraries"
    },
    "web_frameworks": {
        "search_query": "web framework stars:>10000",
        "expected_results": 5,
        "description": "Popular web frameworks"
    },
    "data_visualization": {
        "search_query": "data visualization Python stars:>1000",
        "expected_results": 5,
        "description": "Data viz libraries"
    }
}

def get_optimized_query(user_query):
    """
    Get optimized search query based on user input
    
    Args:
        user_query: User's question
        
    Returns:
        Optimized query or None
    """
    query_lower = user_query.lower()
    
    # Check for known patterns
    if "ai agent" in query_lower or "autonomous agent" in query_lower:
        return QUERY_TEMPLATES["ai_agents"]
    
    elif "machine learning" in query_lower or "ml" in query_lower:
        return QUERY_TEMPLATES["machine_learning"]
    
    elif "web framework" in query_lower or "web dev" in query_lower:
        return QUERY_TEMPLATES["web_frameworks"]
    
    elif "data viz" in query_lower or "visualization" in query_lower:
        return QUERY_TEMPLATES["data_visualization"]
    
    return None