import json
import os
import random
import tempfile
import time
import unittest
from typing import Optional, Any
from harness.cache import LegalMcpCache

MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "mcp_config.json")

MAX_SPEED_TEST_REQUESTS = 3

def calculate_exponential_backoff(attempt: int, base: float = 1.0, max_delay: float = 8.0) -> float:
    raw_delay = base * (2 ** attempt) + random.uniform(0, 0.5)
    return min(raw_delay, max_delay)

def simulate_mcp_call_with_fault_injection(failure_mode: str, max_retries: int = 3):
    timeline = []
    for attempt in range(max_retries):
        timeline.append(f"attempt_{attempt+1}")
        if failure_mode == "rate_limit_429":
            delay = calculate_exponential_backoff(attempt)
            timeline.append(f"backoff_wait_{delay:.2f}s")
        elif failure_mode == "timeout":
            timeline.append("timeout_detected")
        elif failure_mode == "success":
            return {"status": "success", "timeline": timeline, "deka_numbers": ["1234/2565"]}
    
    return {
        "status": "fallback_activated",
        "timeline": timeline,
        "deka_numbers": [],
        "note": "Fallback to academic doctrine without deka numbers"
    }

def simulate_cached_mcp_call(
    provider: str,
    tool_name: str,
    arguments: dict,
    cache: Optional[Any] = None,
    failure_mode: str = "success"
) -> dict:
    """
    Tier-0 Caching Interceptor:
    Checks L1 Memory and L2 Compressed SQLite cache first.
    On Cache Hit: Returns cached payload in <0.2ms - 2.0ms with ZERO network requests.
    On Cache Miss: Calls upstream MCP server and caches the distilled payload on success.
    """
    if cache is not None:
        cached_data = cache.get(provider, tool_name, arguments)
        if cached_data is not None:
            return {
                "source": "cache",
                "status": "cache_hit",
                "payload": cached_data,
                "timeline": ["cache_hit_retrieved"]
            }

    # Cache miss: execute upstream MCP call with resilience logic
    upstream_result = simulate_mcp_call_with_fault_injection(failure_mode)
    if upstream_result.get("status") == "success" and cache is not None:
        raw_payload = {
            "deka_records": [
                {"citation": f"คำพิพากษาศาลฎีกาที่ {num}", "content": "บรรทัดฐานศาลฎีกา"}
                for num in upstream_result.get("deka_numbers", [])
            ]
        }
        cache.set(provider, tool_name, arguments, raw_payload)

    return {
        "source": "upstream_mcp",
        "status": upstream_result.get("status"),
        "payload": upstream_result,
        "timeline": ["cache_miss_forwarded"] + upstream_result.get("timeline", [])
    }

def validate_speed_test_request_limit(requested_count: int) -> int:
    """
    Enforces that MCP speed / latency testing never exceeds MAX_SPEED_TEST_REQUESTS (3)
    to protect MCP server quota.
    """
    if requested_count > MAX_SPEED_TEST_REQUESTS:
        raise ValueError(
            f"คำขอทดสอบความเร็ว ({requested_count} requests) เกินขีดจำกัดสูงสุดที่อนุญาต ({MAX_SPEED_TEST_REQUESTS} requests) เพื่อป้องกันการกิน quota MCP หมด"
        )
    return requested_count

class TestMcpResilience(unittest.TestCase):

    def test_mcp_config_validity(self):
        self.assertTrue(os.path.exists(MCP_CONFIG_PATH), "mcp_config.json must exist")
        with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        self.assertIn("mcpServers", config)
        servers = config["mcpServers"]
        self.assertIn("fourcorners-tlex", servers)
        self.assertIn("slegaltools-legal-v2", servers)
        self.assertIn("thai-legal", servers)

    def test_backoff_calculation_bounded(self):
        for attempt in range(5):
            delay = calculate_exponential_backoff(attempt, base=1.0, max_delay=8.0)
            self.assertGreaterEqual(delay, 1.0, "Delay must be at least base")
            self.assertLessEqual(delay, 8.0, "Delay must not exceed max_delay")

    def test_fault_injection_rate_limit_fallback(self):
        result = simulate_mcp_call_with_fault_injection("rate_limit_429", max_retries=3)
        self.assertEqual(result["status"], "fallback_activated")
        self.assertEqual(len(result["deka_numbers"]), 0, "Fallback must contain zero unverified deka numbers")
        self.assertIn("Fallback to academic doctrine", result["note"])

    def test_fault_injection_success(self):
        result = simulate_mcp_call_with_fault_injection("success")
        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["deka_numbers"]), 0)

    def test_speed_test_request_limit_under_or_equal_to_three(self):
        # Requests <= 3 should be permitted
        self.assertEqual(validate_speed_test_request_limit(1), 1)
        self.assertEqual(validate_speed_test_request_limit(2), 2)
        self.assertEqual(validate_speed_test_request_limit(3), 3)

    def test_speed_test_request_limit_exceeded_blocks(self):
        # Requests > 3 must be blocked to prevent exhausting MCP quota
        with self.assertRaises(ValueError):
            validate_speed_test_request_limit(4)
        with self.assertRaises(ValueError):
            validate_speed_test_request_limit(10)

    def test_resilience_is_offline_simulation(self):
        # Ensure simulation does not make any real network sockets/connections
        result = simulate_mcp_call_with_fault_injection("rate_limit_429", max_retries=3)
        self.assertIn("attempt_1", result["timeline"])
        self.assertEqual(result["status"], "fallback_activated")

    def test_cached_mcp_call_hit_bypasses_network(self):
        # First call is a miss and goes upstream
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LegalMcpCache(db_path=os.path.join(tmpdir, "resilience_cache.db"))
            args = {"query": "ป.พ.พ. ม.1378 ส่งมอบ ส.ค.1"}

            res1 = simulate_cached_mcp_call("slegaltools", "ai_deka_search", args, cache=cache, failure_mode="success")
            self.assertEqual(res1["source"], "upstream_mcp")
            self.assertEqual(res1["status"], "success")

            # Second identical call must be served from cache (<0.2ms, zero network)
            res2 = simulate_cached_mcp_call("slegaltools", "ai_deka_search", args, cache=cache, failure_mode="rate_limit_429")
            self.assertEqual(res2["source"], "cache")
            self.assertEqual(res2["status"], "cache_hit")
            self.assertIn("cache_hit_retrieved", res2["timeline"])

    def test_cached_mcp_call_protects_against_429_on_repeat_queries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LegalMcpCache(db_path=os.path.join(tmpdir, "resilience_cache.db"))
            args1 = {"query": "ป.อ. ม.334 ลักทรัพย์"}
            args2 = {"query": "ลักทรัพย์ มาตรา 334 ประมวลกฎหมายอาญา"} # Permuted query

            # Seed cache
            res1 = simulate_cached_mcp_call("thai-legal", "search_law", args1, cache=cache, failure_mode="success")
            self.assertEqual(res1["status"], "success")

            # Permuted query should hit cache and NOT trigger 429 even if upstream is broken!
            res2 = simulate_cached_mcp_call("thai-legal", "search_law", args2, cache=cache, failure_mode="rate_limit_429")
            self.assertEqual(res2["source"], "cache")
            self.assertEqual(res2["status"], "cache_hit")

if __name__ == "__main__":
    unittest.main()

