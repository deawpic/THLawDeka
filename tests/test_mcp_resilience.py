import json
import os
import random
import time
import unittest

MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "mcp_config.json")

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

if __name__ == "__main__":
    unittest.main()
