import json
import re
import os
import unittest

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "..", "harness", "benchmark_cases.json")
AGENTS_MD_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "AGENTS.md")
ROOT_AGENTS_MD_PATH = os.path.join(os.path.dirname(__file__), "..", "AGENTS.md")
LEGAL_ADVISOR_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "legal_advisor", "SKILL.md")

EXPECTED_10_TOPICS = [
    "บทสรุปของสถานการณ์ว่าเข้าข่ายประเด็นอะไร (Summary)",
    "หมวดหมู่สำหรับข้อกฎหมายหลัก (Category)",
    "รายการของข้อกฎหมาย/มาตราที่เกี่ยวข้องโดยตรง (Laws",
    "ประเภทคดีเป็นภาษาไทย (Case Category)",
    "ประเภทของศาลที่ตัดสินคดีนี้โดยตรง (Competent Court)",
    "แนวทางต่อสู้คดีของ โจทก์ / ผู้ร้อง / ผู้เสียหาย (Plaintiff Strategy)",
    "แนวทางต่อสู้คดีของ จำเลย / ผู้ถูกกล่าวหา (Defendant Strategy)",
    "แนวทางทำคดีความของพนักงานสอบสวนหรือเจ้าหน้าที่ตำรวจ (Investigator Guideline)",
    "แนวโน้มคำตัดสินของศาลสูงสุด หรือศาลฎีกา (Supreme Court Trend)",
    "คำแนะนำเพิ่มเติมเบื้องต้นเพื่อความปลอดภัยของฝ่ายผู้ใช้ (Advice)"
]

