"""
Test cache manager
"""

from utils.cache_manager import CacheManager
import time

cache = CacheManager(ttl_seconds=2)  # 2 second TTL for testing

print("="*60)
print("TESTING CACHE MANAGER")
print("="*60)

# Test 1: Basic cache operations
print("\n--- Test 1: Basic Operations ---")
cache.set("key1", "value1")
result = cache.get("key1")
print(f"Set and Get: {result}")  # Should be "value1"

# Test 2: Cache miss
print("\n--- Test 2: Cache Miss ---")
result = cache.get("nonexistent_key")
print(f"Non-existent key: {result}")  # Should be None

# Test 3: Cache expiration
print("\n--- Test 3: Expiration ---")
cache.set("temp_key", "temp_value")
print(f"Immediately after set: {cache.get('temp_key')}")  # Should work
print("Waiting 3 seconds for expiration...")
time.sleep(3)
print(f"After expiration: {cache.get('temp_key')}")  # Should be None

# Test 4: Complex data
print("\n--- Test 4: Complex Data ---")
data = {"repos": ["langchain", "autogpt"], "count": 2}
cache.set("search:ai", data)
cached = cache.get("search:ai")
print(f"Cached complex data: {cached}")

# Test 5: Multiple hits
print("\n--- Test 5: Multiple Hits ---")
cache.set("popular", "value")
for i in range(5):
    cache.get("popular")  # 5 hits

# Show statistics
cache.print_stats()

print("\n✅ Cache test complete!")
print("="*60)