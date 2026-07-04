"""
Test performance monitoring
"""

from utils.performance_monitor import PerformanceMonitor
import time

monitor = PerformanceMonitor()

print("="*60)
print("TESTING PERFORMANCE MONITOR")
print("="*60)

# Simulate some operations
@monitor.track_llm_call
def simulate_llm_call():
    time.sleep(0.5)  # Simulate LLM delay
    return "LLM response"

@monitor.track_tool_call
def simulate_tool_call():
    time.sleep(0.2)  # Simulate tool delay
    return "Tool result"

@monitor.track_query
def simulate_query():
    # Simulate a query with LLM and tool calls
    simulate_llm_call()
    simulate_tool_call()
    simulate_llm_call()
    return "Query result"

# Run simulations
print("\n🔄 Simulating 3 queries...\n")

for i in range(3):
    print(f"Query {i+1}:")
    simulate_query()
    print()

# Show stats
monitor.print_stats()

print("\n✅ Performance monitoring test complete!")
print("="*60)