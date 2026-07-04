"""
Test parallel execution
"""

from utils.parallel_executor import ParallelExecutor
import time

def slow_task(task_id, duration=1):
    """Simulate a slow task"""
    print(f"  Task {task_id} starting...")
    time.sleep(duration)
    print(f"  Task {task_id} done!")
    return f"Result from task {task_id}"

print("="*60)
print("TESTING PARALLEL EXECUTION")
print("="*60)

executor = ParallelExecutor(max_workers=3)

# Test 1: Sequential vs Parallel
print("\n--- Test 1: Speed Comparison ---")

# Sequential
print("\n🐌 Sequential execution (3 tasks × 1s each):")
start = time.time()
for i in range(3):
    slow_task(i + 1)
sequential_time = time.time() - start
print(f"Sequential time: {sequential_time:.2f}s")

# Parallel
print("\n⚡ Parallel execution (3 tasks × 1s each):")
tasks = [(slow_task, (i + 1,), {}) for i in range(3)]
start = time.time()
results = executor.execute_parallel(tasks)
parallel_time = time.time() - start
print(f"Parallel time: {parallel_time:.2f}s")

print(f"\n🚀 Speedup: {sequential_time / parallel_time:.1f}x faster!")

# Test 2: Batch search simulation
print("\n--- Test 2: Batch Search ---")

def mock_search(query):
    """Mock search function"""
    time.sleep(0.5)
    return f"Results for: {query}"

queries = ["AI agents", "machine learning", "web frameworks"]

start = time.time()
results = executor.execute_batch_search(mock_search, queries)
duration = time.time() - start

print(f"Searched {len(queries)} queries in {duration:.2f}s")
for query, result in results.items():
    if result["success"]:
        print(f"  ✅ {query}: {result['data']}")

print("\n✅ Parallel execution test complete!")
print("="*60)