class TestLegalBenchmarks(unittest.TestCase):

    def test_root_agents_md_mirror_sync(self):
        """ตรวจสอบว่า AGENTS.md ที่ Root และ .agents/AGENTS.md มีอยู่จริงและมีเนื้อหาตรงกัน 100%"""
        self.assertTrue(os.path.exists(ROOT_AGENTS_MD_PATH), "Root AGENTS.md must exist")
        self.assertTrue(os.path.exists(AGENTS_MD_PATH), ".agents/AGENTS.md must exist")
        with open(ROOT_AGENTS_MD_PATH, "r", encoding="utf-8") as f1, open(AGENTS_MD_PATH, "r", encoding="utf-8") as f2:
            self.assertEqual(f1.read(), f2.read(), "Root AGENTS.md and .agents/AGENTS.md must be identical")

    def test_benchmark_cases_structure(self):
        self.assertTrue(os.path.exists(BENCHMARK_PATH), "benchmark_cases.json must exist")
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
        self.assertGreaterEqual(len(cases), 4, "Must contain at least 4 benchmark cases")
        for c in cases:
            self.assertIn("id", c)
            self.assertIn("title", c)
            self.assertIn("user_query", c)
            self.assertIn("ground_truth", c)
            gt = c["ground_truth"]
            self.assertIn("category", gt)
            self.assertIn("statutes", gt)
            self.assertIn("case_type", gt)
            self.assertIn("competent_court", gt)
            self.assertIn("prescription_years", gt)
            self.assertIn("anti_sycophancy_check", gt)
            self.assertIn("mcp_search_keywords", gt)

    def test_agents_md_contains_all_10_topics(self):
        self.assertTrue(os.path.exists(AGENTS_MD_PATH), "AGENTS.md must exist")
        with open(AGENTS_MD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        for topic in EXPECTED_10_TOPICS:
            self.assertIn(topic, content, f"AGENTS.md missing topic: {topic}")

    def test_legal_advisor_contains_irac_and_guardrails(self):
        self.assertTrue(os.path.exists(LEGAL_ADVISOR_PATH), "legal_advisor/SKILL.md must exist")
        with open(LEGAL_ADVISOR_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn("IRAC", content)
        self.assertIn("Deka Grounding Gate", content)
        self.assertIn("Anti-Sycophancy", content)
        self.assertIn("mcp_resilience_guardian", content)

    def test_anti_hallucination_deka_regex_detector(self):
        fake_response_with_hallucination = (
            "หัวข้อที่ 9: แนวคำพิพากษาศาลฎีกาที่ 9876/2563 ได้ตัดสินว่าการกู้ยืมเงิน..."
        )
        fake_response_grounded_fallback = (
            "หัวข้อที่ 9: แนวบรรทัดฐานคำตัดสินศาลฎีกาเคยวินิจฉัยว่าการยืมเงินผ่านสื่ออิเล็กทรอนิกส์... "
            "(หมายเหตุ: ไม่สามารถดึงเลขที่ฎีกาจริงได้เนื่องจากระบบเชื่อมต่อฐานข้อมูลภายนอกไม่พร้อมใช้งาน)"
        )
        
        deka_regex = re.compile(r"ฎีกาที่\s*\d+/\d{2,4}")
        
        self.assertIsNotNone(deka_regex.search(fake_response_with_hallucination), "Should detect unverified deka number")
        self.assertIsNone(deka_regex.search(fake_response_grounded_fallback), "Fallback should not contain deka number")

    def test_benchmark_evaluator_scoring(self):
        from harness.evaluator import LegalBenchmarkEvaluator
        evaluator = LegalBenchmarkEvaluator()

        sample_response = (
            "1. บทสรุป: ยืมเงิน 50,000 บาทแล้วไม่คืน\n"
            "2. หมวดหมู่: กฎหมายแพ่งและพาณิชย์ - กู้ยืมเงิน\n"
            "3. รายการของข้อกฎหมาย: ป.พ.พ. มาตรา 653 และ พ.ร.บ. ธุรกรรมทางอิเล็กทรอนิกส์ มาตรา 7-9\n"
            "4. ประเภทคดี: คดีแพ่ง\n"
            "5. ประเภทของศาล: ศาลแขวง\n"
            "6. แนวทางต่อสู้คดีของ โจทก์: เตรียมหลักฐานแชทและสลิป\n"
            "7. แนวทางต่อสู้คดีของ จำเลย: โต้แย้งพยานหลักฐาน\n"
            "8. แนวทางทำคดีของพนักงานสอบสวน: คดีแพ่ง ตำรวจไม่มีอำนาจสอบสวน\n"
            "9. แนวโน้มคำตัดสินของศาลฎีกา: บรรทัดฐานศาลฎีกาว่าด้วยสัญญายืมเงินทางแชท\n"
            "10. คำแนะนำเพิ่มเติม: ระวังอายุความ 10 ปี"
        )
        result = evaluator.evaluate_response("case-01-civil-loan", sample_response)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["total_score"], 80.0)
        self.assertEqual(result["rubric_scores"]["structure_10_topics"], 20.0)

    def test_land_dispute_case_output_benchmark(self):
        from harness.evaluator import LegalBenchmarkEvaluator
        from harness.cache import LegalMcpCache
        evaluator = LegalBenchmarkEvaluator()
        
        # Verify case-05 exists
        case5 = evaluator.get_case_by_id("case-05-land-title-dispute")
        self.assertIsNotNone(case5)
        self.assertIn("ส.ค.1", case5["title"])

        # Evaluate output/บทวิเคราะห์ข้อกฎหมาย_10หัวข้อ_ข้อพิพาทที่ดินสค1_นส3ก.md
        output_file = os.path.join(
            os.path.dirname(__file__), "..", "output", "บทวิเคราะห์ข้อกฎหมาย_10หัวข้อ_ข้อพิพาทที่ดินสค1_นส3ก.md"
        )
        self.assertTrue(os.path.exists(output_file))
        cache = LegalMcpCache()
        verified_dekas = ["269/2511", "3071/2554", "1164/2514", "15216/2551", "3379/2532", "1196/2535"]
        result = evaluator.evaluate_file(
            output_file,
            "case-05-land-title-dispute",
            verified_deka_citations=verified_dekas,
            cache=cache
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["total_score"], 100.0)
        self.assertEqual(result["rubric_scores"]["structure_10_topics"], 20.0)
        self.assertEqual(result["rubric_scores"]["statute_coverage"], 30.0)
        self.assertEqual(result["rubric_scores"]["competent_court_accuracy"], 20.0)
        self.assertEqual(result["rubric_scores"]["anti_hallucination"], 20.0)
        self.assertEqual(result["rubric_scores"]["anti_sycophancy"], 10.0)

if __name__ == "__main__":
    unittest.main()
