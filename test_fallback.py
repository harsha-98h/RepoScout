"""
Test fallback manager
"""

from utils.fallback_manager import FallbackManager
import random

# Simulate primary and fallback functions
def primary_search(query):
    """Primary GitHub API (unreliable)"""
    if random.random() < 0.7:  # 70% failure rate
        raise Exception("GitHub API rate limit exceeded")
    return f"Primary result for: {query}"

def fallback_cached_search(query):
    """Fallback: Cached results (50% success)"""
    if random.random() < 0.5:
        raise Exception("No cached results")
    return f"Cached result for: {query}"

def fallback_basic_search(query):
    """Last resort: Basic search (always works)"""
    return f"Basic search result for: {query}"

print("="*60)
print("TESTING FALLBACK MANAGER")
print("="*60)

# Create fallback manager
manager = FallbackManager()

# Register fallback chain
manager.register_fallback(
    "search_github",
    fallback_cached_search,
    "Cached search results"
)

manager.register_fallback(
    "search_github",
    fallback_basic_search,
    "Basic search (always available)"
)

# Test execution
print("\n" + "-"*60)
print("TEST: Search with fallback chain")
print("-"*60)

result = manager.execute_with_fallback(
    "search_github",
    primary_search,
    "AI agents"
)

print(f"\n📊 RESULT:")
print(f"Success: {result['success']}")
print(f"Data: {result.get('data', result.get('error'))}")
print(f"Source: {result.get('source', 'N/A')}")
if 'fallback_used' in result:
    print(f"Fallback used: {result['fallback_used']}")

print("\n" + "="*60)
print("✅ Fallback test complete!")
print("="*60)