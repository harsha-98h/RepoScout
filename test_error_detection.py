"""
Test error detection
"""

from utils.error_handler import ErrorDetector
import requests

detector = ErrorDetector()

print("="*60)
print("TESTING ERROR DETECTION")
print("="*60)

# Test 1: Simulated 403 rate limit
print("\nTest 1: Rate Limit Error")
class MockResponse:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}

rate_limit_response = MockResponse(403, {"X-RateLimit-Remaining": "0"})
error = detector.classify_api_error(rate_limit_response)
print(f"Classification: {error}")
print(f"Should retry: {detector.should_retry(error)}")
print(f"Wait time: {detector.get_wait_time(error)}s")
print(f"Message: {detector.get_user_message(error)}")

# Test 2: 500 server error
print("\n" + "-"*60)
print("Test 2: Server Error")
server_error_response = MockResponse(500)
error = detector.classify_api_error(server_error_response)
print(f"Classification: {error}")
print(f"Should retry: {detector.should_retry(error)}")

# Test 3: Network timeout
print("\n" + "-"*60)
print("Test 3: Network Timeout")
timeout_error = requests.exceptions.Timeout("Connection timeout")
error = detector.classify_network_error(timeout_error)
print(f"Classification: {error}")
print(f"Should retry: {detector.should_retry(error)}")
print(f"Max retries: {error.get('max_retries')}")

print("\n" + "="*60)
print("✅ Error detection tests complete!")
print("="*60)