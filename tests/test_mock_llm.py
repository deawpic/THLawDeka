#!/usr/bin/env python3
"""
Unit & Integration Tests for Mock / Synthetic LLM Pipeline
ทดสอบการจำลองคำตอบบทวิเคราะห์กฎหมายและการประเมินผล End-to-End โดยไม่ต้องต่อเน็ต
"""

import os
import unittest
from harness.mock_llm import (
    MockLegalLLMClient,
    SyntheticResponseMode,
    run_synthetic_benchmark_suite
)
from harness.evaluator import LegalBenchmarkEvaluator
from harness.cache import LegalMcpCache

class TestMockLLMPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.evaluator = LegalBenchmarkEvaluator()
        cls.cache = LegalMcpCache()
        cls.client = MockLegalLLMClient()

    def test_mock_client_has_all_ten_cases(self):
        """ตรวจสอบว่า Mock Client รู้จักคดีทดสอบครบทั้ง 10 คดี"""
        self.assertEqual(len(self.client.cases), 10)
        case_ids = [c["id"] for c in self.client.cases]
        self.assertIn("case-01-civil-loan", case_ids)
        self.assertIn("case-08-administrative-unlawful-order", case_ids)
        self.assertIn("case-09-pdpa-unauthorized-disclosure", case_ids)
        self.assertIn("case-10-ip-trademark-infringement", case_ids)

    def test_ideal_generation_scores_100_percent(self):
        """ทดสอบว่าการจำลองคำตอบแบบ Ideal ได้คะแนนเต็ม 100 และผ่านการประเมินทุกคดี"""
        for case in self.client.cases:
            case_id = case["id"]
            resp = self.client.generate_response(case, mode=SyntheticResponseMode.IDEAL)
            res = self.evaluator.evaluate_response(case_id, resp, cache=self.cache)
            self.assertTrue(res["passed"], f"Case {case_id} failed in IDEAL mode")
            self.assertEqual(res["total_score"], 100.0, f"Case {case_id} did not score 100.0")
            self.assertEqual(res["rubric_scores"]["structure_10_topics"], 20.0)
            self.assertEqual(res["rubric_scores"]["statute_coverage"], 30.0)
            self.assertEqual(res["rubric_scores"]["competent_court_accuracy"], 20.0)
            self.assertEqual(res["rubric_scores"]["anti_hallucination"], 20.0)
            self.assertEqual(res["rubric_scores"]["anti_sycophancy"], 10.0)

    def test_hallucination_gate_triggers_on_fake_deka(self):
        """ทดสอบว่าเมื่อ LLM แต่งเลขฎีกาปลอม ระบบตรวจจับได้และตัดคะแนน Anti-Hallucination เหลือ 0"""
        case_id = "case-01-civil-loan"
        resp = self.client.generate_response(case_id, mode=SyntheticResponseMode.HALLUCINATED)
        res = self.evaluator.evaluate_response(case_id, resp, verified_deka_citations=[], cache=None)
        
        self.assertEqual(res["rubric_scores"]["anti_hallucination"], 0.0)
        self.assertFalse(res["passed"])
        self.assertTrue(any("Deka Grounding Gate" in f for f in res["findings"]))

    def test_sycophancy_gate_triggers_on_absolute_guarantee(self):
        """ทดสอบว่าเมื่อ LLM การันตีผลชนะ 100% ระบบตรวจจับได้และตัดคะแนน Anti-Sycophancy เหลือ 0"""
        case_id = "case-02-criminal-theft"
        resp = self.client.generate_response(case_id, mode=SyntheticResponseMode.SYCOPHANTIC)
        res = self.evaluator.evaluate_response(case_id, resp, cache=None)
        
        self.assertEqual(res["rubric_scores"]["anti_sycophancy"], 0.0)
        self.assertFalse(res["passed"])
        self.assertTrue(any("Judicial Discretion Gate" in f for f in res["findings"]))

    def test_incomplete_structure_triggers_penalty(self):
        """ทดสอบว่าเมื่อคำตอบขาดหัวข้อสำคัญ โครงสร้าง 10 หัวข้อจะถูกหักคะแนนตามสัดส่วน"""
        case_id = "case-03-labor-severance"
        resp = self.client.generate_response(case_id, mode=SyntheticResponseMode.INCOMPLETE_STRUCTURE)
        res = self.evaluator.evaluate_response(case_id, resp, cache=None)
        
        self.assertLess(res["rubric_scores"]["structure_10_topics"], 20.0)
        self.assertTrue(any("Missing" in f for f in res["findings"]))

    def test_wrong_court_triggers_accuracy_penalty(self):
        """ทดสอบว่าเมื่อระบุศาลผิดเขตอำนาจ คะแนนความถูกต้องของศาลจะถูกตัดเหลือ 0"""
        case_id = "case-04-tort-accident"
        resp = self.client.generate_response(case_id, mode=SyntheticResponseMode.WRONG_COURT)
        res = self.evaluator.evaluate_response(case_id, resp, cache=None)
        
        self.assertEqual(res["rubric_scores"]["competent_court_accuracy"], 0.0)

    def test_full_synthetic_suite_runner(self):
        """ทดสอบการรันชุดประเมิน Synthetic Benchmark ครบทุกเคสและทุกโหมด"""
        suite_res = run_synthetic_benchmark_suite(evaluator=self.evaluator, cache=self.cache)
        summ = suite_res["summary"]
        self.assertEqual(summ["ideal_passed"], 10)
        self.assertEqual(summ["ideal_total"], 10)
        self.assertEqual(summ["adversarial_blocked"], 6)
        self.assertEqual(summ["adversarial_total"], 6)

if __name__ == "__main__":
    unittest.main()
